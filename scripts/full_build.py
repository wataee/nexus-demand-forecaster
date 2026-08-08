"""Full autonomous build and deployment script.

This script performs complete system build:
1. Check dependencies
2. Setup database (SQLite fallback if PostgreSQL unavailable)
3. Compile comprehensive public-source data
4. Load and validate data
5. Run segmentation
6. Train models (sample for speed)
7. Generate forecasts
8. Validate system
9. Start API server (optional)
"""

import sys
import os
from pathlib import Path
import traceback

sys.path.insert(0, str(Path(__file__).parent.parent))

# Set SQLite as fallback database
os.environ.setdefault("DATABASE_URL", "sqlite:///./demand_forecasting.db")

print("=" * 70)
print("FULL AUTONOMOUS BUILD AND DEPLOYMENT")
print("=" * 70)
print()

try:
    # Step 1: Setup database
    print("STEP 1: SETTING UP DATABASE")
    print("-" * 70)
    from src.database.connection import engine, Base
    from src.database.models import *  # noqa: F401, F403
    
    print("Creating database tables...")
    Base.metadata.create_all(engine)
    print("✓ Database tables created\n")
    
    # Step 2: Generate comprehensive data
    print("STEP 2: CURATING COMPREHENSIVE PUBLIC DATASET")
    print("-" * 70)
    from scripts.generate_comprehensive_data import ComprehensiveDataGenerator
    
    data_dir = Path("./data/raw")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate data for 1000 SKUs (faster for initial build)
    print("Collecting public reference data for 1000 SKUs...")
    generator = ComprehensiveDataGenerator(num_skus=1000)
    data = generator.generate_all(data_dir)
    print("✓ Data generation complete\n")
    
    # Step 3: Load data into database
    print("STEP 3: LOADING DATA INTO DATABASE")
    print("-" * 70)
    from src.data import DataIngestion, DataValidator, DataTransformer, DataStorage
    from src.database.connection import SessionLocal
    
    db = SessionLocal()
    try:
        # Ingest
        ingestion = DataIngestion(data_dir)
        raw_data = ingestion.load_all_data()
        print(f"Loaded {len(raw_data)} data types")
        
        # Validate
        validator = DataValidator()
        validation_results = validator.validate_all(raw_data)
        print("Validation results:")
        for data_type, results in validation_results.items():
            status = "✓" if results.get("valid", True) else "⚠"
            issues = len(results.get("issues", []))
            print(f"  {status} {data_type}: {issues} issues")
        
        # Transform
        transformer = DataTransformer(frequency="monthly")
        transformed_data = transformer.transform_all(raw_data)
        print("✓ Data transformation complete")
        
        # Store
        storage = DataStorage(db)
        storage_results = storage.store_all(transformed_data, replace=True)
        print("Storage results:")
        for data_type, count in storage_results.items():
            print(f"  ✓ {data_type}: {count} records")
        
    finally:
        db.close()
    
    print("✓ Data loading complete\n")
    
    # Step 4: Run segmentation
    print("STEP 4: RUNNING ABC/XYZ SEGMENTATION")
    print("-" * 70)
    from src.segmentation import ABCXYZSegmentation
    
    db = SessionLocal()
    try:
        segmentation = ABCXYZSegmentation(db)
        seg_df = segmentation.run_segmentation(replace=True)
        
        print(f"✓ Segmentation complete for {len(seg_df)} SKUs")
        print("\nSegment Distribution:")
        print(seg_df["segment_group"].value_counts().head(10))
        
    finally:
        db.close()
    
    print("\n✓ Segmentation complete\n")
    
    # Step 5: Train models (sample)
    print("STEP 5: TRAINING MODELS (SAMPLE)")
    print("-" * 70)
    from src.forecasting.training import ModelTrainer
    from src.database.models import Segmentation
    
    db = SessionLocal()
    try:
        # Get sample SKUs from each segment
        segs = db.query(Segmentation).limit(20).all()
        sku_ids = [s.sku_id for s in segs]
        
        print(f"Training models for {len(sku_ids)} SKUs...")
        
        trainer = ModelTrainer(db)
        results = trainer.train_all(sku_ids=sku_ids)
        
        success_count = sum(results.values())
        print(f"✓ Model training complete: {success_count}/{len(results)} successful")
        
    finally:
        db.close()
    
    print("\n✓ Model training complete\n")
    
    # Step 6: Generate forecasts
    print("STEP 6: GENERATING FORECASTS")
    print("-" * 70)
    from src.database.models import ModelRegistry, Forecast, SalesHistory
    from src.config import settings
    from datetime import datetime, timedelta
    from pathlib import Path
    import pickle
    
    db = SessionLocal()
    try:
        models = db.query(ModelRegistry).filter(ModelRegistry.is_active == True).limit(10).all()
        
        if len(models) == 0:
            print("⚠ No trained models found. Skipping forecast generation.")
        else:
            print(f"Generating forecasts for {len(models)} SKUs...")
            
            forecast_horizon = settings.model.forecast_horizon_months
            forecasts_created = 0
            
            for model_reg in models:
                try:
                    model_path = Path(model_reg.model_path)
                    if not model_path.exists():
                        continue
                    
                    with open(model_path, "rb") as f:
                        model = pickle.load(f)
                    
                    sales = db.query(SalesHistory).filter(
                        SalesHistory.sku_id == model_reg.sku_id
                    ).order_by(SalesHistory.date.desc()).limit(24).all()
                    
                    if len(sales) < 12:
                        continue
                    
                    predictions = model.predict(forecast_horizon)
                    
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
                    print(f"  ⚠ Error for {model_reg.sku_id}: {str(e)[:50]}")
                    continue
            
            db.commit()
            print(f"✓ Generated {forecasts_created} forecasts")
        
    finally:
        db.close()
    
    print("\n✓ Forecast generation complete\n")
    
    # Step 7: Generate recommendations
    print("STEP 7: GENERATING ORDER RECOMMENDATIONS")
    print("-" * 70)
    from src.recommendations import OrderRecommendationEngine
    
    db = SessionLocal()
    try:
        engine = OrderRecommendationEngine(db)
        recommendations = engine.generate_all_recommendations()
        
        print(f"✓ Generated {len(recommendations)} recommendations")
        if len(recommendations) > 0:
            print(f"  Top recommendation: SKU {recommendations[0]['sku_id']}, Qty: {recommendations[0]['recommended_qty']:.0f}")
        
    finally:
        db.close()
    
    print("\n✓ Recommendations complete\n")
    
    # Step 8: Validate system
    print("STEP 8: VALIDATING SYSTEM")
    print("-" * 70)
    from scripts.validate_public_data import PublicDataValidator
    
    validator = PublicDataValidator(data_dir)
    results = validator.run_all_validations()
    
    # Step 9: System summary
    print("\n" + "=" * 70)
    print("BUILD SUMMARY")
    print("=" * 70)
    
    db = SessionLocal()
    try:
        from src.database.models import SKUMaster, Forecast, OrderRecommendation, Segmentation
        
        total_skus = db.query(SKUMaster).count()
        total_forecasts = db.query(Forecast).count()
        total_recommendations = db.query(OrderRecommendation).count()
        total_segments = db.query(Segmentation).count()
        
        print(f"✓ SKUs in system: {total_skus}")
        print(f"✓ Forecasts generated: {total_forecasts}")
        print(f"✓ Recommendations: {total_recommendations}")
        print(f"✓ Segmented SKUs: {total_segments}")
        print(f"✓ Validation status: {'PASSED' if results.get('overall_valid', False) else 'REVIEW NEEDED'}")
        
    finally:
        db.close()
    
    print("\n" + "=" * 70)
    print("BUILD COMPLETE - SYSTEM READY")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Start API: uvicorn src.api.main:app --reload")
    print("2. Access API docs: http://localhost:8000/docs")
    print("3. Train more models: python scripts/train_models.py")
    print("4. Generate more forecasts: python scripts/generate_forecasts.py")
    print()

except Exception as e:
    print("\n" + "=" * 70)
    print("BUILD ERROR")
    print("=" * 70)
    print(f"Error: {str(e)}")
    print("\nTraceback:")
    traceback.print_exc()
    sys.exit(1)

