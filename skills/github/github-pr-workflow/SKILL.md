---
name: github-pr-workflow
description: "GitHub PR lifecycle: branch, commit, open, CI, merge."
version: 1.3.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Pull-Requests, CI/CD, Git, Automation, Merge]
    related_skills: [github-auth, github-code-review]
---

# GitHub Pull Request Workflow

Complete guide for managing the PR lifecycle. Each section shows the `gh` way first, then the `git` + `curl` fallback for machines without `gh`.

## Prerequisites

- Authenticated with GitHub (see `github-auth` skill)
- Inside a git repository with a GitHub remote

### Quick Auth Detection

```bash
# Determine which method to use throughout this workflow
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="git"
  # Ensure we have a token for API calls
  if [ -z "$GITHUB_TOKEN" ]; then
    if [ -f ~/.hermes/.env ] && grep -q "^GITHUB_TOKEN=" ~/.hermes/.env; then
      GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" ~/.hermes/.env | head -1 | cut -d= -f2 | tr -d '\n\r')
    elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
      GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
    fi
  fi
fi
echo "Using: $AUTH"
```

### Extracting Owner/Repo from the Git Remote

Many `curl` commands need `owner/repo`. Extract it from the git remote:

```bash
# Works for both HTTPS and SSH remote URLs
REMOTE_URL=$(git remote get-url origin)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
echo "Owner: $OWNER, Repo: $REPO"
```

---

## 1. Branch Creation

This part is pure `git` — identical either way:

```bash
# Make sure you're up to date
git fetch origin
git checkout main && git pull origin main

# Create and switch to a new branch
git checkout -b feat/add-user-authentication
```

Branch naming conventions:
- `feat/description` — new features
- `fix/description` — bug fixes
- `refactor/description` — code restructuring
- `docs/description` — documentation
- `ci/description` — CI/CD changes

## 2. Making Commits

Use the agent's file tools (`write_file`, `patch`) to make changes, then commit:

```bash
# Stage specific files
git add src/auth.py src/models/user.py tests/test_auth.py

# Commit with a conventional commit message
git commit -m "feat: add JWT-based user authentication

- Add login/register endpoints
- Add User model with password hashing
- Add auth middleware for protected routes
- Add unit tests for auth flow"
```

Commit message format (Conventional Commits):
```
type(scope): short description

Longer explanation if needed. Wrap at 72 characters.
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `ci`, `chore`, `perf`

## 2.5 Pre-Push Local Hygiene (Mandatory)

**Apply these checks before any `git push`.** This section prevents the "mixed commit with config pollution" pattern that damages PR history. Skip any of these and you risk contaminating a clean PR branch with unrelated personal changes.

### Check 1: Config / Personal File Tracking

Detect tracked personal config files that should not be in git:

```bash
# Check if any personal config files are staged or tracked
git ls-files config.yaml .env cli-config.yaml 2>/dev/null | while read f; do
  echo "⚠️  WARNING: $f is tracked by git. Personal config files should not be in version control."
done

# Check what's staged right now
git diff --cached --name-only | grep -E 'config\.yaml$|\.env$|cli-config\.yaml$|export' && \
  echo "❌ Staged changes include personal config files. Add to .gitignore first."
```

**If found:** Do NOT push a commit that tracks personal config. Fix immediately:

```bash
echo "config.yaml" >> .gitignore
git rm --cached config.yaml
git commit -m "chore: gitignore config.yaml — personal config, not source code"
```

> ⚠️ **Stash trap:** If you `git rm --cached` + gitignore on one branch, then switch to another and try to pop a stash that modifies config.yaml, git will refuse. Cherry-pick specific files from the stash instead:
> ```bash
> git checkout stash@{N} -- <specific-files-you-need>
> git stash drop stash@{N}
> ```

### Check 2: Branch Name Validation

Verify the branch name follows a recognizable pattern:

```bash
BRANCH=$(git branch --show-current)

