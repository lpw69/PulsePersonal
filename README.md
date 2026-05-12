# Personal X Engine

Generates draft threads for @WaldronLewis by trend-jacking big personal brands (Musk, Bezos, Hormozi, etc), extracting principles, and connecting them to distribution/content infrastructure.

## Structure

Every output is a 2-post thread:
1. **Main post**: reacts to what a big name said/did, extracts a principle, ends with an open loop
2. **Reply**: completes the thought, connects to distribution/content, occasionally sells agentic content infrastructure

## Key difference from other engines

This pushes **drafts for review**, not auto-published posts. Your personal brand, your approval.

## Required secrets

| Secret | What |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key |
| `APIFY_API_TOKEN` | Apify token |
| `TYPEFULLY_API_KEY` | Typefully API key |
| `TYPEFULLY_PERSONAL_SOCIAL_SET_ID` | Social set ID for @WaldronLewis |

## Schedule

3x daily (7am, 12pm, 5pm UTC). Each run generates 3 draft threads = 9 drafts/day for review.
