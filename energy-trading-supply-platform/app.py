from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from src.assistant import generate_market_note
from src.data_loader import load_forward_curves, load_market_data
from src.market_data import dashboard_regime, key_price_moves, latest_snapshot, normalised_prices
from src.report import build_report_markdown
from src.risk import daily_returns, drawdown, risk_summary, stress_loss
from src.scenarios import SCENARIOS, apply_scenario
from src.spreads import brent_wti_spread, crude_gas_ratio, curve_structure, spread_table
from src.storage import storage_economics
from src.supply_demand import BalanceInputs, calculate_balance
from src.ui import configure_page, inject_css, interpretation, status_panel


@st.cache_data(show_spinner=False)
def get_market_bundle(prefer_live: bool, start_date: date, end_date: date):
    return load_market_data(prefer_live=prefer_live, start_date=start_date, end_date=end_date)


@st.cache_data(show_spinner=False)
def get_forward_curves():
    return load_forward_curves()


def default_context(prices: pd.DataFrame, forward_curves: pd.DataFrame) -> dict:
    latest = prices.ffill().iloc[-1]
    balance_inputs = BalanceInputs()
    balance = calculate_balance(balance_inputs)
    brent_curve = forward_curves[forward_curves["Commodity"] == "Brent"].sort_values("Months Ahead")
    forward_price = float(brent_curve.iloc[2]["Price"]) if len(brent_curve) >= 3 else float(latest["Brent"] + 0.75)
    storage = storage_economics(
        spot_price=float(latest["Brent"]),
        forward_price=forward_price,
        storage_cost=0.70,
        financing_rate=0.06,
        shrinkage_pct=0.003,
        capacity=500_000,
    )
    scenario = apply_scenario(
        "Base case",
        balance_inputs,
        float(latest["Brent"]),
        forward_price,
        0.70,
        0.06,
        0.003,
        500_000,
    )
    return {
        "latest": latest,
        "snapshot": latest_snapshot(prices),
        "balance_inputs": balance_inputs,
        "balance": balance,
        "storage": storage,
        "scenario": scenario,
        "forward_price": forward_price,
    }


def price_chart(prices: pd.DataFrame, assets: list[str], title: str):
    available = [asset for asset in assets if asset in prices.columns]
    indexed = normalised_prices(prices[available])
    indexed.index.name = "Date"
    fig = px.line(indexed.reset_index(), x="Date", y=available, title=title)
    fig.update_layout(legend_title_text="", hovermode="x unified", height=420)
    return fig


def storage_signal_explanation(signal: str) -> str:
    explanations = {
        "Store": "Forward carry covers estimated storage, financing, and product-loss costs.",
        "Optionality / hold if strategic": "Economics are near breakeven; operational flexibility may still justify holding inventory.",
        "Sell prompt / avoid storage": "Forward carry does not currently compensate for the cost of holding inventory.",
    }
    return explanations.get(signal, "The signal compares forward value with the full estimated cost of carry.")


def regime_explanation(regime: str) -> str:
    explanations = {
        "Tight prompt market": "Nearby demand is stronger than available supply, supporting prompt prices.",
        "Oversupplied carry market": "Available supply exceeds demand and may create an incentive to store inventory.",
        "Logistics-driven dislocation": "A wide regional spread points to transport, quality, or location constraints.",
        "Balanced but watch spreads": "The outright balance is stable; spreads and inventory changes are the main signals.",
    }
    return explanations.get(regime, "The regime combines the physical balance, regional spread, and storage signal.")


