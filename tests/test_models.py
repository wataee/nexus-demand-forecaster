"""Tests for forecast models."""

import pytest
import pandas as pd
import numpy as np
from src.forecasting.models.moving_average_model import MovingAverageModel
from src.forecasting.models.croston_model import CrostonModel
from src.forecasting.models.sba_model import SBAModel


def test_moving_average_model():
    """Test Moving Average model."""
    dates = pd.date_range("2024-01-01", periods=24, freq="ME")
    data = pd.DataFrame({
        "sku_id": ["SKU-001"] * 24,
        "date": dates,
        "demand": np.random.uniform(50, 150, 24),
    })

    model = MovingAverageModel(window=6)
    metrics = model.train(data, target_col="demand", date_col="date", group_col="sku_id")

    assert model.is_trained
    assert model.mean_value is not None

    predictions = model.predict(horizon=6)
    assert len(predictions) == 6
    assert all(p >= 0 for p in predictions)


def test_croston_model():
    """Test Croston intermittent demand model."""
    dates = pd.date_range("2024-01-01", periods=20, freq="ME")
    # Intermittent demand series with zeros
    demands = [0, 5, 0, 0, 12, 0, 8, 0, 0, 0, 15, 0, 0, 6, 0, 0, 9, 0, 0, 10]
    data = pd.DataFrame({
        "sku_id": ["SKU-INTERMITTENT"] * 20,
        "date": dates,
        "demand": demands,
    })

    model = CrostonModel(alpha=0.15)
    metrics = model.train(data, target_col="demand", date_col="date", group_col="sku_id")

    assert model.is_trained
    predictions = model.predict(horizon=4)
    assert len(predictions) == 4
    assert all(p >= 0 for p in predictions)


def test_sba_model():
    """Test Syntetos-Boylan Approximation model."""
    dates = pd.date_range("2024-01-01", periods=16, freq="ME")
    demands = [0, 10, 0, 0, 20, 0, 0, 15, 0, 0, 0, 25, 0, 10, 0, 0]
    data = pd.DataFrame({
        "sku_id": ["SKU-SBA"] * 16,
        "date": dates,
        "demand": demands,
    })

    model = SBAModel(alpha=0.1)
    metrics = model.train(data, target_col="demand", date_col="date", group_col="sku_id")

    assert model.is_trained
    predictions = model.predict(horizon=3)
    assert len(predictions) == 3
