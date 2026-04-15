# CE Variant Correction -- Accuracy Improvement Strategy

## The Problem (validated April 14, 2026)

Manual validation of 4 disputed opportunities revealed:
- **3 out of 4 were wrong SCP matches** (pipeline matched wrong parallel/variant)
- **1 out of 4 was CE being wrong** (CE identified base card instead of Dark Yellow variant)

The root cause: the SCP cache returns thousands of variations per player, many sharing
the same card number but different parallels. The pipeline's parallel matching uses
keyword overlap (`any(kw in title)`) which can't distinguish "Blue Rainbow" from
"Aqua Rainbow" or "Green Rainbow" -- they all contain "rainbow."

## What CE Gets Right vs Wrong

From 20 verified opportunities with CE variant data:

**CE reliably identifies:**
- Card COLOR (Green vs Blue vs Aqua vs Red)
- Refractor type (Atomic, Raywave, Chrome)
- Print run when visible (/5, /99, /100)

**CE is unreliable on:**
- Year (recurring designs, retro inserts -- 2025 Stadium Club looks like 1993)
- Price (varies wildly, sometimes 10x off)
- Subtle variants (missed "Dark Yellow Bordered" entirely, called it "Base")

## The Solution: CE Variant -> SCP Lookup

Instead of using CE as a pass/fail verifier, use CE's variant identification
to find the CORRECT SCP entry:

1. Pipeline finds opportunity: player + year + card# + pipeline_parallel + SCP price
2. CE identifies card from image: returns ce_variant (color, refractor type)
3. Search SCP cache for: player + year + card# + ce_variant keywords
4. If SCP entry found: use THAT price for profit calculation
5. If corrected price still shows $10+ profit after fees: confirmed opportunity
6. If corrected price kills the profit: reject (pipeline had wrong SCP match)

## Example: Ohtani #200

- Pipeline: "Blue Rainbow" parallel, SCP $193.58
- CE: "Aqua Border" / "Green Rainbow Foil"
- SCP cache has "Aqua Rainbow" at $56.47
- eBay price: $59.99
- Corrected profit: $56.47 - $59.99 - fees = NEGATIVE -> not an opportunity
- Old pipeline showed $120+ "profit" that didn't exist

## Price Triangle (complementary check)

When CE variant lookup isn't conclusive, use price agreement:
- eBay price ≈ CE median, SCP far off -> wrong SCP match
- CE median ≈ SCP, eBay much lower -> possible real opportunity
- All three agree -> strong confirmation

## Implementation Status

- [x] CE API integration (call_ce_identify_api)
- [x] CE variant extraction (ce_variant field in verification_detail)
- [x] Price triangle logic (verify_opportunities_ce.py)
- [x] CE variant -> SCP cache lookup (ce_variant_correction.py)
- [x] 130point sold comps as confirmation (real sales data, fastest signal)
- [x] 4-signal recalculation (SCP + CE + 130point + eBay asking price)
- [ ] Wire full_variant_correction into verify_opportunities_ce.py
- [ ] Integration into CI pipeline
- [ ] Handle CE variant misidentification (e.g., "Base" when card is "Dark Yellow")

## Known Limitations (honest)

1. **CE variant misidentification**: CE called a Dark Yellow Heritage card "Base" -- when CE
   gets the variant wrong, 130point confirms the wrong card too. 2/3 correct in manual testing.
2. **CE year unreliable**: CE frequently returns wrong year (recurring designs, retro inserts).
   Year should NOT be used as a hard pass/fail signal.
3. **CE price approximate**: CE prices can be 10x off. Useful as a signal alongside other
   sources, not as a standalone reference.
4. **130point rate limit**: 10 requests/minute, 429 = blocked ~1 hour. Can't query for every
   opportunity in a single pipeline run.
5. **SCP variant matching still keyword-based**: "Aqua Rainbow" vs "Blue Rainbow" requires
   exact color word match. Works when CE identifies the color correctly, fails when CE doesn't.
