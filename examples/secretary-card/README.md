# AI Secretary Card

This folder contains a self-bootstrapping secretary card.

The card is designed to be useful even when the receiver does not have an AI secretary installed yet:

1. If the secretary exists, the receiving agent connects to the Agent Card and starts the exchange.
2. If the secretary does not exist, the receiving agent uses the framework repository to deploy one.
3. The agent asks the owner only for missing personal facts and approvals, not for protocol details.
4. The exchange continues through the deployed secretary endpoint.

Use:

- `ai-secretary-card.json`: machine-readable card.
- `schemas/secretary-card.schema.json`: schema for card validation.
