# Personal AI Secretaries

## One-Line Concept

Two people exchange contacts for their AI secretaries. The secretaries exchange only permissioned context, search for mutual upside, and return concrete collaboration proposals to their owners.

## Actors

- Owner: the human represented by a secretary.
- Secretary: the owner's AI agent with a public Agent Card and private policy.
- Contact secretary: another person's secretary.
- Context capsule: a small structured packet of shareable context.
- Approval gate: a human confirmation before private disclosure or external action.

## Core Flow

1. Owner A and Owner B exchange secretary URLs.
2. Secretary A fetches Secretary B's Agent Card, and Secretary B does the same.
3. Both sides perform a handshake: identity, protocol, topic, disclosure level, and rate limits.
4. Each side shares public context capsules.
5. Secretaries calculate possible matches: asks against offers, timing, constraints, trust, and next steps.
6. Each secretary drafts proposals for its owner.
7. Humans approve, reject, or ask for more context.
8. Only approved private details are disclosed.

## Disclosure Levels

- `public`: safe to share with any discovered secretary.
- `trusted`: share after an accepted contact or verified relationship.
- `approval_required`: share only after owner confirmation.
- `sealed`: never send out; use only for local reasoning.

## Opportunity Types

- collaboration;
- hiring or contracting;
- intros;
- sales or partnerships;
- investment conversations;
- advisory calls;
- knowledge exchange;
- project staffing.

## Safety Rules

- Never share credentials, private keys, or secrets.
- Never share client data unless explicitly approved and allowed.
- Prefer summaries over raw documents.
- Keep an audit log of every exchanged capsule.
- Ask owner approval before revealing identities, contact details, calendar details, financials, documents, or private project data.

## Minimal Protocol Surface

- `GET /.well-known/agent-card.json`: discover the secretary.
- `POST /a2a`: JSON-RPC exchange.
- `secretary.handshake`: negotiate identity, topic, and disclosure.
- `secretary.context.offer`: send allowed context capsules.
- `secretary.match.propose`: request collaboration proposals.
- `secretary.approval.request`: ask the human before private disclosure.