def page_dashboard(prices: pd.DataFrame, context: dict, source: str, active_range: str) -> None:
    st.title("Energy Trading & Supply Analytics Platform")
    st.caption(f"Active data range: {active_range} | Data source: {source}")

    latest = context["latest"]
    spread = float(latest["Brent"] - latest["WTI"])
    storage_signal = context["storage"]["signal"]
    regime = dashboard_regime(spread, context["balance"]["surplus_deficit"], storage_signal)

    cols = st.columns(4)
    cols[0].metric("Brent Price", f"{latest['Brent']:.2f}", help="Brent crude proxy")
    cols[1].metric("WTI Price", f"{latest['WTI']:.2f}", help="WTI crude proxy")
    cols[2].metric("Natural Gas", f"{latest['Natural Gas']:.2f}", help="Henry Hub natural gas proxy")
    cols[3].metric("Carbon Price", f"{latest['Carbon']:.2f}", help="Carbon allowance / ETF proxy")

    cols = st.columns(3)
    with cols[0]:
        status_panel(
            "Brent-WTI Spread",
            f"{spread:.2f}",
            "A regional crude spread shaped by quality, freight, and export economics.",
        )
    with cols[1]:
        status_panel("Storage Signal", storage_signal, storage_signal_explanation(storage_signal))
    with cols[2]:
        status_panel("Market Regime", regime, regime_explanation(regime))

    interpretation(
        f"The dashboard links outright prices with physical trading signals. Current balance is "
        f"{context['balance']['market_regime'].lower()}, Brent-WTI is {spread:.2f}, and storage economics say "
        f"{storage_signal.lower()}."
    )

    left, right = st.columns([2, 1])
    with left:
        st.plotly_chart(
            price_chart(prices, ["Brent", "WTI", "Natural Gas", "Carbon", "USD Index"], "Normalised Market Prices"),
            width="stretch",
        )
    with right:
        st.subheader("Market Read")
        for move in key_price_moves(prices):
            st.write(f"- {move}")
        st.dataframe(context["snapshot"], width="stretch")


def page_market_data(prices: pd.DataFrame, source: str, tickers: dict[str, str], active_range: str) -> None:
    st.title("Market Data")
    st.caption(f"Active data range: {active_range} | Current mode: {source}")
    interpretation(
        "The data layer attempts to use free public market data and falls back to bundled sample data. "
        "Power, carbon, and LNG-related views use representative proxies where direct public data is limited."
    )

    st.subheader("Ticker Map")
    st.dataframe(pd.DataFrame({"Asset": tickers.keys(), "Ticker / Proxy": tickers.values()}), width="stretch")

    assets = st.multiselect("Assets to plot", list(prices.columns), default=list(prices.columns[:5]))
    if assets:
        st.plotly_chart(price_chart(prices, assets, "Normalised Price History"), width="stretch")

    st.subheader("Latest Market Table")
    st.dataframe(latest_snapshot(prices), width="stretch")
    st.subheader("Raw Price Data")
    st.dataframe(prices.tail(20), width="stretch")


def page_supply_demand() -> dict:
    st.title("Supply-Demand Balance")
    interpretation(
        "This simplified balance converts physical supply and demand assumptions into a surplus/deficit, "
        "then translates that into directional price pressure and a market regime."
    )

    cols = st.columns(3)
    production = cols[0].number_input("Production", 0.0, 200.0, 100.0, 1.0)
    imports = cols[1].number_input("Imports", 0.0, 100.0, 8.0, 0.5)
    exports = cols[2].number_input("Exports", 0.0, 100.0, 7.0, 0.5)
    refinery_demand = cols[0].number_input("Refinery demand", 0.0, 200.0, 72.0, 1.0)
    industrial_demand = cols[1].number_input("Industrial demand", 0.0, 200.0, 24.0, 1.0)
    seasonal_uplift = cols[2].number_input("Seasonal demand uplift", -20.0, 50.0, 2.0, 0.5)
    disruption = st.slider("Disruption / shock adjustment to supply", -20.0, 20.0, 0.0, 0.5)

    inputs = BalanceInputs(production, imports, exports, refinery_demand, industrial_demand, seasonal_uplift, disruption)
    result = calculate_balance(inputs)

    cols = st.columns(4)
    cols[0].metric("Supply", f"{result['supply']:.2f}")
    cols[1].metric("Demand", f"{result['demand']:.2f}")
    cols[2].metric("Surplus / Deficit", f"{result['surplus_deficit']:.2f}")
    cols[3].metric("Regime", result["market_regime"])
    interpretation(result["interpretation"])

    chart_data = pd.DataFrame({"Category": ["Supply", "Demand"], "Value": [result["supply"], result["demand"]]})
    fig = px.bar(chart_data, x="Category", y="Value", color="Category", title="Supply vs Demand")
    fig.update_layout(showlegend=False, height=360)
    st.plotly_chart(fig, width="stretch")
    return {"inputs": inputs, "result": result}


