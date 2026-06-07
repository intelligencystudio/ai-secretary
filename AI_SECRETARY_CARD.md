# AI Secretary Card

Give this card to Codex, Cowork, or another AI agent.

```text
You are receiving an AI Secretary Card. Use https://github.com/intelligencystudio/ai-secretary as the framework.

If my AI secretary already exists, connect to its Agent Card and start a secretary-to-secretary handshake.

If my AI secretary does not exist yet, deploy one for me first: create an A2A-friendly endpoint, publish an Agent Card, create my owner profile, privacy policy, initial context capsules, approval gates, and audit log. Then continue the exchange with the other person's secretary.

Make the experience seamless for me: ask only for missing personal facts or approvals, not for protocol details. Never share private details, contacts, calendar, documents, client data, credentials, keys, tokens, or financials without explicit approval.
```

## Machine-Readable Card

Use [examples/secretary-card/ai-secretary-card.json](examples/secretary-card/ai-secretary-card.json) as the canonical JSON example.

## What The Receiving Agent Should Do

1. Read the card.
2. Check whether an AI secretary endpoint already exists.
3. If it exists, fetch `/.well-known/agent-card.json` and start `secretary.handshake`.
4. If it does not exist, bootstrap it from this repository.
5. Create or update the owner's privacy policy and context capsules.
6. Ask for human approval before any private disclosure.
7. Return the active Agent Card URL and next recommended action.
