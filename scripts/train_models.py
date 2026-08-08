"""Script to train models for all SKUs."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import SessionLocal
from src.forecasting.training import ModelTrainer
import argparse


def main():
    parser = argparse.ArgumentParser(description="Train models for SKUs")
    parser.add_argument("--sku-id", type=str, help="Train model for specific SKU")
    parser.add_argument("--segment", type=str, help="Train models for specific segment (e.g., AX, BY)")
    parser.add_argument("--limit", type=int, help="Limit number of SKUs to train")
    
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        trainer = ModelTrainer(db)
        
        if args.sku_id:
            # Train single SKU
            success = trainer.train_sku(args.sku_id)
            print(f"Training {'successful' if success else 'failed'} for SKU {args.sku_id}")
        else:
            # Train all or filtered
            sku_ids = None
            if args.limit:
                from src.database.models import Segmentation
                segs = db.query(Segmentation).limit(args.limit).all()
                sku_ids = [s.sku_id for s in segs]
            
            results = trainer.train_all(sku_ids=sku_ids, segment_filter=args.segment)
            success_count = sum(results.values())
            print(f"Training complete: {success_count}/{len(results)} successful")
    finally:
        db.close()


if __name__ == "__main__":
    main()

