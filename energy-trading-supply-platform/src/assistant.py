from __future__ import annotations

import pandas as pd


def generate_market_note(
    snapshot: pd.DataFrame,
    balance: dict,
    storage: dict,
    risk_table: pd.DataFrame,
    scenario_result: dict | None = None,
) -> str:
    brent = snapshot.loc["Brent", "Latest"] if "Brent" in snapshot.index else 0.0
    wti = snapshot.loc["WTI", "Latest"] if "WTI" in snapshot.index else 0.0
    gas = snapshot.loc["Natural Gas", "Latest"] if "Natural Gas" in snapshot.index else 0.0
    carbon = snapshot.loc["Carbon", "Latest"] if "Carbon" in snapshot.index else 0.0
    brent_wti = brent - wti

    riskiest = "commodity exposure"
    if not risk_table.empty and "Annualised Volatility" in risk_table:
        riskiest = str(risk_table["Annualised Volatility"].astype(float).idxmax())

    scenario_line = ""
    if scenario_result:
        scenario_line = (
            f"\n\nSelected scenario: {scenario_result['name']}. "
            f"{scenario_result['description']} Suggested action: {scenario_result['commercial_action']}"
        )

    return f"""Market backdrop:
Brent is trading around {brent:.2f}, WTI around {wti:.2f}, natural gas around {gas:.2f}, and carbon around {carbon:.2f}. The Brent-WTI spread is {brent_wti:.2f}, which frames regional crude logistics and export economics.

Key price moves:
The current screen points to a {balance['market_regime'].lower()} balance with {balance['price_pressure'].lower()} price pressure. For a trading desk, this means outright price direction should be discussed together with spreads, inventories, and optionality rather than in isolation.

Supply-demand summary:
Modelled supply is {balance['supply']:.2f} versus demand of {balance['demand']:.2f}, leaving a surplus/deficit of {balance['surplus_deficit']:.2f}. {balance['interpretation']}

Storage recommendation:
Storage signal: {storage['signal']}. Carry return is {storage['carry_return']:.2f} per unit and expected gross margin is {storage['expected_gross_margin']:,.0f}. Breakeven forward price is {storage['breakeven_forward_price']:.2f}.

Major risks:
The highest recent volatility is in {riskiest}. Key risks are weather, unplanned outages, freight constraints, policy shifts, liquidity, and basis risk between proxies and physical exposures.

Commercial recommendation:
Use the balance model to assess prompt exposure, then use the curve and storage module to test whether physical optionality is being paid for. Current recommendation: {storage['recommendation']}{scenario_line}
"""
