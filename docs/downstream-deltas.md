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

### Slack send_message explicit target + thread routing
- Status: active
- Scope: `tools/send_message_tool.py`, `tests/tools/test_send_message_tool.py`
- Reason: our Slack workflow depends on correct handling of explicit channel targets and thread targets when using `send_message`.
- Upstream status: not proposed
- Revalidation trigger: upstream changes to Slack routing semantics or our Slack delivery requirements changing.
- Notes: local downstream work included commits such as `ac773dce9`, `65893239b`, `5b44e5b7e`.

---

## Removed / upstreamed deltas

Move entries here after they are no longer active.
