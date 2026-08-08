"""Script to generate forecasts for all SKUs."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.workflows.forecast_pipeline import forecast_pipeline_flow
import argparse


def main():
    parser = argparse.ArgumentParser(description="Generate forecasts")
    parser.add_argument("--sku-id", type=str, help="Generate forecast for specific SKU")
    parser.add_argument("--retrain", action="store_true", help="Retrain models before forecasting")
    
    args = parser.parse_args()
    
    sku_ids = [args.sku_id] if args.sku_id else None
    
    forecasts_created = forecast_pipeline_flow(sku_ids=sku_ids, retrain=args.retrain)
    print(f"Generated {forecasts_created} forecasts")


if __name__ == "__main__":
    main()

