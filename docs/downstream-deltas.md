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

## Release revalidation: v0.22.5 (2026-11-02)

- Target: official stable release `v0.22.5`, commit `bf0203a794a07aac3ff764972ab9087baa4e4f4e`; not upstream/main or a canary.
- Provider override/logging: retained at `_resolve_runtime_agent_kwargs`, forwarding `HERMES_INFERENCE_PROVIDER` through upstream's shared `resolve_runtime_with_fallback(requested=...)`. Adopted upstream capability/request-override propagation and fallback notices instead of retaining the obsolete downstream resolver loop.
- Installed-local skill preview: retained in upstream's refactored `do_inspect()` and `inspect_skill()` paths. Regression coverage exercises real installed-skill discovery with a temporary Hermes home and rejects remote-source access.
- Registry generation compatibility: retained as an inline guarded read in upstream's `_tool_defs_cache_key`; upstream cache structure, scope and invalidation remain intact. A cache-miss/cache-hit regression covers a registry without `_generation`.
- Adopted upstream deletion of `tests/gateway/test_max_tokens_propagation.py`: legacy gateway max-token kwargs were removed upstream. Ported its downstream provider-override regression to `tests/gateway/test_downstream_provider_override.py`; did not restore obsolete token plumbing.
- Kept the four downstream operator documents under `docs/` (including this ledger), rejecting Git's directory-rename heuristic into the upstream documentation site. Existing operator links and rollback scripts remain unchanged.
- Validation is targeted, not a full-release certification. The operator maintenance scripts remain retained but were not executed against the live installation.
- Local installation adoption and gateway restart require Victor's explicit confirmation; neither is part of this release-sync PR.

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
- Reason: we honour `HERMES_INFERENCE_PROVIDER` by passing `requested=` into upstream's shared `resolve_runtime_with_fallback()` and emit `gateway runtime resolve start/result` log lines for routing diagnostics. The shared fallback resolver accepts `requested=`, so this remains additive.
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
- Scope: `model_tools.py` (`_tool_defs_cache_key` / tool-definition cache key)
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
