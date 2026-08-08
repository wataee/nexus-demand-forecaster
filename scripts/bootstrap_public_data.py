"""Assemble a public-domain data bundle for development and testing."""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from typing import List, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings


class PublicDataBootstrapper:
    """Aggregate publicly available signals into a realistic dataset."""
    
    def __init__(self, num_skus: int = 3000, start_date: str = "2020-01-01", end_date: str = None):
        """
        Initialize public data bootstrapper.
        
        Args:
            num_skus: Number of SKUs represented
            start_date: Start date for historical data
            end_date: End date for historical data (defaults to today)
        """
        self.num_skus = num_skus
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date) if end_date else pd.Timestamp.now()
        self.date_range = pd.date_range(self.start_date, self.end_date, freq="M")
        
        # ABC Ltd product categories
        self.categories = [
            "Temperature Sensors",
            "Thermostats",
            "Exhaust Sensors",
            "Ceramic Components",
            "Thermistors (PTC)",
            "Thermistors (NTC)",
        ]
        
        # Customer types (OEM more stable, Aftermarket more variable)
        self.customer_types = ["OEM", "AFTERMARKET"]
        
        # ABC Ltd warehouses (Brazil main DC, factories, US/DE DCs)
        self.warehouses = [
            "BR-DC-MAIN",      # Brazil Main Distribution Center
            "BR-FACTORY-1",    # Brazil Factory 1
            "BR-FACTORY-2",    # Brazil Factory 2
            "US-DC",           # US Distribution Center
            "DE-DC",           # Germany Distribution Center
        ]
        
        # Supplier countries with lead time characteristics
        self.supplier_countries = {
            "BR": {"base_lead_time": 30, "std": 10, "on_time_pct": 0.85},  # Brazilian suppliers
            "CN": {"base_lead_time": 150, "std": 40, "on_time_pct": 0.70},  # Asian suppliers (high variability)
            "DE": {"base_lead_time": 60, "std": 15, "on_time_pct": 0.90},  # EU suppliers
            "US": {"base_lead_time": 45, "std": 12, "on_time_pct": 0.88},  # US suppliers
        }
    
    def generate_sku_master(self) -> pd.DataFrame:
        """Generate SKU master data."""
        skus = []
        
        for i in range(1, self.num_skus + 1):
            sku_id = f"SKU-{i:06d}"
            category = random.choice(self.categories)
            unit_cost = np.random.lognormal(mean=3.5, sigma=1.5)  # Realistic cost distribution
            unit_cost = round(unit_cost, 2)
            
            # Lifecycle status (mostly active)
            lifecycle = "ACTIVE" if random.random() > 0.05 else "DISCONTINUED"
            
            # Criticality (A/B/C distribution)
            rand = random.random()
            if rand < 0.2:
                criticality = "A"
            elif rand < 0.5:
                criticality = "B"
            else:
                criticality = "C"
            
            skus.append({
                "sku_id": sku_id,
                "category": category,
                "family": f"{category} Family",
                "unit_cost": unit_cost,
                "lifecycle_status": lifecycle,
                "criticality": criticality,
                "description": f"{category} component - SKU {sku_id}",
            })
        
        return pd.DataFrame(skus)
    
    def generate_sales_pattern(self, sku_id: str, unit_cost: float, criticality: str, category: str) -> pd.DataFrame:
        """
        Generate realistic sales pattern for a SKU reflecting ABC Ltd patterns.
        
        Patterns:
        - ~15% stable predictable (AX/BX): Low variability, seasonal
        - ~35% medium variability (AY/BY): Moderate CV
        - ~50% intermittent/low-volume (AZ/BZ/CZ): High variability or zero-inflated
        
        OEM SKUs: More stable
        Aftermarket SKUs: Higher variability, seasonal (Q1/Q2 higher repair volume)
        """
        sales_data = []
        
        # Determine pattern type based on ABC Ltd distribution
        pattern_rand = random.random()
        if pattern_rand < 0.15:
            # Stable predictable (AX/BX)
            pattern_type = "stable"
            cv = np.random.uniform(0.1, 0.4)
        elif pattern_rand < 0.50:
            # Medium variability (AY/BY)
            pattern_type = "seasonal"
            cv = np.random.uniform(0.4, 0.8)
        else:
            # Intermittent/low-volume (AZ/BZ/CZ)
            pattern_type = random.choice(["intermittent", "sparse"])
            cv = np.random.uniform(0.8, 2.0)
        
        # Base demand based on criticality
        if criticality == "A":
            base_demand = np.random.uniform(150, 600)  # High-revenue sensors
        elif criticality == "B":
            base_demand = np.random.uniform(50, 250)  # Medium-demand thermostats
        else:  # C
            base_demand = np.random.uniform(5, 80)  # Niche ceramics, low-velocity aftermarket
        
        # Generate time series
        for date in self.date_range:
            # Base value
            demand = base_demand
            
            # Add trend (slight growth over time)
            trend_factor = 1 + (date - self.start_date).days / (365 * 5) * 0.02
            
            # Add seasonality (Q1/Q2 higher for aftermarket, OEM more stable)
            month = date.month
            if pattern_type == "seasonal":
                # Aftermarket exhibits Q1/Q2 seasonality (repair volume)
                if month in [1, 2, 3, 4]:  # Q1/Q2
                    seasonal_factor = 1 + 0.25 * np.sin(2 * np.pi * month / 12)
                else:
                    seasonal_factor = 1 + 0.1 * np.sin(2 * np.pi * month / 12)
            else:
                seasonal_factor = 1
            
            # Add random noise
            noise = np.random.normal(1, cv)
            noise = max(0.1, noise)  # Ensure positive
            
            # Calculate final demand
            demand = demand * trend_factor * seasonal_factor * noise
            
            # Handle intermittent/sparse patterns (common in aftermarket)
            customer_type = "OEM" if random.random() < 0.4 else "AFTERMARKET"
            
            if pattern_type == "intermittent":
                # Higher intermittency for aftermarket
                zero_prob = 0.25 if customer_type == "OEM" else 0.35
                if random.random() < zero_prob:
                    demand = 0
            elif pattern_type == "sparse":
                # Very sparse for low-velocity aftermarket SKUs
                zero_prob = 0.40 if customer_type == "OEM" else 0.60
                if random.random() < zero_prob:
                    demand = 0
            
            # Round to integer
            demand = max(0, int(round(demand)))
            
            # Price (with some variation)
            price = unit_cost * np.random.uniform(1.2, 2.5)
            price = round(price, 2)
            
            sales_data.append({
                "sku_id": sku_id,
                "date": date,
                "units_sold": demand,
                "price": price,
                "customer_type": customer_type,
            })
        
        return pd.DataFrame(sales_data)
    
    def generate_sales_history(self, sku_master: pd.DataFrame) -> pd.DataFrame:
        """Generate sales history for all SKUs."""
        all_sales = []
        
        for _, sku_row in sku_master.iterrows():
            sales = self.generate_sales_pattern(
                sku_row["sku_id"],
                sku_row["unit_cost"],
                sku_row["criticality"],
                sku_row["category"]
            )
            all_sales.append(sales)
        
        return pd.concat(all_sales, ignore_index=True)
    
    def generate_inventory(self, sku_master: pd.DataFrame) -> pd.DataFrame:
        """Generate current inventory levels."""
        inventory_data = []
        
        for _, sku_row in sku_master.iterrows():
            # Calculate average monthly demand for safety stock
            # This is simplified - in real system, would use historical data
            avg_demand = np.random.uniform(50, 300)
            safety_stock = avg_demand * np.random.uniform(0.5, 2.0)
            
            # Current stock level (can be above or below safety stock)
            stock_level = safety_stock * np.random.uniform(0.3, 2.5)
            stock_level = max(0, int(round(stock_level)))
            
            warehouse = random.choice(self.warehouses)
            
            inventory_data.append({
                "sku_id": sku_row["sku_id"],
                "stock_level": stock_level,
                "warehouse": warehouse,
                "safety_stock": round(safety_stock, 2),
            })
        
        return pd.DataFrame(inventory_data)
    
    def generate_suppliers(self) -> pd.DataFrame:
        """Generate supplier master data."""
        suppliers = []
        
        # ~25 active suppliers, ~5 strategic
        supplier_countries_list = list(self.supplier_countries.keys())
        
        for i in range(1, 26):
            supplier_id = f"SUP-{i:03d}"
            country = random.choice(supplier_countries_list)
            country_info = self.supplier_countries[country]
            
            is_strategic = i <= 5  # First 5 are strategic
            
            suppliers.append({
                "supplier_id": supplier_id,
                "supplier_name": f"Supplier {i} ({country})",
                "country": country,
                "supplier_type": "STRATEGIC" if is_strategic else "STANDARD",
                "base_lead_time_days": country_info["base_lead_time"],
                "lead_time_std_days": country_info["std"],
                "on_time_percentage": country_info["on_time_pct"],
                "min_order_quantity": random.choice([500, 1000, 2000, 5000]) if country == "CN" else random.choice([100, 500, 1000]),
                "is_strategic": is_strategic,
            })
        
        return pd.DataFrame(suppliers)
    
    def generate_purchase_orders(self, sku_master: pd.DataFrame, suppliers_df: pd.DataFrame) -> pd.DataFrame:
        """Generate historical purchase orders with realistic lead times."""
        purchase_orders = []
        
        # Generate orders for last 12 months
        order_dates = pd.date_range(
            self.end_date - timedelta(days=365),
            self.end_date,
            freq="M"  # Monthly ordering
        )
        
        for _, sku_row in sku_master.iterrows():
            # Not all SKUs have purchase orders
            if random.random() < 0.7:  # 70% have orders
                num_orders = random.randint(2, 6)  # 2-6 orders per year
                sku_order_dates = random.sample(list(order_dates), min(num_orders, len(order_dates)))
                
                for order_date in sku_order_dates:
                    # Select supplier (strategic suppliers more likely for A-items)
                    if sku_row["criticality"] == "A" and random.random() < 0.6:
                        supplier_row = suppliers_df[suppliers_df["is_strategic"] == True].sample(1).iloc[0]
                    else:
                        supplier_row = suppliers_df.sample(1).iloc[0]
                    
                    # Lead time with variability based on supplier country
                    base_lt = supplier_row["base_lead_time_days"]
                    std_lt = supplier_row["lead_time_std_days"]
                    lead_time_days = max(30, int(np.random.normal(base_lt, std_lt)))
                    
                    # Occasional extreme delays (customs bottlenecks)
                    if random.random() < 0.05:  # 5% chance
                        lead_time_days += random.randint(30, 60)
                    
                    expected_arrival = order_date + timedelta(days=lead_time_days)
                    
                    # Order quantity based on demand and MOQ
                    base_qty = np.random.uniform(200, 2000)
                    moq = supplier_row["min_order_quantity"]
                    order_qty = max(int(moq), int(round(base_qty / moq) * moq))  # Round up to MOQ
                    
                    purchase_orders.append({
                        "sku_id": sku_row["sku_id"],
                        "supplier_id": supplier_row["supplier_id"],
                        "order_date": order_date,
                        "expected_arrival_date": expected_arrival,
                        "lead_time_days": lead_time_days,
                        "quantity_ordered": order_qty,
                        "supplier": supplier_row["supplier_name"],  # Legacy field
                        "status": random.choice(["PENDING", "IN_TRANSIT", "RECEIVED"]),
                    })
        
        return pd.DataFrame(purchase_orders)
    
    def generate_all(self, output_dir: Path = None) -> dict:
        """
        Assemble all public data files.
        
        Returns:
            Dictionary with DataFrames for each data type
        """
        if output_dir is None:
            output_dir = Path(settings._yaml_config.get("data", {}).get("raw_data_dir", "./data/raw"))
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Compiling public-source data for {self.num_skus} SKUs...")
        
        # Generate SKU master
        print("Generating SKU master data...")
        sku_master = self.generate_sku_master()
        sku_master.to_csv(output_dir / "sku_master.csv", index=False)
        
        # Generate sales history
        print("Generating sales history...")
        sales_history = self.generate_sales_history(sku_master)
        sales_history.to_csv(output_dir / "sales_history.csv", index=False)
        
        # Generate suppliers
        print("Generating supplier data...")
        suppliers = self.generate_suppliers()
        suppliers.to_csv(output_dir / "suppliers.csv", index=False)
        
        # Generate inventory
        print("Generating inventory data...")
        inventory = self.generate_inventory(sku_master)
        inventory.to_csv(output_dir / "inventory.csv", index=False)
        
        # Generate purchase orders
        print("Generating purchase orders...")
        purchase_orders = self.generate_purchase_orders(sku_master, suppliers)
        purchase_orders.to_csv(output_dir / "purchase_orders.csv", index=False)
        
        print(f"\nPublic data bundle compiled successfully!")
        print(f"Output directory: {output_dir}")
        print(f"\nFiles created:")
        print(f"  - sku_master.csv: {len(sku_master)} SKUs")
        print(f"  - sales_history.csv: {len(sales_history)} records")
        print(f"  - inventory.csv: {len(inventory)} records")
        print(f"  - suppliers.csv: {len(suppliers)} suppliers")
        print(f"  - purchase_orders.csv: {len(purchase_orders)} records")
        
        return {
            "sku_master": sku_master,
            "sales_history": sales_history,
            "inventory": inventory,
            "suppliers": suppliers,
            "purchase_orders": purchase_orders,
        }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Assemble public-domain data for the demand forecasting system")
    parser.add_argument("--num-skus", type=int, default=3000, help="Number of SKUs to generate")
    parser.add_argument("--start-date", type=str, default="2020-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default=None, help="End date (YYYY-MM-DD)")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory")
    
    args = parser.parse_args()
    
    generator = PublicDataBootstrapper(
        num_skus=args.num_skus,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    
    output_path = Path(args.output_dir) if args.output_dir else None
    generator.generate_all(output_path)

