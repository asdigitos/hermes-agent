# Local Hermes installation upgrade / rollback SOP

This SOP defines how to upgrade or roll back the **local running Hermes installation** for our downstream fork.

Scope:

- local checkout used by the real Hermes runtime
- local CLI / gateway code refresh
- downstream-fork commit adoption on the local machine

Out of scope:

- routine upstream-drift checks
- preparing integration branches / PRs in worktrees
- fork maintenance that does **not** change the running local installation

## Hard rule

**Never upgrade or roll back the local running Hermes installation without explicit confirmation from Victor.**

Scheduled automation may prepare branches, PRs, reports, and validation results. It must stop before touching the live installation.

## Runtime location model

Current runtime repository:

```bash
~/.hermes/hermes-agent
```

Current runtime may be on a branch other than `origin/main`, so first verify what is actually running instead of assuming.

## SOP goals

1. make upgrades reproducible
2. make rollbacks fast and low-risk
3. preserve an audit trail for what commit the local runtime adopted
4. avoid treating the live checkout as a scratchpad

## A. Pre-change checklist

Run these checks before **any** upgrade or rollback:

```bash
cd ~/.hermes/hermes-agent
command -v hermes
hermes --version
git branch --show-current
git rev-parse HEAD
git status --short --branch
git remote -v
```

Record in the change note / Slack report:

- current branch
- current HEAD SHA
- target branch / target SHA
- reason for change
- relevant PR(s)
- validation plan

### Safety gates

Do **not** proceed if any of these are true unless Victor explicitly approves the exception:

- runtime checkout has uncommitted production-relevant changes
- target commit is not present on `origin`
- required validation has not been run
- it is unclear which launchd service / gateway process is serving traffic

## B. Accepted upgrade sources

Upgrades should come from one of these sources only:

1. `origin/main`
2. a reviewed downstream PR branch on `origin`
3. a specific commit SHA that exists on `origin`
4. a release tag that the team intentionally chose

Do **not** upgrade from:

- unpushed local commits
- a dirty worktree
- an ad-hoc detached HEAD with no audit trail

## C. Preferred upgrade method

### 1) Confirm target

Example:

```bash
cd ~/.hermes/hermes-agent
git fetch origin --prune
git fetch upstream --prune
git log --oneline --decorate -n 20 origin/main
```

Decide the target explicitly:

- target branch: `origin/main` or `origin/<topic>`
- target SHA: exact commit to adopt locally

### 2) Snapshot current runtime state for rollback

Create a rollback note before changing anything:

```bash
cd ~/.hermes/hermes-agent
PREV_BRANCH=$(git branch --show-current)
PREV_SHA=$(git rev-parse HEAD)
printf 'branch=%s\nsha=%s\ntime=%s\n' "$PREV_BRANCH" "$PREV_SHA" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

Store those values in the change report. They are the minimum rollback handle.

### 3) Adopt the target commit in the runtime checkout

If adopting `origin/main`:

```bash
cd ~/.hermes/hermes-agent
git fetch origin --prune
git switch main
git reset --hard origin/main
```

If adopting a reviewed branch from the fork:

```bash
cd ~/.hermes/hermes-agent
git fetch origin --prune
git switch -C runtime/<topic> origin/<topic>
```

If adopting a specific commit that is already in the fork:

```bash
cd ~/.hermes/hermes-agent
git fetch origin --prune
git switch --detach <target_sha>
```

Notes:

- prefer `main` when the target is already merged
- use a named runtime branch only when intentionally running ahead of `main`
- detached HEAD is acceptable only for a short, explicit, auditable test window

## D. Validation after code adoption

Run the smallest validation set that still covers the changed surface area.

Examples:

```bash
cd ~/.hermes/hermes-agent
./venv/bin/python -m pytest tests/tools/test_send_message_tool.py -q
```

or

```bash
cd ~/.hermes/hermes-agent
./venv/bin/python -m pytest tests/test_model_tools.py tests/tools/test_send_message_tool.py -q
```

Also verify the working tree is clean:

```bash
cd ~/.hermes/hermes-agent
git status --short --branch
```

## E. Reload the running gateway cleanly

### Routine restart

Use for ordinary restarts when the service definition itself did not change:

```bash
hermes gateway restart
```

### Fully clean refresh

Use after Hermes code, Python path, virtualenv, launchd env, or service wiring changes:

```bash
hermes gateway stop
hermes gateway install --force
hermes gateway start
```

On this macOS host, prefer the **fully clean refresh** after real installation updates.

## F. Post-upgrade verification

Verify all of the following:

```bash
hermes gateway status
launchctl list | grep -i hermes
pgrep -af 'hermes_cli.main gateway|hermes-slack|hermes gateway'
```

Then verify the runtime checkout identity again:

```bash
cd ~/.hermes/hermes-agent
git branch --show-current
git rev-parse HEAD
hermes --version
```

Report:

- adopted branch / SHA
- validation results
- restart method used
- gateway status

## G. Rollback triggers

Rollback is appropriate when any of these happen after adoption:

- gateway fails to boot cleanly
- a targeted regression test fails
- the live workflow regresses
- the wrong branch / SHA was adopted
- duplicate-service / mixed-process behavior appears

## H. Rollback procedure

### 1) Identify the last known good state

Use the pre-change snapshot:

- previous branch
- previous SHA

### 2) Restore the prior code state

If returning to the previous branch tip is correct:

```bash
cd ~/.hermes/hermes-agent
git fetch origin --prune
git switch <previous_branch>
```

If returning to the exact previous commit is required:

```bash
cd ~/.hermes/hermes-agent
git switch --detach <previous_sha>
```

If the previous good state was the previous remote branch head:

```bash
cd ~/.hermes/hermes-agent
git fetch origin --prune
git switch -C <previous_branch> origin/<previous_branch>
```

### 3) Cleanly reload the gateway

```bash
hermes gateway stop
hermes gateway install --force
hermes gateway start
```

### 4) Re-run the key verification

```bash
hermes gateway status
cd ~/.hermes/hermes-agent
git branch --show-current
git rev-parse HEAD
```

## I. Change record template

Every local installation upgrade / rollback should record:

- change type: upgrade or rollback
- approved by: Victor
- previous branch / SHA
- new branch / SHA
- related PR / issue / reason
- tests run
- restart method used
- final gateway status
- follow-up actions

## J. Operational boundaries for cron / automation

Automation may do these without approval:

- fetch `origin` / `upstream`
- compare drift
- create worktrees
- create integration branches
- merge upstream in a worktree
- run validation in a worktree
- push branches
- open PRs
- send reports

Automation must **not** do these without explicit approval from Victor:

- switch the runtime checkout used by the local installation
- reset the live runtime branch to a new commit
- run `hermes update`
- restart / reinstall the local gateway as part of adopting new code
- roll back the local installation

## K. Practical recommendation for this fork

For this environment, use a two-step operating model:

1. **fork maintenance path**
   - prepare and validate updates in worktrees
   - merge reviewed changes into `origin/main`
2. **local installation adoption path**
   - separately ask Victor for confirmation
   - adopt a specific reviewed commit into `~/.hermes/hermes-agent`
   - perform a clean gateway refresh
   - verify and report
