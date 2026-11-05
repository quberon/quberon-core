# Live Meta inference — status

**Not run / not verified as of 2026-11-05.**

- Runtime default is `META_MODE=mock`; mock proposals are labelled `provider: mock`.
- A live OpenAI-compatible adapter exists in `integrations/meta.py` (`LiveMetaProvider`, env: `META_API_URL`, `META_API_KEY`, `META_MODEL`), but no successful real provider call was made or recorded in this pass, and no endpoint/model was invented to fill this file.
- Therefore: **do not claim runtime Meta inference works.** The honest claim is development-time Meta assistance (see `docs/BUILT-DURING-HACKATHON.md`) plus a mock runtime planner with a deterministic validator.
- If a live call is later made, record here: exact model ID, provider, UTC time, input, redacted response, validation result, and commit. Never log credentials.
