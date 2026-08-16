# Operator manual steps for the ranking-ops roadmap

These steps **cannot** be done from the laptop agent. Run them on the mini
or in Google Console. Code and runbooks are already in the repo.

## A. Mini deploy + launchd + FileVault

Follow [mini-deploy-apply-loop.md](mini-deploy-apply-loop.md) in order:

1. `git pull origin main` on `/Users/aiagentecosystem/services/ols`
2. Confirm `GTM_ACCOUNT_ID`, `GTM_CONTAINER_ID`, `GA4_MEASUREMENT_ID` on
   **server** `.env`
3. `infra/server/deploy_server.sh`
4. `infra/server/install_launchd_platform_sync.sh`
5. `launchctl kickstart -k gui/$(id -u)/com.ols.platform-sync.daily`
6. Choose a FileVault posture (keep FileVault + `pmset autorestart 1`, or
   FileVault off + auto-login). Record it in
   [mac-mini-implementation-guide.md](../mac-mini-implementation-guide.md).

Do not import `workflows/n8n/*.json`.

## B. First frozen-meta Apply (after PR B is deployed)

1. Open the dashboard task queue. Pick a **service page** (not homepage,
   not `/products/*`) with `action_kind=shopify.apply_frozen_meta`.
2. Read the frozen payload (`new_title`, `new_meta_description`, `page_id`).
   Edit is not supported in the modal — dismiss and wait for a new draft if
   the copy is wrong.
3. Apply with human confirmation and judge `PASS`.
4. Wait ~5 minutes. Incognito-check `<title>` and meta description.
5. Add a line to [seo-audits/CHANGELOG.md](../seo-audits/CHANGELOG.md).

Homepage organizer title iteration still uses
`data/session12_homepage_organizers_ctr.py` with the mutation guard.

## C. GBP reapply + Ads OAuth

### GBP (read only)

1. Confirm live JSON-LD has **no** `streetAddress`:

   ```bash
   curl -sL https://organizinglifeservices.com/ | tr '\n' ' ' | grep -o 'streetAddress[^,}]*' || echo 'no streetAddress'
   ```

   If a street address is still published, run the documented `data/` scripts
   in [GBP_API_ACCESS_NOTES.md](../../GBP_API_ACCESS_NOTES.md) with the
   mutation guard. Do not add a GBP write API.
2. Reapply Performance API access (case `7-8753000040474`, project
   `ols-marketing-agent`, SA `ols-operations@ols-marketing-agent.iam.gserviceaccount.com`).
3. When Google approves, set `GBP_LOCATION_ID` on **server** `.env` and
   redeploy.

### Google Ads (laptop, then copy to mini)

1. MCC developer token from https://ads.google.com/aw/apicenter
2. GCP OAuth Desktop client → `GOOGLE_ADS_CLIENT_ID` /
   `GOOGLE_ADS_CLIENT_SECRET` in the **laptop** `.env`
3. `python scripts/get_google_ads_refresh_token.py` (browser consent)
4. Copy `GOOGLE_ADS_DEVELOPER_TOKEN`, client id/secret, refresh token, and
   `GOOGLE_ADS_CUSTOMER_ID=5486213910` onto the **mini** `.env`. Never commit.
5. Redeploy. Apply one `ads.disable_bogus_conversions` task in a non-peak
   hour (pauses the frozen conversion action id only).

See [complete-google-api-access.md](complete-google-api-access.md).