# Pattern: type/description (kebab-case)
if ! echo "$BRANCH" | grep -qE '^(feature|feat|fix|bugfix|hotfix|chore|docs|refactor|test|ci|release)/[a-z0-9]+(-[a-z0-9]+)*$'; then
  echo "⚠️  Branch name '$BRANCH' doesn't follow 'type/description' convention."
  echo "   Suggested: fix/login-redirect, feat/user-auth, chore/upgrade-deps"
fi
```

### Check 3: Commit Atomicity Verification

Ensure each commit in the branch contains only one logical change:

```bash
# Show staged files grouped by area
echo "=== Staged changes ==="
git diff --cached --stat

# For commits already in the branch (but not on base):
BASE=$(git merge-base HEAD origin/main 2>/dev/null || git merge-base HEAD upstream/main 2>/dev/null || echo "HEAD~1")
echo "=== Commits in this branch (vs $BASE) ==="
git log --oneline "$BASE..HEAD"
```

**Red flags:**
- A single commit touches both `config.yaml` AND new scripts → likely mixed
- A commit modifies `.github/workflows/` alongside feature code → belongs in separate PR
- A commit's diffstat shows files in 3+ unrelated directories → split it

**Quick split (if the commit is the latest, not pushed):**
```bash
# Soft-unstage the top commit, then re-commit each part separately
git reset --soft HEAD~1
git add -p    # interactively pick hunks for the first logical change
git commit -m "fix: first logical change"
git add -p    # pick the next set
git commit -m "chore: second logical change"
# ... repeat until working tree is clean
```

> If the branch has also drifted from its intended base (e.g., fork PR branch), save the full change set first, reset the branch, then split on a new branch. See `references/commit-atomicity.md` → "Recovery: Splitting a Mixed Commit" for the full procedure.

### Check 4: Fork Sync (Upstream + Fork Branch Drift Detection)

Before pushing to your fork, confirm you're not diverged from upstream AND that your local branch hasn't drifted from the fork's copy:

```bash
# For repos with an upstream remote
if git remote | grep -q upstream; then
  echo "=== Upstream status ==="
  git fetch upstream 2>&1
  BEHIND=$(git rev-list --count HEAD..upstream/$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main) 2>/dev/null)
  AHEAD=$(git rev-list --count upstream/$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)..HEAD 2>/dev/null)
  echo "Behind upstream: $BEHIND commits"
  echo "Ahead of upstream: $AHEAD commits"
  if [ "$BEHIND" -gt 0 ] 2>/dev/null; then
    echo "❌ Branch is behind upstream. Run: git rebase upstream/$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"
  fi
fi

# Check for local-only commits not on the fork remote (if a fork remote exists besides origin)
BRANCH=$(git branch --show-current)
for REMOTE in $(git remote); do
  if [ "$REMOTE" != "origin" ] && [ "$REMOTE" != "upstream" ]; then
    git fetch "$REMOTE" "$BRANCH" 2>/dev/null
    AHEAD=$(git rev-list --count "$REMOTE/$BRANCH..HEAD" 2>/dev/null || echo 0)
    if [ "$AHEAD" -gt 0 ] 2>/dev/null; then
      echo "⚠️  Local branch has $AHEAD commits NOT on $REMOTE/$BRANCH (fork copy)"
      echo "   git log --oneline $REMOTE/$BRANCH..HEAD"
      echo "   If these don't belong to the PR, create a separate branch for them."
    fi
  fi
done
```

### Check 5: Commit Message Format Verification

Verify each unpushed commit follows conventional commits:

```bash
BASE=$(git merge-base HEAD origin/main 2>/dev/null || git merge-base HEAD upstream/main 2>/dev/null || echo "HEAD~1")
git log --format="%h %s" "$BASE..HEAD" | while read hash subject; do
  if ! echo "$subject" | grep -qE '^(feat|fix|refactor|docs|test|ci|chore|perf|style|build|revert)(\([a-z0-9._-]+\))?!?:\s.+'; then
    echo "⚠️  Commit $hash: '$subject' doesn't follow conventional commits"
    echo "   Expected: type(scope): description"
  fi
