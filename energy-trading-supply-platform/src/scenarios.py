from __future__ import annotations

from dataclasses import replace

from src.storage import storage_economics
from src.supply_demand import BalanceInputs, calculate_balance


SCENARIOS = {
    "Base case": {
        "description": "Current assumptions with no additional demand or supply shock.",
        "demand_delta": 0.0,
        "supply_delta": 0.0,
        "forward_delta": 0.0,
        "risk_shock": {"Brent": -0.03, "WTI": -0.03, "Natural Gas": -0.04, "Carbon": -0.02},
        "action": "Stay balanced; let spreads and storage economics drive marginal decisions.",
    },
    "Cold winter demand shock": {
        "description": "Weather lifts gas, power, heating, and refinery demand.",
        "demand_delta": 4.5,
        "supply_delta": 0.0,
        "forward_delta": 1.5,
        "risk_shock": {"Brent": 0.04, "WTI": 0.035, "Natural Gas": 0.12, "Carbon": 0.03},
        "action": "Secure prompt supply, protect short exposure, and value storage optionality.",
    },
    "Supply disruption": {
        "description": "Unexpected outage removes available supply from the system.",
        "demand_delta": 0.0,
        "supply_delta": -4.0,
        "forward_delta": 2.0,
        "risk_shock": {"Brent": 0.08, "WTI": 0.07, "Natural Gas": 0.04, "Carbon": 0.01},
        "action": "Prioritise supply assurance, review short physical commitments, and monitor freight.",
    },
    "Weak demand / recession": {
        "description": "Industrial and transport demand soften together.",
        "demand_delta": -5.0,
        "supply_delta": 0.0,
        "forward_delta": -1.5,
        "risk_shock": {"Brent": -0.10, "WTI": -0.10, "Natural Gas": -0.07, "Carbon": -0.08},
        "action": "Reduce length, watch credit exposure, and test whether contango pays for storage.",
    },
    "LNG import surge": {
        "description": "Additional LNG arrivals loosen regional gas balances.",
        "demand_delta": 0.0,
        "supply_delta": 3.0,
        "forward_delta": -0.75,
        "risk_shock": {"Brent": -0.01, "WTI": -0.01, "Natural Gas": -0.09, "Carbon": -0.02},
        "action": "Expect gas weakness, evaluate storage injection economics, and watch power spreads.",
    },
    "Carbon price shock": {
        "description": "Policy or compliance pressure lifts carbon costs.",
        "demand_delta": -0.5,
        "supply_delta": 0.0,
        "forward_delta": 0.5,
        "risk_shock": {"Brent": -0.01, "WTI": -0.01, "Natural Gas": 0.02, "Carbon": 0.15},
        "action": "Review carbon pass-through, hedge compliance exposure, and reassess generation merit order.",
    },
}


def apply_scenario(
    name: str,
    balance_inputs: BalanceInputs,
    spot_price: float,
    forward_price: float,
    storage_cost: float,
    financing_rate: float,
    shrinkage_pct: float,
    capacity: float,
) -> dict:
    scenario = SCENARIOS[name]
    adjusted = replace(
        balance_inputs,
        refinery_demand=balance_inputs.refinery_demand + scenario["demand_delta"],
        disruption_adjustment=balance_inputs.disruption_adjustment + scenario["supply_delta"],
    )
    balance = calculate_balance(adjusted)
    storage = storage_economics(
        spot_price=spot_price,
        forward_price=forward_price + scenario["forward_delta"],
        storage_cost=storage_cost,
        financing_rate=financing_rate,
        shrinkage_pct=shrinkage_pct,
        capacity=capacity,
    )
    return {
        "name": name,
        "description": scenario["description"],
        "adjusted_inputs": adjusted,
        "balance": balance,
        "storage": storage,
        "risk_shock": scenario["risk_shock"],
        "commercial_action": scenario["action"],
    }
