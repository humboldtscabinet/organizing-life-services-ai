"""Round-4 meta sweep — title_tag + description_tag for 9 high-value pages
that round-3 didn't cover. Past-sale event pages (body<100 chars) are
deliberately skipped — they are archive content and should arguably be
noindexed in a separate pass.
"""
import os, sys, time, httpx

STORE=os.getenv('SHOPIFY_STORE'); CID=os.getenv('SHOPIFY_CLIENT_ID')
CS=os.getenv('SHOPIFY_CLIENT_SECRET'); API=os.getenv('SHOPIFY_API_VERSION','2024-10')

# (handle, title_tag, description_tag)
METAS = [
    ("testimonials",
     "Client Reviews & Estate Sale Testimonials | Tampa Bay",
     "Read 100+ five-star client reviews of Organizing Life Services — Tampa Bay's most trusted estate sale company since 2010. See why families pick us."),
    ("contact-us",
     "Contact Us | Free Estate Sale Consultation | Tampa Bay",
     "Contact Organizing Life Services for a free estate sale consultation in Tampa Bay. Call (727) 542-6028 or send a message — we respond within 1 business day."),
    ("estate-liquidators-tampa-bay",
     "Estate Liquidators Tampa Bay | Full-Service Liquidation",
     "Trusted Tampa Bay estate liquidators since 2010. Full-service pricing, staging, marketing, sale-day staffing & cleanout. Free quote: (727) 542-6028."),
    ("estate-sale-appraisal-services",
     "Estate Sale & Appraisal Services Tampa Bay | Free Quote",
     "Estate sale and personal property appraisal services across Tampa Bay. Written reports accepted by insurance, IRS & Florida probate courts. Call (727) 542-6028."),
    ("estate-sale-companies-near-me",
     "Estate Sale Companies Near Me | Tampa Bay's Top-Rated",
     "Looking for estate sale companies near you? Organizing Life Services serves Pinellas, Pasco, Hillsborough, Hernando & Citrus counties. (727) 542-6028."),
    ("estate-sale-citrus-county",
     "Estate Sales Citrus County, FL | Inverness & Crystal River",
     "Estate sales across Citrus County — Inverness, Crystal River, Homosassa, Beverly Hills & Lecanto. Full-service liquidation by Organizing Life Services."),
    ("estate-sale-pasco-county",
     "Estate Sales Pasco & Hernando County, FL | Free Quote",
     "Professional estate sales across Pasco & Hernando County, FL. Pricing, staging, marketing & cleanout by Organizing Life Services. Call (727) 542-6028."),
    ("how-it-works",
     "How Our Estate Sales Work | 8-Step Process | Tampa Bay",
     "See the 8-step Organizing Life Services estate sale process — from free consultation to broom-clean turnover. Tampa Bay's most trusted liquidator since 2010."),
    ("tarpon-springs-estate-sale-in-woodfield",
     "Estate Sales Tarpon Springs FL | Woodfield & Sponge Docks",
     "Estate sales across Tarpon Springs FL — Woodfield, Sponge Docks, Whitcomb Bayou & Riverside Drive. Full-service liquidation. Call (727) 542-6028."),
]


def _retry(fn,*a,**k):
    for i in range(6):
        try:
            r=fn(*a,**k)
            if hasattr(r,'status_code') and r.status_code==429:
                time.sleep(float(r.headers.get('Retry-After',2**i))); continue
            return r
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError):
            time.sleep(2**i)
    raise RuntimeError('retries exhausted')


def upsert(B,H,pid,key,val):
    r=_retry(httpx.post,f'{B}/pages/{pid}/metafields.json',headers=H,timeout=30,
             json={'metafield':{'namespace':'global','key':key,'value':val,'type':'single_line_text_field'}})
    if r.status_code in (200,201): return 'created'
    existing=_retry(httpx.get,f'{B}/pages/{pid}/metafields.json',headers=H,timeout=30).json().get('metafields',[])
    for m in existing:
        if m.get('namespace')=='global' and m.get('key')==key:
            r2=_retry(httpx.put,f'{B}/metafields/{m["id"]}.json',headers=H,timeout=30,
                      json={'metafield':{'id':m['id'],'value':val,'type':'single_line_text_field'}})
            r2.raise_for_status(); return 'updated'
    raise RuntimeError(f'fail {r.status_code}: {r.text}')


def main():
    tok=httpx.post(f'https://{STORE}.myshopify.com/admin/oauth/access_token',
        json={'client_id':CID,'client_secret':CS,'grant_type':'client_credentials'},timeout=30).json()['access_token']
    H={'X-Shopify-Access-Token':tok,'Content-Type':'application/json'}
    B=f'https://{STORE}.myshopify.com/admin/api/{API}'
    pages=_retry(httpx.get,f'{B}/pages.json?limit=250',headers=H,timeout=30).json()['pages']
    bh={p['handle']:p['id'] for p in pages}
    # Validate
    for h,t,d in METAS:
        assert len(t)<=65, f'{h}: title {len(t)} too long'
        assert len(d)<=160, f'{h}: desc {len(d)} too long'
    for h,t,d in METAS:
        pid=bh.get(h)
        if not pid: print(f'  [skip] {h}'); continue
        s1=upsert(B,H,pid,'title_tag',t); time.sleep(0.6)
        s2=upsert(B,H,pid,'description_tag',d); time.sleep(0.6)
        print(f'  [ok] {h}: title={s1} desc={s2} | title_len={len(t)} desc_len={len(d)}')


if __name__=='__main__':
    main()
