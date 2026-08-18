"""Data ingestion module for reading CSV/Excel files."""

import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List
import structlog
from src.utils.logger import logger

logger = structlog.get_logger()


class DataIngestion:
    """Handle data ingestion from various sources."""
    
    SUPPORTED_FORMATS = [".csv", ".xlsx", ".xls"]
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize data ingestion.
        
        Args:
            data_dir: Directory containing data files
        """
        self.data_dir = Path(data_dir) if data_dir else Path("./data/raw")
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def read_csv(self, file_path: Path, **kwargs) -> pd.DataFrame:
        """
        Read CSV file with schema validation.
        
        Args:
            file_path: Path to CSV file
            **kwargs: Additional arguments for pd.read_csv
            
        Returns:
            DataFrame with loaded data
        """
        logger.info("Reading CSV file", file_path=str(file_path))
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        df = pd.read_csv(file_path, **kwargs)
        logger.info("CSV file loaded", rows=len(df), columns=list(df.columns))
        
        return df
    
    def read_excel(self, file_path: Path, sheet_name: Optional[str] = None, **kwargs) -> pd.DataFrame:
        """
        Read Excel file with schema validation.
        
        Args:
            file_path: Path to Excel file
            sheet_name: Sheet name to read (defaults to first sheet)
            **kwargs: Additional arguments for pd.read_excel
            
        Returns:
            DataFrame with loaded data
        """
        logger.info("Reading Excel file", file_path=str(file_path), sheet=sheet_name)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        df = pd.read_excel(file_path, sheet_name=sheet_name, **kwargs)
        logger.info("Excel file loaded", rows=len(df), columns=list(df.columns))
        
        return df
    
    def read_file(self, file_path: Path, **kwargs) -> pd.DataFrame:
        """
        Read file based on extension (CSV or Excel).
        
        Args:
            file_path: Path to file
            **kwargs: Additional arguments for pandas read functions
            
        Returns:
            DataFrame with loaded data
        """
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()
        
        if suffix == ".csv":
            return self.read_csv(file_path, **kwargs)
        elif suffix in [".xlsx", ".xls"]:
            return self.read_excel(file_path, **kwargs)
        else:
            raise ValueError(f"Unsupported file format: {suffix}. Supported: {self.SUPPORTED_FORMATS}")
    
    def load_all_data(self) -> Dict[str, pd.DataFrame]:
        """
        Load all data files from data directory.
        
        Returns:
            Dictionary mapping data type to DataFrame
        """
        data_files = {
            "sku_master": "sku_master.csv",
            "sales_history": "sales_history.csv",
            "inventory": "inventory.csv",
            "suppliers": "suppliers.csv",
            "purchase_orders": "purchase_orders.csv",
        }
        
        loaded_data = {}
        
        for data_type, filename in data_files.items():
            file_path = self.data_dir / filename
            if file_path.exists():
                logger.info("Loading data file", data_type=data_type, file=filename)
                loaded_data[data_type] = self.read_file(file_path)
            else:
                logger.warning("Data file not found", data_type=data_type, file=filename)
        
        return loaded_data

