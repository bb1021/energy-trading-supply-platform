from __future__ import annotations

import numpy as np
import pandas as pd


def daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    return prices.ffill().pct_change().dropna(how="all")


def volatility(returns: pd.DataFrame) -> pd.Series:
    return returns.std() * np.sqrt(252)


def drawdown(prices: pd.DataFrame) -> pd.DataFrame:
    indexed = prices.ffill()
    running_max = indexed.cummax()
    return indexed / running_max - 1.0


def historical_var(returns: pd.DataFrame, confidence: float = 0.95, notional: float = 1_000_000) -> pd.Series:
    quantile = returns.quantile(1.0 - confidence)
    return (quantile * notional).round(0)


def stress_loss(latest_prices: pd.Series, shocks: dict[str, float], notionals: dict[str, float]) -> pd.DataFrame:
    rows = []
    for asset, shock in shocks.items():
        if asset not in latest_prices:
            continue
        notional = notionals.get(asset, 0.0)
        rows.append(
            {
                "Asset": asset,
                "Shock %": shock * 100,
                "Notional": notional,
                "Estimated P&L": notional * shock,
            }
        )
    return pd.DataFrame(rows)


def risk_summary(prices: pd.DataFrame, notional: float = 1_000_000) -> pd.DataFrame:
    returns = daily_returns(prices)
    vols = volatility(returns)
    var = historical_var(returns, notional=notional)
    max_dd = drawdown(prices).min()
    summary = pd.DataFrame(
        {
            "Annualised Volatility": vols,
            "Historical 95% 1D VaR": var,
            "Max Drawdown": max_dd,
        }
    )
    summary["Annualised Volatility"] = (summary["Annualised Volatility"] * 100).round(2)
    summary["Max Drawdown"] = (summary["Max Drawdown"] * 100).round(2)
    return summary

