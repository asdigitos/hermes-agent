# Downstream fork maintenance

This repository is maintained as a **long-lived downstream fork** of `NousResearch/hermes-agent`.

- `upstream` → official Hermes repository (`NousResearch/hermes-agent`)
- `origin` → our maintained fork
- `origin/main` → our stable, releasable downstream line

## Goals

1. Keep our production/runtime behavior reproducible from commits in the fork.
2. Avoid carrying important changes only as unpushed local commits.
3. Regularly ingest upstream improvements without losing our private workflow patches.
4. Minimize permanent fork drift by upstreaming generic fixes whenever practical.

## Branch model

### Long-lived branches

- `main`
  - our stable downstream baseline
  - always deployable / runnable
- `integration/upstream-YYYYMMDD`
  - temporary integration branch created when pulling from official upstream
  - used for conflict resolution, regression checks, and downstream patch review

### Short-lived branches

- `fix/...`
- `feat/...`
- `chore/...`
- `docs/...`

All local changes that matter must land in the fork through a branch and commit history. Do **not** rely on a machine-specific dirty working tree as the source of truth.

## Remote setup

Expected remotes:

```bash
git remote -v
# origin   git@github.com:<our-org-or-user>/hermes-agent.git
# upstream git@github.com:NousResearch/hermes-agent.git
```

If `upstream` is missing:

```bash
git remote add upstream git@github.com:NousResearch/hermes-agent.git
```

## Operating rules

### 1) Day-to-day downstream changes

Use this flow for our own fixes and features:

```bash
git fetch origin --prune
git switch main
git pull --ff-only origin main
git switch -c fix/<topic>
# edit, test, commit
git push -u origin fix/<topic>
# open PR into origin/main
```

Rules:

- keep commits in the fork, not only on a laptop
- prefer small PRs
- run relevant tests before pushing
- if a fix is generic, consider opening an upstream PR too

### 2) Upstream sync cadence

Recommended cadence:

- lightweight sync every 1-2 weeks
- mandatory sync after important upstream releases or when we need an upstream fix

Create an integration branch from our `main`, then merge upstream:

```bash
git fetch origin --prune
git fetch upstream --prune
git switch main
git pull --ff-only origin main
git switch -c integration/upstream-$(date +%Y%m%d)
git merge --no-ff upstream/main
```

Why merge instead of rebase for upstream sync:

- preserves a clear history of when upstream was integrated
- makes regression archaeology easier
- is safer for a long-lived shared fork

### 3) Integration review checklist

On the integration branch:

1. resolve merge conflicts
2. review `docs/downstream-deltas.md`
3. confirm each downstream-only patch is still needed
4. run targeted regression tests for touched subsystems
5. smoke-test the gateway / CLI paths impacted by the merge
6. push the integration branch and open a PR into `origin/main`

Example:

```bash
git push -u origin integration/upstream-$(date +%Y%m%d)
gh pr create \
  --base main \
  --head integration/upstream-$(date +%Y%m%d) \
  --title "chore: merge upstream Hermes into downstream fork" \
  --body-file docs/downstream-sync-pr-template.md
```

## Conflict handling policy

When upstream and downstream touch the same area:

### Prefer upstream directly when

- the upstream implementation supersedes ours cleanly
- our behavior difference was accidental, not intentional
- our patch only existed because upstream had not fixed it yet

### Preserve downstream behavior when

- the behavior is company-specific or workflow-specific
- we depend on different defaults than upstream
- the patch addresses our gateway/runtime environment specifically

If keeping downstream behavior, update `docs/downstream-deltas.md` with:

- why the patch still exists
- which files are affected
- whether upstream has a partial equivalent

## Runtime safety rule

The checkout used by the live gateway/CLI must not become a scratchpad.

Avoid doing all of the following in the runtime checkout:

- switching between unrelated branches casually
- leaving uncommitted production-relevant changes around
- testing upstream merges directly in the live checkout

Use a separate branch or `git worktree` for integration and risky edits.

## Recommended release discipline

Before updating the running Hermes instance to a new downstream commit:

1. ensure the commit exists on `origin`
2. ensure relevant tests passed
3. record the reason in PR / commit history
4. restart the gateway after code updates
5. get explicit approval from Victor before changing the live local installation

For the full upgrade / rollback procedure, see `docs/local-installation-upgrade-rollback-sop.md`.

## Local installation change boundary

Routine fork maintenance and local installation adoption are separate operations.

Allowed without extra approval:

- fetch from `origin` / `upstream`
- create worktrees
- prepare integration branches
- run validation in non-runtime worktrees
- push branches and open PRs

Not allowed without explicit approval from Victor:

- switching the live runtime checkout to a new branch / commit
- resetting the live runtime checkout to `origin/main`
- running `hermes update` for local adoption
- restarting / reinstalling the gateway as part of adopting a new local code version
- rolling back the local installation

## Suggested maintenance ownership

For each upstream sync, explicitly assign:

- **sync owner** — performs the merge and conflict resolution
- **review owner** — reviews downstream deltas and regression risk
- **runtime owner** — updates the running Hermes deployment after merge approval

## Quick command summary

### Show current fork drift

```bash
git fetch origin --prune
git fetch upstream --prune
git log --oneline --left-right --graph upstream/main...origin/main
```

### See downstream-only commits on our main

```bash
git log --oneline upstream/main..origin/main
```

### See upstream-only commits not yet merged

```bash
git log --oneline origin/main..upstream/main
```

## Related documents

- `docs/downstream-deltas.md`
- `docs/downstream-sync-pr-template.md`
