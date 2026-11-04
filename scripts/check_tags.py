#!/usr/bin/env python
"""List every AWS resource that belongs to this project and flag the ones missing `auto-delete=no`.

    uv run scripts/check_tags.py              # report
    uv run scripts/check_tags.py --fix        # add missing tags and remove stale keys (asks first)

Two sources, because AgentCore resources are not all visible through the Resource Groups Tagging API:
  1. Resource Groups Tagging API: everything tagged Project=<project> in eu-west-2 (the CDK stack's resources).
  2. AgentCore control plane: list-* for runtimes, gateways, memories, policy engines, code interpreters,
     evaluators, workload identities and OAuth2 credential providers, then list-tags-for-resource for each.
     Untagged AgentCore resources are reported too, since one of them without a Project tag is still ours
     if its name starts with `surv`.
"""

from __future__ import annotations

import argparse
import sys

import boto3

REGION = "eu-west-2"
PROJECT = "agentcore-surveillance-investigator"
REQUIRED = {"Project": PROJECT, "auto-delete": "no"}
STALE_KEYS = {"auto-remove"}  # the key used by mistake on 2026-11-03; must not remain anywhere
NAME_PREFIX = "surv"


def _paginate(fn, key: str, **kwargs):
    token = None
    while True:
        resp = fn(**kwargs, **({"nextToken": token} if token else {}))
        yield from resp.get(key, [])
        token = resp.get("nextToken")
        if not token:
            return


def agentcore_resources(region: str) -> list[tuple[str, str, str]]:
    """(kind, name, arn) for every AgentCore control-plane resource in the region."""
    c = boto3.client("bedrock-agentcore-control", region_name=region)
    account = boto3.client("sts").get_caller_identity()["Account"]
    out = []
    for r in _paginate(c.list_agent_runtimes, "agentRuntimes"):
        out.append(("runtime", r["agentRuntimeName"], r["agentRuntimeArn"]))
    for g in _paginate(c.list_gateways, "items"):
        out.append(("gateway", g["name"], f"arn:aws:bedrock-agentcore:{region}:{account}:gateway/{g['gatewayId']}"))
    for m in _paginate(c.list_memories, "memories"):
        out.append(("memory", m["id"], m["arn"]))
    for p in _paginate(c.list_policy_engines, "policyEngines"):
        out.append(("policy-engine", p["name"], p["policyEngineArn"]))
    for ci in _paginate(c.list_code_interpreters, "codeInterpreterSummaries", type="CUSTOM"):
        out.append(("code-interpreter", ci["name"], ci["codeInterpreterArn"]))
    for e in _paginate(c.list_evaluators, "evaluators"):
        if e["evaluatorArn"].split(":")[4] == "":  # built-ins (AWS, DeepEval, AutoEval) have no account in the ARN
            continue
        out.append(("evaluator", e["evaluatorName"], e["evaluatorArn"]))
    for w in _paginate(c.list_workload_identities, "workloadIdentities"):
        out.append(("workload-identity", w["name"], w["workloadIdentityArn"]))
    for cp in _paginate(c.list_oauth2_credential_providers, "credentialProviders"):
        out.append(("oauth2-provider", cp["name"], cp["credentialProviderArn"]))
    return out


def agentcore_tags(arn: str, region: str) -> dict[str, str]:
    c = boto3.client("bedrock-agentcore-control", region_name=region)
    try:
        return c.list_tags_for_resource(resourceArn=arn).get("tags", {}) or {}
    except c.exceptions.ClientError as exc:  # some resource types reject tagging calls
        return {"__error__": str(exc)}


def tagged_resources(region: str) -> list[tuple[str, dict[str, str]]]:
    """(arn, tags) for everything the Tagging API knows with our Project tag."""
    c = boto3.client("resourcegroupstaggingapi", region_name=region)
    out = []
    paginator = c.get_paginator("get_resources")
    for page in paginator.paginate(TagFilters=[{"Key": "Project", "Values": [PROJECT]}]):
        for r in page["ResourceTagMappingList"]:
            out.append((r["ResourceARN"], {t["Key"]: t["Value"] for t in r.get("Tags", [])}))
    return out


def missing(tags: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in REQUIRED.items() if tags.get(k) != v}


def stale(tags: dict[str, str]) -> list[str]:
    return sorted(k for k in tags if k in STALE_KEYS)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", default=REGION)
    ap.add_argument("--fix", action="store_true", help="add missing tags (after confirmation)")
    args = ap.parse_args()

    problems: list[tuple[str, str, dict[str, str]]] = []  # (how to tag, arn, tags to add)
    removals: list[tuple[str, str, list[str]]] = []  # (how to untag, arn, keys to remove)

    print(f"== resources tagged Project={PROJECT} ({args.region}, Tagging API)")
    for arn, tags in tagged_resources(args.region):
        m, s = missing(tags), stale(tags)
        flag = ("MISSING " + ",".join(m)) if m else ("STALE " + ",".join(s)) if s else "ok"
        print(f"  {flag:28s} {arn}")
        if m:
            problems.append(("tagging-api", arn, m))
        if s:
            removals.append(("tagging-api", arn, s))

    print("== AgentCore control plane")
    for kind, name, arn in agentcore_resources(args.region):
        tags = agentcore_tags(arn, args.region)
        ours = tags.get("Project") == PROJECT or name.lower().startswith(NAME_PREFIX)
        if "__error__" in tags:
            print(f"  {'tags unreadable':28s} {kind:18s} {name:32s} {arn}")
            continue
        if not ours:
            print(f"  {'not ours':28s} {kind:18s} {name:32s} {arn}")
            continue
        m, s = missing(tags), stale(tags)
        flag = ("MISSING " + ",".join(m)) if m else ("STALE " + ",".join(s)) if s else "ok"
        print(f"  {flag:28s} {kind:18s} {name:32s} {arn}")
        if m:
            problems.append(("agentcore", arn, m))
        if s:
            removals.append(("agentcore", arn, s))

    if not problems and not removals:
        print("all project resources carry the required tags and no stale keys")
        return 0
    print(f"{len(problems)} resource(s) need tags; {len(removals)} carry stale keys")
    if not args.fix:
        return 1
    if input("apply the changes now? [y/N] ").strip().lower() != "y":
        return 1
    ac = boto3.client("bedrock-agentcore-control", region_name=args.region)
    rg = boto3.client("resourcegroupstaggingapi", region_name=args.region)
    for how, arn, add in problems:
        if how == "agentcore":
            ac.tag_resource(resourceArn=arn, tags=add)
        else:
            rg.tag_resources(ResourceARNList=[arn], Tags=add)
        print(f"  tagged {arn} {add}")
    for how, arn, keys in removals:
        if how == "agentcore":
            ac.untag_resource(resourceArn=arn, tagKeys=keys)
        else:
            rg.untag_resources(ResourceARNList=[arn], TagKeys=keys)
        print(f"  untagged {arn} {keys}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
