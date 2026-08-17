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

### Gateway runtime-provider routing + resolve logging
- Status: active
- Scope: `gateway/run.py` (`_resolve_runtime_agent_kwargs`)
- Reason: we honour `HERMES_INFERENCE_PROVIDER` by passing `requested=` into `resolve_runtime_provider()` and emit a `gateway runtime resolve start/result` log line for routing diagnostics. `resolve_runtime_provider` accepts `requested=` upstream, so this is additive.
- Upstream status: not proposed (param is upstream-compatible; only the call-site arg + logging are ours)
- Revalidation trigger: upstream changing `resolve_runtime_provider` provider-selection semantics.
- Notes: downstream commit `5d230fcb8` (#11), re-applied to the refactored gateway runtime in the `v2026.8.16` release sync.

### Installed local skill inspect fallback
- Status: active
- Scope: `hermes_cli/skills_hub.py`
- Reason: bare-name `hermes skills inspect <name>` should preview an already-installed local skill before consulting remote skill sources.
- Upstream status: not proposed
- Revalidation trigger: upstream adding an installed-local fallback to `do_inspect()` / `inspect_skill()`.
- Notes: downstream commit `5d230fcb8` (#11); the fallback merged cleanly into `v2026.8.16`.

### Mixed-version tool-registry generation compatibility
- Status: active
- Scope: `model_tools.py` (`_registry_generation` / tool-definition cache key)
- Reason: a long-lived process may retain a pre-generation `ToolRegistry` object while newer source code is loaded; a guarded generation read avoids a startup/refresh crash without changing normal cache invalidation.
- Upstream status: not proposed
- Revalidation trigger: upstream adopting a migration-safe registry generation accessor or eliminating mixed-version reload paths.
- Notes: downstream MCP hardening commits preceding #16; re-integrated with the release's scoped, locked tool-definition cache.

---

## Removed / upstreamed deltas

Move entries here after they are no longer active.

### Slack thinking-steps card + tool-call record — SUPERSEDED upstream (2026-08-17 sync)
- Status: dropped
- Scope: was `gateway/run.py`, `gateway/platforms/slack.py`, `gateway/stream_consumer.py`, and `tests/test_slack_thinking_card_overflow.py`
- Reason it existed: collapse Slack tool progress into a self-updating `chat.startStream` task card with a complete tool-call record and final answer.
- Resolution: upstream `v2026.8.16` moved Slack to `plugins/platforms/slack/adapter.py` and now ships native Slack task cards keyed by authoritative tool-call IDs, using `chat.startStream` / `appendStream` / `stopStream`. The downstream implementation targeted the deleted legacy adapter and old in-function progress runner, so it was removed in favor of the upstream implementation.

### MCP add argparse destination compatibility — SUPERSEDED upstream (2026-08-17 sync)
- Status: dropped
- Scope: was `hermes_cli/mcp_config.py` and related parser tests
- Reason it existed: avoid the nested MCP `--command` flag overwriting the top-level subcommand destination.
- Resolution: upstream `v2026.8.16` uses the dedicated `mcp_command` destination. Transitional `mcp_stdio_command` / legacy-field compatibility was intentionally not carried forward.

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
