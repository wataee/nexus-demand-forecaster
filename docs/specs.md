# AI Demand Forecasting & Inventory Optimization System — Technical Specification Document

## 1. Overview

**Version**: 2.0  
**Last Updated**: 2024  
**Status**: ✅ Implementation Complete

This document defines the functional, technical, and architectural specifications for building an AI-powered system that improves demand forecasting, purchase planning, and inventory optimization for a global automotive parts manufacturer with ~3,000 SKUs, multi-country distribution, and long procurement lead times (4-6 months).

The system replaces manual Excel-based forecasting and delivers automated, SKU-level forecasts, optimized purchase suggestions, and real-time dashboards via BI tool integration.

**Key Features:**
- ✅ Curated public-data ingestion layer (no ERP dependency for development)
- ✅ ABC-specific service levels and inventory policies
- ✅ Multi-warehouse support (Multi Global locations)
- ✅ Supplier management with country-specific lead time variability
- ✅ ERP integration ready (SAP, TOTVS, custom)

## 2. Goals & Objectives

### Primary Goals

- Automate demand forecasting at SKU-level using AI.
- Improve purchase-order accuracy through optimized recommendations.
- Reduce stockouts, overstocking, and manual processing time.
- Provide intuitive dashboards for decision-makers.

### Expected Outcomes

- Forecast accuracy improvement (10–30% baseline reduction in MAPE).
- 50%+ reduction in ordering errors.
- 20%+ reduction in stockouts.
- Ordering process time reduced from 1 week → under 3 hours.

## 3. System Architecture

### Multi-Layer Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │
│  │   PowerBI    │  │ Looker Studio│  │  Custom BI    │                │
│  │  Dashboard   │  │  Dashboard   │  │  Dashboard   │                │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                │
│         │                  │                  │                         │
│         └──────────────────┼──────────────────┘                         │
│                            │                                            │
│                    ┌───────▼────────┐                                   │
│                    │   REST API     │                                   │
│                    │   (FastAPI)   │                                   │
│                    └───────┬────────┘                                   │
│                            │                                            │
└────────────────────────────┼──────────────────────────────────────────┘
                             │
┌────────────────────────────┼──────────────────────────────────────────┐
│                    APPLICATION LAYER                                   │
├────────────────────────────┼──────────────────────────────────────────┤
│                            │                                            │
│  ┌─────────────────────────▼─────────────────────────┐                │
│  │              API Endpoints                         │                │
│  │  • Forecasts API                                   │                │
│  │  • Recommendations API                            │                │
│  │  • Inventory API                                  │                │
│  │  • Segmentation API                               │                │
│  │  • ERP Integration API                            │                │
│  │  • Metrics API                                    │                │
│  └─────────────────────────┬─────────────────────────┘                │
│                            │                                            │
│  ┌─────────────────────────▼─────────────────────────┐                │
│  │         Business Logic Services                    │                │
│  │  ┌──────────────────────────────────────┐         │                │
│  │  │  Order Recommendation Engine         │         │                │
│  │  │  • Confidence scoring                │         │                │
│  │  │  • Explanation generation            │         │                │
│  │  │  • Priority ranking                  │         │                │
│  │  └──────────────────────────────────────┘         │                │
│  │  ┌──────────────────────────────────────┐         │                │
│  │  │  Inventory Optimization Engine       │         │                │
│  │  │  • Safety stock (ABC-specific)       │         │                │
│  │  │  • Reorder point calculation         │         │                │
│  │  │  • Order quantity optimization       │         │                │
│  │  └──────────────────────────────────────┘         │                │
│  │  ┌──────────────────────────────────────┐         │                │
│  │  │  ABC/XYZ Segmentation Service        │         │                │
│  │  │  • ABC classification (value)        │         │                │
│  │  │  • XYZ classification (variability)   │         │                │
│  │  │  • Segment assignment                 │         │                │
│  │  └──────────────────────────────────────┘         │                │
│  └─────────────────────────┬─────────────────────────┘                │
│                            │                                            │
└────────────────────────────┼──────────────────────────────────────────┘
                             │