def page_storage(latest: pd.Series, default_forward: float) -> dict:
    st.title("Storage Optimisation")
    interpretation(
        "Physical storage decisions depend on whether the forward price covers prompt purchase cost, tankage, "
        "financing, losses, and operational risk. This module keeps the calculation transparent."
    )

    cols = st.columns(3)
    spot = cols[0].number_input("Spot price", 0.0, 300.0, float(latest["Brent"]), 0.25)
    forward = cols[1].number_input("Forward price", 0.0, 300.0, float(default_forward), 0.25)
    storage_cost = cols[2].number_input("Storage cost per unit", 0.0, 20.0, 0.70, 0.05)
    financing = cols[0].number_input("Annual financing cost", 0.0, 0.5, 0.06, 0.005, format="%.3f")
    shrinkage = cols[1].number_input("Loss / shrinkage assumption", 0.0, 0.1, 0.003, 0.001, format="%.3f")
    capacity = cols[2].number_input("Capacity", 1_000.0, 5_000_000.0, 500_000.0, 10_000.0)

    result = storage_economics(spot, forward, storage_cost, financing, shrinkage, capacity)

    cols = st.columns(4)
    cols[0].metric("Carry Return", f"{result['carry_return']:.2f}")
    with cols[1]:
        status_panel("Storage Signal", result["signal"], storage_signal_explanation(result["signal"]))
    cols[2].metric("Gross Margin", f"{result['expected_gross_margin']:,.0f}")
    cols[3].metric("Breakeven Forward", f"{result['breakeven_forward_price']:.2f}")
    interpretation(result["recommendation"])

    waterfall = pd.DataFrame(
        {
            "Item": ["Forward price", "Spot price", "Storage cost", "Financing", "Shrinkage", "Carry return"],
            "Value": [forward, -spot, -storage_cost, -result["financing_cost"], -result["shrinkage_cost"], result["carry_return"]],
        }
    )
    fig = px.bar(waterfall, x="Item", y="Value", title="Storage Carry Bridge")
    fig.update_layout(height=380)
    st.plotly_chart(fig, width="stretch")
    return result


def page_spreads(prices: pd.DataFrame, forward_curves: pd.DataFrame) -> None:
    st.title("Spread Analysis")
    interpretation(
        "Commodity traders often express views through spreads rather than outright price. "
        "Spreads can reveal quality differences, logistics constraints, regional tightness, and storage incentives."
    )

    spread = brent_wti_spread(prices)
    ratio = crude_gas_ratio(prices)
    chart = pd.DataFrame({"Brent-WTI Spread": spread, "Brent / Natural Gas Ratio": ratio})
    chart.index.name = "Date"
    st.plotly_chart(px.line(chart.reset_index(), x="Date", y=chart.columns, title="Key Spread Indicators"), width="stretch")

    st.subheader("Spread Table")
    st.dataframe(spread_table(prices), width="stretch")

    commodity = st.selectbox("Forward curve", sorted(forward_curves["Commodity"].unique()))
    curve = curve_structure(forward_curves, commodity)
    cols = st.columns(2)
    cols[0].metric("Curve Structure", curve["structure"])
    cols[1].metric("Front vs Deferred", f"{curve['front_deferred_spread']:.2f}")
    interpretation(curve["interpretation"])
    st.plotly_chart(
        px.line(curve["curve"], x="Tenor", y="Price", markers=True, title=f"{commodity} Sample Forward Curve"),
        width="stretch",
    )


