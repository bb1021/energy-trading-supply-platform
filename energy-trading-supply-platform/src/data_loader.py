from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except Exception:  # pragma: no cover - handled at runtime for offline demos
    yf = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SAMPLE_MARKET_DATA = DATA_DIR / "sample_market_data.csv"
SAMPLE_FORWARD_CURVES = DATA_DIR / "sample_forward_curves.csv"


TICKERS = {
    "Brent": "BZ=F",
    "WTI": "CL=F",
    "Natural Gas": "NG=F",
    "Heating Oil": "HO=F",
    "Gasoline": "RB=F",
    "Power Proxy": "XLU",
    "Carbon": "KRBN",
    "USD Index": "DX-Y.NYB",
}


@dataclass(frozen=True)
class MarketDataBundle:
    prices: pd.DataFrame
    source: str
    tickers: dict[str, str]
    is_fallback: bool = False


def load_sample_market_data() -> pd.DataFrame:
    prices = pd.read_csv(SAMPLE_MARKET_DATA, parse_dates=["Date"])
    prices = prices.set_index("Date").sort_index()
    return prices.apply(pd.to_numeric, errors="coerce").ffill().bfill()


def load_forward_curves() -> pd.DataFrame:
    return pd.read_csv(SAMPLE_FORWARD_CURVES)


def load_sample_market_data_for_range(start_date: date, end_date: date) -> pd.DataFrame:
    sample = load_sample_market_data()
    target_dates = pd.bdate_range(start=pd.Timestamp(start_date), end=pd.Timestamp(end_date))
    if len(target_dates) < 2:
        target_dates = pd.date_range(start=pd.Timestamp(start_date), end=pd.Timestamp(end_date), freq="D")

    source_positions = np.arange(len(sample), dtype=float)
    target_positions = np.linspace(0, len(sample) - 1, len(target_dates))
    aligned = {
        column: np.interp(target_positions, source_positions, sample[column].to_numpy(dtype=float))
        for column in sample.columns
    }
    return pd.DataFrame(aligned, index=target_dates)


def _normalise_download(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"] if "Close" in raw.columns.get_level_values(0) else raw.xs("Close", axis=1, level=1)
    else:
        close = raw[["Close"]]

    inverse = {ticker: name for name, ticker in TICKERS.items()}
    close = close.rename(columns=inverse)

    if len(close.columns) == 1 and close.columns[0] == "Close":
        close = close.rename(columns={"Close": next(iter(TICKERS))})

    expected = list(TICKERS)
    close = close[[col for col in expected if col in close.columns]]
    close.index = pd.DatetimeIndex(close.index)
    if close.index.tz is not None:
        close.index = close.index.tz_localize(None)
    close.index = close.index.normalize()
    return close.dropna(how="all").ffill().bfill()


def fetch_live_market_data(start_date: date, end_date: date) -> pd.DataFrame:
    if yf is None:
        return pd.DataFrame()

    try:
        raw = yf.download(
            list(TICKERS.values()),
            start=pd.Timestamp(start_date).strftime("%Y-%m-%d"),
            end=(pd.Timestamp(end_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        prices = _normalise_download(raw)
    except Exception:
        return pd.DataFrame()

    usable_columns = [col for col in TICKERS if col in prices.columns and prices[col].notna().sum() >= 2]
    if len(usable_columns) < 3:
        return pd.DataFrame()

    return prices[usable_columns].dropna(how="all")


def synthetic_fallback(days: int = 90) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=days)
    anchors = {
        "Brent": 82.0,
        "WTI": 76.0,
        "Natural Gas": 3.7,
        "Heating Oil": 2.7,
        "Gasoline": 2.4,
        "Power Proxy": 72.0,
        "Carbon": 77.0,
        "USD Index": 101.0,
    }
    vols = {
        "Brent": 0.012,
        "WTI": 0.013,
        "Natural Gas": 0.026,
        "Heating Oil": 0.015,
        "Gasoline": 0.016,
        "Power Proxy": 0.009,
        "Carbon": 0.014,
        "USD Index": 0.004,
    }
    data = {}
    for asset, start in anchors.items():
        returns = rng.normal(0.0004, vols[asset], size=len(dates))
        data[asset] = start * np.exp(np.cumsum(returns))
    return pd.DataFrame(data, index=dates)


def load_market_data(
    prefer_live: bool = True,
    start_date: date | None = None,
    end_date: date | None = None,
) -> MarketDataBundle:
    end_date = end_date or date.today()
    start_date = start_date or (end_date - timedelta(days=180))

    if prefer_live:
        live = fetch_live_market_data(start_date, end_date)
        if not live.empty:
            sample = load_sample_market_data_for_range(start_date, end_date)
            combined = live.combine_first(sample)
            return MarketDataBundle(
                combined.sort_index().ffill().bfill(),
                "Live public data with sample proxy backfill",
                TICKERS,
            )

    try:
        sample = load_sample_market_data_for_range(start_date, end_date)
        return MarketDataBundle(sample, "Fallback sample data", TICKERS, is_fallback=True)
    except Exception:
        target_dates = pd.bdate_range(start_date, end_date)
        if len(target_dates) < 2:
            target_dates = pd.date_range(start_date, end_date, freq="D")
        days = len(target_dates)
        generated = synthetic_fallback(days)
        generated.index = target_dates
        return MarketDataBundle(generated, "Generated offline fallback data", TICKERS, is_fallback=True)
