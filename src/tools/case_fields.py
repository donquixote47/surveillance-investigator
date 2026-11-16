"""The attributes of a `surv-cases` row, by who may write them. One list, three readers: the tools Lambda's IAM
statement (`infra/surv_firm/stack.py`), the test that reads the attribute names out of the Lambda's own update
expressions, and `scripts/reset_cases.py`.

Why a list and not "the code has no path": the tools Lambda is the agent's hand on the firm's data, and "it has no
code path that writes `recorded_*`" is a property of today's code. The IAM statement makes it a property of the
role: `dynamodb:UpdateItem` on the cases table is allowed only when every attribute the request names is in
AGENT_WRITABLE (condition key `dynamodb:Attributes`), and `PutItem`, `DeleteItem` and `BatchWriteItem`, which
replace or remove a whole item, are not granted at all.

`decision_lock` is in the agent's list on purpose. DynamoDB counts an attribute named in a ConditionExpression as
accessed by the request (developer guide, "Using IAM policy conditions for fine-grained access control": allowed
attributes "can be read, written, or evaluated in a conditional write"; a role limited to them "cannot perform
conditional write operations based on any other attributes"). A proposal conditioned on
`attribute_not_exists(recorded_disposition)` would therefore need `recorded_disposition` in the allowed list, which
is the attribute the list exists to protect. So the human path sets a separate marker when it records, and the
proposal is conditioned on that. The tools role could write the marker; all that buys is refusing its own proposals.
"""

from __future__ import annotations

# Key attributes of the table and of its `by_trader` index must be listed, or DynamoDB cannot perform the update.
CASE_KEYS = ("alert_id", "trader_id", "proposed_at")

# What the agent's path (propose_disposition, draft_stor_narrative) may name in an update.
AGENT_WRITABLE = (
    *CASE_KEYS,
    "case_id",
    "date",
    "scenario",
    "status",
    "proposed_disposition",
    "confidence",
    "report",
    "proposal_count",
    "proposal_history",
    "proposal_provenance",
    "stor_draft",
    "stor_draft_id",
    "stor_draft_at",
    "decision_lock",
)

# What only the human path writes: the firm's decision, its history, the analyst's words.
HUMAN_ONLY = (
    "recorded_disposition",
    "recorded_by",
    "recorded_at",
    "analyst_note",
    "override",
    "decision_history",
    "feedback",
)

# scripts/reset_cases.py: what "back to no proposal" removes, and what `--include-recorded` removes on top.
PROPOSAL_FIELDS = (
    "proposed_disposition",
    "confidence",
    "report",
    "proposed_at",
    "proposal_count",
    "proposal_history",
    "proposal_provenance",
)
RECORD_FIELDS = (*HUMAN_ONLY, "decision_lock")
