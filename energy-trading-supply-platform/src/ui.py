from __future__ import annotations

from html import escape

import streamlit as st


def configure_page() -> None:
    st.set_page_config(
        page_title="Energy Trading & Supply Analytics Platform",
        page_icon="ET",
        layout="wide",
    )


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.5rem; padding-bottom: 3rem;}
        h1, h2, h3 {letter-spacing: 0; color: var(--text-color);}
        p, li, label, [data-testid="stCaptionContainer"] {color: var(--text-color);}
        [data-testid="stMetric"] {
            background: var(--secondary-background-color);
            border: 1px solid color-mix(in srgb, var(--text-color) 14%, transparent);
            border-radius: 8px;
            padding: 14px 16px;
            min-height: 6.75rem;
            height: auto;
            overflow: visible;
            box-shadow: 0 1px 2px color-mix(in srgb, var(--text-color) 7%, transparent);
        }
        [data-testid="stMetric"] * {color: var(--text-color) !important;}
        [data-testid="stMetricValue"] {
            overflow: visible;
            min-height: 2.6rem;
        }
        [data-testid="stMetricValue"] > div {
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
            overflow-wrap: anywhere;
            line-height: 1.2;
        }
        .interpretation {
            border: 1px solid color-mix(in srgb, var(--primary-color) 38%, transparent);
            background: color-mix(in srgb, var(--primary-color) 9%, var(--background-color));
            padding: 12px 14px;
            border-radius: 6px;
            color: var(--text-color);
            margin: 8px 0 18px;
            line-height: 1.55;
            overflow: visible;
        }
        .status-panel {
            background: var(--secondary-background-color);
            border: 1px solid color-mix(in srgb, var(--text-color) 14%, transparent);
            border-radius: 8px;
            padding: 14px 16px;
            min-height: 9.25rem;
            height: auto;
            color: var(--text-color);
            overflow: visible;
        }
        .status-label {
            color: color-mix(in srgb, var(--text-color) 72%, transparent);
            font-size: 0.88rem;
            margin-bottom: 0.35rem;
        }
        .status-value {
            color: var(--text-color);
            font-size: 1.35rem;
            font-weight: 650;
            line-height: 1.2;
            overflow-wrap: anywhere;
            white-space: normal;
        }
        .status-comment {
            color: color-mix(in srgb, var(--text-color) 78%, transparent);
            font-size: 0.84rem;
            line-height: 1.4;
            margin-top: 0.6rem;
            overflow-wrap: anywhere;
            white-space: normal;
        }
        [data-testid="stDataFrame"] {color: var(--text-color);}
        </style>
        """,
        unsafe_allow_html=True,
    )


def interpretation(text: str) -> None:
    st.markdown(f"<div class='interpretation'>{escape(text)}</div>", unsafe_allow_html=True)


def status_panel(label: str, value: str, comment: str) -> None:
    st.markdown(
        (
            "<div class='status-panel'>"
            f"<div class='status-label'>{escape(label)}</div>"
            f"<div class='status-value'>{escape(value)}</div>"
            f"<div class='status-comment'>{escape(comment)}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def money(value: float) -> str:
    return f"{value:,.2f}"