done
```

### Check 6: Confirm Before Push (For Upstream PR Branches)

If pushing to a fork from which you plan to open an upstream PR:

```bash
# Show what will land upstream
echo "=== Summary for user confirmation ==="
git log --oneline "$BASE..HEAD"
git diff --stat "$BASE..HEAD"
echo "---"
echo "Does this branch contain ONLY changes intended for this PR?"
```

**If any check fails, do NOT push automatically.** Present findings to the user and ask for direction (split commits, add to .gitignore, rebase, or push anyway with acknowledgment).

### Incident Reference

See `references/commit-atomicity.md` for a real-world case where skipping these checks resulted in 4 unrelated changes in a single commit on a PR branch.

---

## 3. Pushing and Creating a PR

### Push the Branch (same either way)

```bash
git push -u origin HEAD
```

### Create the PR

**With gh:**

```bash
gh pr create \
  --title "feat: add JWT-based user authentication" \
  --body "## Summary
- Adds login and register API endpoints
- JWT token generation and validation

## Test Plan
- [ ] Unit tests pass

Closes #42"
```

Options: `--draft`, `--reviewer user1,user2`, `--label "enhancement"`, `--base develop`

**With git + curl:**

```bash
BRANCH=$(git branch --show-current)

curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/$OWNER/$REPO/pulls \
  -d "{
    \"title\": \"feat: add JWT-based user authentication\",
    \"body\": \"## Summary\nAdds login and register API endpoints.\n\nCloses #42\",
    \"head\": \"$BRANCH\",
    \"base\": \"main\"
  }"
```

The response JSON includes the PR `number` — save it for later commands.

To create as a draft, add `"draft": true` to the JSON body.

## 4. Monitoring CI Status

### Check CI Status

**With gh:**

```bash
# One-shot check
gh pr checks

# Watch until all checks finish (polls every 10s)
gh pr checks --watch
```

**With git + curl:**

```bash
# Get the latest commit SHA on the current branch
SHA=$(git rev-parse HEAD)

