"""Validate public-source data statistical behavior.

Validates:
- Distribution of SKU velocities
- ABC/XYZ segmentation spread
- Inventory turnover
- Lead-time variance
- Demand pattern distributions
"""

import sys
from pathlib import Path
from typing import Dict
import pandas as pd
import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import DataIngestion
from src.segmentation import ABCXYZSegmentation
from src.database.connection import SessionLocal


class PublicDataValidator:
    """Validate harmonized public data against expected statistical properties."""
    
    def __init__(self, data_dir: Path):
        """
        Initialize validator.
        
        Args:
            data_dir: Directory containing curated public data files
        """
        self.data_dir = Path(data_dir)
        self.ingestion = DataIngestion(data_dir)
        self.data = {}
        self.validation_results = {}
    
    def load_data(self):
        """Load all data files."""
        print("Loading data files...")
        self.data = self.ingestion.load_all_data()
        print(f"Loaded {len(self.data)} data types")
    
    def validate_sku_velocity_distribution(self) -> Dict:
        """Validate distribution of SKU velocities."""
        print("\n" + "=" * 60)
        print("VALIDATING SKU VELOCITY DISTRIBUTION")
        print("=" * 60)
        
        sales = self.data["sales_history"]
        
        # Calculate annual velocity per SKU
        sku_velocity = sales.groupby("sku_id")["units_sold"].sum()
        
        # Expected: Long-tail distribution (few high-velocity, many low-velocity)
        # Check if distribution is log-normal or power-law
        
        # Remove zeros
        sku_velocity_nonzero = sku_velocity[sku_velocity > 0]
        
        # Calculate statistics
        mean_velocity = sku_velocity_nonzero.mean()
        median_velocity = sku_velocity_nonzero.median()
        std_velocity = sku_velocity_nonzero.std()
        cv = std_velocity / mean_velocity if mean_velocity > 0 else 0
        
        # Percentiles
        p10 = sku_velocity_nonzero.quantile(0.10)
        p50 = sku_velocity_nonzero.quantile(0.50)
        p90 = sku_velocity_nonzero.quantile(0.90)
        p99 = sku_velocity_nonzero.quantile(0.99)
        
        # Check for long-tail (high ratio of p99/p50)
        tail_ratio = p99 / p50 if p50 > 0 else 0
        
        results = {
            "total_skus": len(sku_velocity),
            "skus_with_sales": len(sku_velocity_nonzero),
            "zero_sales_skus": len(sku_velocity) - len(sku_velocity_nonzero),
            "mean_velocity": mean_velocity,
            "median_velocity": median_velocity,
            "std_velocity": std_velocity,
            "coefficient_of_variation": cv,
            "percentiles": {
                "p10": p10,
                "p50": p50,
                "p90": p90,
                "p99": p99,
            },
            "tail_ratio": tail_ratio,
            "validation": {
                "has_long_tail": tail_ratio > 10,  # Long-tail if p99 >> p50
                "cv_reasonable": 0.5 < cv < 3.0,  # Reasonable variability
                "zero_sales_pct": (len(sku_velocity) - len(sku_velocity_nonzero)) / len(sku_velocity),
            },
        }
        
        print(f"Total SKUs: {results['total_skus']}")
        print(f"SKUs with sales: {results['skus_with_sales']}")
        print(f"Zero sales SKUs: {results['zero_sales_skus']} ({results['validation']['zero_sales_pct']*100:.1f}%)")
        print(f"Mean velocity: {mean_velocity:.0f}")
        print(f"Median velocity: {median_velocity:.0f}")
        print(f"Coefficient of variation: {cv:.2f}")
        print(f"Tail ratio (p99/p50): {tail_ratio:.2f}")
        print(f"Long-tail distribution: {results['validation']['has_long_tail']}")
        
        return results
    
    def validate_abc_xyz_segmentation(self) -> Dict:
        """Validate ABC/XYZ segmentation spread."""
        print("\n" + "=" * 60)
        print("VALIDATING ABC/XYZ SEGMENTATION")
        print("=" * 60)
        
        # Run segmentation
        db = SessionLocal()
        try:
            # Load data into database first
            from src.data.storage import DataStorage
            storage = DataStorage(db)
            storage.store_all(self.data, replace=True)
            
            # Run segmentation
            segmentation = ABCXYZSegmentation(db)
            seg_df = segmentation.run_segmentation(replace=True)
            
            # Analyze distribution
            abc_dist = seg_df["abc_class"].value_counts()
            xyz_dist = seg_df["xyz_class"].value_counts()
            segment_dist = seg_df["segment_group"].value_counts()
            
            # Expected: ~20% A, ~30% B, ~50% C
            total = len(seg_df)
            a_pct = abc_dist.get("A", 0) / total
            b_pct = abc_dist.get("B", 0) / total
            c_pct = abc_dist.get("C", 0) / total
            
            results = {
                "total_skus": total,
                "abc_distribution": {
                    "A": {"count": abc_dist.get("A", 0), "percentage": a_pct},
                    "B": {"count": abc_dist.get("B", 0), "percentage": b_pct},
                    "C": {"count": abc_dist.get("C", 0), "percentage": c_pct},
                },
                "xyz_distribution": {
                    "X": {"count": xyz_dist.get("X", 0), "percentage": xyz_dist.get("X", 0) / total},
                    "Y": {"count": xyz_dist.get("Y", 0), "percentage": xyz_dist.get("Y", 0) / total},
                    "Z": {"count": xyz_dist.get("Z", 0), "percentage": xyz_dist.get("Z", 0) / total},
                },
                "segment_groups": segment_dist.to_dict(),
                "validation": {
                    "abc_balanced": 0.15 < a_pct < 0.25 and 0.25 < b_pct < 0.35 and 0.45 < c_pct < 0.55,
                    "all_segments_present": len(segment_dist) == 9,
                },
            }
            
            print(f"ABC Distribution:")
            print(f"  A: {abc_dist.get('A', 0)} ({a_pct*100:.1f}%)")
            print(f"  B: {abc_dist.get('B', 0)} ({b_pct*100:.1f}%)")
            print(f"  C: {abc_dist.get('C', 0)} ({c_pct*100:.1f}%)")
            print(f"\nXYZ Distribution:")
            print(f"  X: {xyz_dist.get('X', 0)} ({xyz_dist.get('X', 0)/total*100:.1f}%)")
            print(f"  Y: {xyz_dist.get('Y', 0)} ({xyz_dist.get('Y', 0)/total*100:.1f}%)")
            print(f"  Z: {xyz_dist.get('Z', 0)} ({xyz_dist.get('Z', 0)/total*100:.1f}%)")
            print(f"\nSegment Groups: {len(segment_dist)} groups present")
            print(f"ABC balanced: {results['validation']['abc_balanced']}")
            
            return results
        
        finally:
            db.close()
    
    def validate_inventory_turnover(self) -> Dict:
        """Validate inventory turnover rates."""
        print("\n" + "=" * 60)
        print("VALIDATING INVENTORY TURNOVER")
        print("=" * 60)
        
        sales = self.data["sales_history"]
        inventory = self.data["inventory"]
        
        # Calculate annual sales per SKU
        annual_sales = sales.groupby("sku_id")["units_sold"].sum()
        
        # Get average inventory levels
        avg_inventory = inventory.groupby("sku_id")["stock_level"].mean()
        
        # Calculate turnover (sales / avg_inventory)
        turnover = annual_sales / avg_inventory.replace(0, np.nan)
        turnover = turnover.dropna()
        
        # Statistics
        mean_turnover = turnover.mean()
        median_turnover = turnover.median()
        
        # Expected: Turnover between 2-12 for most SKUs
        reasonable_turnover = turnover[(turnover >= 2) & (turnover <= 12)]
        
        results = {
            "skus_with_turnover": len(turnover),
            "mean_turnover": mean_turnover,
            "median_turnover": median_turnover,
            "turnover_range": {
                "min": turnover.min(),
                "max": turnover.max(),
            },
            "reasonable_turnover_pct": len(reasonable_turnover) / len(turnover) if len(turnover) > 0 else 0,
            "validation": {
                "median_reasonable": 2 <= median_turnover <= 12,
                "most_reasonable": len(reasonable_turnover) / len(turnover) > 0.6 if len(turnover) > 0 else False,
            },
        }
        
        print(f"SKUs with turnover data: {results['skus_with_turnover']}")
        print(f"Mean turnover: {mean_turnover:.2f}")
        print(f"Median turnover: {median_turnover:.2f}")
        print(f"Turnover range: {results['turnover_range']['min']:.2f} - {results['turnover_range']['max']:.2f}")
        print(f"Reasonable turnover (%): {results['reasonable_turnover_pct']*100:.1f}%")
        
        return results
    
    def validate_lead_time_variance(self) -> Dict:
        """Validate lead time variance by supplier country."""
        print("\n" + "=" * 60)
        print("VALIDATING LEAD TIME VARIANCE")
        print("=" * 60)
        
        pos = self.data["purchase_orders"]
        suppliers = self.data["suppliers"]
        
        # Merge PO with supplier data
        po_with_supplier = pos.merge(
            suppliers[["supplier_id", "country", "base_lead_time_days"]],
            on="supplier_id",
            how="left"
        )
        
        # Calculate variance by country
        lead_time_stats = po_with_supplier.groupby("country")["lead_time_days"].agg([
            "count", "mean", "std", "min", "max"
        ]).round(2)
        
        # Calculate CV (coefficient of variation) by country
        lead_time_stats["cv"] = (lead_time_stats["std"] / lead_time_stats["mean"]).round(3)
        
        results = {
            "by_country": lead_time_stats.to_dict("index"),
            "validation": {
                "asian_high_variance": lead_time_stats.loc["CN", "cv"] > 0.2 if "CN" in lead_time_stats.index else False,
                "brazilian_low_variance": lead_time_stats.loc["BR", "cv"] < 0.4 if "BR" in lead_time_stats.index else False,
            },
        }
        
        print("Lead Time Statistics by Country:")
        print(lead_time_stats)
        
        return results
    
    def validate_demand_patterns(self) -> Dict:
        """Validate demand pattern distributions."""
        print("\n" + "=" * 60)
        print("VALIDATING DEMAND PATTERNS")
        print("=" * 60)
        
        sales = self.data["sales_history"]
        
        # Calculate CV per SKU to classify patterns
        sku_stats = sales.groupby("sku_id")["units_sold"].agg([
            "mean", "std", "count"
        ])
        sku_stats["cv"] = sku_stats["std"] / sku_stats["mean"].replace(0, np.nan)
        sku_stats = sku_stats.dropna()
        
        # Classify patterns
        stable = sku_stats[sku_stats["cv"] < 0.5]
        seasonal = sku_stats[(sku_stats["cv"] >= 0.5) & (sku_stats["cv"] < 1.0)]
        intermittent = sku_stats[sku_stats["cv"] >= 1.0]
        
        # Zero-inflation check
        zero_sales_pct = (sales["units_sold"] == 0).sum() / len(sales)
        
        results = {
            "total_skus": len(sku_stats),
            "pattern_distribution": {
                "stable": {"count": len(stable), "percentage": len(stable) / len(sku_stats)},
                "seasonal": {"count": len(seasonal), "percentage": len(seasonal) / len(sku_stats)},
                "intermittent": {"count": len(intermittent), "percentage": len(intermittent) / len(sku_stats)},
            },
            "zero_sales_percentage": zero_sales_pct,
            "validation": {
                "pattern_distribution_reasonable": (
                    0.10 < len(stable) / len(sku_stats) < 0.20 and
                    0.30 < len(seasonal) / len(sku_stats) < 0.40 and
                    0.45 < len(intermittent) / len(sku_stats) < 0.55
                ),
                "zero_inflation_reasonable": 0.05 < zero_sales_pct < 0.25,
            },
        }
        
        print(f"Pattern Distribution:")
        print(f"  Stable (CV < 0.5): {len(stable)} ({len(stable)/len(sku_stats)*100:.1f}%)")
        print(f"  Seasonal (0.5 ≤ CV < 1.0): {len(seasonal)} ({len(seasonal)/len(sku_stats)*100:.1f}%)")
        print(f"  Intermittent (CV ≥ 1.0): {len(intermittent)} ({len(intermittent)/len(sku_stats)*100:.1f}%)")
        print(f"Zero sales percentage: {zero_sales_pct*100:.1f}%")
        
        return results
    
    def run_all_validations(self) -> Dict:
        """Run all validation checks."""
        print("\n" + "=" * 60)
        print("COMPREHENSIVE STATISTICAL VALIDATION")
        print("=" * 60)
        
        self.load_data()
        
        results = {
            "sku_velocity": self.validate_sku_velocity_distribution(),
            "abc_xyz": self.validate_abc_xyz_segmentation(),
            "inventory_turnover": self.validate_inventory_turnover(),
            "lead_time_variance": self.validate_lead_time_variance(),
            "demand_patterns": self.validate_demand_patterns(),
        }
        
        # Overall validation summary
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        
        all_valid = True
        for check_name, check_results in results.items():
            if "validation" in check_results:
                validations = check_results["validation"]
                for key, value in validations.items():
                    status = "✓" if value else "✗"
                    print(f"{status} {check_name}.{key}: {value}")
                    if not value:
                        all_valid = False
        
        results["overall_valid"] = all_valid
        
        return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate curated public data")
    parser.add_argument("--data-dir", type=str, default="./data/raw", help="Data directory")
    
    args = parser.parse_args()
    
    validator = PublicDataValidator(Path(args.data_dir))
    results = validator.run_all_validations()
    
    if results["overall_valid"]:
        print("\n✓ All validations passed!")
        sys.exit(0)
    else:
        print("\n✗ Some validations failed. Review results above.")
        sys.exit(1)

