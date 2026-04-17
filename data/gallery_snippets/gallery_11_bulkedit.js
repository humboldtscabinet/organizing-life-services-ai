// XO Gallery Alt Text Filler — Gallery #11 (Bulk Edit view)
// Run this in DevTools Console with the gallery.xopify.com iframe context selected
// 70 images total — handles pagination automatically
(async function() {
  "use strict";

  const ALT_DATA = {
    "photo-mar1622450pm-kcF_500x.jpg": "Large ceramic elephant figurine with gold accents on glass dining table, estate sale East Lake Woodlands FL",
    "photo-mar1622458pm-amh_500x.jpg": "Artificial magnolia tree bonsai with pink flowers in decorative pot, estate sale East Lake Woodlands FL",
    "photo-mar1622516pm-Akl_500x.jpg": "Mid-century modern teak credenza hutch with glass doors and sliding panels, estate sale East Lake Woodlands FL",
    "photo-mar1622520pm-mfl_500x.jpg": "Two landscape paintings on white wall showing lake and mountain scenes, estate sale East Lake Woodlands FL",
    "photo-mar1622533pm-Sqs_500x.jpg": "Estate sale display cabinet with vintage glassware pottery and collectibles East Lake Woodlands FL",
    "photo-mar1622609pm-Llk_500x.jpg": "Handmade ceramic pottery bowls with earth tone glazes, estate sale New Port Richey FL",
    "photo-mar1622623pm-Wng_500x.jpg": "Vintage wooden animal figurines and brass finger cymbals, estate sale New Port Richey FL",
    "photo-mar1622631pm-ouo_500x.jpg": "Crystal cut glass vases including Crystal d'Arques brand, estate sale New Port Richey FL",
    "photo-mar1622638pm-hhJ_500x.jpg": "Purple ceramic figurine woman holding basket, decorative collectible, estate sale New Port Richey FL",
    "photo-mar1622643pm-CaS_500x.jpg": "Set of 8 smoky gray glass tumblers drinking glasses estate sale New Port Richey FL",
    "photo-mar1622644pm-yye_500x.jpg": "Set of clear crystal wine glasses with etched pattern, estate sale New Port Richey FL",
    "photo-mar1622652pm-AWa_500x.jpg": "Vintage decorative plate with painted landscape scene featuring tree and sunset, estate sale New Port Richey FL",
    "photo-mar1622653pm-OEr_500x.jpg": "Vintage ceramic pottery vase with red X-shaped tape and label, estate sale New Port Richey FL",
    "photo-mar1622702pm-Sxn_500x.jpg": "Indoor houseplants collection with wicker basket planters, estate sale New Port Richey FL",
    "photo-mar1622712pm-OeZ_500x.jpg": "Black leather recliner chair with ottoman and decorative pillows, estate sale New Port Richey FL",
    "photo-mar1622723pm-Ffv_500x.jpg": "Three framed abstract geometric art prints in black frames, modern wall art collection from estate sale New Port Richey FL",
    "photo-mar1622734pm-vph_500x.jpg": "Framed abstract geometric art print signed Elliott Debt '77, estate sale New Port Richey FL",
    "photo-mar1622740pm-KXR_500x.jpg": "Limited edition art print 158/240, signed artwork in white matting, estate sale New Port Richey FL",
    "photo-mar1622758pm-ArU_500x.jpg": "Modern glass-top coffee table with black cylindrical base and decorative orange vase, estate sale New Port Richey FL",
    "photo-mar1622801pm-hQr_500x.jpg": "Mid-century modern wood credenza with Native American pottery collection, estate sale New Port Richey FL",
    "photo-mar1622809pm-FZl_500x.jpg": "Framed Van Gogh Starry Night reproduction print in silver frame, estate sale New Port Richey FL",
    "photo-mar1622811pm-XvR_500x.jpg": "Blue ceramic lantern holders with cutout holes, decorative pottery set at estate sale New Port Richey FL",
    "photo-mar1622816pm-JFJ_500x.jpg": "Carved wood pelican bird sculptures on driftwood base, estate sale New Port Richey FL",
    "photo-mar1622820pm-PZt_500x.jpg": "Framed geometric op art print with red blue circles squares pattern, estate sale New Port Richey FL",
    "photo-mar1622830pm-PuH_500x.jpg": "Framed Japanese ink painting of koi fish with calligraphy, matted and professionally framed, estate sale New Port Richey FL",
    "photo-mar1622844pm-Vdp_500x.jpg": "Gray tweed upholstered swivel chair with curved back, estate sale New Port Richey FL",
    "photo-mar1622847pm-pze_500x.jpg": "Round mosaic tile top accent table with wrought iron base, estate sale New Port Richey FL",
    "photo-mar1622858pm-Gih_500x.jpg": "Wood bookshelf with books, storage boxes, and organizational items, estate sale New Port Richey FL",
    "photo-mar1622928pm-rhk_500x.jpg": "Two-drawer white chest with orange wood trim and handles, good condition estate sale New Port Richey FL",
    "photo-mar1622931pm-IwR_500x.jpg": "Journey brand manual wheelchair in good condition, estate sale New Port Richey FL",
    "photo-mar1622951pm-IBQ_500x.jpg": "Wooden crutches leaning against closet shelving unit, estate sale New Port Richey FL",
    "photo-mar1623000pm-iRB_500x.jpg": "Galaxy brand desk fan with blue blades, vintage electric fan in working condition, estate sale New Port Richey FL",
    "photo-mar1623011pm-wef_500x.jpg": "Framed beach sunset photograph with ocean waves, estate sale New Port Richey FL",
    "photo-mar1623017pm-zxW_500x.jpg": "Collection of seashells and conch shells with vintage poster, estate sale New Port Richey FL",
    "photo-mar1623023pm-mjT_500x.jpg": "Modern white cylindrical floor lamp with black cord, good condition, estate sale New Port Richey FL",
    "photo-mar1623027pm-lRm_500x.jpg": "Mid-century modern copper sculptural cattail water feature with glass bowl, estate sale New Port Richey FL",
    "photo-mar1623037pm-Hja_500x.jpg": "Framed Asian botanical artwork with bamboo plant and Chinese calligraphy, estate sale New Port Richey FL",
    "photo-mar1623047pm-iOG_500x.jpg": "Light oak wood twin bed frame with vertical slat headboard, white bedding, estate sale New Port Richey FL",
    "photo-mar1623057pm-OAw_500x.jpg": "Light wood chest of drawers with metal handles, good condition, estate sale New Port Richey FL",
    "photo-mar1623105pm-bTU_500x.jpg": "Framed Native American style cave painting artwork with figures and animals, estate sale New Port Richey FL",
    "photo-mar1623225pm-Yxd_500x.jpg": "Knoll Associates Inc furniture manufacturer label sticker, vintage mid-century modern designer furniture tag",
    "photo-mar1623630pm-mAi_500x.jpg": "Mid-century modern walnut chest of drawers with 5 drawers and sleek hardware, estate sale New Port Richey FL",
    "photo-mar1623634pm-CMC_500x.jpg": "Mid-century modern walnut chest of drawers with blue disc feet, estate sale New Port Richey FL",
    "photo-mar1623636pm-lsg_500x.jpg": "Mid-century modern walnut 3-drawer chest of drawers with tapered legs, estate sale New Port Richey FL",
    "photo-mar1623649pm-epr_500x.jpg": "Black mini refrigerator with glass door and papers on top, estate sale New Port Richey FL",
    "photo-mar1623657pm-HLS_500x.jpg": "Samsung flat screen TV black bezel estate sale New Port Richey FL good condition",
    "photo-mar1623700pm-NMj_500x.jpg": "White TV stand entertainment center with cabinet doors and shelves, estate sale New Port Richey FL",
    "photo-mar1623707pm-UlW_500x.jpg": "Wooden laundry drying rack with white vertical dowels, folding design, estate sale New Port Richey FL",
    "photo-mar1623718pm-tOD_500x.jpg": "Women's clothing collection in walk-in closet, estate sale New Port Richey FL including jackets and dresses",
    "photo-mar1623753pm-jLm_500x.jpg": "Large collection of DVDs and CDs with remote control, estate sale New Port Richey FL",
    "photo-mar1623803pm-Spo_500x.jpg": "Set of 4 Asian lacquered wall panels with silver floral designs, estate sale New Port Richey FL",
    "photo-mar1623826pm-pCc_500x.jpg": "White plastic outdoor chaise lounge chair with adjustable back, estate sale New Port Richey FL",
    "photo-mar1623831pm-jnM_500x.jpg": "Modern table lamp with pleated orange lampshade and white ceramic base, estate sale New Port Richey FL",
    "photo-mar1623833pm-SNn_500x.jpg": "Modern floor lamp with beige shade and black metal base, estate sale New Port Richey FL",
    "photo-mar1623834pm-uHp_500x.jpg": "Blue butterfly chair with metal frame, good condition, estate sale New Port Richey FL",
    "photo-mar1623838pm-afA_500x.jpg": "Ceramic beige vase with dried decorative branches, estate sale New Port Richey FL",
    "photo-mar1623908pm-Dgj_500x.jpg": "Organized pantry shelving unit with household items and supplies, estate sale New Port Richey FL",
    "photo-mar1624009pm-nhM_500x.jpg": "Vintage white torchiere floor lamp with frosted glass shade, estate sale New Port Richey FL",
    "photo-mar1624026pm-Lgd_500x.jpg": "Native American pottery collection including wedding vases and bowls, estate sale New Port Richey FL",
    "photo-mar1624047pm-jDO_500x.jpg": "Vintage wooden chisel set in original wood case, estate sale New Port Richey FL",
    "photo-mar1624050pm-bUr_500x.jpg": "Kitchen cabinet with vintage glassware dishes bowls and serving pieces, estate sale New Port Richey FL",
    "photo-mar1624055pm-eRS_500x.jpg": "Large collection of clear glass drinkware and stemware on white cabinet shelves, estate sale New Port Richey FL",
    "photo-mar1624106pm-Lxo_500x.jpg": "Kitchen appliance lot with blender, electric kettle, and toaster oven on wire shelving, estate sale New Port Richey FL",
    "photo-mar1624121pm-JEC_500x.jpg": "Vintage white ceramic cookie jar with Native American geometric design and wooden lid, estate sale New Port Richey FL",
    "photo-mar1624126pm-VPB_500x.jpg": "Stack of kitchen dish towels and cleaning cloths, various colors and patterns, estate sale New Port Richey FL",
    "photo-mar1624446pm-IqM_500x.jpg": "Hamilton Beach stand mixer with bowl and attachments, vintage cream color, estate sale New Port Richey FL",
    "photo-mar1624458pm-FjR_500x.jpg": "Navy blue travel duffel bag with straps and tags, estate sale New Port Richey FL",
    "photo-mar1625233pm-jda_500x.jpg": "Hoover Tempo upright vacuum cleaner blue and black, estate sale New Port Richey FL",
    "photo-mar1625449pm-TDw_500x.jpg": "Two black wicker patio chairs with metal frames on tile porch, estate sale New Port Richey FL",
    "photo-mar1680311pm-qkS_500x.jpg": "Bedroom furniture set with mattress, pillows, and clothing storage from estate sale New Port Richey FL"
  };

  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const log = (msg, icon = "ℹ️") => console.log(icon + " [XO-Alt] " + msg);

  // Extract filename from CDN URL
  function extractFilename(src) {
    if (!src) return "";
    try {
      const url = new URL(src);
      return url.pathname.split("/").pop();
    } catch {
      return src.split("/").pop().split("?")[0];
    }
  }

  // Fuzzy match: try exact, then stem match (ignore size suffix)
  function findAltText(filename) {
    if (ALT_DATA[filename]) return ALT_DATA[filename];
    const stem = filename.replace(/_\d+x\d*\.\w+$/i, "").replace(/_\d+x\.\w+$/i, "").replace(/\.\w+$/, "").toLowerCase();
    for (const [k, v] of Object.entries(ALT_DATA)) {
      const kStem = k.replace(/_\d+x\d*\.\w+$/i, "").replace(/_\d+x\.\w+$/i, "").replace(/\.\w+$/, "").toLowerCase();
      if (kStem === stem) return v;
    }
    return null;
  }

  // React-compatible input setter
  function setReactInput(input, value) {
    const proto = input instanceof HTMLTextAreaElement
      ? HTMLTextAreaElement.prototype
      : HTMLInputElement.prototype;
    const nativeSetter = Object.getOwnPropertyDescriptor(proto, "value").set;
    nativeSetter.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    input.dispatchEvent(new Event("blur", { bubbles: true }));
  }

  // ── Strategy 1: Walk from each CDN image up to find its alt text input ──
  function fillByImageWalk() {
    const allImages = document.querySelectorAll("img");
    const cdnImages = Array.from(allImages).filter(img =>
      img.src && (img.src.includes("cdn.shopify.com") || img.src.includes("xopify"))
    );
    log("Strategy 1: Found " + cdnImages.length + " CDN images");

    let filled = 0, skipped = 0, notFound = 0, noInput = 0;

    for (const img of cdnImages) {
      const filename = extractFilename(img.src);
      if (!filename) continue;
      const altText = findAltText(filename);
      if (!altText) { notFound++; continue; }

      // Walk up from image to find the card/row container
      let container = img.parentElement;
      let altInput = null;

      for (let depth = 0; depth < 12 && container; depth++) {
        // Look for inputs in this container
        const inputs = container.querySelectorAll('input[type="text"], input:not([type]), textarea');
        if (inputs.length >= 2) {
          // In bulk edit: first input = Title, second = Alt text
          altInput = inputs[1];
          break;
        }
        // Also check for labels
        const labels = container.querySelectorAll('label, [class*="label"], [class*="Label"]');
        for (const label of labels) {
          if (label.textContent.toLowerCase().includes("alt")) {
            const nextInput = label.parentElement?.querySelector('input, textarea') ||
                              label.nextElementSibling?.querySelector('input, textarea') ||
                              label.nextElementSibling;
            if (nextInput && (nextInput.tagName === "INPUT" || nextInput.tagName === "TEXTAREA")) {
              altInput = nextInput;
              break;
            }
          }
        }
        if (altInput) break;
        container = container.parentElement;
      }

      if (!altInput) { noInput++; continue; }

      const current = (altInput.value || "").trim();
      if (current.length > 5) { skipped++; continue; }

      setReactInput(altInput, altText);
      filled++;
    }

    return { filled, skipped, notFound, noInput };
  }

  // ── Strategy 2: Pair images and inputs by DOM order ──
  function fillByOrder() {
    const allImages = Array.from(document.querySelectorAll("img")).filter(img =>
      img.src && (img.src.includes("cdn.shopify.com") || img.src.includes("xopify"))
    );
    // Find all inputs — in bulk edit, every image card has Title + Alt text
    const allInputs = Array.from(document.querySelectorAll('input[type="text"], input:not([type]), textarea'));

    log("Strategy 2: " + allImages.length + " CDN images, " + allInputs.length + " text inputs");

    // Each image should have 2 inputs (Title, Alt text) — alt text is the 2nd one
    let filled = 0, skipped = 0, notFound = 0;

    for (let i = 0; i < allImages.length; i++) {
      const img = allImages[i];
      const filename = extractFilename(img.src);
      if (!filename) continue;

      const altText = findAltText(filename);
      if (!altText) { notFound++; continue; }

      // The alt text input for image i should be at index (i*2 + 1)
      const altInputIdx = i * 2 + 1;
      if (altInputIdx >= allInputs.length) {
        log("⚠️ No input at index " + altInputIdx + " for image " + i + " (" + filename + ")");
        continue;
      }
      const altInput = allInputs[altInputIdx];
      const current = (altInput.value || "").trim();
      if (current.length > 5) { skipped++; continue; }

      setReactInput(altInput, altText);
      filled++;
    }

    return { filled, skipped, notFound };
  }

  // ── Try Strategy 1 first, fall back to Strategy 2 ──
  log("🚀 Starting Gallery #11 alt text fill (70 images)...");

  let result = fillByImageWalk();
  log("Strategy 1 result: filled=" + result.filled + " skipped=" + result.skipped +
      " notFound=" + result.notFound + " noInput=" + (result.noInput || 0));

  if (result.filled === 0) {
    log("Strategy 1 found nothing, trying Strategy 2...", "🔄");
    result = fillByOrder();
    log("Strategy 2 result: filled=" + result.filled + " skipped=" + result.skipped +
        " notFound=" + result.notFound);
  }

  if (result.filled > 0) {
    log("✅ Filled " + result.filled + " alt text fields! Click Save to persist.", "🏁");
  } else {
    log("❌ No fields were filled. Check: are you in the correct frame context? Is Alt text column enabled?", "🏁");
    log("Debug: " + document.querySelectorAll("img").length + " total imgs, " +
        document.querySelectorAll("input, textarea").length + " total inputs");
  }

  return "Done: " + result.filled + " filled, " + result.skipped + " skipped, " + result.notFound + " not found";
})();
