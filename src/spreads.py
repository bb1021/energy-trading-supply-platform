from __future__ import annotations

import pandas as pd


def brent_wti_spread(prices: pd.DataFrame) -> pd.Series:
    return prices["Brent"] - prices["WTI"]


def crude_gas_ratio(prices: pd.DataFrame) -> pd.Series:
    return prices["Brent"] / prices["Natural Gas"]


def curve_structure(forward_curves: pd.DataFrame, commodity: str) -> dict[str, float | str | pd.DataFrame]:
    curve = forward_curves[forward_curves["Commodity"] == commodity].sort_values("Months Ahead")
    if curve.empty:
        return {"structure": "Unavailable", "front_deferred_spread": 0.0, "curve": curve}

    front = float(curve.iloc[0]["Price"])
    deferred = float(curve.iloc[-1]["Price"])
    spread = front - deferred
    if spread > 0.25:
        structure = "Backwardation"
        interpretation = "Prompt prices are above deferred prices, consistent with tight nearby supply."
    elif spread < -0.25:
        structure = "Contango"
        interpretation = "Deferred prices are above prompt prices, which can support storage if carry covers costs."
    else:
        structure = "Flat"
        interpretation = "The curve is relatively flat, so physical optionality may matter more than outright carry."

    return {
        "structure": structure,
        "front_deferred_spread": round(spread, 2),
        "curve": curve,
        "interpretation": interpretation,
    }


def spread_table(prices: pd.DataFrame) -> pd.DataFrame:
    latest = prices.ffill().iloc[-1]
    table = pd.DataFrame(
        [
            {
                "Spread / Ratio": "Brent-WTI",
                "Value": latest["Brent"] - latest["WTI"],
                "Commercial Read": "Regional crude quality, logistics, and export economics.",
            },
            {
                "Spread / Ratio": "Brent / Natural Gas",
                "Value": latest["Brent"] / latest["Natural Gas"],
                "Commercial Read": "Cross-commodity energy value comparison.",
            },
            {
                "Spread / Ratio": "Heating Oil - Gasoline",
                "Value": latest["Heating Oil"] - latest["Gasoline"],
                "Commercial Read": "Refined product demand and seasonal distillate strength proxy.",
            },
        ]
    )
    table["Value"] = table["Value"].round(2)
    return table

