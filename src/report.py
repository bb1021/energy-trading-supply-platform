from __future__ import annotations

import pandas as pd


def _correlation_observation(correlation: pd.DataFrame) -> str:
    strongest_pair: tuple[str, str] | None = None
    strongest_value = 0.0
    columns = list(correlation.columns)

    for left_index, left_asset in enumerate(columns):
        for right_asset in columns[left_index + 1 :]:
            value = correlation.loc[left_asset, right_asset]
            if pd.notna(value) and abs(float(value)) > abs(strongest_value):
                strongest_pair = (left_asset, right_asset)
                strongest_value = float(value)

    if strongest_pair is None:
        return "The selected range does not contain enough observations for a reliable correlation reading."

    relationship = "move together" if strongest_value >= 0 else "move in opposite directions"
    return (
        f"The strongest observed relationship is between {strongest_pair[0]} and {strongest_pair[1]} "
        f"({strongest_value:.2f}); within this sample they tend to {relationship}."
    )


def build_report_markdown(
    snapshot: pd.DataFrame,
    balance: dict,
    storage: dict,
    scenario_result: dict,
    risk_table: pd.DataFrame,
    correlation: pd.DataFrame,
    active_range: str,
) -> str:
    metric_lines = []
    for asset in ["Brent", "WTI", "Natural Gas", "Carbon"]:
        if asset not in snapshot.index:
            continue
        latest = float(snapshot.loc[asset, "Latest"])
        daily_change = float(snapshot.loc[asset, "1D Change %"])
        metric_lines.append(f"- **{asset}:** {latest:.2f} ({daily_change:+.2f}% latest-session change)")

    risk_assets = risk_table.dropna(subset=["Annualised Volatility"]) if not risk_table.empty else risk_table
    if risk_assets.empty:
        risk_comment = "The selected range is too short to estimate volatility and drawdown reliably."
    else:
        highest_volatility_asset = str(risk_assets["Annualised Volatility"].idxmax())
        highest_volatility = float(risk_assets.loc[highest_volatility_asset, "Annualised Volatility"])
        deepest_drawdown_asset = str(risk_assets["Max Drawdown"].idxmin())
        deepest_drawdown = float(risk_assets.loc[deepest_drawdown_asset, "Max Drawdown"])
        risk_comment = (
            f"{highest_volatility_asset} has the highest annualised volatility at {highest_volatility:.2f}%. "
            f"The deepest observed drawdown is {deepest_drawdown:.2f}% in {deepest_drawdown_asset}. "
            f"{_correlation_observation(correlation)}"
        )

    scenario_balance = scenario_result["balance"]
    scenario_storage = scenario_result["storage"]

    return f"""# Energy Trading & Supply Analytics Report

*Active market data range: {active_range}*

## Executive Summary

The simplified market balance is **{balance['market_regime'].lower()}**, with **{balance['price_pressure'].lower()} implied price pressure**. Modelled supply is {balance['supply']:.2f} against demand of {balance['demand']:.2f}, leaving a surplus/deficit of {balance['surplus_deficit']:.2f}.

The storage model indicates **{storage['signal'].lower()}**. Expected gross margin is {storage['expected_gross_margin']:,.0f}, and the breakeven forward price is {storage['breakeven_forward_price']:.2f}. The overall commercial view is to combine the physical balance with curve structure and carrying costs before adding prompt exposure or committing storage capacity.

## Key Market Metrics

{chr(10).join(metric_lines)}

## Supply-Demand Balance

Current modelled supply is **{balance['supply']:.2f}**, while demand is **{balance['demand']:.2f}**. The resulting surplus/deficit is **{balance['surplus_deficit']:.2f}**. {balance['interpretation']}

## Scenario Analysis

The selected scenario is **{scenario_result['name']}**. {scenario_result['description']} Under these assumptions, the balance moves to {scenario_balance['surplus_deficit']:.2f}, the market regime is {scenario_balance['market_regime'].lower()}, and storage carry is {scenario_storage['carry_return']:.2f} per unit. The suggested commercial response is to {scenario_result['commercial_action'][0].lower() + scenario_result['commercial_action'][1:]}

## Storage and Supply Decision

The estimated carry return is **{storage['carry_return']:.2f} per unit**, producing an expected gross margin of **{storage['expected_gross_margin']:,.0f}** at the modelled capacity. The current signal is **{storage['signal']}**. {storage['recommendation']} This matters in physical energy markets because inventory only creates value when forward carry and operational optionality compensate for financing, losses, and tankage.

## Risk Assessment

{risk_comment}

## Commercial Recommendation

Use the current balance as the directional anchor, then confirm the position through regional spreads and the forward curve. {storage['recommendation']} Under the selected scenario, {scenario_result['commercial_action'][0].lower() + scenario_result['commercial_action'][1:]}

## Limitations

Public market data are representative proxies, and the forward curves are simplified. Physical logistics, credit, tax, product quality, storage availability, and operational constraints are not fully modelled. The platform is intended for analytical demonstration and research purposes only.
"""
