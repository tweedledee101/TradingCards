"""
Report Generator - Creates daily trending card reports
"""
import yaml
import csv
from pathlib import Path
from datetime import date, datetime
from backend.services.data_pipeline import DataPipeline


class ReportGenerator:
    """Generates daily reports of trending cards"""
    
    def __init__(self, config_path="config/targets.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.pipeline = DataPipeline()
        self.output_dir = Path(self.config['reports']['output_dir'])
        self.output_dir.mkdir(exist_ok=True)
    
    def _load_config(self):
        """Load configuration"""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def generate_daily_report(self):
        """Generate daily trending cards report"""
        today = date.today()
        limit = self.config['reports']['top_cards_limit']
        
        print(f"\n📊 Generating Daily Report - {today}")
        print("=" * 80)
        
        # Get trending cards
        trending = self.pipeline.get_trending_cards(limit=limit)
        
        if not trending:
            print("⚠️  No trending cards found. Import data first.")
            return None
        
        # Generate CSV report
        csv_path = self.output_dir / f"trending_cards_{today}.csv"
        self._write_csv_report(trending, csv_path)
        print(f"✅ CSV report saved: {csv_path}")
        
        # Generate text report
        txt_path = self.output_dir / f"trending_cards_{today}.txt"
        self._write_text_report(trending, txt_path)
        print(f"✅ Text report saved: {txt_path}")
        
        # Print summary
        self._print_summary(trending)
        
        return {
            'csv': str(csv_path),
            'txt': str(txt_path),
            'count': len(trending)
        }
    
    def _write_csv_report(self, trending, path):
        """Write CSV report"""
        with open(path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'rank', 'player_name', 'card_year', 'card_set', 'is_rookie',
                'avg_price', 'sales_count', 'velocity_score', 'hotness_score', 'category'
            ])
            writer.writeheader()
            
            for i, card in enumerate(trending, 1):
                writer.writerow({
                    'rank': i,
                    'player_name': card['player_name'],
                    'card_year': card['card_year'],
                    'card_set': card['card_set'],
                    'is_rookie': card['is_rookie'],
                    'avg_price': card['avg_price'],
                    'sales_count': card['sales_count'],
                    'velocity_score': card['velocity_score'],
                    'hotness_score': card['hotness_score'],
                    'category': card['category']
                })
    
    def _write_text_report(self, trending, path):
        """Write human-readable text report"""
        with open(path, 'w') as f:
            f.write(f"TRENDING CARDS REPORT\n")
            f.write(f"Generated: {datetime.now()}\n")
            f.write("=" * 80 + "\n\n")
            
            for i, card in enumerate(trending, 1):
                f.write(f"{i}. {card['player_name']} - {card['card_year']} {card['card_set']}\n")
                if card['is_rookie']:
                    f.write(f"   🏆 ROOKIE CARD\n")
                f.write(f"   💰 Avg Price: ${card['avg_price']:.2f}\n")
                f.write(f"   📈 Sales: {card['sales_count']} | Velocity: {card['velocity_score']:.1f}\n")
                f.write(f"   🔥 Hotness: {card['hotness_score']:.1f} - {card['category']}\n")
                f.write("\n")
    
    def _print_summary(self, trending):
        """Print summary to console"""
        print(f"\n🔥 TOP 10 TRENDING CARDS")
        print("=" * 80)
        
        for i, card in enumerate(trending[:10], 1):
            print(f"{i}. {card['player_name']} - {card['card_year']} {card['card_set']}")
            print(f"   💰 ${card['avg_price']:.2f} | 🔥 {card['hotness_score']:.1f} - {card['category']}")


if __name__ == "__main__":
    generator = ReportGenerator()
    generator.generate_daily_report()
