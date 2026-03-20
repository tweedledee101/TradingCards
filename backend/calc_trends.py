"""Calculate price trends for all cards with sales data."""
from backend.services.data_pipeline import DataPipeline

pipeline = DataPipeline()
count = pipeline.calculate_trends()
print(f"Calculated trends for {count} cards")
