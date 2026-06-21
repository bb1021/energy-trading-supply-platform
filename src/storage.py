from __future__ import annotations


def storage_economics(
    spot_price: float,
    forward_price: float,
    storage_cost: float,
    financing_rate: float,
    shrinkage_pct: float,
    capacity: float,
    months: int = 3,
) -> dict[str, float | str]:
    financing_cost = spot_price * financing_rate * (months / 12.0)
    shrinkage_cost = spot_price * shrinkage_pct
    total_cost = storage_cost + financing_cost + shrinkage_cost
    carry_return = forward_price - spot_price - total_cost
    expected_gross_margin = carry_return * capacity
    breakeven_forward_price = spot_price + total_cost

    if carry_return > 0:
        signal = "Store"
        recommendation = "Forward carry covers storage, financing, and losses; storage has positive expected economics."
    elif carry_return > -0.5:
        signal = "Optionality / hold if strategic"
        recommendation = "Economics are close to breakeven; storage may still be useful for operational flexibility."
    else:
        signal = "Sell prompt / avoid storage"
        recommendation = "The forward price does not compensate for carrying costs, so prompt sale is cleaner."

    return {
        "financing_cost": round(financing_cost, 2),
        "shrinkage_cost": round(shrinkage_cost, 2),
        "total_carry_cost": round(total_cost, 2),
        "carry_return": round(carry_return, 2),
        "expected_gross_margin": round(expected_gross_margin, 2),
        "breakeven_forward_price": round(breakeven_forward_price, 2),
        "signal": signal,
        "recommendation": recommendation,
    }