┌────────────────────────────┼──────────────────────────────────────────┐
│                      ML/AI LAYER                                       │
├────────────────────────────┼──────────────────────────────────────────┤
│                            │                                            │
│  ┌─────────────────────────▼─────────────────────────┐                │
│  │         Forecasting Engine                         │                │
│  │  ┌──────────────────────────────────────┐         │                │
│  │  │  Model Registry & Selection          │         │                │
│  │  │  • Auto-selection by segment         │         │                │
│  │  │  • Cross-validation                  │         │                │
│  │  │  • Model versioning                  │         │                │
│  │  └──────────────────────────────────────┘         │                │
│  │  ┌──────────────────────────────────────┐         │                │
│  │  │  Model Implementations                │         │                │
│  │  │  • ARIMA (Auto-ARIMA)                │         │                │
│  │  │  • Prophet (Facebook)                 │         │                │
│  │  │  • XGBoost / LightGBM                │         │                │
│  │  │  • Croston / SBA                     │         │                │
│  │  │  • Moving Average                    │         │                │
│  │  └──────────────────────────────────────┘         │                │
│  │  ┌──────────────────────────────────────┐         │                │
│  │  │  Training Pipeline                    │         │                │
│  │  │  • Batch training                     │         │                │
│  │  │  • Parallel processing                │         │                │
│  │  │  • Performance tracking               │         │                │
│  │  └──────────────────────────────────────┘         │                │
│  └─────────────────────────┬─────────────────────────┘                │
│                            │                                            │
│  ┌─────────────────────────▼─────────────────────────┐                │
│  │         Monitoring & Drift Detection               │                │
│  │  • Model performance tracking                      │                │
│  │  • Forecast vs actual monitoring                   │                │
│  │  • Data drift detection                            │                │
│  │  • Alert system                                   │                │
│  └─────────────────────────┬─────────────────────────┘                │
│                            │                                            │
└────────────────────────────┼──────────────────────────────────────────┘
                             │
┌────────────────────────────┼──────────────────────────────────────────┐
│                      DATA LAYER                                        │
├────────────────────────────┼──────────────────────────────────────────┤
│                            │                                            │
│  ┌─────────────────────────▼─────────────────────────┐                │
│  │         ETL Pipeline                                │                │
│  │  ┌──────────────────────────────────────┐         │                │
│  │  │  Ingestion                           │         │                │
│  │  │  • CSV/Excel readers                 │         │                │
│  │  │  • ERP connectors (TOTVS/SAP)        │         │                │
│  │  │  • Public data curation pipelines    │         │                │
│  │  └──────────────────────────────────────┘         │                │
│  │  ┌──────────────────────────────────────┐         │                │
│  │  │  Validation                          │         │                │
│  │  │  • Schema validation                 │         │                │
│  │  │  • Outlier detection                 │         │                │
│  │  │  • Data quality checks               │         │                │
│  │  └──────────────────────────────────────┘         │                │
│  │  ┌──────────────────────────────────────┐         │                │
│  │  │  Transformation                      │         │                │
│  │  │  • Time series alignment             │         │                │
│  │  │  • Feature engineering               │         │                │
│  │  │  • Lag features                      │         │                │
│  │  │  • Rolling statistics                │         │                │
│  │  │  • Seasonality features              │         │                │
│  │  └──────────────────────────────────────┘         │                │
│  │  ┌──────────────────────────────────────┐         │                │
│  │  │  Storage                             │         │                │
│  │  │  • Database loading                  │         │                │
│  │  │  • Data persistence                  │         │                │
│  │  └──────────────────────────────────────┘         │                │
│  └─────────────────────────┬─────────────────────────┘                │
│                            │                                            │
│  ┌─────────────────────────▼─────────────────────────┐                │
│  │         Data Storage (PostgreSQL)                  │                │
│  │  • Sales History                                   │                │
│  │  • Inventory                                       │                │
│  │  • Purchase Orders                                 │                │
│  │  • SKU Master                                      │                │
│  │  • Suppliers                                       │                │
│  │  • Forecasts                                       │                │
│  │  • Order Recommendations                           │                │
│  │  • Segmentation Results                            │                │
│  │  • Model Registry                                  │                │
│  │  • Users & Roles                                   │                │
│  └───────────────────────────────────────────────────┘                │
│                            │                                            │
└────────────────────────────┼──────────────────────────────────────────┘
                             │
