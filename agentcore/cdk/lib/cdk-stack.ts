import { AgentCoreApplication, type AgentCoreApplicationProps } from '@aws/agentcore-cdk';
import { RemovalPolicy, Stack, type StackProps, aws_bedrockagentcore as bedrockagentcore, aws_iam as iam, aws_logs as logs } from 'aws-cdk-lib';
import { Construct } from 'constructs';

export interface AgentCoreStackProps extends StackProps {
  /** Props for the AgentCore application, produced by transformAgentCoreJson from agentcore/agentcore.json. */
  application: AgentCoreApplicationProps;
}

/**
 * The stack the AgentCore CLI deploys. Everything declared in agentcore/agentcore.json is
 * created by the AgentCoreApplication construct. Add your own resources below it and wire
 * them to your runtimes and harnesses through the application's accessors.
 */
export class AgentCoreStack extends Stack {
  public readonly application: AgentCoreApplication;

  constructor(scope: Construct, id: string, props: AgentCoreStackProps) {
    super(scope, id, props);
    this.application = new AgentCoreApplication(this, 'Application', props.application);

    // ---- Per-analyst rate limits on the tools Gateway (design doc section 8; data doc 4.3 pairs them with
    // the policy cool-down). Buckets key on the JWT `sub` claim, so every analyst gets an independent budget.
    // Rate limits fail open when a dimension cannot be resolved: they shape behaviour, Policy is the boundary.
    const gateway = this.application.gateway('surv-investigator');
    const analyst = '$.context.jwt.sub';

    // ---- Gateway observability: application logs (every tool call, every policy decision) and traces are vended
    // logs; nothing is delivered until a delivery source/destination pair exists (devguide "Add observability").
    // Logs go to their own group, traces to X-Ray (which lands them in aws/spans with Transaction Search on).
    const gwLogs = new logs.LogGroup(this, 'GatewayLogs', {
      logGroupName: `/aws/vendedlogs/bedrock-agentcore/${gateway.gatewayId}`,
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: RemovalPolicy.DESTROY,
    });
    const logsSource = new logs.CfnDeliverySource(this, 'GatewayLogsSource', {
      name: `${gateway.gatewayId}-logs`,
      logType: 'APPLICATION_LOGS',
      resourceArn: gateway.gatewayArn,
    });
    const tracesSource = new logs.CfnDeliverySource(this, 'GatewayTracesSource', {
      name: `${gateway.gatewayId}-traces`,
      logType: 'TRACES',
      resourceArn: gateway.gatewayArn,
    });
    const logsDest = new logs.CfnDeliveryDestination(this, 'GatewayLogsDestination', {
      name: `${gateway.gatewayId}-logs-cwl`,
      deliveryDestinationType: 'CWL',
      destinationResourceArn: gwLogs.logGroupArn,
    });
    const tracesDest = new logs.CfnDeliveryDestination(this, 'GatewayTracesDestination', {
      name: `${gateway.gatewayId}-traces-xray`,
      deliveryDestinationType: 'XRAY',
    });
    const logsDelivery = new logs.CfnDelivery(this, 'GatewayLogsDelivery', {
      deliverySourceName: logsSource.name,
      deliveryDestinationArn: logsDest.attrArn,
    });
    logsDelivery.addDependency(logsSource);
    const tracesDelivery = new logs.CfnDelivery(this, 'GatewayTracesDelivery', {
      deliverySourceName: tracesSource.name,
      deliveryDestinationArn: tracesDest.attrArn,
    });
    tracesDelivery.addDependency(tracesSource);
    tracesDelivery.addDependency(logsDelivery); // one delivery per source at a time; serialise creation


    // ---- Temporal policies need the Gateway to mint a Workload Access Token per policy session
    // (devguide "IAM permissions for temporal policies"). The CLI's generated role grants AuthorizeAction,
    // PartiallyAuthorizeActions and GetPolicyEngine but not this one; without it every tool call fails with
    // "Failed to get workload identity token" as soon as a policy session header is present.
    gateway.addToRolePolicy(
      new iam.PolicyStatement({
        sid: 'PolicySessionWorkloadIdentity',
        actions: ['bedrock-agentcore:GetWorkloadAccessToken'],
        resources: [
          `arn:aws:bedrock-agentcore:${this.region}:${this.account}:workload-identity-directory/default`,
          // the Gateway's id is `<project>-<target>-<name>-<suffix>`; referencing gateway.gatewayId here would make the
          // role depend on the Gateway that depends on the role (circular), so the known prefix is used instead
          `arn:aws:bedrock-agentcore:${this.region}:${this.account}:workload-identity-directory/default/workload-identity/surv-default-surv-investigator-*`,
        ],
      }),
    );

    // ---- Configuration bundles (Optimization, data doc 4.5.3 and the model arm in 4.3): the Runtime app resolves
    // the bundle referenced in the request's `baggage` header through the control plane
    // (bedrock_agentcore.config_bundle.client -> GetConfigurationBundleVersion). The CLI's generated role does not
    // include it; without it get_config_bundle() raises and the agent falls back to its code defaults.
    // The Gateway needs the same grant: the agent's MCP client propagates the W3C baggage into every request's
    // `_meta`, and the Gateway's built-in rule `system_config-bundle_header` then fetches the bundle itself (to
    // apply tool-description overrides). Without the grant every tools/list under a bundle fails with 400
    // "Config bundle fetch failed: ... not authorized to perform GetConfigurationBundleVersion" (Gateway log,
    // 2026-11-06) and the agent cannot start.
    const bundleRead = (sid: string) =>
      new iam.PolicyStatement({
        sid,
        actions: ['bedrock-agentcore:GetConfigurationBundle', 'bedrock-agentcore:GetConfigurationBundleVersion'],
        resources: [`arn:aws:bedrock-agentcore:${this.region}:${this.account}:configuration-bundle/surv_*`],
      });
    const runtime = this.application.runtime('surv_investigator_l1');
    runtime.addToRolePolicy(bundleRead('ReadConfigurationBundles'));
    gateway.addToRolePolicy(bundleRead('GatewayReadsConfigurationBundles'));
    // 60 requests a minute per analyst. Measured 2026-11-18: one investigation makes about 13 Gateway requests in
    // about 25 s, so one analyst working one alert at a time stays near 30 a minute and two investigations in
    // parallel near 50. This limit has not been seen to answer: in run v6 every throttled request that was traced,
    // 78 of them, was `propose_disposition`, which is the write limit below. It was raised to 120 for an hour on
    // 2026-11-18 on that wrong diagnosis and put back. A brake on volume, not a security boundary.
    new bedrockagentcore.CfnGatewayRateLimit(this, 'PerAnalystRequests', {
      gatewayIdentifier: gateway.gatewayId,
      rateLimitId: 'per-analyst-requests',
      description: 'Every analyst: at most 60 tool calls a minute across all tools (an investigation uses 8-12)',
      dimensionKeys: [analyst],
      entries: [{ dimensions: { [analyst]: '*' }, requests: [{ rate: 60, period: 'minute' }] }],
    });
    // 3 proposals and 3 drafts a minute per analyst: one alert at a time fits (an investigation takes about 25 s),
    // two in parallel sit on it. This is the limit evaluation runs meet at concurrency 2: 79 of 169 invocations
    // of run v6 got a 429 on their proposal. It is meant to push back; the agent waits it out (RetryOn429, up to
    // about a minute since Runtime v20) instead of failing.
    new bedrockagentcore.CfnGatewayRateLimit(this, 'PerAnalystWrites', {
      gatewayIdentifier: gateway.gatewayId,
      rateLimitId: 'per-analyst-writes',
      description: 'Every analyst: at most 3 proposals and 3 STOR drafts a minute (one alert at a time)',
      dimensionKeys: ['toolName', analyst],
      entries: [
        { dimensions: { toolName: 'surv___propose_disposition', [analyst]: '*' }, requests: [{ rate: 3, period: 'minute' }] },
        { dimensions: { toolName: 'surv___draft_stor_narrative', [analyst]: '*' }, requests: [{ rate: 3, period: 'minute' }] },
      ],
    });

    // Example: give a runtime a DynamoDB table.
    //
    // import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
    // const orders = new dynamodb.Table(this, 'Orders', {
    //   partitionKey: { name: 'pk', type: dynamodb.AttributeType.STRING },
    // });
    // const checkout = this.application.runtime('checkout'); // or .harness('support')
    // checkout.grantReadWrite(orders);
    // checkout.addEnvironmentVariable('ORDERS_TABLE', orders.tableName);
  }
}
