# Secretary Exchange Examples

These files model a full exchange between two personal AI secretaries:

- Alice: founder building AI workflow tools.
- Bob: operator with B2B distribution and CRM automation needs.

The exchange is intentionally structured as small JSON-RPC messages. Each message can be sent to `/a2a`, stored as an audit event, or used as a fixture for an implementation.

## Files

- `00-agent-card-alice.json`: Alice secretary discovery card.
- `01-agent-card-bob.json`: Bob secretary discovery card.
- `02-handshake-request.json`: Alice starts a secretary-to-secretary handshake.
- `03-handshake-response.json`: Bob accepts with disclosure limits.
- `04-public-context-capsule-alice.json`: Alice shares public context.
- `05-public-context-capsule-bob.json`: Bob shares public context.
- `06-match-request.json`: Alice asks Bob's secretary to look for mutual upside.
- `07-match-proposal.json`: Bob's secretary returns collaboration proposals.
- `08-approval-request.json`: Alice's secretary asks Alice before releasing private detail.
- `09-approval-response.json`: Alice approves a limited release.
- `10-private-context-release.json`: Alice's secretary releases only approved fields.
- `11-introduction-draft.json`: Secretaries draft a human-readable intro.
- `12-audit-log-entry.json`: One auditable exchange event.
- `13-full-exchange-batch.json`: A compact batch containing the core JSON-RPC sequence.

## Schemas

Use:

- `schemas/secretary-exchange.schema.json` for envelopes, messages, approvals, proposals, releases, and audit entries.
- `schemas/context-capsule.schema.json` for a single context capsule.
