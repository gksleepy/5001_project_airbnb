from __future__ import annotations

from decimal import Decimal
from typing import Iterable

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from bson.decimal128 import Decimal128
from pymongo import MongoClient


BRAND = "#ff385c"
ACCENT = "#00a699"
INK = "#222222"
MUTED = "#717171"
PANEL = "#ffffff"
BG = "#f7f7f5"


def configure_page(title: str) -> None:
    st.set_page_config(page_title=title, page_icon=":house:", layout="wide")
    st.markdown(
        f"""
        <style>
        :root {{
            --brand: {BRAND};
            --accent: {ACCENT};
            --ink: {INK};
            --muted: {MUTED};
            --panel: {PANEL};
            --bg: {BG};
        }}
        .stApp {{ background: var(--bg); color: var(--ink); }}
        [data-testid="stSidebar"] {{
            background: #ffffff;
            border-right: 1px solid #e6e2dc;
        }}
        [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
            color: var(--ink);
            letter-spacing: 0;
        }}
        .block-container {{ padding-top: 1.3rem; max-width: 1480px; }}
        .hero {{
            border: 1px solid #e8e4de;
            background: #ffffff;
            border-radius: 8px;
            padding: 18px 20px;
            margin-bottom: 14px;
        }}
        .hero h1 {{ font-size: 2rem; margin: 0 0 0.2rem 0; letter-spacing: 0; }}
        .hero p {{ color: var(--muted); margin: 0; }}
        .brand-eyebrow {{
            color: var(--brand);
            font-size: 0.82rem;
            font-weight: 800;
            letter-spacing: 0;
            text-transform: uppercase;
            margin-bottom: 8px;
        }}
        .status-pill {{
            display: inline-flex;
            gap: 8px;
            align-items: center;
            padding: 6px 10px;
            border: 1px solid #ddd8d1;
            border-radius: 999px;
            background: #fbfaf8;
            font-size: 0.86rem;
            color: var(--muted);
        }}
        .dot {{
            width: 8px;
            height: 8px;
            border-radius: 999px;
            background: var(--accent);
            display: inline-block;
        }}
        .kpi-card {{
            border: 1px solid #e5e1db;
            background: #ffffff;
            border-radius: 8px;
            padding: 15px 16px;
            min-height: 116px;
        }}
        .kpi-label {{
            color: var(--muted);
            font-weight: 700;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0;
        }}
        .kpi-value {{
            font-size: 1.9rem;
            font-weight: 800;
            line-height: 1.1;
            margin-top: 6px;
        }}
        .kpi-note {{ color: var(--muted); font-size: 0.9rem; margin-top: 5px; }}
        .section-card {{
            border: 1px solid #e5e1db;
            background: #ffffff;
            border-radius: 8px;
            padding: 14px;
            margin-bottom: 14px;
        }}
        .section-card h3 {{ margin: 0 0 10px 0; font-size: 1.05rem; letter-spacing: 0; }}
        div[data-testid="stMetric"] {{
            border: 1px solid #e5e1db;
            background: #ffffff;
            border-radius: 8px;
            padding: 12px 14px;
        }}
        .stButton>button {{
            border-radius: 8px;
            border: 1px solid #d9d3ca;
            background: #ffffff;
            color: var(--ink);
        }}
        .stButton>button:hover {{
            border-color: var(--brand);
            color: var(--brand);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str, right: str = "MongoDB Atlas") -> None:
    left, spacer, status = st.columns([4.5, 1, 1.4])
    with left:
        st.markdown(
            f"""
            <div class="hero">
                <div class="brand-eyebrow">Airbnb Intelligence</div>
                <h1>{title}</h1>
                <p>{subtitle}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with spacer:
        st.empty()
    with status:
        st.markdown(
            f"""
            <div class="hero" style="text-align:center;">
                <span class="status-pill"><span class="dot"></span>{right}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


@st.cache_resource(show_spinner=False)
def get_collection():
    uri = st.secrets.get("mongo", {}).get("uri")
    if not uri:
        st.error("Missing MongoDB URI. Add [mongo].uri to .streamlit/secrets.toml or Streamlit Cloud secrets.")
        st.stop()

    db_name = st.secrets.get("mongo", {}).get("db_name", "sample_airbnb")
    collection_name = st.secrets.get("mongo", {}).get("collection_name", "listingsAndReviews")
    client = MongoClient(uri, serverSelectionTimeoutMS=15000)
    return client[db_name][collection_name]


def to_float(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal128):
        return float(value.to_decimal())
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def first_number(values: Iterable, default=None):
    for value in values:
        converted = to_float(value)
        if converted is not None:
            return converted
    return default


@st.cache_data(ttl=3600, show_spinner="Loading Airbnb listings from MongoDB...")
def load_airbnb_data(limit: int = 6000) -> pd.DataFrame:
    projection = {
        "_id": 1,
        "name": 1,
        "summary": 1,
        "property_type": 1,
        "room_type": 1,
        "price": 1,
        "weekly_price": 1,
        "monthly_price": 1,
        "security_deposit": 1,
        "cleaning_fee": 1,
        "accommodates": 1,
        "bedrooms": 1,
        "beds": 1,
        "bathrooms": 1,
        "number_of_reviews": 1,
        "amenities": 1,
        "host.host_is_superhost": 1,
        "host.host_identity_verified": 1,
        "host.host_response_rate": 1,
        "address.market": 1,
        "address.country": 1,
        "address.country_code": 1,
        "address.location.coordinates": 1,
        "review_scores": 1,
    }
    rows = []
    for doc in get_collection().find({}, projection, limit=limit):
        address = doc.get("address", {}) or {}
        location = address.get("location", {}) or {}
        coordinates = location.get("coordinates", [None, None]) or [None, None]
        host = doc.get("host", {}) or {}
        reviews = doc.get("review_scores", {}) or {}
        amenities = doc.get("amenities", []) or []
        rows.append(
            {
                "id": str(doc.get("_id", "")),
                "name": doc.get("name") or "Untitled listing",
                "summary": doc.get("summary") or "",
                "market": address.get("market") or "Unknown",
                "country": address.get("country") or "Unknown",
                "country_code": address.get("country_code") or "",
                "longitude": first_number([coordinates[0] if len(coordinates) > 0 else None]),
                "latitude": first_number([coordinates[1] if len(coordinates) > 1 else None]),
                "property_type": doc.get("property_type") or "Unknown",
                "room_type": doc.get("room_type") or "Unknown",
                "price": to_float(doc.get("price")),
                "weekly_price": to_float(doc.get("weekly_price")),
                "monthly_price": to_float(doc.get("monthly_price")),
                "security_deposit": to_float(doc.get("security_deposit")),
                "cleaning_fee": to_float(doc.get("cleaning_fee")),
                "accommodates": first_number([doc.get("accommodates")], 0),
                "bedrooms": first_number([doc.get("bedrooms")], 0),
                "beds": first_number([doc.get("beds")], 0),
                "bathrooms": first_number([doc.get("bathrooms")], 0),
                "number_of_reviews": first_number([doc.get("number_of_reviews")], 0),
                "is_superhost": bool(host.get("host_is_superhost")),
                "identity_verified": bool(host.get("host_identity_verified")),
                "host_response_rate": first_number([host.get("host_response_rate")]),
                "review_rating": first_number([reviews.get("review_scores_rating")]),
                "review_accuracy": first_number([reviews.get("review_scores_accuracy")]),
                "review_cleanliness": first_number([reviews.get("review_scores_cleanliness")]),
                "review_checkin": first_number([reviews.get("review_scores_checkin")]),
                "review_communication": first_number([reviews.get("review_scores_communication")]),
                "review_location": first_number([reviews.get("review_scores_location")]),
                "review_value": first_number([reviews.get("review_scores_value")]),
                "amenities": amenities,
                "amenities_count": len(amenities),
                "amenities_text": ", ".join(amenities[:18]),
            }
        )

    df = pd.DataFrame(rows)
    numeric_cols = [
        "price",
        "weekly_price",
        "monthly_price",
        "security_deposit",
        "cleaning_fee",
        "accommodates",
        "bedrooms",
        "beds",
        "bathrooms",
        "number_of_reviews",
        "latitude",
        "longitude",
        "host_response_rate",
        "review_rating",
        "review_accuracy",
        "review_cleanliness",
        "review_checkin",
        "review_communication",
        "review_location",
        "review_value",
        "amenities_count",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["price"])
    df = df[df["price"] > 0]
    return df


def sidebar_filters(df: pd.DataFrame, key_prefix: str = "global") -> pd.DataFrame:
    st.sidebar.markdown("## Airbnb Intelligence")
    st.sidebar.caption("Market filters")

    markets = sorted([m for m in df["market"].dropna().unique() if m != "Unknown"])
    default_markets = markets[:6] if markets else []
    selected_markets = st.sidebar.multiselect(
        "City / market",
        options=markets,
        default=default_markets,
        key=f"{key_prefix}_markets",
    )

    max_price = int(min(max(df["price"].quantile(0.98), 100), 2000))
    price_range = st.sidebar.slider(
        "Price / night",
        min_value=0,
        max_value=max_price,
        value=(0, min(400, max_price)),
        step=10,
        key=f"{key_prefix}_price",
    )

    room_types = sorted(df["room_type"].dropna().unique())
    selected_room_types = st.sidebar.multiselect(
        "Room type",
        options=room_types,
        default=room_types,
        key=f"{key_prefix}_room",
    )

    superhost_only = st.sidebar.checkbox("Superhost only", value=False, key=f"{key_prefix}_superhost")
    min_reviews = st.sidebar.slider("Minimum reviews", 0, int(df["number_of_reviews"].max()), 5, key=f"{key_prefix}_reviews")
    min_score = st.sidebar.slider("Minimum review score", 0, 100, 80, key=f"{key_prefix}_score")
    min_beds = st.sidebar.slider("Minimum beds", 0, int(max(df["beds"].max(), 1)), 0, key=f"{key_prefix}_beds")

    filtered = df.copy()
    if selected_markets:
        filtered = filtered[filtered["market"].isin(selected_markets)]
    if selected_room_types:
        filtered = filtered[filtered["room_type"].isin(selected_room_types)]
    filtered = filtered[(filtered["price"] >= price_range[0]) & (filtered["price"] <= price_range[1])]
    filtered = filtered[filtered["number_of_reviews"] >= min_reviews]
    filtered = filtered[(filtered["review_rating"].fillna(0) >= min_score) | (filtered["review_rating"].isna() & (min_score == 0))]
    filtered = filtered[filtered["beds"].fillna(0) >= min_beds]
    if superhost_only:
        filtered = filtered[filtered["is_superhost"]]

    st.sidebar.caption(f"{len(filtered):,} of {len(df):,} listings selected")
    return filtered


def kpi_card(label: str, value: str, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def clean_plotly(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=42, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=INK, family="Arial"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#eee9e2", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#eee9e2", zeroline=False)
    return fig


def safe_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        st.warning("No listings match the current filters. Try widening the sidebar filters.")
        st.stop()
    return df


def top_markets(df: pd.DataFrame, limit: int = 7) -> pd.DataFrame:
    return (
        df.groupby("market", as_index=False)
        .agg(listings=("id", "count"), avg_price=("price", "mean"), median_price=("price", "median"), avg_score=("review_rating", "mean"))
        .sort_values("listings", ascending=False)
        .head(limit)
    )


def amenity_impact(df: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    baseline = df["price"].median()
    exploded = df[["id", "price", "amenities"]].explode("amenities").dropna()
    if exploded.empty:
        return pd.DataFrame(columns=["amenity", "listings", "avg_price", "median_price", "premium_vs_median"])

    result = (
        exploded.groupby("amenities", as_index=False)
        .agg(listings=("id", "count"), avg_price=("price", "mean"), median_price=("price", "median"))
    )
    minimum = max(12, int(len(df) * 0.03))
    result = result[result["listings"] >= minimum]
    result["premium_vs_median"] = result["median_price"] - baseline
    return result.sort_values(["premium_vs_median", "listings"], ascending=[False, False]).head(limit).rename(columns={"amenities": "amenity"})


def market_snapshot(df: pd.DataFrame) -> dict:
    premium = amenity_impact(df, limit=5)
    markets = top_markets(df, limit=5)
    return {
        "listings": int(len(df)),
        "avg_price": round(df["price"].mean(), 2),
        "median_price": round(df["price"].median(), 2),
        "avg_review_rating": round(df["review_rating"].mean(), 2) if df["review_rating"].notna().any() else None,
        "superhost_rate": round(df["is_superhost"].mean() * 100, 1),
        "avg_capacity": round(df["accommodates"].mean(), 2),
        "top_markets": markets.to_dict(orient="records"),
        "premium_amenities": premium.to_dict(orient="records"),
    }


def openrouter_chat(messages: list[dict], model: str | None = None, temperature: float = 0.35) -> str:
    api_key = st.secrets.get("openrouter", {}).get("api_key")
    if not api_key:
        raise RuntimeError("Missing OpenRouter API key. Add [openrouter].api_key in Streamlit secrets.")

    selected_model = model or st.secrets.get("openrouter", {}).get("model", "openrouter/free")
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://streamlit.io",
            "X-Title": "Airbnb Intelligence Streamlit Dashboard",
        },
        json={
            "model": selected_model,
            "messages": messages,
            "temperature": temperature,
        },
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()
    return payload["choices"][0]["message"]["content"]


def price_map(df: pd.DataFrame, height: int = 440) -> go.Figure:
    map_df = df.dropna(subset=["latitude", "longitude"]).copy()
    map_df["display_price"] = map_df["price"].clip(upper=map_df["price"].quantile(0.97))
    fig = px.scatter_map(
        map_df,
        lat="latitude",
        lon="longitude",
        color="display_price",
        size="accommodates",
        hover_name="name",
        hover_data={
            "market": True,
            "room_type": True,
            "price": ":$,.0f",
            "review_rating": ":.0f",
            "display_price": False,
            "latitude": False,
            "longitude": False,
        },
        color_continuous_scale=["#00a699", "#f7c05a", "#ff385c"],
        size_max=22,
        zoom=1,
        height=height,
    )
    fig.update_layout(map_style="carto-positron", margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)")
    return fig


def market_price_bar(df: pd.DataFrame) -> go.Figure:
    data = top_markets(df, limit=10).sort_values("avg_price")
    fig = px.bar(data, x="avg_price", y="market", orientation="h", text="avg_price", color="avg_price", color_continuous_scale=["#00a699", "#f7c05a", "#ff385c"])
    fig.update_traces(texttemplate="$%{text:.0f}", textposition="outside", marker_line_width=0)
    fig.update_layout(coloraxis_showscale=False, xaxis_title="Avg price / night", yaxis_title="")
    return clean_plotly(fig, 360)
