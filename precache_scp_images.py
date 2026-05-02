#!/usr/bin/env python3
"""
Pre-cache SCP image URLs for all liquid cards.

Run this ONCE (locally, not in CI). It loads each SCP product page
via Selenium, grabs the Google Cloud Storage CDN image URL, and stores
it in the scp_cache variants JSONB.

After this runs, the daily auction pipeline skips Selenium entirely
and downloads images directly from the CDN.

Usage:
    /usr/local/bin/python3.12 precache_scp_images.py --limit 500
    /usr/local/bin/python3.12 precache_scp_images.py --limit 3000  # all liquid cards
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv('backend/.env')

from backend.utils.database import SessionLocal
from backend.scrapers.sportscardspro_scraper import SportsCardsProScraper
from sqlalchemy import text
from contextlib import closing


def main():
    parser = argparse.ArgumentParser(description='Pre-cache SCP image URLs')
    parser.add_argument('--limit', type=int, default=500)
    parser.add_argument('--skip-cached', action='store_true', default=True,
                        help='Skip variants that already have scp_image_url (default: True)')
    args = parser.parse_args()

    print(f"Loading liquid variants (limit {args.limit})...")
    with closing(SessionLocal()) as db:
        rows = db.execute(text("""
            SELECT sc.id, sc.player_name, sc.card_year, sc.card_number, sc.variants
            FROM scp_cache sc, jsonb_array_elements(sc.variants) v
            WHERE (v->>'ungraded')::numeric BETWEEN 5 AND 1000
              AND v->>'volume' IS NOT NULL AND v->>'volume' != ''
              AND (LOWER(v->>'volume') LIKE '%per day%'
                   OR LOWER(v->>'volume') LIKE '%per week%'
                   OR LOWER(v->>'volume') LIKE '%per month%')
            GROUP BY sc.id, sc.player_name, sc.card_year, sc.card_number, sc.variants
            LIMIT :lim
        """), {'lim': args.limit}).fetchall()

    print(f"Found {len(rows)} SCP cache entries to process")

    # Count how many need caching
    needs_cache = 0
    already_cached = 0
    for row in rows:
        variants = row[4] if isinstance(row[4], list) else json.loads(row[4])
        for v in variants:
            if v.get('scp_image_url'):
                already_cached += 1
            elif v.get('url'):
                needs_cache += 1

    print(f"Already cached: {already_cached}")
    print(f"Need caching: {needs_cache}")

    if needs_cache == 0:
        print("Nothing to cache!")
        return

    # Start Selenium
    print("Starting Selenium...")
    scraper = SportsCardsProScraper(headless=True)

    cached = 0
    errors = 0
    db = SessionLocal()

    try:
        for row_idx, row in enumerate(rows):
            cache_id = row[0]
            player = row[1]
            year = row[2]
            number = row[3]
            variants = row[4] if isinstance(row[4], list) else json.loads(row[4])

            for var_idx, v in enumerate(variants):
                if v.get('scp_image_url'):
                    continue  # Already cached
                if not v.get('url'):
                    continue  # No product page URL

                scp_url = v['url']
                parallel = v.get('parallel', 'Base')

                try:
                    img_url = scraper.get_product_image_url(scp_url)
                    if img_url:
                        # Update the variant in JSONB
                        db.execute(
                            text(
                                "UPDATE scp_cache SET variants = "
                                "jsonb_set(variants, ('{' || :idx || ',scp_image_url}')::text[], to_jsonb(:img_url::text)) "
                                "WHERE id = :cid"
                            ),
                            {'idx': str(var_idx), 'img_url': img_url, 'cid': cache_id},
                        )
                        db.commit()
                        cached += 1
                        if cached % 10 == 0:
                            print(f"  [{cached}/{needs_cache}] {player} {year} #{number} [{parallel}] -> cached")
                    else:
                        errors += 1
                except Exception as e:
                    db.rollback()
                    errors += 1
                    if errors <= 5:
                        print(f"  ERROR: {player} {year} #{number} [{parallel}]: {e}")

                time.sleep(1.5)  # Don't hammer SCP

            if (row_idx + 1) % 50 == 0:
                print(f"  Progress: {row_idx + 1}/{len(rows)} entries, {cached} cached, {errors} errors")

    finally:
        scraper.close()
        db.close()

    print(f"\nDone! Cached {cached} image URLs, {errors} errors")
    print(f"Next pipeline run will skip Selenium for these {cached} variants")


if __name__ == '__main__':
    main()
