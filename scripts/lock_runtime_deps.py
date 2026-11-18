#!/usr/bin/env python
"""Lock the Runtime bundle's Python packages, so that a deploy builds what was evaluated.

The AgentCore CLI builds the agent's zip with `uv pip install -r app/<runtime>/pyproject.toml --target ...` and reads
nothing but `[project].dependencies` (no lock file, no constraints). With ranges there, every deploy resolves again:
on 2026-11-17 a deploy that changed nothing in the agent cut Runtime v18 because boto3 had a new patch release. So
the exact version of every package of the bundle is written into `[project].dependencies`, between two marker
lines, below the direct requirements. The direct requirements say what the agent needs; the locked block says what
is built.

    uv run scripts/lock_runtime_deps.py                        # check: the resolver gives exactly the locked set
    uv run scripts/lock_runtime_deps.py --runtime-version 17   # lock what that deployed version carries
    uv run scripts/lock_runtime_deps.py --from-zip bundle.zip  # the same, from a bundle already downloaded
    uv run scripts/lock_runtime_deps.py --from-staging         # lock what the last local build carried
    uv run scripts/lock_runtime_deps.py --upgrade              # resolve the direct requirements afresh and lock that
    uv run scripts/lock_runtime_deps.py --outdated             # report only: what an upgrade would change, and the
                                                               # advisories published for the locked versions

An upgrade is a change to the agent: review the diff, deploy, evaluate, and only then move `demo`.

A lock also stops security fixes from arriving by themselves, so `--outdated` is the look that has to be taken on a
schedule (operations doc, section 5). It writes nothing. It exits 2 when a locked version has a published advisory,
so a scheduled job can tell. The advisories come from OSV (osv.dev), the open database behind `pip-audit` for PyPI.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = "surv_investigator_l1"
PYPROJECT = ROOT / "app" / RUNTIME / "pyproject.toml"
STAGING = ROOT / "agentcore" / ".cache" / RUNTIME / "staging"
BEGIN = "    # --- locked: every package of the bundle, exact. Written by scripts/lock_runtime_deps.py, not by hand."
END = "    # --- end locked ---"
PYTHON_VERSION = "3.14"
# The packager's own order (`@aws/agentcore-cdk`, packaging/python.js): the first platform that resolves is used.
PLATFORMS = ("aarch64-manylinux2014", "aarch64-manylinux_2_28", "aarch64-manylinux_2_34")


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _from_metadata(text: str) -> tuple[str, str]:
    name = re.search(r"^Name: (.+)$", text, re.M)
    version = re.search(r"^Version: (.+)$", text, re.M)
    if not name or not version:
        raise SystemExit("a dist-info METADATA file has no Name or Version")
    return norm(name.group(1).strip()), version.group(1).strip()


def from_zip(path: Path) -> dict[str, str]:
    with zipfile.ZipFile(path) as z:
        metas = [n for n in z.namelist() if re.fullmatch(r"[^/]+\.dist-info/METADATA", n)]
        return dict(_from_metadata(z.read(n).decode("utf-8", "replace")) for n in metas)


def from_staging(path: Path = STAGING) -> dict[str, str]:
    return dict(_from_metadata(p.read_text(errors="replace")) for p in sorted(path.glob("*.dist-info/METADATA")))


def from_runtime_version(version: int) -> tuple[dict[str, str], str]:
    import boto3

    sys.path.insert(0, str(ROOT / "scripts"))
    from smoke_gateway import CREDS, load_env

    runtime_id = load_env(CREDS)["SURV_RUNTIME_ARN"].rsplit("/", 1)[-1]
    region = "eu-west-2"
    got = boto3.client("bedrock-agentcore-control", region_name=region).get_agent_runtime(
        agentRuntimeId=runtime_id, agentRuntimeVersion=str(version)
    )
    s3 = got["agentRuntimeArtifact"]["codeConfiguration"]["code"]["s3"]
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "bundle.zip"
        boto3.client("s3", region_name=region).download_file(s3["bucket"], s3["prefix"], str(target))
        return from_zip(target), f"Runtime v{version} (bundle {s3['prefix'][:12]})"


def read_pyproject() -> tuple[str, list[str], dict[str, str]]:
    """The file's text, the direct requirements (above the marker) and the locked set (between the markers)."""
    text = PYPROJECT.read_text()
    body = text[text.index("dependencies = [") : text.index("\n]", text.index("dependencies = ["))]
    head, _, rest = body.partition(BEGIN)
    direct = re.findall(r'^\s*"([^"]+)",', head, re.M)
    locked = dict(m.groups() for m in re.finditer(r'^\s*"([A-Za-z0-9._-]+)==([^"]+)",', rest, re.M))
    return text, direct, {norm(k): v for k, v in locked.items()}


def write_lock(pins: dict[str, str], source: str) -> None:
    text, direct, _ = read_pyproject()
    start = text.index("dependencies = [")
    end = text.index("\n]", start)
    lines = ["dependencies = ["]
    lines += [
        "    # Direct: what the agent imports. The ranges say what is acceptable.",
        *[f'    "{d}",' for d in direct],
        BEGIN,
        f"    # {len(pins)} packages, from {source}.",
        *[f'    "{name}=={version}",' for name, version in sorted(pins.items())],
        END,
    ]
    PYPROJECT.write_text(text[:start] + "\n".join(lines) + text[end:])


