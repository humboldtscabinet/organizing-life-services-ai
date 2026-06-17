# Git History Secret Purge Runbook

Use this only if the repository needs historical transcript blobs removed from
Git history, not just removed from the current tree.

Current state:

- The current `main` tree no longer tracks `conversations/raw/`,
  `conversations/markdown/`, or `conversations/INDEX.md`.
- Future transcript payloads and key/token-like audit artifacts are ignored.
- A private local copy of the old transcript archive may exist at
  `~/.ols/private/conversations/legacy-git-archive-2026-06-17/`.
- Older Git commits still contain the removed transcript blobs until history is
  rewritten.

## When To Run This

Run this only after the owner explicitly approves a history rewrite and force
push. Everyone with a clone will need to fetch/reset or reclone afterward.

Do not run it during normal feature work.

## Before Rewriting

1. Confirm GitHub `main` is quiet: no open work, deploys, or active PR merges.
2. Make a local backup bundle:

   ```bash
   git bundle create ../ols-before-history-purge-$(date +%Y%m%d).bundle --all
   ```

3. Confirm `git-filter-repo` is installed:

   ```bash
   git filter-repo --help >/dev/null
   ```

   If missing:

   ```bash
   brew install git-filter-repo
   ```

4. Rotate any still-relevant sessions or secrets found in historical
   transcripts before assuming the risk is closed. At minimum, review:

   - QuickBooks / Intuit browser sessions and URL tokens
   - Shopify app credentials if they appeared in transcripts
   - XO Gallery session tokens/cookies
   - GitHub tokens or OAuth callback URLs

## Rewrite Command

From a clean clone:

```bash
git status --short
git fetch origin main
git checkout main
git reset --hard origin/main

git filter-repo \
  --path conversations/raw/ \
  --path conversations/markdown/ \
  --path conversations/INDEX.md \
  --invert-paths
```

Verify the rewritten history:

```bash
git log -- conversations/raw conversations/markdown conversations/INDEX.md
git grep -I -n "QuickBooks\\|quickbooks\\|realmId\\|access_token=\\|refresh_token=\\|sessionid" $(git rev-list --all) -- conversations || true
```

The first command should show no history for those paths. The second command
should return no sensitive transcript hits.

## Force Push Window

After verification and explicit approval:

```bash
git push --force-with-lease origin main
```

Then refresh every deployment clone:

```bash
git fetch origin main
git checkout main
git reset --hard origin/main
git status --short
```

On the Mac mini, run the same refresh from:

```bash
/Users/aiagentecosystem/services/ols
```

Then verify:

```bash
infra/server/verify_stack.sh
```

## Aftercare

- Ask collaborators to reclone or hard-reset their clones.
- Delete old local `.git` backups only after the owner confirms the rewrite is
  accepted.
- Keep transcript backups outside this repo. The supported private archive path
  is `~/.ols/private/conversations/`.
