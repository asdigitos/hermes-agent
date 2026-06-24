# Downstream deltas

This file tracks behavior that intentionally differs between our fork and official `NousResearch/hermes-agent`.

Update this file whenever a downstream-only patch is added, removed, or superseded by upstream.

## How to use this file

For every downstream-only patch, record:

- **Status**: active / upstreamed / dropped / under review
- **Scope**: module(s) or subsystem(s) affected
- **Reason**: why the delta exists
- **Upstream status**: not proposed / proposed / merged upstream / rejected / replaced upstream
- **Revalidation trigger**: what should cause us to revisit the patch

If upstream later makes the patch unnecessary, mark it and remove the code in the next sync PR.

---

## Active downstream deltas

### Template

```md
### <short patch name>
- Status: active
- Scope: <files or subsystem>
- Reason: <why this must differ from upstream>
- Upstream status: <not proposed / proposed / merged upstream / rejected / replaced upstream>
- Revalidation trigger: <what event means we should revisit this>
- Notes: <optional links to commits / PRs / incidents>
```

### Slack thinking-steps card + tool-call record
- Status: active
- Scope: `gateway/run.py` (`send_progress_messages` / `_drive_thinking_card` / `_slack_card_active`), `gateway/platforms/slack.py`, `gateway/stream_consumer.py`
- Reason: our Slack UX collapses the per-tool wall of edited messages into one self-updating "thinking card" via `chat.startStream`/`appendStream`/`stopStream`, keeps a full tool-call record across paginated cards, and suppresses interim status/commentary so the card body stays clean until finalize. Upstream has no equivalent.
- Upstream status: not proposed
- Revalidation trigger: upstream adding native Slack streaming-card support, or any further upstream refactor of `send_progress_messages` / the progress queue.
- Notes: downstream commits `e11d6e330` (#6), `1d2870945` (#12). During the 2026-06-24 sync these call sites were re-integrated on top of upstream's refactored progress loop (`progress_grouping`, `_roll_progress_overflow_if_needed`). NEEDS gateway smoke-test against a live Slack thread.

### Gateway runtime-provider routing + resolve logging
- Status: active
- Scope: `gateway/run.py` (`_resolve_runtime_provider_credentials`)
- Reason: we honour `HERMES_INFERENCE_PROVIDER` by passing `requested=` into `resolve_runtime_provider()` and emit a `gateway runtime resolve start/result` log line for routing diagnostics. `resolve_runtime_provider` accepts `requested=` upstream, so this is additive.
- Upstream status: not proposed (param is upstream-compatible; only the call-site arg + logging are ours)
- Revalidation trigger: upstream changing `resolve_runtime_provider` provider-selection semantics.
- Notes: downstream commit `5d230fcb8` (#11).

---

## Removed / upstreamed deltas

Move entries here after they are no longer active.

### Slack send_message explicit target + thread routing — SUPERSEDED upstream (2026-06-24 sync)
- Status: dropped
- Scope: was `tools/send_message_tool.py`, `tests/tools/test_send_message_tool.py`
- Reason it existed: correct handling of explicit Slack channel/thread targets in `send_message`.
- Resolution: upstream `v2026.6.19` now implements Slack thread targets, explicit-target detection, and the U→D (user-id → DM conversation) resolution path natively (`_SLACK_THREAD_TARGET_RE`, `is_explicit = chat_id[0] not in {"U","W"}`, `_send_slack(..., thread_ts=...)`). The downstream patch (commit `b9177ed31`, #3) was a strict subset, so the file and its tests were resolved entirely to upstream.

### Gateway placeholder-MEDIA `isfile` guard in `extract_media` — SUPERSEDED upstream (2026-06-24 sync)
- Status: dropped
- Scope: was `gateway/platforms/base.py` (`extract_media`)
- Reason it existed: stop bare `MEDIA:/example/path` text in skills/docs from becoming bogus uploads.
- Resolution: upstream now masks MEDIA: in code/quote/JSON spans (`_mask_protected_spans`, `_mask_json_string_media`) and gates actual delivery through `extract_local_files` (which already requires `os.path.isfile`) plus a strict allowlist/recency validator. The downstream `isfile` check in `extract_media` was redundant and broke upstream's extraction tests, so `extract_media` was resolved to upstream.
