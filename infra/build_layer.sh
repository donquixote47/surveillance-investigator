#!/usr/bin/env bash
# Build the Lambda layer with pandas, numpy and a current boto3 for the Lambda runtime (Python 3.14, arm64).
#
# boto3 is included because the runtime's bundled copy lags the AgentCore Memory API (its BatchCreateMemoryRecords
# did not know `metadata` on 2026-11-04); the layer pins the same version uv.lock resolved for the project.
#
# pyarrow is deliberately left out: the tools Lambda reads DynamoDB, never parquet, and pandas 3.x falls back to
# Python-backed strings without it. pyarrow alone is 139 MB unzipped; without it the layer is about 80 MB unzipped.
#
# The layer is built from pre-built manylinux wheels, never from source, so the result does not depend on the
# machine that runs this script (a macOS laptop here). Versions are pinned to what uv.lock resolved for the
# project so the Lambda computes exactly what the local tests compute.
#
# Output: infra/build/layer/python/...  (the directory CDK zips as the LayerVersion asset)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/infra/build/layer"
PY_VERSION="3.14"
PLATFORM="aarch64-manylinux_2_28"  # Lambda python3.14 runs on Amazon Linux 2023 (glibc 2.34)

pinned() {  # read the locked version of a package from uv.lock
  awk -v pkg="$1" '
    $0 == "[[package]]" {inpkg=1; name=""; next}
    inpkg && /^name = / {gsub(/"/, "", $3); name=$3}
    inpkg && /^version = / && name == pkg {gsub(/"/, "", $3); print $3; exit}
  ' "$ROOT/uv.lock"
}

PANDAS="$(pinned pandas)"
NUMPY="$(pinned numpy)"
BOTO3="$(pinned boto3)"
BOTOCORE="$(pinned botocore)"
echo "layer: pandas==$PANDAS numpy==$NUMPY boto3==$BOTO3 for cp${PY_VERSION/./} $PLATFORM"

rm -rf "$OUT"
mkdir -p "$OUT/python"

uv pip install \
  --python-platform "$PLATFORM" \
  --python-version "$PY_VERSION" \
  --only-binary=:all: \
  --no-deps \
  --target "$OUT/python" \
  "pandas==$PANDAS" "numpy==$NUMPY" "boto3==$BOTO3" "botocore==$BOTOCORE" \
  python-dateutil tzdata jmespath s3transfer urllib3

# trim what Lambda never needs: tests, headers for compiling against numpy, bytecode caches
find "$OUT/python" -type d \( -name tests -o -name test -o -name __pycache__ \) -prune -exec rm -rf {} +
rm -rf "$OUT/python/numpy/_core/include"
find "$OUT/python" -name "*.pyx" -delete -o -name "*.pxd" -delete -o -name "*.h" -delete

du -sh "$OUT/python"
echo "zipped size estimate:"; (cd "$OUT" && zip -qr - python | wc -c | awk '{printf "  %.1f MB (limit 250 MB unzipped per function incl. layers)\n", $1/1024/1024}')
