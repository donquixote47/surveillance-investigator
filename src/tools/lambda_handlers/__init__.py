"""Lambda entry points: `gateway_tools` (one function behind the Gateway target `surv`, dispatching on the
tool name) and `human_path` (the analyst's HTTP API: record a disposition, send feedback). The agent can
never reach `human_path`: it is not a Gateway tool and runs behind a Cognito-authorised API."""
