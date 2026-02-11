"""
Automated Collector - Runs imports for all targets
"""
import yaml
from pathlib import Path
from datetime import datetime
from backend.services.data_pipeline import DataPipeline


class AutomatedCollector:
    """Runs data collection for all configured targets"""
    
    def __init__(self, config_path="config/targets.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.pipeline = DataPipeline()
    
    def _load_config(self):
        """Load targets configuration"""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def run_daily_collection(self):
        """Run full daily collection for all targets"""
        print(f"🚀 Starting automated collection - {datetime.now()}")
        print("=" * 80)
        
        schedule = self.config['schedule']
        days_back = schedule['days_back']
        
        total_sales = 0
        total_listings = 0
        
        # Import sales for each player
        if schedule['import_sales']:
            print("\n📥 IMPORTING SALES")
            print("-" * 80)
            
            for player in self.config['players']:
                player_name = player['name']
                print(f"\n🏀 {player_name} ({player['sport']})")
                
                for query_template in player['queries']:
                    query = query_template.format(name=player_name)
                    print(f"   Query: {query}")
                    
                    sales = self.pipeline.import_sales(query, days_back=days_back)
                    total_sales += sales
                    print(f"   ✅ Imported {sales} sales")
        
        # Import active listings
        if schedule['import_listings']:
            print("\n\n📋 IMPORTING ACTIVE LISTINGS")
            print("-" * 80)
            
            for player in self.config['players']:
                player_name = player['name']
                print(f"\n🏀 {player_name}")
                
                for query_template in player['queries']:
                    query = query_template.format(name=player_name)
                    
                    listings = self.pipeline.import_active_listings(query)
                    total_listings += listings
                    print(f"   ✅ Imported {listings} listings")
        
        # Calculate trends
        if schedule['calculate_trends']:
            print("\n\n📊 CALCULATING TRENDS")
            print("-" * 80)
            
            trends = self.pipeline.calculate_trends()
            print(f"✅ Calculated trends for {trends} cards")
        
        # Summary
        print("\n\n" + "=" * 80)
        print("📈 COLLECTION SUMMARY")
        print("=" * 80)
        print(f"Total sales imported: {total_sales}")
        print(f"Total listings imported: {total_listings}")
        print(f"Trends calculated: {trends}")
        print(f"Completed: {datetime.now()}")
        
        return {
            'sales': total_sales,
            'listings': total_listings,
            'trends': trends
        }
    
    def get_target_players(self):
        """Get list of all target players"""
        return [p['name'] for p in self.config['players']]


if __name__ == "__main__":
    collector = AutomatedCollector()
    collector.run_daily_collection()