def page_scenarios(prices: pd.DataFrame, context: dict) -> dict:
    st.title("Scenario Analysis")
    scenario_name = st.selectbox("Scenario", list(SCENARIOS), key="selected_scenario")
    latest = prices.ffill().iloc[-1]

    result = apply_scenario(
        scenario_name,
        context["balance_inputs"],
        float(latest["Brent"]),
        context["forward_price"],
        0.70,
        0.06,
        0.003,
        500_000,
    )

    interpretation(result["description"])
    cols = st.columns(4)
    cols[0].metric("Scenario Regime", result["balance"]["market_regime"])
    cols[1].metric("Price Pressure", result["balance"]["price_pressure"])
    with cols[2]:
        status_panel(
            "Storage Signal",
            result["storage"]["signal"],
            storage_signal_explanation(result["storage"]["signal"]),
        )
    cols[3].metric("Carry Return", f"{result['storage']['carry_return']:.2f}")

    decision = pd.DataFrame(
        [
            {"Area": "Balance", "Impact": result["balance"]["surplus_deficit"], "Decision Read": result["balance"]["interpretation"]},
            {"Area": "Storage", "Impact": result["storage"]["carry_return"], "Decision Read": result["storage"]["recommendation"]},
            {"Area": "Commercial Action", "Impact": "", "Decision Read": result["commercial_action"]},
        ]
    )
    st.dataframe(decision, width="stretch")

    notionals = {asset: 1_000_000 for asset in result["risk_shock"]}
    stress = stress_loss(latest, result["risk_shock"], notionals)
    st.subheader("Stress Loss / Gain Approximation")
    st.dataframe(stress, width="stretch")
    return result


def page_risk(prices: pd.DataFrame, scenario: dict, active_range: str) -> None:
    st.title("Risk Analytics")
    st.caption(f"Active data range: {active_range}")
    interpretation(
        "Risk analytics translate price history into volatility, drawdown, correlation, VaR, and stress loss. "
        "These are simplified desk-style diagnostics, not full risk system outputs."
    )

    notional = st.number_input(
        "Position size for risk estimate",
        10_000.0,
        25_000_000.0,
        1_000_000.0,
        50_000.0,
        help="Used to translate the historical 95% one-day VaR percentage into an estimated monetary loss.",
    )
    returns = daily_returns(prices)
    summary = risk_summary(prices, notional=notional)
    st.dataframe(summary, width="stretch")

    left, right = st.columns(2)
    with left:
        corr = returns.corr()
        fig = px.imshow(corr, text_auto=".2f", title="Return Correlation Matrix", aspect="auto")
        fig.update_layout(height=500)
        st.plotly_chart(fig, width="stretch")
    with right:
        dd = drawdown(prices[["Brent", "WTI", "Natural Gas", "Carbon"]])
        dd.index.name = "Date"
        st.plotly_chart(px.line(dd.reset_index(), x="Date", y=dd.columns, title="Drawdown"), width="stretch")

    st.subheader("Selected Scenario Stress")
    latest = prices.ffill().iloc[-1]
    notionals = {asset: notional for asset in scenario["risk_shock"]}
    st.dataframe(stress_loss(latest, scenario["risk_shock"], notionals), width="stretch")


def page_assistant(prices: pd.DataFrame, context: dict) -> None:
    st.title("Trading & Supply Assistant")
    interpretation(
        "Generates a structured market note from the platform outputs without requiring an external API."
    )
    risk_table = risk_summary(prices)
    note = generate_market_note(context["snapshot"], context["balance"], context["storage"], risk_table, context["scenario"])
    st.text_area("Generated market note", note, height=560)


def page_report(prices: pd.DataFrame, context: dict, active_range: str) -> None:
    st.title("Report Summary")
    risk_table = risk_summary(prices)
    correlation = daily_returns(prices).corr()
    report = build_report_markdown(
        context["snapshot"],
        context["balance"],
        context["storage"],
        context["scenario"],
        risk_table,
        correlation,
        active_range,
    )
    st.markdown(report)
    st.download_button(
        "Download report",
        report,
        file_name="energy_trading_supply_report.md",
        mime="text/markdown",
    )


