// 02 Defence in depth for "the agent never records a disposition". The engine's Cedar schema is generated from
// the Gateway's tool manifest, so a policy cannot even name a tool that does not exist (a forbid on
// surv___record_disposition is rejected at creation: "unrecognized action"). What CAN be written is the
// closed list: any action outside the twelve known tools is forbidden for everyone. If a record_disposition
// tool is ever added to the target, it is denied until someone edits this list on purpose.
// The resource must be the specific Gateway ARN: with `resource is AgentCore::Gateway` the validator does not bind
// the Gateway's tool manifest and rejects every tool name as unrecognized (observed 2026-11-04).
forbid (
  principal,
  action,
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:eu-west-2:384308066035:gateway/surv-default-surv-investigator-gsq1ismkrw"
)
unless {
  action in [
    AgentCore::Action::"surv___get_alert",
    AgentCore::Action::"surv___get_procedures",
    AgentCore::Action::"surv___recall_memory",
    AgentCore::Action::"surv___get_order_events",
    AgentCore::Action::"surv___reconstruct_book",
    AgentCore::Action::"surv___compute_discriminators",
    AgentCore::Action::"surv___get_trader_profile",
    AgentCore::Action::"surv___get_trader_alert_history",
    AgentCore::Action::"surv___get_market_events",
    AgentCore::Action::"surv___get_instrument_stats",
    AgentCore::Action::"surv___propose_disposition",
    AgentCore::Action::"surv___draft_stor_narrative"
  ]
};
