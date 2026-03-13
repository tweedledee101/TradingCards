"""
Pipeline Runner - Test end-to-end data flow

Usage:
    python -m backend.run_pipeline --query "Wembanyama rookie" --days 7
"""
import argparse
from backend.services.data_pipeline import DataPipeline


def main():
    parser = argparse.ArgumentParser(description='Run trading card data pipeline')
    parser.add_argument('--query', type=str, required=True, help='Search query (e.g., "Wembanyama rookie")')
    parser.add_argument('--player', type=str, help='Player name (validated, e.g., "Victor Wembanyama")')
    parser.add_argument('--sport', type=str, help='Sport (e.g., "Basketball")')
    parser.add_argument('--days', type=int, default=7, help='Days back to search (default: 7)')
    parser.add_argument('--skip-listings', action='store_true', help='Skip active listings import')
    parser.add_argument('--skip-trends', action='store_true', help='Skip trend calculation')
    
    args = parser.parse_args()
    
    pipeline = DataPipeline()
    
    print(f"🔍 Searching eBay for: {args.query}")
    if args.player:
        print(f"👤 Player: {args.player} ({args.sport or 'Sport not specified'})")
    print(f"📅 Looking back: {args.days} days\n")
    
    # Import sales
    print("📥 Importing sold listings...")
    sales_imported = pipeline.import_sales(args.query, args.days, args.player, args.sport)
    print(f"✅ Imported {sales_imported} sales\n")
    
    # Import active listings
    if not args.skip_listings:
        print("📥 Importing active listings...")
        listings_imported = pipeline.import_active_listings(args.query)
        print(f"✅ Imported {listings_imported} listings\n")
    
    # Calculate trends
    if not args.skip_trends:
        print("📊 Calculating trends...")
        trends_calculated = pipeline.calculate_trends()
        print(f"✅ Calculated trends for {trends_calculated} cards\n")
    
    # Show top trending
    print("🔥 TOP TRENDING CARDS:")
    print("=" * 80)
    trending = pipeline.get_trending_cards(limit=10)
    
    if not trending:
        print("No trending cards found. Import more data first.")
    else:
        for i, card in enumerate(trending, 1):
            print(f"{i}. {card['player_name']} - {card['card_year']} {card['card_set']}")
            print(f"   {'🏆 ROOKIE' if card['is_rookie'] else ''}")
            print(f"   💰 Avg Price: ${card['avg_price']:.2f}")
            print(f"   📈 Sales: {card['sales_count']} | Velocity: {card['velocity_score']:.1f}")
            print(f"   🔥 Hotness: {card['hotness_score']:.1f} - {card['category']}")
            print()


if __name__ == '__main__':
    main()
