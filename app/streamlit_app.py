"""Streamlit app answering: how do delivery delays affect customer
review scores, broken down by product category and region?
Reads only from the dbt marts -- never touches raw/staging directly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from ingestion.load_raw import build_engine

st.set_page_config(page_title="Delivery Delays vs. Reviews", layout="wide")


@st.cache_data
def load_kpis() -> dict:
    query = """
        select
            count(*) as total_items,
            avg(case when is_late then 1.0 else 0.0 end) as late_rate,
            avg(review_score) as avg_review_score
        from marts.fct_order_items
        where is_late is not null
    """
    row = pd.read_sql(query, build_engine()).iloc[0]
    return {
        "total_items": int(row["total_items"]),
        "late_rate": float(row["late_rate"]),
        "avg_review_score": float(row["avg_review_score"]),
    }


@st.cache_data
def load_late_rate_by_category(top_n: int = 15) -> pd.DataFrame:
    query = """
        select
            dp.category_name_english as category,
            count(*) as total_items,
            avg(case when f.is_late then 1.0 else 0.0 end) as late_rate
        from marts.fct_order_items f
        join marts.dim_products dp on f.product_id = dp.product_id
        where f.is_late is not null
        group by dp.category_name_english
        order by total_items desc
        limit %(top_n)s
    """
    df = pd.read_sql(query, build_engine(), params={"top_n": top_n})
    return df.sort_values("late_rate", ascending=True)


@st.cache_data
def load_review_score_by_region() -> pd.DataFrame:
    query = """
        select
            dc.region,
            case when f.is_late then 'Late' else 'On time' end as delivery_status,
            avg(f.review_score) as avg_review_score
        from marts.fct_order_items f
        join marts.dim_customers dc on f.customer_id = dc.customer_id
        where f.is_late is not null and f.review_score is not null
        group by dc.region, f.is_late
        order by dc.region
    """
    return pd.read_sql(query, build_engine())


def plot_late_rate_by_category(df: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(df["category"], df["late_rate"] * 100, color="#c0392b")
    ax.set_xlabel("Late delivery rate (%)")
    ax.set_title("Late-delivery rate by product category (top 15 by volume)")
    fig.tight_layout()
    return fig


def plot_review_score_by_region(df: pd.DataFrame) -> plt.Figure:
    pivot = df.pivot(index="region", columns="delivery_status", values="avg_review_score")
    pivot = pivot[["On time", "Late"]]
    fig, ax = plt.subplots(figsize=(8, 6))
    pivot.plot(kind="bar", ax=ax, color=["#2e86ab", "#c0392b"])
    ax.set_ylabel("Average review score (1-5)")
    ax.set_xlabel("Customer region")
    ax.set_title("Average review score: on-time vs. late deliveries, by region")
    ax.legend(title=None)
    plt.xticks(rotation=0)
    fig.tight_layout()
    return fig


st.title("Delivery Delays vs. Customer Reviews")
st.caption(
    "How do delivery delays affect customer review scores, broken down by "
    "product category and region? Data: Olist Brazilian e-commerce dataset."
)

kpis = load_kpis()
col1, col2, col3 = st.columns(3)
col1.metric("Order items analyzed", f"{kpis['total_items']:,}")
col2.metric("Overall late-delivery rate", f"{kpis['late_rate']:.1%}")
col3.metric("Overall average review score", f"{kpis['avg_review_score']:.2f} / 5")

st.subheader("Late-delivery rate by product category")
st.pyplot(plot_late_rate_by_category(load_late_rate_by_category()))

st.subheader("Review score vs. delivery delay, by region")
st.pyplot(plot_review_score_by_region(load_review_score_by_region()))
