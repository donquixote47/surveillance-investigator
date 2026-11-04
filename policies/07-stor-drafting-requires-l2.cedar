// 07 Only Level-2 analysts may draft a STOR. JWT claims arrive as string tags; the Cognito groups claim is
// an array, so it reaches Cedar as the text ["L2"] and is matched with `like`.
forbid (
  principal is AgentCore::OAuthUser,
  action == AgentCore::Action::"surv___draft_stor_narrative",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:eu-west-2:384308066035:gateway/surv-default-surv-investigator-gsq1ismkrw"
)
unless {
  principal.hasTag("cognito:groups") && principal.getTag("cognito:groups") like "*L2*"
};
