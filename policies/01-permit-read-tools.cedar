// 01 Read tools: any authenticated analyst may call the evidence tools. Deny-by-default means every
// prerequisite of a temporal rule needs its own permit, or it is never recorded as a response.
permit (
  principal is AgentCore::OAuthUser,
  action in [
    AgentCore::Action::"surv___get_alert",
    AgentCore::Action::"surv___get_procedures",
    AgentCore::Action::"surv___get_order_events",
    AgentCore::Action::"surv___reconstruct_book",
    AgentCore::Action::"surv___compute_discriminators",
    AgentCore::Action::"surv___get_trader_profile",
    AgentCore::Action::"surv___get_trader_alert_history",
    AgentCore::Action::"surv___get_market_events",
    AgentCore::Action::"surv___get_instrument_stats"
  ],
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:eu-west-2:384308066035:gateway/surv-default-surv-investigator-gsq1ismkrw"
);
