import { AgentCoreApplication, type AgentCoreApplicationProps } from '@aws/agentcore-cdk';
import { Stack, type StackProps, aws_bedrockagentcore as bedrockagentcore } from 'aws-cdk-lib';
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
