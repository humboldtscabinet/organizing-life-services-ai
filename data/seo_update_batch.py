"""
SEO Batch Update Script — Service Pages, Location Pages, Blog Articles
Run inside Docker: docker exec ols-api python /app/data/seo_update_batch.py
"""
import sys
sys.path.insert(0, "/app")

from app.services.shopify_service import update_page_seo, update_article_seo

# ===== SERVICE PAGES =====
service_pages = [
    {
        "page_id": 48471736364,
        "title": "Estate Sale FAQs | Common Questions | Organizing Life Services",
        "meta_description": "Find answers to common estate sale questions: pricing, timelines, what sells, how to prepare, and what to expect when hiring Organizing Life Services in Tampa Bay.",
    },
    {
        "page_id": 96294502554,
        "title": "How Our Estate Sales Work | Step-by-Step Process | Organizing Life Services",
        "meta_description": "Learn our proven estate sale process from consultation to sale day. Organizing Life Services handles pricing, staging, marketing, and selling — serving Tampa Bay since 2010.",
    },
    {
        "page_id": 80166650010,
        "title": "Client Reviews & Testimonials | Organizing Life Services Estate Sales",
        "meta_description": "Read real client reviews of Organizing Life Services. Trusted estate liquidation company serving Palm Harbor, Tampa, and all of Tampa Bay for over 15 years.",
    },
    {
        "page_id": 103728840858,
        "title": "Personal Property Appraisal Services | Tampa Bay | Organizing Life Services",
        "meta_description": "Professional personal property appraisals for estates, insurance, divorce, and downsizing. Certified appraisers serving Palm Harbor, Tampa, and the Tampa Bay area.",
    },
    {
        "page_id": 96707739802,
        "title": "Selling Your House in Florida? | Estate Liquidation Before You Move",
        "meta_description": "Planning to sell your Florida home? Organizing Life Services helps you liquidate personal property, downsize, and prepare your house for sale in Tampa Bay.",
    },
    {
        "page_id": 96296272026,
        "title": "Senior Downsizing & Estate Services | Pinellas County | Organizing Life Services",
        "meta_description": "Compassionate senior downsizing, estate sales, and move management in Pinellas County. Helping seniors and families transition with care since 2010.",
    },
    {
        "page_id": 99735634074,
        "title": "Full House Liquidation Services | Tampa Bay | Organizing Life Services",
        "meta_description": "Need to liquidate an entire home? Organizing Life Services provides full house estate liquidation in Palm Harbor, Tampa, Clearwater, and all of Tampa Bay.",
    },
    {
        "page_id": 94961172634,
        "title": "Our Successful Estate Sales | Portfolio | Organizing Life Services",
        "meta_description": "Browse our portfolio of successful estate sales across Tampa Bay. See why homeowners, attorneys, and families trust Organizing Life Services.",
    },
]

# ===== LOCATION PAGES (meta descriptions only — titles already good) =====
location_pages = [
    {
        "page_id": 99768631450,
        "meta_description": "Top-rated estate sale company in Palm Harbor, Clearwater, Dunedin, and Pinellas County. Professional estate liquidation, downsizing, and cleanout services since 2010.",
    },
    {
        "page_id": 99768598682,
        "meta_description": "Professional estate sale services in Tampa, Westchase, and Hillsborough County. Full-service estate liquidation, appraisals, and cleanout. Call for a free consultation.",
    },
    {
        "page_id": 99768664218,
        "meta_description": "Trusted estate sale company serving New Port Richey, Hudson, Holiday, and all of Pasco & Hernando County. Estate liquidation, downsizing, and cleanout services.",
    },
    {
        "page_id": 99768729754,
        "meta_description": "Professional estate sale services in Citrus County, Brooksville, and Inverness. Organizing Life Services provides full-service estate liquidation and cleanouts.",
    },
]

