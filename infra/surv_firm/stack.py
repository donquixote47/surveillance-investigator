"""SurvFirmStack: DynamoDB tables, S3 bucket, the Gateway tools Lambda, the human-path HTTP API with Cognito.

Every resource is tagged Project=agentcore-surveillance-investigator and auto-delete=no at the app level
(infra/app.py). Removal policies are DESTROY so `cdk destroy` leaves nothing behind at the end of the project;
the tag protects the resources from the account's automatic cleaner in the meantime.
"""

from __future__ import annotations

import sys
from pathlib import Path

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import (
    aws_apigatewayv2 as apigw,
)
from aws_cdk import (
    aws_apigatewayv2_authorizers as authz,
)
from aws_cdk import (
    aws_apigatewayv2_integrations as integ,
)
from aws_cdk import (
    aws_cognito as cognito,
)
from aws_cdk import (
    aws_dynamodb as ddb,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_lambda as lambda_,
)
from aws_cdk import (
    aws_logs as logs,
)
from aws_cdk import (
    aws_s3 as s3,
)
from constructs import Construct

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
LAYER_DIR = ROOT / "infra" / "build" / "layer"

if str(SRC) not in sys.path:  # the list of attributes the agent's path may write lives with the code that writes them
    sys.path.insert(0, str(SRC))
from tools.case_fields import AGENT_WRITABLE  # noqa: E402


class SurvFirmStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        gateway_role_arn: str | None = None,
        memory_id: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ----- tables -----
        def tbl(name: str, pk: str, sk: str | None = None, **extra) -> ddb.TableV2:
            return ddb.TableV2(
                self,
                f"Tbl{name}",
                table_name=f"surv-{name}",
                partition_key=ddb.Attribute(name=pk, type=ddb.AttributeType.STRING),
                sort_key=ddb.Attribute(name=sk, type=ddb.AttributeType.STRING) if sk else None,
                billing=ddb.Billing.on_demand(),
                removal_policy=RemovalPolicy.DESTROY,
                point_in_time_recovery_specification=ddb.PointInTimeRecoverySpecification(
                    point_in_time_recovery_enabled=False
                ),
                **extra,
            )

        order_events = tbl(
            "order-events",
            "pk",
            "sk",
            global_secondary_indexes=[
                ddb.GlobalSecondaryIndexPropsV2(
                    index_name="by_date",
                    partition_key=ddb.Attribute(name="date", type=ddb.AttributeType.STRING),
                    sort_key=ddb.Attribute(name="sk", type=ddb.AttributeType.STRING),
                )
            ],
        )
        trades = tbl("trades", "date", "sk")
        traders = tbl("traders", "trader_id")
        market_events = tbl("market-events", "date", "sk")
        instrument_stats = tbl("instrument-stats", "instrument", "date")
        alerts = tbl(
            "alerts",
            "alert_id",
            global_secondary_indexes=[
                ddb.GlobalSecondaryIndexPropsV2(
                    index_name="by_date",
                    partition_key=ddb.Attribute(name="date", type=ddb.AttributeType.STRING),
                    sort_key=ddb.Attribute(name="trigger_sk", type=ddb.AttributeType.STRING),
                )
            ],
        )
        cases_history = tbl("cases-history", "trader_id", "sk")
        cases = tbl(
            "cases",
            "alert_id",
            global_secondary_indexes=[
                ddb.GlobalSecondaryIndexPropsV2(
                    index_name="by_trader",
                    partition_key=ddb.Attribute(name="trader_id", type=ddb.AttributeType.STRING),
                    sort_key=ddb.Attribute(name="proposed_at", type=ddb.AttributeType.STRING),
                )
            ],
        )
        read_tables = [order_events, trades, traders, market_events, instrument_stats, alerts, cases_history, cases]
        table_env = {
            "ORDER_EVENTS_TABLE": order_events.table_name,
            "TRADES_TABLE": trades.table_name,
            "TRADERS_TABLE": traders.table_name,
            "MARKET_EVENTS_TABLE": market_events.table_name,
            "INSTRUMENT_STATS_TABLE": instrument_stats.table_name,
            "ALERTS_TABLE": alerts.table_name,
            "CASES_HISTORY_TABLE": cases_history.table_name,
            "CASES_TABLE": cases.table_name,
        }
        if memory_id:  # AgentCore Memory lives in the AgentCore stack; its id arrives as a context value
            table_env["MEMORY_ID"] = memory_id

        # ----- bucket for parquet datasets and reports -----
        bucket = s3.Bucket(
            self,
            "DataBucket",
            bucket_name=f"surv-firm-data-{self.account}-{self.region}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # ----- Lambda code: src/ as the asset root so `tools` and `market_sim` are importable -----
        # Only `tools/` and `market_sim/types.py` (imported by discriminators) ship; the simulator and the
        # detector stay local.
        code = lambda_.Code.from_asset(
            str(SRC),
            exclude=[
                "**/tests/**",
                "**/__pycache__/**",
                "detector/**",
                "market_sim/*",
                "!market_sim/__init__.py",
                "!market_sim/types.py",
            ],
        )
        pandas_layer = lambda_.LayerVersion(
            self,
            "PandasLayer",
            layer_version_name="surv-deps-py314-arm64",
            code=lambda_.Code.from_asset(str(LAYER_DIR)),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_14],
            compatible_architectures=[lambda_.Architecture.ARM_64],
            description="pandas + numpy + boto3 manylinux_2_28 wheels for Python 3.14 arm64 (infra/build_layer.sh)",
            removal_policy=RemovalPolicy.DESTROY,
        )

        tools_fn = lambda_.Function(
            self,
            "GatewayToolsFn",
            function_name="surv-gateway-tools",
            runtime=lambda_.Runtime.PYTHON_3_14,
            architecture=lambda_.Architecture.ARM_64,
            handler="tools.lambda_handlers.gateway_tools.handler",
            code=code,
            layers=[pandas_layer],
            memory_size=1024,
            timeout=Duration.seconds(60),
            environment=table_env,
            log_group=logs.LogGroup(
                self,
                "GatewayToolsLogs",
                log_group_name="/aws/lambda/surv-gateway-tools",
                retention=logs.RetentionDays.ONE_MONTH,
                removal_policy=RemovalPolicy.DESTROY,
            ),
            description=(
                "All Gateway tools under target `surv`; reads every table, may update only the proposal fields "
                "of surv-cases (IAM dynamodb:Attributes)"
            ),
        )
        for t in read_tables:
            t.grant_read_data(tools_fn)
        # The agent's only write, enforced on the role and not only in the code: UpdateItem on the cases table, and
        # only when every attribute the request names (set, removed, or tested in a condition) is one of the
        # proposal fields. `recorded_*`, `decision_history`, `analyst_note`, `override` and `feedback` are the human
        # path's and cannot be named. PutItem, DeleteItem and BatchWriteItem replace or remove a whole item and are
        # not granted. Before 2026-11-16 this was `cases.grant_write_data(tools_fn)`, i.e. every write on every
        # attribute, with "the function has no code path for recorded_*" as the only control.
        tools_fn.add_to_role_policy(
            iam.PolicyStatement(
                sid="ProposalFieldsOnly",
                actions=["dynamodb:UpdateItem"],
                resources=[cases.table_arn],
                conditions={
                    "ForAllValues:StringEquals": {"dynamodb:Attributes": list(AGENT_WRITABLE)},
                    # an update may not hand back the whole item (which holds the human path's attributes)
                    "StringEqualsIfExists": {"dynamodb:ReturnValues": ["NONE", "UPDATED_OLD", "UPDATED_NEW"]},
                },
            )
        )
        if memory_id:
            memory_arn = f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:memory/{memory_id}"
            # the agent's tool only reads Memory; the human path writes it (records + events for extraction)
            tools_fn.add_to_role_policy(
                iam.PolicyStatement(actions=["bedrock-agentcore:RetrieveMemoryRecords"], resources=[memory_arn])
            )

        human_fn = lambda_.Function(
            self,
            "HumanPathFn",
            function_name="surv-human-path",
            runtime=lambda_.Runtime.PYTHON_3_14,
            architecture=lambda_.Architecture.ARM_64,
            handler="tools.lambda_handlers.human_path.handler",
            code=code,
            layers=[pandas_layer],  # for the current boto3 (Memory API); pandas is unused here
            memory_size=512,
            timeout=Duration.seconds(30),
            environment=table_env,
            log_group=logs.LogGroup(
                self,
                "HumanPathLogs",
                log_group_name="/aws/lambda/surv-human-path",
                retention=logs.RetentionDays.ONE_MONTH,
                removal_policy=RemovalPolicy.DESTROY,
            ),
            description=(
                "Analyst HTTP API: queue, case view, record disposition, send feedback. Not reachable from the Gateway."
            ),
        )
        for t in (alerts, cases, cases_history):
            t.grant_read_write_data(human_fn)
        traders.grant_read_data(human_fn)  # the desk, for the Memory namespace; the human path never writes a trader
        if memory_id:
            human_fn.add_to_role_policy(
                iam.PolicyStatement(
                    actions=[
                        "bedrock-agentcore:BatchCreateMemoryRecords",
                        "bedrock-agentcore:CreateEvent",
                        "bedrock-agentcore:UpdateMemoryRecordExpirySpecification",
                    ],
                    resources=[memory_arn],
                )
            )

        # ----- Cognito: analysts, groups L1 and L2 -----
        pool = cognito.UserPool(
            self,
            "Analysts",
            user_pool_name="surv-analysts",
            self_sign_up_enabled=False,
            sign_in_aliases=cognito.SignInAliases(username=True),
            password_policy=cognito.PasswordPolicy(
                min_length=12,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=False,
            ),
            account_recovery=cognito.AccountRecovery.NONE,
            removal_policy=RemovalPolicy.DESTROY,
            feature_plan=cognito.FeaturePlan.ESSENTIALS,
        )
        # Two app clients, so that the token the agent holds cannot record a decision (2026-11-17).
        #   agent session    the access token the UI passes to the AgentCore Runtime, which forwards it to the
        #                    Gateway. Runtime and Gateway accept this client only (`allowedClients`, agentcore.json).
        #   analyst records  the access token the UI keeps for itself and sends to the recording API. The HTTP
        #                    API's JWT authorizer accepts this client only (it checks `client_id` against its
        #                    audience when the token has no `aud`, which is a Cognito access token's case).
        # Same analyst, same groups, two tokens. Until this change one client served both, so the token inside the
        # agent's session was also a valid credential for POST /cases/{id}/disposition, and "the agent cannot
        # record" rested on the agent having no HTTP tool. The first client keeps its construct id ("AnalystUi"):
        # it is the client id the deployed Runtime and Gateway already accept, and a new id there would be a new
        # Runtime version.
        client = pool.add_client(
            "AnalystUi",
            user_pool_client_name="surv-agent-session",
            generate_secret=False,
            auth_flows=cognito.AuthFlow(user_password=True, user_srp=True),
            id_token_validity=Duration.hours(8),
            access_token_validity=Duration.hours(8),
        )
        records_client = pool.add_client(
            "AnalystRecords",
            user_pool_client_name="surv-analyst-records",
            generate_secret=False,
            auth_flows=cognito.AuthFlow(user_password=True, user_srp=True),
            id_token_validity=Duration.hours(8),
            access_token_validity=Duration.hours(8),
        )
        for g in ("L1", "L2"):
            cognito.CfnUserPoolGroup(
                self,
                f"Group{g}",
                user_pool_id=pool.user_pool_id,
                group_name=g,
                description=f"Level {g[1]} surveillance analysts",
            )
        for user, group in (("l1.analyst", "L1"), ("l2.reviewer", "L2")):
            u = cognito.CfnUserPoolUser(
                self, f"User{group}", user_pool_id=pool.user_pool_id, username=user, message_action="SUPPRESS"
            )
            att = cognito.CfnUserPoolUserToGroupAttachment(
                self, f"Attach{group}", user_pool_id=pool.user_pool_id, group_name=group, username=user
            )
            att.add_resource_dependency(u)

        # ----- HTTP API with JWT authoriser -----
        api = apigw.HttpApi(
            self,
            "AnalystApi",
            api_name="surv-analyst-api",
            default_authorizer=authz.HttpUserPoolAuthorizer("Jwt", pool, user_pool_clients=[records_client]),
            cors_preflight=apigw.CorsPreflightOptions(
                allow_origins=["http://localhost:8501"],
                allow_methods=[apigw.CorsHttpMethod.GET, apigw.CorsHttpMethod.POST, apigw.CorsHttpMethod.OPTIONS],
                allow_headers=["authorization", "content-type"],
            ),
        )
        human_integration = integ.HttpLambdaIntegration("HumanInt", human_fn)
        api.add_routes(path="/alerts", methods=[apigw.HttpMethod.GET], integration=human_integration)
        api.add_routes(path="/cases/{alert_id}", methods=[apigw.HttpMethod.GET], integration=human_integration)
        api.add_routes(
            path="/cases/{alert_id}/disposition", methods=[apigw.HttpMethod.POST], integration=human_integration
        )
        api.add_routes(
            path="/cases/{alert_id}/feedback", methods=[apigw.HttpMethod.POST], integration=human_integration
        )

        # ----- Gateway invoke permission (set once the AgentCore Gateway role exists) -----
        if gateway_role_arn:
            tools_fn.grant_invoke(iam.ArnPrincipal(gateway_role_arn))

        # ----- outputs -----
        for k, v in table_env.items():
            CfnOutput(self, k, value=v)
        CfnOutput(self, "DataBucketName", value=bucket.bucket_name)
        CfnOutput(self, "GatewayToolsFunctionArn", value=tools_fn.function_arn)
        CfnOutput(self, "GatewayToolsFunctionName", value=tools_fn.function_name)
        CfnOutput(self, "UserPoolId", value=pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=client.user_pool_client_id)  # the agent-session client
        CfnOutput(self, "RecordsClientId", value=records_client.user_pool_client_id)
        CfnOutput(
            self,
            "UserPoolDiscoveryUrl",
            value=f"https://cognito-idp.{self.region}.amazonaws.com/{pool.user_pool_id}/.well-known/openid-configuration",
        )
        CfnOutput(self, "AnalystApiUrl", value=api.api_endpoint)
