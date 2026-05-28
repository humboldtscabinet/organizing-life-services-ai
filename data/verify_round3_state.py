"""Verify all 16 round-3 pushes by reading metafields directly from Shopify
and comparing to the approved drafts. Also re-verify theme patch + intlinks
block + FAQ block. Pure read-only audit."""
import json
import os
import sys
import time
import httpx

STORE = os.getenv("SHOPIFY_STORE")
CID = os.getenv("SHOPIFY_CLIENT_ID")
CS = os.getenv("SHOPIFY_CLIENT_SECRET")
API_VER = os.getenv("SHOPIFY_API_VERSION", "2024-10")

if not all([STORE, CID, CS]):
    sys.exit("missing creds")

tok = httpx.post(f"https://{STORE}.myshopify.com/admin/oauth/access_token",
    json={"client_id": CID, "client_secret": CS, "grant_type": "client_credentials"},
    timeout=30).json()["access_token"]
H = {"X-Shopify-Access-Token": tok}
BASE = f"https://{STORE}.myshopify.com/admin/api/{API_VER}"


def _retry(fn, *a, **k):
    for i in range(5):
        try: return fn(*a, **k)
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
            time.sleep(2 ** i)
    raise


def get(p):
    r = _retry(httpx.get, f"{BASE}/{p}", headers=H, timeout=60)
    r.raise_for_status()
    return r.json()


def fetch_mfs(owner, oid):
    data = get(f"{owner}/{oid}/metafields.json")
    out = {}
    for m in data["metafields"]:
        if m["namespace"] == "global" and m["key"] in ("title_tag", "description_tag"):
            out[m["key"]] = m["value"]
    return out


drafts = json.load(open("data/audit_output/round3_meta_drafts.json"))["drafts"]
approved = [d for d in drafts if d.get("approved")]

# Build resolvers
pages = {p["handle"]: p["id"] for p in get("pages.json?limit=250")["pages"]}
blogs = get("blogs.json?limit=50")["blogs"]
art_id = {}
for b in blogs:
    for a in get(f"blogs/{b['id']}/articles.json?limit=250")["articles"]:
        art_id[a["handle"]] = a["id"]

ok = []
bad = []
for d in approved:
    kind = d["kind"]
    handle = d["handle"]
    exp_t = d["draft"]["new_title"]
    exp_m = d["draft"]["new_meta_description"]
    if kind == "special":
        continue
    if kind == "page":
        oid = pages.get(handle); owner = "pages"
    else:
        oid = art_id.get(handle); owner = "articles"
    if not oid:
        bad.append((handle, "not_found"))
        continue
    mfs = fetch_mfs(owner, oid)
    t_ok = mfs.get("title_tag") == exp_t
    m_ok = mfs.get("description_tag") == exp_m
    time.sleep(0.3)
    if t_ok and m_ok:
        ok.append(handle)
    else:
        bad.append((handle, {
            "title_match": t_ok, "meta_match": m_ok,
            "got_title": mfs.get("title_tag"), "exp_title": exp_t,
            "got_meta_len": len(mfs.get("description_tag") or ""), "exp_meta_len": len(exp_m),
        }))

print(f"\n=== METAFIELD VERIFY: {len(ok)} OK / {len(bad)} mismatched ===")
for h in ok: print(f"  OK  {h}")
for h, info in bad: print(f"  XX  {h} :: {info}")

# Theme patch + intlinks
themes = get("themes.json")["themes"]
live = next(t for t in themes if t["role"] == "main")
print(f"\n=== LIVE THEME: {live['id']} ({live['name']}) ===")
theme_src = get(f"themes/{live['id']}/assets.json?asset[key]=layout/theme.liquid")["asset"]["value"]
print("  title-patch marker present:", "assign has_custom_title_tag = false" in theme_src)
print("  intlinks marker present:   ", "SEO-INTLINKS-V1" in theme_src)
print("  /pages/estate-cleanout-services anchors in theme:",
      theme_src.count('/pages/estate-cleanout-services'))

# Article FAQ
art = get(f"blogs/52179501100/articles/560955195546.json")["article"]
print(f"\n=== FAQ ARTICLE estate-sale-vs-garage-sale-know-the-differences ===")
print("  body length:", len(art["body_html"]))
print("  FAQ-YGE-V1 marker present:", "FAQ-YGE-V1" in art["body_html"])
print("  FAQPage schema present:", '"@type": "FAQPage"' in art["body_html"])
print("  target Q present:", "What is the difference between a yard sale and a garage sale" in art["body_html"])