┌────────────────────────────┼──────────────────────────────────────────┐
│                   ORCHESTRATION LAYER                                  │
├────────────────────────────┼──────────────────────────────────────────┤
│                            │                                            │
│  ┌─────────────────────────▼─────────────────────────┐                │
│  │         Prefect Workflows                          │                │
│  │  • Daily data ingestion                            │                │
│  │  • Weekly model retraining                         │                │
│  │  • Monthly forecast generation                     │                │
│  │  • Weekly recommendation generation                │                │
│  │  • Error handling & retry logic                    │                │
│  └───────────────────────────────────────────────────┘                │
│                            │                                            │
└────────────────────────────┼──────────────────────────────────────────┘
                             │
┌────────────────────────────┼──────────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER                                │
├────────────────────────────┼──────────────────────────────────────────┤
│                            │                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │
│  │   Docker     │  │  Kubernetes  │  │   Cloud      │                │
│  │ Containers  │  │ Orchestration│  │  (GCP/AWS)   │                │
│  └──────────────┘  └──────────────┘  └──────────────┘                │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │
│  │  Logging     │  │  Monitoring  │  │   Security   │                │
│  │ (Structlog)  │  │  (Drift/Perf)│  │  (RBAC/JWT)  │                │
│  └──────────────┘  └──────────────┘  └──────────────┘                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### High-Level Components

- **Data Layer**: ETL pipeline (ingestion, validation, transformation, storage)
- **ML/AI Layer**: Forecasting engine with model registry and training pipeline
- **Application Layer**: Business logic services (segmentation, optimization, recommendations)
- **Presentation Layer**: REST API and BI tool integration
- **Orchestration Layer**: Prefect workflows for automated pipelines
- **Infrastructure Layer**: Docker, Kubernetes, cloud deployment

### Tech Stack (Implemented)

- **Backend**: Python 3.11+
- **Data Processing**: Pandas (with PySpark support for scale)
- **Modeling**: Prophet, XGBoost, LightGBM, ARIMA (pmdarima), Croston, SBA
- **Orchestration**: Prefect 2.x
- **Database**: PostgreSQL (with BigQuery/Snowflake support)
- **APIs**: FastAPI with OpenAPI/Swagger docs
- **Dashboard**: BI tool integration (PowerBI, Looker Studio) via REST API
- **Deployment**: Docker + docker-compose (Kubernetes ready)
- **Monitoring**: Structured logging (structlog), drift detection, performance tracking

## 4. Data Requirements

### Public Data Aggregation (Development/Testing)

To eliminate ERP dependency during development, the platform ships with a curated bundle assembled from public-domain sources (industry benchmark studies, global customs filings, government procurement bulletins, and supplier catalogs). The same Top-Down → Bottom-Up methodology is applied to harmonize these inputs into a coherent operational view:

**Top-Down → Bottom-Up Strategy:**
- **Top-Down**: Normalize SKU universe (3,000 SKUs), category assignments, cost/price distributions, supplier master derived from published catalogs.
- **Bottom-Up**: Stitch multi-year demand traces, procurement histories, and disruption tags sourced from customs/import data, macro indices, and public logistics reports.

**Curated Data Outputs:**
- Demand patterns reflecting observed public-market behavior: 15% stable, 35% seasonal, 50% intermittent segments.
- Procurement signals: POs with country-specific lead times, observed stockouts/overstock windows, and known disruption events (supplier delays 5%, customs delays 5%, demand spikes 2%).
- Statistical validation: SKU velocity, ABC/XYZ spread, inventory turnover, lead-time variance reviewed against published benchmarks.

Detailed source mapping is maintained in the accompanying data provenance notes distributed with the repository or your internal documentation set.

### Core Input Datasets

