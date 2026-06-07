# AI Secretary

Personal AI secretaries that exchange limited context and find mutually useful collaboration opportunities.

## Open Codex or Cowork and paste this prompt

```text
Create my personal AI secretary using https://github.com/intelligencystudio/ai-secretary as the detailed framework: an A2A-friendly endpoint with an Agent Card, owner profile, interests, offers, asks, and privacy rules. When I exchange secretary contacts with another person, make the secretaries handshake, share only allowed context capsules, find mutually beneficial collaboration options, and ask my approval before revealing private details.
```

That is the whole starting point.

## The Idea

People should not have to manually explain their whole context every time they meet someone useful. Each person can run an AI secretary that knows a bounded, permissioned version of their context.

When two people exchange AI secretary contacts, the secretaries:

1. discover each other through Agent Cards;
2. negotiate privacy and supported protocols;
3. exchange public or approved context capsules;
4. compare interests, offers, asks, projects, constraints, and timing;
5. propose concrete collaboration options;
6. ask humans for approval before disclosing private details or taking action.

The result is a lightweight protocol for opportunity search between people, teams, founders, candidates, investors, clients, and collaborators.

## Context Capsules

An AI secretary should share context in small capsules, not raw memory dumps.

```json
{
  "owner": "Example Person",
  "publicProfile": {
    "roles": ["founder", "operator", "developer"],
    "interests": ["AI agents", "automation", "B2B workflows"],
    "offers": ["technical implementation", "product strategy"],
    "asks": ["distribution", "partnerships", "project context"]
  },
  "privacy": {
    "defaultDisclosure": "summary_only",
    "requiresApproval": ["contacts", "documents", "calendar", "financials"],
    "neverShare": ["credentials", "private keys", "unapproved client data"]
  }
}
```

## Reference Prototype

This repository includes a tiny dependency-free Python prototype:

- `server.py`: a personal context intake endpoint;
- `hr_agent.py`: a context provider that can be generalized into a personal secretary;
- `/.well-known/agent-card.json`: A2A-friendly discovery;
- `/a2a`: JSON-RPC context exchange;
- `/contexts`, `/projects`, `/employees`, `/dispatch`: simple REST helpers.

See [docs/prototype.md](docs/prototype.md) for local run commands and smoke tests.

## Why This Matters

The social graph has contacts. The professional graph needs context. AI secretaries can make context portable, permissioned, and useful without forcing people to expose everything to everyone.

The smallest useful version is simple: exchange secretary URLs, let agents compare context, then bring humans only the best next moves.