def initialise_session_state() -> None:
    today = date.today()
    if "active_start_date" not in st.session_state:
        st.session_state.active_start_date = today - timedelta(days=180)
    if "active_end_date" not in st.session_state:
        st.session_state.active_end_date = today
    if "prefer_live_data" not in st.session_state:
        st.session_state.prefer_live_data = True
    if "selected_scenario" not in st.session_state:
        st.session_state.selected_scenario = "Base case"


def sidebar_market_controls() -> tuple[bool, date, date]:
    st.sidebar.subheader("Market data")
    with st.sidebar.form("market_data_form"):
        start_date = st.date_input(
            "Start date",
            value=st.session_state.active_start_date,
            max_value=date.today(),
        )
        end_date = st.date_input(
            "End date",
            value=st.session_state.active_end_date,
            max_value=date.today(),
        )
        prefer_live = st.toggle(
            "Use live public data where available",
            value=st.session_state.prefer_live_data,
        )
        submitted = st.form_submit_button("Load market data", type="primary", width="stretch")

    if submitted:
        if start_date >= end_date:
            st.sidebar.error("Start date must be before end date.")
        elif end_date > date.today():
            st.sidebar.error("End date cannot be in the future.")
        else:
            st.session_state.active_start_date = start_date
            st.session_state.active_end_date = end_date
            st.session_state.prefer_live_data = prefer_live

    active_start = st.session_state.active_start_date
    active_end = st.session_state.active_end_date
    active_live = st.session_state.prefer_live_data
    st.sidebar.caption(f"Active range: {active_start:%d %b %Y} to {active_end:%d %b %Y}")
    return active_live, active_start, active_end


def main() -> None:
    configure_page()
    inject_css()
    initialise_session_state()

    st.sidebar.title("Navigation")
    prefer_live, start_date, end_date = sidebar_market_controls()
    bundle = get_market_bundle(prefer_live, start_date, end_date)
    prices = bundle.prices
    forward_curves = get_forward_curves()
    context = default_context(prices, forward_curves)
    context["scenario"] = apply_scenario(
        st.session_state.selected_scenario,
        context["balance_inputs"],
        float(context["latest"]["Brent"]),
        context["forward_price"],
        0.70,
        0.06,
        0.003,
        500_000,
    )
    active_range = f"{start_date:%d %b %Y} to {end_date:%d %b %Y}"

    page = st.sidebar.radio(
        "Module",
        [
            "Dashboard",
            "Market Data",
            "Supply-Demand Balance",
            "Storage Optimisation",
            "Spread Analysis",
            "Scenario Analysis",
            "Risk Analytics",
            "Trading & Supply Assistant",
            "Report Summary",
        ],
    )

    st.sidebar.caption("Commodity market analytics across supply, storage, risk, and scenarios.")

    if prefer_live and bundle.is_fallback:
        st.warning("Live market data unavailable; using sample data for demonstration.")

    if page == "Dashboard":
        page_dashboard(prices, context, bundle.source, active_range)
    elif page == "Market Data":
        page_market_data(prices, bundle.source, bundle.tickers, active_range)
    elif page == "Supply-Demand Balance":
        page_supply_demand()
    elif page == "Storage Optimisation":
        page_storage(context["latest"], context["forward_price"])
    elif page == "Spread Analysis":
        page_spreads(prices, forward_curves)
    elif page == "Scenario Analysis":
        page_scenarios(prices, context)
    elif page == "Risk Analytics":
        page_risk(prices, context["scenario"], active_range)
    elif page == "Trading & Supply Assistant":
        page_assistant(prices, context)
    elif page == "Report Summary":
        page_report(prices, context, active_range)


if __name__ == "__main__":
    main()