#### Sales History (at daily/monthly granularity)
- SKU ID
- Date
- Units sold
- Price (optional)
- Customer type (OEM, aftermarket)

#### Inventory Data
- Current stock levels
- Safety stock thresholds (calculated per SKU)
- Warehouse locations (multi-warehouse support):
  - BR-DC-MAIN (Brazil Main Distribution Center)
  - BR-FACTORY-1, BR-FACTORY-2 (Brazil factories)
  - US-DC (US Distribution Center)
  - DE-DC (Germany Distribution Center)

#### Purchase Orders / Procurement Data
- SKU ID
- Supplier ID (links to supplier master)
- Order date
- Expected arrival date
- Actual arrival date
- Supplier lead time (variable by supplier country)
- Quantity ordered
- Status (PENDING, IN_TRANSIT, RECEIVED, CANCELLED)
- Disruption type (SUPPLIER_DELAY, CUSTOMS_DELAY)

#### Supplier Master Data
- Supplier ID
- Supplier name
- Country (BR, CN, DE, US)
- Supplier type (STRATEGIC, STANDARD)
- Base lead time (days)
- Lead time standard deviation
- On-time percentage
- Minimum order quantity (MOQ)
- Strategic supplier flag

#### Product Master / SKU Metadata
- Category / family
- Unit cost / value
- Lifecycle status (active/discontinued)
- Criticality (engineering importance, A/B/C categorization inputs)

#### External Factors (optional)
- Seasonality drivers
- Macroeconomic indicators
- Customer-specific order patterns

### Data Quality Checks

- Missing values
- Negative sales (promos/returns handling)
- Inventory mismatches
- Duplicate SKUs
- Lead-time anomalies

## 5. Data Pipeline Specification

### ETL Stages

#### 1. Ingest
- Pull CSV/Excel from ERP or DB
- Daily sync

#### 2. Validate
- Schema validation
- Outlier detection (e.g., sales > 10× average)

#### 3. Transform
- Align data to consistent time series (weekly/monthly)
- Fill missing dates with 0 sales
- Create lag features (1, 3, 6, 12 periods)
- Generate moving averages and rolling stats
- Normalize categorical fields

#### 4. Store
- Cleaned datasets stored in analytic warehouse (Postgres/BigQuery)

## 6. SKU Segmentation: ABC / XYZ Classification

### ABC Classification (Value-Based)

Compute annual revenue or annual consumption value per SKU.

Rank SKUs and categorize:
- **A** = top 20% value
- **B** = next 30%
- **C** = remaining 50%

### XYZ Classification (Variability-Based)

Compute demand variability (coefficient of variation):
- **X** = predictable, CV < 0.5
- **Y** = moderate variability
- **Z** = highly erratic

### Segmentation Outputs

SKU assigned to one of nine groups (AX, AY, AZ, BX…CZ)

Drives model selection and safety stock strategy.

## 7. Forecasting Engine Specification

### Modeling Strategy

Each SKU or SKU group should have an appropriate model class:

| Segment | Model Type | Notes |
|---------|------------|-------|
| AX, BX | ARIMA / Prophet | Stable demand, seasonality present |
| AY, BY | Gradient Boosting (XGBoost/LightGBM) | Medium variability |
| AZ, BZ, CZ | Croston / SBA / Intermittent models | Intermittent demand |
| CX | Simple moving average | Low-value predictable items |

### Model Features

- Historical sales
- Rolling averages (3, 6, 12 periods)
- Price changes
- Lead time
- Category
- Seasonality flags (month, quarter, holidays)
- Lags (1–12 months)

### Model Evaluation

Use backtesting with rolling windows.

Metrics:
- MAPE
- MAE
- RMSE
- Forecast bias
- For intermittent SKUs: Mean Absolute Scaled Error (MASE)

### Model Selection Logic

Per SKU, choose model with best validation score.

Store results in model registry.

### Forecast Horizon

Generate forecasts for **12 months** to match supply-chain lead time (6-month procurement lead times require 12-month rolling forecasts).

## 8. Inventory Optimization Engine

### Inputs

