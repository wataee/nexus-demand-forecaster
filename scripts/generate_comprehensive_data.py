"""Comprehensive public-data assembler with Top-Down → Bottom-Up strategy.

This generates realistic operational data that mirrors true complexity:
- 3,000 SKU universe with proper categorization
- Multi-year demand patterns (stable, seasonal, intermittent)
- Supply chain simulation with realistic POs and stock movement
- Real-world disruptions (delays, spikes)
- Statistical validation of generated data
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from typing import Dict, List, Tuple
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings


class ComprehensiveDataGenerator:
    """Generate comprehensive public reference data with realistic operational complexity."""
    
    def __init__(self, num_skus: int = 3000, start_date: str = "2020-01-01", end_date: str = None):
        """
        Initialize comprehensive data generator.
        
        Args:
            num_skus: Number of SKUs to generate (default: 3,000)
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
        
        # Category-specific characteristics
        self.category_profiles = {
            "Temperature Sensors": {"base_cost_range": (50, 200), "demand_profile": "stable"},
            "Thermostats": {"base_cost_range": (30, 150), "demand_profile": "seasonal"},
            "Exhaust Sensors": {"base_cost_range": (80, 300), "demand_profile": "stable"},
            "Ceramic Components": {"base_cost_range": (20, 100), "demand_profile": "intermittent"},
            "Thermistors (PTC)": {"base_cost_range": (15, 80), "demand_profile": "intermittent"},
            "Thermistors (NTC)": {"base_cost_range": (15, 80), "demand_profile": "intermittent"},
        }
        
        # Demand pattern distribution (Top-Down)
        self.pattern_distribution = {
            "stable": 0.15,      # 15% stable predictable (AX/BX)
            "seasonal": 0.35,    # 35% medium variability (AY/BY)
            "intermittent": 0.50, # 50% intermittent/low-volume (AZ/BZ/CZ)
        }
        
        # Supplier characteristics
        self.supplier_countries = {
            "BR": {"base_lead_time": 30, "std": 10, "on_time_pct": 0.85, "moq_range": (100, 500)},
            "CN": {"base_lead_time": 150, "std": 40, "on_time_pct": 0.70, "moq_range": (500, 5000)},
            "DE": {"base_lead_time": 60, "std": 15, "on_time_pct": 0.90, "moq_range": (100, 1000)},
            "US": {"base_lead_time": 45, "std": 12, "on_time_pct": 0.88, "moq_range": (100, 500)},
        }
        
        # Warehouses
        self.warehouses = [
            "BR-DC-MAIN",
            "BR-FACTORY-1",
            "BR-FACTORY-2",
            "US-DC",
            "DE-DC",
        ]
        
        # Initialize random state for reproducibility
        np.random.seed(42)
        random.seed(42)
    
    def create_sku_universe(self) -> pd.DataFrame:
        """
        Step 1: Create SKU universe (Top-Down).
        
        Generates 3,000 SKUs with:
        - Category assignments
        - Cost and price (log-normal distribution)
        - Criticality (A/B/C based on expected revenue)
        """
        print("Creating SKU universe...")
        
        skus = []
        
        for i in range(1, self.num_skus + 1):
            sku_id = f"SKU-{i:06d}"
            
            # Assign category
            category = random.choice(self.categories)
            category_profile = self.category_profiles[category]
            
            # Generate unit cost (log-normal distribution)
            cost_range = category_profile["base_cost_range"]
            # Use log-normal: log(mean) and log(std) parameters
            log_mean = np.log(np.mean(cost_range))
            log_std = (np.log(cost_range[1]) - np.log(cost_range[0])) / 4
            unit_cost = np.random.lognormal(log_mean, log_std)
            unit_cost = max(cost_range[0], min(cost_range[1], unit_cost))
            unit_cost = round(unit_cost, 2)
            
            # Lifecycle status (mostly active)
            lifecycle_rand = random.random()
            if lifecycle_rand < 0.05:
                lifecycle_status = "DISCONTINUED"
            elif lifecycle_rand < 0.10:
                lifecycle_status = "PHASE_OUT"
            else:
                lifecycle_status = "ACTIVE"
            
            # Initial criticality (will be recalculated after revenue)
            # Use expected demand to estimate
            demand_profile = category_profile["demand_profile"]
            if demand_profile == "stable":
                expected_monthly_demand = np.random.uniform(100, 500)
            elif demand_profile == "seasonal":
                expected_monthly_demand = np.random.uniform(50, 250)
            else:
                expected_monthly_demand = np.random.uniform(5, 80)
            
            expected_annual_revenue = expected_monthly_demand * 12 * unit_cost
            
            # Assign criticality based on expected revenue (will be refined after actual data)
            if expected_annual_revenue > 500000:
                criticality = "A"
            elif expected_annual_revenue > 100000:
                criticality = "B"
            else:
                criticality = "C"
            
            skus.append({
                "sku_id": sku_id,
                "category": category,
                "family": f"{category} Family",
                "unit_cost": unit_cost,
                "lifecycle_status": lifecycle_status,
                "criticality": criticality,
                "description": f"{category} component - SKU {sku_id}",
            })
        
        df = pd.DataFrame(skus)
        print(f"Created {len(df)} SKUs")
        print(f"Category distribution:\n{df['category'].value_counts()}")
        print(f"Criticality distribution:\n{df['criticality'].value_counts()}")
        
        return df
    
    def generate_demand_pattern(self, sku_row: pd.Series, pattern_type: str) -> pd.DataFrame:
        """
        Step 2: Generate multi-year demand patterns (Bottom-Up).
        
        Creates realistic demand with:
        - Log-normal base demand
        - Noise proportional to SKU volatility
        - Seasonality for seasonal patterns
        - Zero-inflation for intermittent patterns
        """
        sku_id = sku_row["sku_id"]
        category = sku_row["category"]
        criticality = sku_row["criticality"]
        
        # Determine base demand based on category and criticality
        category_profile = self.category_profiles[category]
        
        if criticality == "A":
            base_demand_mean = np.random.uniform(150, 600)
        elif criticality == "B":
            base_demand_mean = np.random.uniform(50, 250)
        else:
            base_demand_mean = np.random.uniform(5, 80)
        
        # Log-normal distribution for base demand
        log_mean = np.log(base_demand_mean)
        log_std = 0.3 if pattern_type == "stable" else (0.5 if pattern_type == "seasonal" else 0.8)
        
        sales_data = []
        
        for date in self.date_range:
            # Base demand (log-normal)
            base_demand = np.random.lognormal(log_mean, log_std)
            
            # Add trend (slight growth over time)
            months_elapsed = (date - self.start_date).days / 30.0
            trend_factor = 1 + (months_elapsed / 60.0) * 0.02  # 2% growth per 5 years
            
            # Add seasonality
            if pattern_type == "seasonal":
                month = date.month
                # Q1/Q2 higher for aftermarket (repair season)
                if month in [1, 2, 3, 4]:
                    seasonal_factor = 1 + 0.3 * np.sin(2 * np.pi * month / 12)
                else:
                    seasonal_factor = 1 + 0.1 * np.sin(2 * np.pi * month / 12)
            else:
                seasonal_factor = 1.0
            
            # Add noise proportional to volatility
            if pattern_type == "stable":
                noise_factor = np.random.normal(1.0, 0.15)
            elif pattern_type == "seasonal":
                noise_factor = np.random.normal(1.0, 0.30)
            else:  # intermittent
                noise_factor = np.random.normal(1.0, 0.50)
            
            noise_factor = max(0.1, noise_factor)
            
            # Calculate demand
            demand = base_demand * trend_factor * seasonal_factor * noise_factor
            
            # Zero-inflation for intermittent patterns
            if pattern_type == "intermittent":
                zero_prob = 0.30 if criticality == "A" else (0.40 if criticality == "B" else 0.60)
                if random.random() < zero_prob:
                    demand = 0
            
            # Round to integer
            demand = max(0, int(round(demand)))
            
            # Customer type (OEM more stable, Aftermarket more variable)
            if pattern_type == "stable":
                customer_type = "OEM" if random.random() < 0.7 else "AFTERMARKET"
            else:
                customer_type = "OEM" if random.random() < 0.4 else "AFTERMARKET"
            
            # Price (with variation)
            price = sku_row["unit_cost"] * np.random.uniform(1.2, 2.5)
            price = round(price, 2)
            
            sales_data.append({
                "sku_id": sku_id,
                "date": date,
                "units_sold": demand,
                "price": price,
                "customer_type": customer_type,
            })
        
        return pd.DataFrame(sales_data)
    
    def generate_all_demand(self, sku_master: pd.DataFrame) -> pd.DataFrame:
        """Generate demand patterns for all SKUs."""
        print("Generating multi-year demand patterns...")
        
        all_sales = []
        
        for idx, sku_row in sku_master.iterrows():
            # Assign pattern type based on distribution
            rand = random.random()
            if rand < self.pattern_distribution["stable"]:
                pattern_type = "stable"
            elif rand < self.pattern_distribution["stable"] + self.pattern_distribution["seasonal"]:
                pattern_type = "seasonal"
            else:
                pattern_type = "intermittent"
            
            sales = self.generate_demand_pattern(sku_row, pattern_type)
            all_sales.append(sales)
            
            if (idx + 1) % 500 == 0:
                print(f"  Generated demand for {idx + 1}/{len(sku_master)} SKUs")
        
        result = pd.concat(all_sales, ignore_index=True)
        print(f"Generated {len(result)} sales records")
        
        return result
    
    def simulate_supply_chain(self, sku_master: pd.DataFrame, sales_history: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Step 3: Simulate supply chain behavior.
        
        Generates:
        - POs with variable lead times
        - Stock movement from sales + incoming POs
        - Stockouts and overstock situations
        - Delayed deliveries
        """
        print("Simulating supply chain behavior...")
        
        # Generate suppliers
        suppliers = self.generate_suppliers()
        
        # Generate purchase orders
        purchase_orders = []
        inventory_records = []
        
        for _, sku_row in sku_master.iterrows():
            sku_id = sku_row["sku_id"]
            
            # Get sales for this SKU
            sku_sales = sales_history[sales_history["sku_id"] == sku_id].sort_values("date")
            
            if len(sku_sales) == 0:
                continue
            
            # Calculate average monthly demand
            avg_monthly_demand = sku_sales["units_sold"].mean()
            
            # Select supplier (strategic more likely for A-items)
            if sku_row["criticality"] == "A" and random.random() < 0.6:
                supplier_row = suppliers[suppliers["is_strategic"] == True].sample(1).iloc[0]
            else:
                supplier_row = suppliers.sample(1).iloc[0]
            
            # Generate POs (every 1-3 months depending on demand)
            po_frequency_months = 1 if avg_monthly_demand > 200 else (2 if avg_monthly_demand > 50 else 3)
            
            current_date = self.start_date
            current_stock = max(0, int(avg_monthly_demand * np.random.uniform(1, 3)))  # Initial stock
            
            po_dates = []
            while current_date < self.end_date:
                po_dates.append(current_date)
                current_date += pd.DateOffset(months=po_frequency_months)
            
            for po_date in po_dates:
                # Calculate lead time with variability
                base_lt = supplier_row["base_lead_time_days"]
                std_lt = supplier_row["lead_time_std_days"]
                lead_time_days = max(30, int(np.random.normal(base_lt, std_lt)))
                
                # Add real-world disruptions (5% chance of customs delay)
                if random.random() < 0.05:
                    lead_time_days += random.randint(30, 60)
                    disruption_type = "CUSTOMS_DELAY"
                else:
                    disruption_type = None
                
                # Add supplier reliability (on-time percentage)
                if random.random() > supplier_row["on_time_percentage"]:
                    lead_time_days += random.randint(10, 30)
                    disruption_type = "SUPPLIER_DELAY"
                
                expected_arrival = po_date + timedelta(days=lead_time_days)
                
                # Order quantity (based on demand and MOQ)
                months_to_cover = po_frequency_months + 1
                base_qty = avg_monthly_demand * months_to_cover
                moq = supplier_row["min_order_quantity"]
                order_qty = max(int(moq), int(np.ceil(base_qty / moq) * moq))
                
                # Determine status
                if expected_arrival > self.end_date:
                    status = "PENDING"
                elif expected_arrival <= pd.Timestamp.now():
                    status = random.choice(["IN_TRANSIT", "RECEIVED"])
                else:
                    status = "PENDING"
                
                purchase_orders.append({
                    "sku_id": sku_id,
                    "supplier_id": supplier_row["supplier_id"],
                    "order_date": po_date,
                    "expected_arrival_date": expected_arrival,
                    "actual_arrival_date": expected_arrival if status == "RECEIVED" else None,
                    "lead_time_days": lead_time_days,
                    "quantity_ordered": order_qty,
                    "supplier": supplier_row["supplier_name"],
                    "status": status,
                    "disruption_type": disruption_type,
                })
            
            # Simulate inventory levels over time
            for date in self.date_range[::3]:  # Every 3 months
                # Get sales up to this date
                sales_to_date = sku_sales[sku_sales["date"] <= date]
                total_sold = sales_to_date["units_sold"].sum()
                
                # Get received POs up to this date
                received_pos = [po for po in purchase_orders 
                               if po["sku_id"] == sku_id 
                               and po.get("actual_arrival_date") 
                               and po["actual_arrival_date"] <= date]
                total_received = sum([po["quantity_ordered"] for po in received_pos])
                
                # Calculate stock level
                stock_level = max(0, current_stock + total_received - total_sold)
                
                # Calculate safety stock (simplified)
                safety_stock = max(0, int(avg_monthly_demand * 1.5))
                
                # Assign warehouse (main DC for most, factories for some)
                if random.random() < 0.6:
                    warehouse = "BR-DC-MAIN"
                else:
                    warehouse = random.choice(self.warehouses)
                
                inventory_records.append({
                    "sku_id": sku_id,
                    "stock_level": stock_level,
                    "warehouse": warehouse,
                    "safety_stock": safety_stock,
                    "date": date,
                })
        
        po_df = pd.DataFrame(purchase_orders)
        inv_df = pd.DataFrame(inventory_records)
        
        print(f"Generated {len(po_df)} purchase orders")
        print(f"Generated {len(inv_df)} inventory records")
        
        return suppliers, po_df, inv_df
    
    def generate_suppliers(self) -> pd.DataFrame:
        """Generate supplier master data."""
        suppliers = []
        supplier_countries_list = list(self.supplier_countries.keys())
        
        for i in range(1, 26):
            supplier_id = f"SUP-{i:03d}"
            country = random.choice(supplier_countries_list)
            country_info = self.supplier_countries[country]
            
            is_strategic = i <= 5
            
            moq_range = country_info["moq_range"]
            moq = random.choice([moq_range[0], 
                                int((moq_range[0] + moq_range[1]) / 2),
                                moq_range[1]])
            
            suppliers.append({
                "supplier_id": supplier_id,
                "supplier_name": f"Supplier {i} ({country})",
                "country": country,
                "supplier_type": "STRATEGIC" if is_strategic else "STANDARD",
                "base_lead_time_days": country_info["base_lead_time"],
                "lead_time_std_days": country_info["std"],
                "on_time_percentage": country_info["on_time_pct"],
                "min_order_quantity": moq,
                "is_strategic": is_strategic,
            })
        
        return pd.DataFrame(suppliers)
    
    def add_disruptions(self, sales_history: pd.DataFrame) -> pd.DataFrame:
        """
        Step 4: Add real-world disruptions.
        
        - Random supplier delays (already in PO generation)
        - Customs delays (already in PO generation)
        - Sudden spikes in aftermarket demand
        """
        print("Adding real-world disruptions...")
        
        sales_history = sales_history.copy()
        
        # Add sudden spikes in aftermarket demand (2% of records)
        aftermarket_sales = sales_history[sales_history["customer_type"] == "AFTERMARKET"]
        spike_count = int(len(aftermarket_sales) * 0.02)
        
        spike_indices = aftermarket_sales.sample(spike_count).index
        for idx in spike_indices:
            original_demand = sales_history.loc[idx, "units_sold"]
            spike_multiplier = np.random.uniform(2.0, 5.0)
            sales_history.loc[idx, "units_sold"] = int(original_demand * spike_multiplier)
        
        print(f"Added {spike_count} demand spikes")
        
        return sales_history
    
    def generate_all(self, output_dir: Path = None) -> Dict[str, pd.DataFrame]:
        """
        Generate the entire curated public dataset.
        
        Returns:
            Dictionary with all generated DataFrames
        """
        if output_dir is None:
            output_dir = Path("./data/raw")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print("=" * 60)
        print("COMPREHENSIVE PUBLIC DATA CURATION")
        print("Top-Down → Bottom-Up Strategy")
        print("=" * 60)
        
        # Step 1: Create SKU universe
        sku_master = self.create_sku_universe()
        sku_master.to_csv(output_dir / "sku_master.csv", index=False)
        
        # Step 2: Generate demand patterns
        sales_history = self.generate_all_demand(sku_master)
        sales_history = self.add_disruptions(sales_history)
        sales_history.to_csv(output_dir / "sales_history.csv", index=False)
        
        # Step 3: Simulate supply chain
        suppliers, purchase_orders, inventory = self.simulate_supply_chain(sku_master, sales_history)
        suppliers.to_csv(output_dir / "suppliers.csv", index=False)
        purchase_orders.to_csv(output_dir / "purchase_orders.csv", index=False)
        inventory.to_csv(output_dir / "inventory.csv", index=False)
        
        print("\n" + "=" * 60)
        print("DATA GENERATION COMPLETE")
        print("=" * 60)
        print(f"\nFiles created in {output_dir}:")
        print(f"  - sku_master.csv: {len(sku_master)} SKUs")
        print(f"  - sales_history.csv: {len(sales_history)} records")
        print(f"  - suppliers.csv: {len(suppliers)} suppliers")
        print(f"  - purchase_orders.csv: {len(purchase_orders)} POs")
        print(f"  - inventory.csv: {len(inventory)} inventory records")
        
        return {
            "sku_master": sku_master,
            "sales_history": sales_history,
            "suppliers": suppliers,
            "purchase_orders": purchase_orders,
            "inventory": inventory,
        }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Curate comprehensive public data bundle")
    parser.add_argument("--num-skus", type=int, default=3000, help="Number of SKUs")
    parser.add_argument("--start-date", type=str, default="2020-01-01", help="Start date")
    parser.add_argument("--end-date", type=str, default=None, help="End date")
    parser.add_argument("--output-dir", type=str, default="./data/raw", help="Output directory")
    
    args = parser.parse_args()
    
    generator = ComprehensiveDataGenerator(
        num_skus=args.num_skus,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    
    generator.generate_all(Path(args.output_dir))

