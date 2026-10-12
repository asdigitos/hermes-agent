Downstream upstream-sync PR checklist

## Summary

- Sync branch: `integration/upstream-YYYYMMDD`
- Base branch: `main`
- Upstream merge source: `upstream/main`

## Why this sync is happening

- [ ] regular scheduled sync
- [ ] required upstream bugfix / feature
- [ ] required security / dependency update
- [ ] other: <!-- explain -->

## Upstream review

- [ ] reviewed upstream-only commits since last sync
- [ ] checked whether any downstream patches are now obsolete
- [ ] updated `docs/downstream-deltas.md`

## Conflict review

- [ ] merge conflicts were resolved consciously, not by blind accept-ours/theirs
- [ ] downstream-specific behavior was preserved where intended
- [ ] generic fixes that should be upstreamed were identified

## Validation

- [ ] targeted tests passed
- [ ] gateway/runtime-sensitive flows were smoke-tested
- [ ] any follow-up cleanup items were documented

## Notes for reviewers

List the main conflict areas, risky modules, and any downstream deltas that remain intentionally different from upstream.
