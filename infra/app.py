"""CDK app for the mock firm back end (DynamoDB, S3, tool Lambdas, Cognito, analyst HTTP API).

Run from the repo root with `uv run --group infra cdk ...` or `cd infra && uv run cdk ...` (cdk.json points here).

Every construct in the app carries the two project tags. `auto-delete=no` is what the account's cleaner looks
for; `Project` is what `scripts/check_tags.py` filters on.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import aws_cdk as cdk

sys.path.insert(0, str(Path(__file__).resolve().parent))

from surv_firm.stack import SurvFirmStack

PROJECT_TAG = "agentcore-surveillance-investigator"
REGION = "eu-west-2"

app = cdk.App()

account = os.environ.get("CDK_DEFAULT_ACCOUNT")
if not account:
    raise SystemExit("CDK_DEFAULT_ACCOUNT is not set; run through the cdk CLI with AWS credentials configured")

SurvFirmStack(
    app,
    "SurvFirm",
    env=cdk.Environment(account=account, region=REGION),
    gateway_role_arn=app.node.try_get_context("gatewayRoleArn"),
    description="Mock surveillance back end for the AgentCore investigator (synthetic data only)",
)

cdk.Tags.of(app).add("Project", PROJECT_TAG)
cdk.Tags.of(app).add("auto-delete", "no")

app.synth()