def resolve(requirements: Path) -> dict[str, str]:
    """What the packager's `uv pip install` would install, without installing: the same resolver, the same flags."""
    last = ""
    for platform in PLATFORMS:
        cmd = ["uv", "pip", "compile", str(requirements), "--python-version", PYTHON_VERSION]
        cmd += ["--python-platform", platform, "--only-binary", ":all:", "--no-header", "--no-annotate", "-q"]
        out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if out.returncode == 0:
            pins = dict(m.groups() for m in re.finditer(r"^([A-Za-z0-9._-]+)==(\S+)$", out.stdout, re.M))
            return {norm(k): v for k, v in pins.items()}
        last = out.stderr.strip()
    raise SystemExit(f"uv could not resolve {requirements} on any platform the packager tries:\n{last}")


def diff(a: dict[str, str], b: dict[str, str]) -> list[str]:
    return [
        f"  {k}: {a.get(k, 'absent')} -> {b.get(k, 'absent')}" for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)
    ]


OSV = "https://api.osv.dev/v1"


def _osv(path: str, body: dict | None = None) -> dict:
    import httpx  # its certificate store works on this machine's Python; urllib's does not

    url = f"{OSV}/{path}"
    resp = httpx.post(url, json=body, timeout=30.0) if body is not None else httpx.get(url, timeout=30.0)
    resp.raise_for_status()
    return resp.json()


def advisories(pins: dict[str, str]) -> dict[str, list[dict[str, str]]]:
    """Advisories published for exactly these versions: one request for the whole list, then one per advisory found
    for its summary and the versions that fix it. Only package names and versions leave the machine."""
    names = sorted(pins)
    queries = [{"package": {"name": n, "ecosystem": "PyPI"}, "version": pins[n]} for n in names]
    found: dict[str, list[dict[str, str]]] = {}
    for name, result in zip(names, _osv("querybatch", {"queries": queries})["results"], strict=True):
        for vuln in result.get("vulns") or []:
            detail = _osv(f"vulns/{vuln['id']}")
            fixed = {
                event["fixed"]
                for affected in detail.get("affected", [])
                if norm(affected.get("package", {}).get("name", "")) == name
                for rng in affected.get("ranges", [])
                for event in rng.get("events", [])
                if "fixed" in event
            }
            summary = detail.get("summary") or (detail.get("details") or "").strip().split("\n")[0][:140]
            found.setdefault(name, []).append(
                {"id": vuln["id"], "summary": summary, "fixed": ", ".join(sorted(fixed)) or "no fixed version listed"}
            )
    return found


def report_outdated(direct: list[str], locked: dict[str, str]) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        req = Path(tmp) / "direct.in"
        req.write_text("\n".join(direct) + "\n")
        fresh = resolve(req)
    changes = diff(locked, fresh)
    print(f"locked: {len(locked)} packages. An upgrade today would change {len(changes)} (locked -> newest allowed):")
    print(*(changes or ["  nothing"]), sep="\n")
    found = advisories(locked)
    if not found:
        print("advisories published for the locked versions (osv.dev): none")
        return 0
    print(f"advisories published for the locked versions (osv.dev): {sum(map(len, found.values()))}")
    for name, items in found.items():
        for item in items:
            print(f"  {name}=={locked[name]}  {item['id']}  fixed in {item['fixed']}  {item['summary']}")
    return 2


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    how = ap.add_mutually_exclusive_group()
    how.add_argument("--runtime-version", type=int, help="lock what this deployed Runtime version carries")
    how.add_argument("--from-zip", type=Path, help="lock what this bundle zip carries")
    how.add_argument("--from-staging", action="store_true", help=f"lock what the last local build carried ({STAGING})")
    how.add_argument("--upgrade", action="store_true", help="resolve the direct requirements afresh and lock that")
    how.add_argument("--outdated", action="store_true", help="report what an upgrade would change, and advisories")
    args = ap.parse_args()

    _, direct, locked = read_pyproject()
    if args.outdated:
        return report_outdated(direct, locked)
    if args.runtime_version is not None:
        pins, source = from_runtime_version(args.runtime_version)
    elif args.from_zip:
        pins, source = from_zip(args.from_zip), f"the bundle {args.from_zip.name}"
    elif args.from_staging:
        pins, source = from_staging(), "the last local build"
    elif args.upgrade:
        with tempfile.TemporaryDirectory() as tmp:
            req = Path(tmp) / "direct.in"
            req.write_text("\n".join(direct) + "\n")
            pins, source = resolve(req), "a fresh resolution of the direct requirements"
    else:
        if not locked:
            print(f"{PYPROJECT.relative_to(ROOT)} has no locked block; run with --runtime-version N or --upgrade")
            return 1
        resolved = resolve(PYPROJECT)
        changes = diff(locked, resolved)
        if changes:
            print("the resolver does NOT give the locked set (locked -> resolved):", *changes, sep="\n")
            return 1
        print(f"locked: {len(locked)} packages; the resolver gives exactly this set for Python {PYTHON_VERSION}")
        return 0

    if not pins:
        print("no packages found; nothing written")
        return 1
    changes = diff(locked, pins)
    write_lock(pins, source)
    print(f"locked {len(pins)} packages from {source} in {PYPROJECT.relative_to(ROOT)}")
    print(*(changes if locked else ["  (first lock)"]), sep="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
