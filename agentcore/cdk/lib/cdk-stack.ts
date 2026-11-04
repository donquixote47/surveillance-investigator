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
    new bedrockagentcore.CfnGatewayRateLimit(this, 'PerAnalystRequests', {
      gatewayIdentifier: gateway.gatewayId,
      rateLimitId: 'per-analyst-requests',
      description: 'Every analyst: at most 60 tool calls a minute across all tools (an investigation uses 8-12)',
      dimensionKeys: [analyst],
      entries: [{ dimensions: { [analyst]: '*' }, requests: [{ rate: 60, period: 'minute' }] }],
    });
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
