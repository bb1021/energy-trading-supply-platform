from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BalanceInputs:
    production: float = 100.0
    imports: float = 8.0
    exports: float = 7.0
    refinery_demand: float = 72.0
    industrial_demand: float = 24.0
    seasonal_demand_uplift: float = 2.0
    disruption_adjustment: float = 0.0


def calculate_balance(inputs: BalanceInputs) -> dict[str, float | str]:
    supply = inputs.production + inputs.imports - inputs.exports + inputs.disruption_adjustment
    demand = inputs.refinery_demand + inputs.industrial_demand + inputs.seasonal_demand_uplift
    surplus_deficit = supply - demand

    if surplus_deficit <= -2.0:
        regime = "Tight"
        pressure = "Bullish"
        pressure_score = min(100.0, 55.0 + abs(surplus_deficit) * 7.5)
    elif surplus_deficit >= 2.0:
        regime = "Oversupplied"
        pressure = "Bearish"
        pressure_score = max(0.0, 45.0 - surplus_deficit * 7.5)
    else:
        regime = "Balanced"
        pressure = "Neutral"
        pressure_score = 50.0 - surplus_deficit * 2.0

    return {
        "supply": round(supply, 2),
        "demand": round(demand, 2),
        "surplus_deficit": round(surplus_deficit, 2),
        "market_regime": regime,
        "price_pressure": pressure,
        "pressure_score": round(pressure_score, 1),
        "interpretation": commercial_interpretation(surplus_deficit, regime),
    }


def commercial_interpretation(balance: float, regime: str) -> str:
    if regime == "Tight":
        return (
            "Supply is not covering demand, so prompt barrels should command a premium. "
            "A trader would monitor replacement costs, freight optionality, and short-covering risk."
        )
    if regime == "Oversupplied":
        return (
            "Supply exceeds demand, which can pressure prompt prices and improve storage economics. "
            "The commercial question becomes whether forward carry pays for tankage and financing."
        )
    return (
        "The balance is close to equilibrium. Spreads, inventory changes, and weather or outage risks "
        "are likely to drive marginal trading decisions."
    )