# ===== BLOG ARTICLES =====
blog_id = 52179501100
articles = [
    {
        "article_id": 561529389210,
        "title": "Estate Sales Near Me: How to Find the Best Deals in Tampa Bay",
        "meta_description": "Discover how to find estate sales near you in Tampa Bay. Tips for finding deals, what to expect, and how professional estate sale companies like Organizing Life Services work.",
    },
    {
        "article_id": 561319870618,
        "title": "What to Expect at an Organizing Life Services Estate Sale",
        "meta_description": "Learn what makes an Organizing Life Services estate sale different. Professional staging, pricing, and marketing that gets top dollar for your personal property.",
    },
    {
        "article_id": 561277632666,
        "title": "The Psychology of Estate Liquidation: Why Decluttering Transforms Your Life",
        "meta_description": "Explore the emotional and psychological benefits of estate liquidation. How clearing physical space creates mental clarity during life transitions.",
    },
    {
        "article_id": 561224810650,
        "title": "How to Sell Furniture When Moving: Tips for Maximum Value",
        "meta_description": "Expert tips for selling furniture before a move. Learn pricing strategies, staging advice, and why estate sale companies get better results than DIY sales.",
    },
    {
        "article_id": 561197449370,
        "title": "How to Get Rid of Furniture Fast: Estate Sale & Donation Options",
        "meta_description": "Need to get rid of furniture quickly? Compare estate sales, donations, and buyout options. Organizing Life Services makes furniture liquidation easy in Tampa Bay.",
    },
    {
        "article_id": 561151246490,
        "title": "Personal Property Appraisals: 10 Expert Tips You Need to Know",
        "meta_description": "Essential guide to personal property appraisals. Learn when you need one, how they work, and expert strategies for estate, insurance, and divorce appraisals.",
    },
    {
        "article_id": 561071358106,
        "title": "The Ultimate Guide to Estate Sale Services | Organizing Life Services",
        "meta_description": "Complete guide to working with Organizing Life Services. From first consultation to final cleanout — everything you need to know about our estate sale process.",
    },
    {
        "article_id": 561023582362,
        "title": "Estate Liquidation Strategies: How to Maximize Your Sale Proceeds",
        "meta_description": "Proven strategies for successful estate liquidation. Professional tips on pricing, marketing, and staging that maximize proceeds from your estate sale.",
    },
    {
        "article_id": 560955195546,
        "title": "Estate Sale vs. Garage Sale: Which Is Right for You?",
        "meta_description": "Understand the key differences between estate sales and garage sales. When to hire a professional estate sale company vs. doing it yourself.",
    },
    {
        "article_id": 560933830810,
        "title": "Estate Auction vs. Estate Sale: Pros, Cons & Which Pays More",
        "meta_description": "Compare estate auctions and estate sales side by side. Learn which option gets better prices, the pros and cons of each, and how to decide for your situation.",
    },
]


def run():
    results = {"success": 0, "errors": 0, "details": []}

    # Update service pages
    print("=" * 60)
    print("UPDATING SERVICE PAGES")
    print("=" * 60)
    for page in service_pages:
        try:
            r = update_page_seo(
                page_id=page["page_id"],
                title=page.get("title"),
                meta_description=page.get("meta_description"),
            )
            status = r.get("status", "unknown")
            print(f"  [{'OK' if status == 'success' else 'FAIL'}] Page {page['page_id']}: {page.get('title', '(meta only)')[:50]}")
            if status == "success":
                results["success"] += 1
            else:
                results["errors"] += 1
                results["details"].append(f"Page {page['page_id']}: {r}")
        except Exception as e:
            results["errors"] += 1
            results["details"].append(f"Page {page['page_id']}: {e}")
            print(f"  [ERR] Page {page['page_id']}: {e}")

    # Update location pages (meta descriptions only)
    print("\n" + "=" * 60)
    print("UPDATING LOCATION PAGES (meta descriptions)")
    print("=" * 60)
    for page in location_pages:
        try:
            r = update_page_seo(
                page_id=page["page_id"],
                meta_description=page["meta_description"],
            )
            status = r.get("status", "unknown")
            print(f"  [{'OK' if status == 'success' else 'FAIL'}] Page {page['page_id']}: meta description updated")
            if status == "success":
                results["success"] += 1
            else:
                results["errors"] += 1
                results["details"].append(f"Page {page['page_id']}: {r}")
        except Exception as e:
            results["errors"] += 1
            results["details"].append(f"Page {page['page_id']}: {e}")
            print(f"  [ERR] Page {page['page_id']}: {e}")

    # Update blog articles
    print("\n" + "=" * 60)
    print("UPDATING BLOG ARTICLES")
    print("=" * 60)
    for article in articles:
        try:
            r = update_article_seo(
                blog_id=blog_id,
                article_id=article["article_id"],
                title=article.get("title"),
                meta_description=article.get("meta_description"),
            )
            status = r.get("status", "unknown")
            print(f"  [{'OK' if status == 'success' else 'FAIL'}] Article {article['article_id']}: {article.get('title', '')[:50]}")
            if status == "success":
                results["success"] += 1
            else:
                results["errors"] += 1
                results["details"].append(f"Article {article['article_id']}: {r}")
        except Exception as e:
            results["errors"] += 1
            results["details"].append(f"Article {article['article_id']}: {e}")
            print(f"  [ERR] Article {article['article_id']}: {e}")

    # Summary
    print("\n" + "=" * 60)
    print(f"DONE: {results['success']} succeeded, {results['errors']} errors")
    if results["details"]:
        print("\nError details:")
        for d in results["details"]:
            print(f"  - {d}")
    print("=" * 60)


if __name__ == "__main__":
    run()
