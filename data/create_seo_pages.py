"""
Create SEO Landing Pages — Targeting keyword gaps from GSC analysis.
Run inside Docker: docker exec ols-api python /app/data/create_seo_pages.py
"""
import sys
sys.path.insert(0, "/app")

from app.services.shopify_service import create_page

pages_to_create = [
    {
        "title": "Estate Sale Companies Near Me | Trusted Local Experts | Organizing Life Services",
        "handle": "estate-sale-companies-near-me",
        "meta_description": "Looking for the best estate sale companies near you? Organizing Life Services has served Tampa Bay for over 15 years. Free consultations, professional service, proven results.",
        "body_html": """
<h1>Find the Best Estate Sale Company Near You in Tampa Bay</h1>

<p>When you search for "estate sale companies near me," you want a team you can trust with your family's belongings. Organizing Life Services has been the Tampa Bay area's trusted estate sale company since 2010, serving Palm Harbor, Clearwater, Tampa, St. Petersburg, and surrounding communities.</p>

<h2>Why Choose Organizing Life Services?</h2>

<p>Not all estate sale companies are created equal. Here's what sets us apart from other companies in the Tampa Bay area:</p>

<p><strong>Over 15 Years of Experience</strong> — We've conducted hundreds of successful estate sales across Pinellas, Hillsborough, Pasco, and Citrus counties. Our team knows the local market, understands fair pricing, and has built a loyal following of buyers who attend our sales.</p>

<p><strong>Full-Service Estate Liquidation</strong> — From the initial consultation to the final cleanout, we handle everything. We sort, organize, price, stage, market, and sell your items. You don't have to lift a finger.</p>

<p><strong>Professional Marketing</strong> — Every sale gets promoted across multiple platforms including EstateSales.net, social media, email lists, and our website. Our marketing reaches thousands of active estate sale shoppers in the Tampa Bay area.</p>

<p><strong>Transparent Process</strong> — We provide detailed accounting of every item sold. You'll know exactly what sold, for how much, and when to expect your proceeds.</p>

<h2>Areas We Serve</h2>

<p>We proudly serve estate sale clients throughout the greater Tampa Bay region including Palm Harbor, Clearwater, Dunedin, Tarpon Springs, Safety Harbor, Largo, St. Petersburg, Tampa, Westchase, New Port Richey, Hudson, Holiday, Brooksville, and all surrounding communities.</p>

<h2>Get a Free Estate Sale Consultation</h2>

<p>Ready to learn how we can help? <a href="/pages/contact-us">Contact us today</a> for a free, no-obligation consultation. We'll visit your home, assess your belongings, and provide an honest recommendation for the best approach to your estate sale.</p>

<p>Call us at <a href="tel:7275426028">(727) 542-6028</a> or <a href="/pages/contact-us">fill out our contact form</a>.</p>
""",
    },
    {
        "title": "What Is an Estate Sale? | Estate Sale Meaning Explained | Organizing Life Services",
        "handle": "what-is-an-estate-sale",
        "meta_description": "What does estate sale mean? Learn everything about estate sales: how they work, what gets sold, how to hire a company, and what to expect. Expert guide from Organizing Life Services.",
        "body_html": """
<h1>What Is an Estate Sale? Everything You Need to Know</h1>

<p>If you've ever wondered "what is an estate sale?" or searched for the meaning of estate sales, you're not alone. Estate sales are one of the most effective ways to liquidate the contents of a home, but many people aren't sure exactly how they work.</p>

<h2>Estate Sale Meaning</h2>

<p>An estate sale is a professionally managed sale of a home's contents, typically conducted when a homeowner is downsizing, relocating, or settling an estate after a loved one passes. Unlike garage sales, estate sales are run by professional companies who price, stage, and sell items at fair market value.</p>

<h2>How Estate Sales Work</h2>

<p><strong>Step 1: Consultation</strong> — A professional estate sale company visits the home to assess the contents and discuss your goals and timeline.</p>

<p><strong>Step 2: Preparation</strong> — The company sorts, organizes, researches, and prices every item in the home. Items are staged attractively to maximize buyer interest.</p>

<p><strong>Step 3: Marketing</strong> — The sale is promoted through online listings, social media, email lists, and signage to attract qualified buyers.</p>

<p><strong>Step 4: Sale Days</strong> — The sale typically runs 2-3 days. The company manages all aspects including crowd control, checkout, and security.</p>

<p><strong>Step 5: Settlement</strong> — After the sale, you receive a detailed accounting and your proceeds. The company can also arrange cleanout of remaining items.</p>

<h2>What Gets Sold at Estate Sales?</h2>

<p>Almost everything in a home can be sold at an estate sale: furniture, art, jewelry, collectibles, kitchenware, tools, electronics, clothing, books, and more. Professional estate sale companies know how to identify valuable items that homeowners might overlook.</p>

<h2>Ready to Learn More?</h2>

<p>Organizing Life Services has conducted hundreds of estate sales in the Tampa Bay area since 2010. <a href="/pages/how-it-works">Learn more about our process</a> or <a href="/pages/contact-us">contact us</a> for a free consultation. Call <a href="tel:7275426028">(727) 542-6028</a>.</p>
""",
    },
    {
        "title": "Estate Liquidators in Tampa Bay | Professional Estate Liquidation Services",
        "handle": "estate-liquidators-tampa-bay",
        "meta_description": "Professional estate liquidators serving Tampa Bay. Organizing Life Services handles complete estate liquidation including sales, appraisals, and cleanouts. Call (727) 542-6028.",
        "body_html": """
<h1>Professional Estate Liquidators Serving Tampa Bay</h1>

<p>When you need experienced estate liquidators, Organizing Life Services delivers comprehensive estate liquidation services throughout the Tampa Bay area. Since 2010, we've helped hundreds of families, attorneys, realtors, and fiduciaries liquidate estates efficiently and profitably.</p>

<h2>Complete Estate Liquidation Services</h2>

<p><strong>Estate Sales</strong> — Our signature service. We manage every aspect of selling your home's contents, from pricing and staging to marketing and checkout. Our sales consistently draw large crowds of serious buyers.</p>

<p><strong>Personal Property Appraisals</strong> — Need to know the value of an estate before selling? Our <a href="/pages/personal-property-appraisal">certified appraisal services</a> provide accurate valuations for insurance, probate, divorce, and tax purposes.</p>

<p><strong>Estate Cleanouts</strong> — After the sale, we handle the complete cleanout of remaining items through donation, recycling, or disposal. We leave the home broom-clean and ready for the next chapter.</p>

<p><strong>Buyout Services</strong> — For situations where a traditional estate sale isn't feasible, we offer fair-market buyout options for entire estates or specific collections.</p>

<h2>Who We Work With</h2>

<p>We partner with homeowners, families, estate attorneys, probate courts, real estate agents, senior living communities, and property managers throughout Pinellas, Hillsborough, Pasco, and Citrus counties.</p>

<h2>Get Started Today</h2>

<p>Every estate liquidation begins with a free consultation. <a href="/pages/contact-us">Contact Organizing Life Services</a> or call <a href="tel:7275426028">(727) 542-6028</a> to discuss your situation.</p>
""",
    },
    {
        "title": "Estate Sale & Appraisal Services | Tampa Bay | Organizing Life Services",
        "handle": "estate-sale-appraisal-services",
        "meta_description": "Combined estate sale and appraisal services in Tampa Bay. Get accurate valuations and professional estate sales from one trusted company. Free consultation available.",
        "body_html": """
<h1>Estate Sale & Appraisal Services in Tampa Bay</h1>

<p>Looking for a company that offers both estate sales and appraisals? Organizing Life Services provides comprehensive estate sale and appraisal services under one roof, serving the entire Tampa Bay area.</p>

<h2>Why Combine Estate Sales and Appraisals?</h2>

<p>Many estates benefit from a professional appraisal before the sale begins. An appraisal ensures that valuable items are properly identified and priced, protects against undervaluing collections, and provides documentation needed for probate, tax, or insurance purposes.</p>

<h2>Our Appraisal Services</h2>

<p>We provide <a href="/pages/personal-property-appraisal">personal property appraisals</a> for a variety of needs including estate settlement and probate, insurance coverage documentation, equitable distribution for divorce proceedings, charitable donation valuations, and downsizing planning.</p>

<h2>Our Estate Sale Services</h2>

<p>Our full-service estate sales include professional sorting, organizing, and pricing of all items, strategic staging to maximize buyer appeal, multi-platform marketing to our network of thousands of buyers, professional management of all sale days, detailed accounting and transparent settlement, and post-sale cleanout services.</p>

<h2>Schedule Your Free Consultation</h2>

<p>Whether you need an appraisal, an estate sale, or both, we're here to help. <a href="/pages/contact-us">Contact us today</a> or call <a href="tel:7275426028">(727) 542-6028</a> for a free consultation.</p>
""",
    },
    {
        "title": "Estate Sales in Clearwater, FL | Estate Sale Company | Organizing Life Services",
        "handle": "estate-sale-clearwater-florida",
        "meta_description": "Professional estate sale company in Clearwater, Florida. Organizing Life Services provides full-service estate sales, liquidation, and cleanouts in Clearwater and Pinellas County.",
        "body_html": """
<h1>Estate Sales in Clearwater, Florida</h1>

<p>Organizing Life Services is Clearwater's trusted estate sale company, providing professional estate liquidation services to homeowners, families, and attorneys throughout Clearwater and the surrounding Pinellas County communities.</p>

<h2>Clearwater Estate Sale Services</h2>

<p>We offer complete estate sale services in Clearwater including full-service estate sales with professional pricing and staging, personal property appraisals, estate cleanout and donation coordination, downsizing assistance, and buyout services for select estates.</p>

<h2>Serving All Clearwater Neighborhoods</h2>

<p>We've conducted successful estate sales throughout Clearwater including Clearwater Beach, Countryside, Feather Sound, Harbor Oaks, Belleair, and all surrounding neighborhoods. Our knowledge of the local market ensures your items are priced to sell while maximizing your return.</p>

<h2>Why Clearwater Families Choose Us</h2>

<p>With over 15 years serving the Tampa Bay area, we understand the Clearwater market. Our extensive buyer network, professional marketing, and compassionate approach make us the preferred choice for Clearwater estate sales. Check out our <a href="/pages/testimonials">client testimonials</a> to see why families trust us.</p>

<h2>Get Your Free Clearwater Estate Sale Consultation</h2>

<p><a href="/pages/contact-us">Contact us today</a> or call <a href="tel:7275426028">(727) 542-6028</a> for a free in-home consultation. We'll assess your estate and recommend the best approach.</p>
""",
    },
    {
        "title": "Estate Sales in Dunedin, FL | Professional Estate Liquidation",
        "handle": "estate-sale-dunedin-florida",
        "meta_description": "Looking for estate sale services in Dunedin, FL? Organizing Life Services provides professional estate sales, appraisals, and cleanouts in Dunedin and northern Pinellas County.",
        "body_html": """
<h1>Estate Sales in Dunedin, Florida</h1>

<p>Organizing Life Services provides professional estate sale services in Dunedin, FL and the surrounding northern Pinellas County area. With over 15 years of experience, we're the trusted choice for estate liquidation in the Dunedin community.</p>

<h2>Our Dunedin Estate Sale Services</h2>

<p>We provide full-service estate sales with expert pricing and staging, personal property appraisals for probate and insurance, complete estate cleanout services, compassionate downsizing assistance, and professional marketing to our network of thousands of buyers.</p>

<h2>Your Dunedin Estate Sale Experts</h2>

<p>Dunedin is home to incredible estates filled with art, antiques, and collectibles. Our team has extensive experience identifying and pricing unique items to ensure you receive fair market value. From vintage finds in the downtown district to waterfront estate collections, we've handled it all.</p>

<h2>Start Your Estate Sale Journey</h2>

<p>Ready to get started? <a href="/pages/contact-us">Contact Organizing Life Services</a> or call <a href="tel:7275426028">(727) 542-6028</a> for a free estate sale consultation in Dunedin.</p>
""",
    },
]


def run():
    created = 0
    errors = 0

    for page in pages_to_create:
        try:
            result = create_page(
                title=page["title"],
                body_html=page["body_html"],
                handle=page["handle"],
                meta_description=page["meta_description"],
                published=True,
            )
            status = result.get("status", "unknown")
            print(f'  [{"OK" if "id" in str(result) or status in ("created","success") else "??"}] {page["handle"]}')
            created += 1
        except Exception as e:
            if "422" in str(e):
                print(f'  [EXISTS] {page["handle"]} — page already exists')
            else:
                print(f'  [ERR] {page["handle"]}: {e}')
                errors += 1

    print(f"\nDone: {created} created, {errors} errors")


if __name__ == "__main__":
    run()