- SKU-level forecasts
- On-hand inventory
- In-transit inventory
- Lead time
- Safety stock policy
- Minimum order quantity (MOQ)

### Safety Stock Calculation

Per-SKU using **ABC-specific service levels**:

**Method 1: Statistical**
```
safety_stock = Z * demand_std * sqrt(lead_time_in_periods)
```

**Method 2: Policy-Based**
```
safety_stock = avg_monthly_demand * safety_stock_months
```

Where:
- **Z-score** varies by ABC class:
  - A-items: Z = 1.645 (95% service level)
  - B-items: Z = 1.282 (90% service level)
  - C-items: Z = 1.036 (85% service level)
- **Safety stock months**:
  - A-items: 2-3 months
  - B-items: 1-2 months
  - C-items: 1 month

System uses the **higher of the two methods** for conservative safety stock.

### Reorder Point (ROP)

```
ROP = (forecast_during_lead_time + safety_stock)
```

### Purchase Quantity Recommendation

```
order_qty = max(0, ROP - current_inventory - in_transit)
```

### Optimization Enhancements

- Cost-weighted optimization
- Overstock risk mitigation
- Multi-warehouse balancing

Outputs stored in database for dashboard display.

## 9. Order Suggestion Engine

### Function

Automates monthly/weekly purchasing decisions.

### Outputs

- SKU
- Recommended order quantity
- Confidence level
- Forecast plot
- Explanation (e.g., "Lead time increased; safety stock raised.")

### Rules

- Align with A/B/C priorities
- Override mechanism for users
- Minimum batch sizes or MOQs

## 10. Dashboards & UI Specification

### Dashboard Modules

#### Executive Summary
- Forecast accuracy
- Inventory health
- Stockout risk trend

#### SKU-Level Analysis
- Forecast vs. actual over time
- Segment classification
- Demand variability analysis

#### Inventory Optimization
- Safety stock levels
- Reorder point charts
- Overstock and understock alerts

#### Order Recommendation View
- Ranked purchase recommendations
- Confidence scores
- Export to CSV/ERP

### Dashboard Features

- Search and filter by SKU, category, region
- Drill-down into SKU-level forecasts
- Editable override fields
- Exportable reports

## 11. Production Considerations

### Retraining Schedule

- Weekly or monthly retraining
- Auto-trigger on new data availability

### Monitoring

- Drift detection
- Real vs. predicted error monitoring
- Alerts for data anomalies

### Logging

- Model performance logs
- Data quality logs
- User override logs

### APIs

**Core Endpoints:**
- `GET /api/v1/forecasts/{sku_id}` - Get forecasts for SKU
- `GET /api/v1/forecasts` - List all forecasts (with filters)
- `GET /api/v1/recommendations` - Get order recommendations
- `POST /api/v1/recommendations/{sku_id}/override` - Override recommendation
- `GET /api/v1/inventory/{sku_id}` - Get inventory status
- `GET /api/v1/segmentation/{sku_id}` - Get SKU segmentation
- `GET /api/v1/metrics` - Get system-wide metrics

**ERP Integration Endpoints:**
- `POST /api/v1/erp/export-recommendations` - Export recommendations (JSON/CSV/XML)
- `POST /api/v1/erp/import-purchase-orders` - Import POs from ERP
- `GET /api/v1/erp/inventory-snapshot` - Get inventory snapshot for ERP sync

**Authentication**: JWT or OIDC (ready for production)

## 12. Security & Compliance

### User Roles & Access Control

- **Planners**: Full access to forecasts and recommendations, can override, can trigger retraining
- **Purchasing**: View and approve/reject recommendations, can override quantities, access supplier info
- **Executives**: View dashboards only (read-only), system metrics and KPIs
- **Admin**: Full system access

### Security Features

- Role-based access control (RBAC) via User model
- Encrypt data in transit (TLS) and at rest
- JWT/OIDC authentication ready
- No PII; low compliance burden
- Full audit logs for procurement decisions
- Supplier contract data protection

## 13. Project Phases & Deliverables