# Query the combined status
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/status \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Overall: {data['state']}\")
for s in data.get('statuses', []):
    print(f\"  {s['context']}: {s['state']} - {s.get('description', '')}\")"

# Also check GitHub Actions check runs (separate endpoint)
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/check-runs \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
for cr in data.get('check_runs', []):
    print(f\"  {cr['name']}: {cr['status']} / {cr['conclusion'] or 'pending'}\")"
```

### Poll Until Complete (git + curl)

```bash
# Simple polling loop — check every 30 seconds, up to 10 minutes
SHA=$(git rev-parse HEAD)
for i in $(seq 1 20); do
  STATUS=$(curl -s \
    -H "Authorization: token $GITHUB_TOKEN" \
    https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/status \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])")
  echo "Check $i: $STATUS"
  if [ "$STATUS" = "success" ] || [ "$STATUS" = "failure" ] || [ "$STATUS" = "error" ]; then
    break
  fi
  sleep 30
done
```

## 5. Auto-Fixing CI Failures

When CI fails, diagnose and fix. This loop works with either auth method.

### Step 1: Get Failure Details

**With gh:**

```bash
# List recent workflow runs on this branch
gh run list --branch $(git branch --show-current) --limit 5

# View failed logs
gh run view <RUN_ID> --log-failed
```

**With git + curl:**

```bash
BRANCH=$(git branch --show-current)

# List workflow runs on this branch
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/actions/runs?branch=$BRANCH&per_page=5" \
  | python3 -c "
import sys, json
runs = json.load(sys.stdin)['workflow_runs']
for r in runs:
    print(f\"Run {r['id']}: {r['name']} - {r['conclusion'] or r['status']}\")"

# Get failed job logs (download as zip, extract, read)
RUN_ID=<run_id>
curl -s -L \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/actions/runs/$RUN_ID/logs \
  -o /tmp/ci-logs.zip
cd /tmp && unzip -o ci-logs.zip -d ci-logs && cat ci-logs/*.txt
```

### Step 2: Fix and Push

After identifying the issue, use file tools (`patch`, `write_file`) to fix it:

```bash
git add <fixed_files>
git commit -m "fix: resolve CI failure in <check_name>"
git push
```

### Step 3: Verify

Re-check CI status using the commands from Section 4 above.

### Auto-Fix Loop Pattern

When asked to auto-fix CI, follow this loop:

1. Check CI status → identify failures
2. Read failure logs → understand the error
3. Use `read_file` + `patch`/`write_file` → fix the code
4. `git add . && git commit -m "fix: ..." && git push`
5. Wait for CI → re-check status
6. Repeat if still failing (up to 3 attempts, then ask the user)

## 6. Merging

**With gh:**

```bash
# Squash merge + delete branch (cleanest for feature branches)
gh pr merge --squash --delete-branch

# Enable auto-merge (merges when all checks pass)
gh pr merge --auto --squash --delete-branch
```

**With git + curl:**

```bash
PR_NUMBER=<number>

# Merge the PR via API (squash)
curl -s -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/merge \
  -d "{
    \"merge_method\": \"squash\",
    \"commit_title\": \"feat: add user authentication (#$PR_NUMBER)\"
  }"

# Delete the remote branch after merge
BRANCH=$(git branch --show-current)
git push origin --delete $BRANCH

# Switch back to main locally
git checkout main && git pull origin main
git branch -d $BRANCH
```

Merge methods: `"merge"` (merge commit), `"squash"`, `"rebase"`

### Enable Auto-Merge (curl)

```bash
# Auto-merge requires the repo to have it enabled in settings.
# This uses the GraphQL API since REST doesn't support auto-merge.
PR_NODE_ID=$(curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['node_id'])")

curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/graphql \
  -d "{\"query\": \"mutation { enablePullRequestAutoMerge(input: {pullRequestId: \\\"$PR_NODE_ID\\\", mergeMethod: SQUASH}) { clientMutationId } }\"}"
```

## 7. Complete Workflow Example

```bash
# 1. Start from clean main
git checkout main && git pull origin main

# 2. Branch
git checkout -b fix/login-redirect-bug

# 3. (Agent makes code changes with file tools)

# 4. Commit
git add src/auth/login.py tests/test_login.py
git commit -m "fix: correct redirect URL after login

Preserves the ?next= parameter instead of always redirecting to /dashboard."

# 5. Push
git push -u origin HEAD

# 6. Create PR (picks gh or curl based on what's available)
# ... (see Section 3)

# 7. Monitor CI (see Section 4)

# 8. Merge when green (see Section 6)
```

## PR Discipline (Mandatory Gates)

These gates apply BEFORE any PR submission, branch deletion, or force push. Violations here damage the user's GitHub reputation.

### Gate 1: Search Existing PRs First

Before creating any PR to an upstream repository:

```bash
curl -s "https://api.github.com/search/issues?q=repo:$OWNER/$REPO+type:pr+KEYWORD&per_page=30" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f'  #{i[\"number\"]} [{i[\"state\"]}] {i[\"title\"]} by @{i[\"user\"][\"login\"]} ({i[\"created_at\"][:10]})') for i in d.get('items',[])]"
```

Search BOTH open and closed PRs. If any PR already exists with the same fix, show results to the user and ask what to do. Do NOT create a competing PR autonomously.

### Gate 2: Ask Before Any PR Action

| Action | Must ask user? | Why |
|--------|---------------|-----|
| Create PR to upstream repo | **YES** | Reputation risk; prior art must be checked |
| Close PR | **YES** | Irreversible from GitHub's activity log |
| Reopen PR | **YES** | Force-pushed branches cannot be reopened |
| Delete remote branch | **YES** | Auto-closes associated PR |
| Force push | **YES** | Makes PR unreopenable |

### Gate 3: Clean Branch Check

Before pushing, verify the branch contains ONLY intended commits:

```bash
git log --oneline "origin/$BASE..HEAD" --not --remotes=upstream
git diff --stat "upstream/$BASE..HEAD"
```

**Reject if:** the diff includes unrelated config changes, other features, `.github/workflows/` files, or cleanup commits.

### Gate 4: PR Body Links Issues

Every PR body must include `Closes #N` or `Addresses #N` or `See also #N`. Skipping this creates orphan PRs.

### Gate 5: Duplicate Handling

If a reviewer marks your PR as duplicate: do NOT create a replacement. Instead, ask the user: "The same fix exists at #NUM. Should I contribute our verification data there, or do something else?"

### Pitfall: Don't Write a Plugin — Extend the Built-In Approvals System

Hermes already has a built-in dangerous command system in `tools/approval.py`. It intercepts `terminal()` calls via `pre_tool_call` internally (not a plugin) and prompts the user for approval. Its `DANGEROUS_PATTERNS` list already covers:

- `git reset --hard`
- `git push --force` / `git push -f` (also in `command_allowlist` in config.yaml)
- `git clean -f`
- `git branch -D`

**Do NOT write a separate Hermes Plugin (`pre_tool_call` hook) to intercept git operations.** The approvals system already does this at the framework level — a second plugin adds complexity without benefit. Instead:

1. **If a git pattern is missing**, add it to `DANGEROUS_PATTERNS` in `tools/approval.py`.
2. **If a pattern should bypass approval**, add it to `command_allowlist` in `config.yaml`.
3. **If you want fine-grained deny/allow per pattern**, use the approvals config sections.

**Currently missing from DANGEROUS_PATTERNS (as of 2026-06-03):** `git push --delete` (`git push <remote> --delete <branch>`). If this operation needs guarding, add a pattern like:
```python
(r'\\bgit\\s+push\\b.*--delete\\b', "git push --delete (removes remote branch)")
```

#### Correct layer division

| What | Layer | Mechanism |
|------|-------|-----------|
| Branch naming / config-file / commit atomicity checks | **Layer 1: Git pre-push hook** | Local git hook, runs outside Hermes process. Genuinely new — no built-in replacement. |
| Destructive git via terminal tool (push --force, --delete, branch -D) | **Layer 2: Hermes approvals system** | Built-in `tools/approval.py` + `approvals.mode`. Extend DANGEROUS_PATTERNS, don't write a plugin. |
| GitHub API operations (delete branch, close PR via curl) | **Layer 3: pre_tool_call plugin** | Only needed if the GitHub REST API is an attack vector. Rare. |

### Incident Reference

See `references/pr-flood-2026-06-03.md` for the full incident report that generated these gates (5 PRs in 2 hours to upstream, one deleting CI workflows).
See `references/git-guard-system-2026-06-03.md` for the git pre-push hook deployment that enforces these gates (note: the Plugin layer described there was later found redundant with `tools/approval.py` — see Pitfall above).
See `references/multi-agent-evaluation-2026-06-03.md` for the multi-agent evaluation that validated and refined these gates against the `local-git-discipline` / `github-issue-pr-discipline` skill proposal.



## Useful PR Commands Reference

| Action | gh | git + curl |
|--------|-----|-----------|
| List my PRs | `gh pr list --author @me` | `curl -s -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$OWNER/$REPO/pulls?state=open"` |
| View PR diff | `gh pr diff` | `git diff main...HEAD` (local) or `curl -H "Accept: application/vnd.github.diff" ...` |
| Add comment | `gh pr comment N --body "..."` | `curl -X POST .../issues/N/comments -d '{"body":"..."}'` |
| Request review | `gh pr edit N --add-reviewer user` | `curl -X POST .../pulls/N/requested_reviewers -d '{"reviewers":["user"]}'` |
| Close PR | `gh pr close N` | `curl -X PATCH .../pulls/N -d '{"state":"closed"}'` |
| Check out someone's PR | `gh pr checkout N` | `git fetch origin pull/N/head:pr-N && git checkout pr-N` |
