from __future__ import annotations

import pandas as pd


def latest_snapshot(prices: pd.DataFrame) -> pd.DataFrame:
    latest = prices.ffill().iloc[-1]
    previous = prices.ffill().iloc[-2] if len(prices) > 1 else latest
    first = prices.ffill().iloc[0]

    frame = pd.DataFrame(
        {
            "Latest": latest,
            "1D Change": latest - previous,
            "1D Change %": (latest / previous - 1.0) * 100,
            "Period Change %": (latest / first - 1.0) * 100,
        }
    )
    return frame.round(2)


def normalised_prices(prices: pd.DataFrame) -> pd.DataFrame:
    cleaned = prices.ffill().dropna(how="all")
    return cleaned.divide(cleaned.iloc[0]).multiply(100)


def key_price_moves(prices: pd.DataFrame) -> list[str]:
    snap = latest_snapshot(prices)
    moves = []
    for asset in ["Brent", "WTI", "Natural Gas", "Carbon"]:
        if asset in snap.index:
            row = snap.loc[asset]
            direction = "higher" if row["1D Change %"] >= 0 else "lower"
            moves.append(f"{asset} is {direction} on the latest session ({row['1D Change %']:.2f}%).")
    return moves


def dashboard_regime(brent_wti_spread: float, balance: float, storage_signal: str) -> str:
    if balance < -1.0 and storage_signal == "Sell prompt / avoid storage":
        return "Tight prompt market"
    if balance > 1.0 and storage_signal == "Store":
        return "Oversupplied carry market"
    if abs(brent_wti_spread) > 7.0:
        return "Logistics-driven dislocation"
    return "Balanced but watch spreads"