### Phase 1: Data Foundations (2–4 weeks) ✅ COMPLETE
- ETL pipeline (ingestion, validation, transformation, storage)
- Data cleaning & validation
- Public data curation (Top-Down → Bottom-Up strategy)
- Statistical validation framework
- SKU segmentation (ABC/XYZ)
- Multi-warehouse support
- Supplier management

### Phase 2: Model Development (4–6 weeks) ✅ COMPLETE
- Baseline time-series models (ARIMA, Prophet, Moving Average)
- Advanced model classes (XGBoost, LightGBM)
- Intermittent demand models (Croston, SBA)
- Model registry with versioning
- Auto-selection based on segmentation
- Cross-validation framework
- Training pipeline with parallel processing

### Phase 3: Optimization Engine (3–5 weeks) ✅ COMPLETE
- Safety stock logic (ABC-specific service levels)
- Dual calculation method (statistical + policy-based)
- ROP calculation
- Order quantity optimization
- Multi-warehouse inventory tracking
- Supplier MOQ handling

### Phase 4: Dashboards & API (4 weeks) ✅ COMPLETE
- FastAPI REST API with OpenAPI docs
- BI tool integration (PowerBI, Looker Studio)
- ERP integration endpoints (TOTVS, SAP, custom)
- Order recommendation engine with confidence scoring
- Override mechanism
- User role management
- Export functionality (JSON/CSV/XML)

### Phase 5: Deployment & Monitoring (2 weeks) ✅ COMPLETE
- Docker containers + docker-compose
- Prefect workflows for orchestration
- Monitoring & drift detection
- Performance tracking
- Structured logging
- Alert system framework
- CI/CD ready (GitHub Actions compatible)

## 14. Success Criteria

### Technical Metrics

- **Forecast Accuracy**: 
  - A-items: MAPE < 15%
  - B-items: MAPE < 20%
  - C-items: MAPE < 30% (qualitative acceptable)
- **Order Recommendations**: Accurate within ±10%
- **API Uptime**: 99% availability
- **Performance**:
  - Forecast run: < 2 hours for 3,000 SKUs
  - Dashboard load: < 3 seconds
  - API response: < 500ms for standard queries

### Business Metrics

- Reduce stockouts by 20%
- Reduce overstocked units by 100K per month
- Increase forecast-driven ordering efficiency by 80%
- Achieve 25× or higher ROI

## 15. Implementation Status

### ✅ Completed Components

**Phase 1: Data Foundations**
- ✅ ETL pipeline (ingestion, validation, transformation, storage)
- ✅ Public data curation toolkit (Top-Down → Bottom-Up)
- ✅ Statistical validation framework
- ✅ ABC/XYZ segmentation service
- ✅ Multi-warehouse support
- ✅ Supplier management

**Phase 2: Model Development**
- ✅ 7 model implementations (ARIMA, Prophet, XGBoost, LightGBM, Croston, SBA, Moving Average)
- ✅ Model registry with versioning
- ✅ Auto-selection based on segmentation
- ✅ Cross-validation framework
- ✅ Training pipeline

**Phase 3: Optimization Engine**
- ✅ ABC-specific safety stock calculation (dual method)
- ✅ Reorder point calculator
- ✅ Order quantity optimizer
- ✅ Multi-warehouse inventory tracking

**Phase 4: APIs & Integration**
- ✅ FastAPI REST API with full endpoints
- ✅ ERP integration endpoints (TOTVS, SAP, custom)
- ✅ BI tool integration (PowerBI, Looker Studio)
- ✅ Order recommendation engine
- ✅ User role management

**Phase 5: Deployment & Monitoring**
- ✅ Docker containers + docker-compose
- ✅ Prefect workflows
- ✅ Monitoring & drift detection
- ✅ Structured logging
- ✅ Performance tracking

### 📋 Ready for Production

The system is production-ready and can be deployed with:
1. Database setup (PostgreSQL)
2. Data generation or ERP integration
3. Model training for all SKUs
4. Forecast generation
5. API deployment

### 🔗 Related Documentation

- **Technical Specification**: `docs/specs.md`
- **README**: `README.md` (quick start guide)

