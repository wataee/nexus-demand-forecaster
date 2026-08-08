"""Script to set up database and run initial migrations."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import engine, Base
from src.database.models import *  # noqa: F401, F403
import argparse


def main():
    parser = argparse.ArgumentParser(description="Set up database schema")
    parser.add_argument("--drop", action="store_true", help="Drop existing tables")
    
    args = parser.parse_args()
    
    if args.drop:
        print("Dropping existing tables...")
        Base.metadata.drop_all(engine)
    
    print("Creating database tables...")
    Base.metadata.create_all(engine)
    print("Database setup complete!")


if __name__ == "__main__":
    main()

