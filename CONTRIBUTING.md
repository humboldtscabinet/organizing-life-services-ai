# Contributing

## Before you start

New to the repo? Read [docs/onboarding.md](docs/onboarding.md) first.

## Branching

- `main` — always deployable. Direct pushes are OK for the project owner; collaborators should open PRs.
- Feature branches: `feat/<short-description>` or `fix/<short-description>`.
- Long-running experiments: `exp/<short-description>`.

## Commit messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Common types:**

| Type | When to use |
|---|---|
| `feat` | New functionality (script, endpoint, integration) |
| `fix` | Bug fix |
| `docs` | Documentation only (audits, runbooks, README) |
| `chore` | Tooling, gitignore, dependency bumps |
| `refactor` | Code restructuring without behavior change |
| `test` | Adding or modifying tests |

**Common scopes for this repo:**

`seo`, `integrations`, `dashboard`, `api`, `infra`, `agents`, `content`

**Examples:**

```
feat(seo): meta title/description rewrite pipeline
docs(seo): 2026-05-25 audit — post-April-changes impact
chore(seo): track audit outputs for historical trend analysis
fix(api): GSC date-range off-by-one in deep audit
```

The body explains **why**, not what — the diff already shows what. Reference any related issue / audit / runbook.

## When you ship an SEO change

1. Commit the script/snippet/content with a `feat(seo)` or `fix(seo)` message.
2. Add an entry at the top of [docs/seo-audits/CHANGELOG.md](docs/seo-audits/CHANGELOG.md) with the commit SHA.
3. Schedule a measurement audit for ~28 days later (see [docs/runbooks/run-deep-seo-audit.md](docs/runbooks/run-deep-seo-audit.md)) so GSC has a clean comparison window.

## When you commit an audit

Always commit both:
- The raw output in `data/audit_output/deep_seo_audit_*.{md,json}`
- The synthesized human-readable summary in `docs/seo-audits/YYYY-MM-DD-<slug>.md`
- An entry in [docs/seo-audits/CHANGELOG.md](docs/seo-audits/CHANGELOG.md)

## Code style

- Python: follow PEP 8. No formatter enforced yet.
- TypeScript/React (dashboard): default ESLint + Prettier (run via `npm run lint`).

## Things that must NEVER be committed

- `.env` (real env values)
- `credentials/*.json` (service-account keys)
- API tokens, refresh tokens, passwords — anywhere
- Customer PII

If you accidentally commit a secret, rotate it immediately and force-push to remove from history (coordinate with the project owner before force-pushing).

## Tests

Run the test suite before pushing:

```bash
pytest
```

Coverage is currently thin; adding tests with new features is encouraged but not strictly required.

## Pull requests

If you're a collaborator (not the owner), open a PR rather than pushing to main:

1. Push your branch: `git push origin feat/your-change`
2. Open a PR against `main` on GitHub
3. Describe **why** in the PR body. Link any related audit or design doc.
4. Wait for review from the project owner.

## Questions

Project owner: Robert Porter. When in doubt, ask before pushing.
