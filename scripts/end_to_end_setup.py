"""End-to-end setup script that generates data, loads it, and validates the system.

This script:
1. Compiles comprehensive public-source data
2. Loads data into database
3. Runs segmentation
4. Trains models (sample)
5. Generates forecasts (sample)
6. Validates statistical behavior
"""

import sys
from pathlib import Path
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import SessionLocal, engine, Base
from src.database.models import *  # noqa: F401, F403
from src.data import DataIngestion, DataValidator, DataTransformer, DataStorage
from src.segmentation import ABCXYZSegmentation
from src.forecasting.training import ModelTrainer
from scripts.generate_comprehensive_data import ComprehensiveDataGenerator
from scripts.validate_public_data import PublicDataValidator


def setup_database():
    """Create database tables."""
    print("Setting up database...")
    Base.metadata.create_all(engine)
    print("✓ Database tables created")


def generate_and_load_data(data_dir: Path, num_skus: int = 3000):
    """Generate comprehensive data and load into database."""
    print("\n" + "=" * 60)
    print("STEP 1: CURATE COMPREHENSIVE PUBLIC DATASET")
    print("=" * 60)
    
    # Generate data
    generator = ComprehensiveDataGenerator(num_skus=num_skus)
    data = generator.generate_all(data_dir)
    
    print("\n" + "=" * 60)
    print("STEP 2: LOAD DATA INTO DATABASE")
    print("=" * 60)
    
    # Load into database
    db = SessionLocal()
    try:
        ingestion = DataIngestion(data_dir)
        raw_data = ingestion.load_all_data()
        
        # Validate
        validator = DataValidator()
        validation_results = validator.validate_all(raw_data)
        
        print("\nValidation Results:")
        for data_type, results in validation_results.items():
            status = "✓" if results.get("valid", True) else "✗"
            print(f"{status} {data_type}: {len(results.get('issues', []))} issues")
        
        # Transform
        transformer = DataTransformer(frequency="monthly")
        transformed_data = transformer.transform_all(raw_data)
        
        # Store
        storage = DataStorage(db)
        storage_results = storage.store_all(transformed_data, replace=True)
        
        print("\nStorage Results:")
        for data_type, count in storage_results.items():
            print(f"  {data_type}: {count} records stored")
        
    finally:
        db.close()
    
    return data


def run_segmentation():
    """Run ABC/XYZ segmentation."""
    print("\n" + "=" * 60)
    print("STEP 3: RUN ABC/XYZ SEGMENTATION")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        segmentation = ABCXYZSegmentation(db)
        seg_df = segmentation.run_segmentation(replace=True)
        
        print(f"\n✓ Segmentation complete for {len(seg_df)} SKUs")
        print(f"\nSegment Distribution:")
        print(seg_df["segment_group"].value_counts())
        
    finally:
        db.close()


def train_sample_models(num_skus: int = 50):
    """Train models for a sample of SKUs."""
    print("\n" + "=" * 60)
    print("STEP 4: TRAIN MODELS (SAMPLE)")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        from src.database.models import Segmentation
        
        # Get sample SKUs from each segment
        segs = db.query(Segmentation).limit(num_skus).all()
        sku_ids = [s.sku_id for s in segs]
        
        print(f"Training models for {len(sku_ids)} SKUs...")
        
        trainer = ModelTrainer(db)
        results = trainer.train_all(sku_ids=sku_ids)
        
        success_count = sum(results.values())
        print(f"\n✓ Model training complete: {success_count}/{len(results)} successful")
        
    finally:
        db.close()


def generate_sample_forecasts():
    """Generate forecasts for sample SKUs."""
    print("\n" + "=" * 60)
    print("STEP 5: GENERATE FORECASTS (SAMPLE)")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        from src.database.models import ModelRegistry, Forecast, SalesHistory
        from src.config import settings
        from datetime import datetime, timedelta
        from pathlib import Path
        import pickle
        
        # Get SKUs with trained models
        models = db.query(ModelRegistry).filter(ModelRegistry.is_active == True).limit(20).all()
        
        if len(models) == 0:
            print("No trained models found. Skipping forecast generation.")
            return
        
        print(f"Generating forecasts for {len(models)} SKUs...")
        
        forecast_horizon = settings.model.forecast_horizon_months
        forecasts_created = 0
        
        for model_reg in models:
            try:
                # Load model
                model_path = Path(model_reg.model_path)
                if not model_path.exists():
                    continue
                
                with open(model_path, "rb") as f:
                    model = pickle.load(f)
                
                # Get training data for prediction
                sales = db.query(SalesHistory).filter(
                    SalesHistory.sku_id == model_reg.sku_id
                ).order_by(SalesHistory.date.desc()).limit(24).all()
                
                if len(sales) < 12:
                    continue
                
                # Generate forecast
                predictions = model.predict(forecast_horizon)
                
                # Store forecasts
                forecast_date = datetime.now().date()
                for i, pred in enumerate(predictions):
                    forecast = Forecast(
                        sku_id=model_reg.sku_id,
                        forecast_date=forecast_date + timedelta(days=30 * (i + 1)),
                        predicted_units=float(pred),
                        confidence_level=0.8,
                        model_type=model_reg.model_type,
                        model_version=model_reg.model_version,
                    )
                    db.add(forecast)
                    forecasts_created += 1
                
            except Exception as e:
                print(f"  Error generating forecast for {model_reg.sku_id}: {e}")
                continue
        
        db.commit()
        print(f"\n✓ Generated {forecasts_created} forecasts")
        
    finally:
        db.close()


def validate_system(data_dir: Path):
    """Validate statistical behavior."""
    print("\n" + "=" * 60)
    print("STEP 6: STATISTICAL VALIDATION")
    print("=" * 60)
    
    validator = PublicDataValidator(data_dir)
    results = validator.run_all_validations()
    
    return results


def main():
    parser = argparse.ArgumentParser(description="End-to-end system setup and validation")
    parser.add_argument("--num-skus", type=int, default=3000, help="Number of SKUs to generate")
    parser.add_argument("--skip-generation", action="store_true", help="Skip data generation (use existing)")
    parser.add_argument("--skip-training", action="store_true", help="Skip model training")
    parser.add_argument("--data-dir", type=str, default="./data/raw", help="Data directory")
    
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("END-TO-END SYSTEM SETUP AND VALIDATION")
    print("=" * 60)
    
    try:
        # Setup database
        setup_database()
        
        # Generate and load data
        if not args.skip_generation:
            generate_and_load_data(data_dir, args.num_skus)
        else:
            print("\nSkipping data generation (using existing data)")
        
        # Run segmentation
        run_segmentation()
        
        # Train models (sample)
        if not args.skip_training:
            train_sample_models(num_skus=min(50, args.num_skus // 10))
        else:
            print("\nSkipping model training")
        
        # Generate forecasts (sample)
        generate_sample_forecasts()
        
        # Validate
        validation_results = validate_system(data_dir)
        
        # Final summary
        print("\n" + "=" * 60)
        print("SETUP COMPLETE")
        print("=" * 60)
        
        if validation_results.get("overall_valid", False):
            print("\n✓ System validation passed!")
            print("\nNext steps:")
            print("1. Review validation results above")
            print("2. Train models for all SKUs: python scripts/train_models.py")
            print("3. Generate forecasts: python scripts/generate_forecasts.py")
            print("4. Start API: uvicorn src.api.main:app --reload")
        else:
            print("\n⚠ Some validations failed. Review results above.")
            print("Data may need adjustment for better realism.")
        
    except Exception as e:
        print(f"\n✗ Error during setup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

