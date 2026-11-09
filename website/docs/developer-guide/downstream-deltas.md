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
- Status: active (reduced)
- Scope: `gateway/run.py` (`_resolve_runtime_agent_kwargs`)
- Reason: we emit the `gateway runtime resolve start/result` diagnostic log lines so operator routing can be traced from the gateway log.
- Upstream status: **partially superseded.** Upstream `v0.23.0` now honors `HERMES_INFERENCE_PROVIDER` natively in `hermes_cli/runtime_provider.py::resolve_requested_provider()` (explicit arg → config → env, with session-client-env binding), so the downstream `requested=` plumbing is no longer ours to carry. Only the two diagnostic `logger.info` lines remain as a delta, re-applied on top of upstream's `resolve_runtime_with_fallback` refactor.
- Revalidation trigger: upstream changing `resolve_runtime_provider` / `resolve_runtime_with_fallback` provider-selection semantics, or emitting equivalent resolve logging.
- Notes: downstream commit `5d230fcb8` (#11); re-applied to the refactored gateway runtime in the `v2026.8.16` sync and again (logging-only) in the `v0.23.0` sync.

### Installed local skill inspect fallback
- Status: active
- Scope: `hermes_cli/skills_hub.py` (`do_inspect`, `inspect_skill`, `_load_installed_skill_preview`, `_render_installed_skill_preview`)
- Reason: bare-name `hermes skills inspect <name>` should preview an already-installed local skill before consulting remote skill sources.
- Upstream status: not proposed. Upstream `v0.23.0` refactored `do_inspect` / `inspect_skill` around a shared `_resolve_identifier()` helper but still has no installed-local fallback, so the fallback is spliced into upstream's refactored functions rather than carried as duplicate definitions.
- Revalidation trigger: upstream adding an installed-local fallback to `do_inspect()` / `inspect_skill()`.
- Notes: downstream commit `5d230fcb8` (#11); merged cleanly into `v2026.8.16`; re-applied onto upstream's new structure in the `v0.23.0` sync.

### Mixed-version tool-registry generation compatibility
- Status: active
- Scope: `model_tools.py` (`_registry_generation` / `_tool_defs_cache_key`)
- Reason: a long-lived process may retain a pre-generation `ToolRegistry` object while newer source code is loaded; a guarded generation read avoids a startup/refresh crash without changing normal cache invalidation.
- Upstream status: **partially superseded / re-applied.** Upstream `v0.23.0` restructured the tool-definition memo (extracted `_tool_defs_cache_key()` and `_live_tool_defs_entry()`, added a `check_fn_cache_epoch()` key component and verdict-window expiry) but reads `registry._generation` **unguarded** in `_tool_defs_cache_key()`. The downstream guard (`_registry_generation()` via `getattr(registry, "_generation", 0)`) is retained and wired into upstream's new key builder.
- Revalidation trigger: upstream adopting a migration-safe registry generation accessor or eliminating mixed-version reload paths.
- Notes: downstream MCP hardening commits preceding #16. **New exposure from `v0.23.0`:** upstream also reads `registry._generation` unguarded in `tools/mcp_tool_agent.py` (3 sites), `hermes_cli/tools_config.py`, and `agent/agent_init.py`. These are upstream-owned call sites outside this delta's original scope; flagged for review rather than expanded here.

---

## Removed / upstreamed deltas

Move entries here after they are no longer active.

### Gateway `HERMES_INFERENCE_PROVIDER` `requested=` plumbing — SUPERSEDED upstream (2026-11-09 / v0.23.0 sync)
- Status: dropped (logging portion retained — see active entry above)
- Scope: was `gateway/run.py` (`_resolve_runtime_agent_kwargs` passing `requested=` into `resolve_runtime_provider`)
- Reason it existed: the managed gateway service sets `HERMES_INFERENCE_PROVIDER` to override the provider read from `config.yaml`.
- Resolution: upstream `v0.23.0` `resolve_requested_provider()` now resolves explicit arg → config → `HERMES_INFERENCE_PROVIDER` natively (including session-client-env binding), and the gateway resolves through `resolve_runtime_with_fallback`. The `requested=` call-site plumbing was dropped; only the downstream diagnostic `logger.info` lines were retained.

### Downstream `tests/gateway/test_max_tokens_propagation.py` env-override test — DROPPED (2026-11-09 / v0.23.0 sync)
- Status: dropped
- Scope: was `tests/gateway/test_max_tokens_propagation.py`
- Reason it existed: asserted the gateway forwarded `HERMES_INFERENCE_PROVIDER` into runtime resolution.
- Resolution: upstream `v0.23.0` deleted the file entirely, and the behavior is now covered by upstream's native `resolve_requested_provider`. The downstream test monkeypatched `resolve_runtime_provider`, which the gateway no longer calls directly, so it would fail; the deletion was accepted.

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
