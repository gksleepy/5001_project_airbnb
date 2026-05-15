import plotly.express as px
import streamlit as st

from airbnb_utils import (
    ACCENT,
    BRAND,
    clean_plotly,
    configure_page,
    hero,
    load_airbnb_data,
    price_map,
    safe_df,
    sidebar_filters,
)

configure_page("Price Map")

df = load_airbnb_data()
filtered = safe_df(sidebar_filters(df, key_prefix="map"))

hero(
    "Price Map",
    "Explore where high-value listings cluster and how price, capacity, and review quality shape each market.",
)

# ─── KPI strip ────────────────────────────────────────────────────────────────
# Quick snapshot at the top so users know the scale of the filtered data
# before reading any chart.
k1, k2, k3, k4, k5 = st.columns(5)

avg_price   = filtered["price"].mean()
median_price = filtered["price"].median()
avg_review  = filtered["review_rating"].dropna().mean()
total       = len(filtered)
markets     = filtered["market"].nunique()

k1.metric("Listings",        f"{total:,}")
k2.metric("Markets",         f"{markets}")
k3.metric("Avg price/night", f"${avg_price:,.0f}")
k4.metric("Median price",    f"${median_price:,.0f}")
k5.metric("Avg review score",f"{avg_review:.1f}" if avg_review == avg_review else "—")

st.divider()

# ─── Row 1: Map  +  Price distribution ────────────────────────────────────────
top_left, top_right = st.columns([1.7, 1])

with top_left:
    st.markdown('<div class="section-card"><h3>Listing locations — price & capacity</h3>', unsafe_allow_html=True)
    st.caption("Colour = nightly price (low → high).  Bubble size = number of guests accommodated.")
    st.plotly_chart(price_map(filtered, height=520), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with top_right:
    # Cap price at 95th-percentile so outliers don't flatten the histogram.
    p95 = filtered["price"].quantile(0.95)
    hist_df = filtered[filtered["price"] <= p95].copy()

    st.markdown('<div class="section-card"><h3>Price distribution by room type</h3>', unsafe_allow_html=True)
    st.caption(f"Prices above ${p95:,.0f}/night (top 5 %) are excluded to keep the view readable.")

    fig_hist = px.histogram(
        hist_df,
        x="price",
        color="room_type",
        nbins=40,
        marginal="box",          # box plot on top still shows full range feel
        color_discrete_sequence=[BRAND, ACCENT, "#f7a91e", "#3b8fd9"],
        labels={"price": "Price / night", "count": "Listings"},
    )
    fig_hist.update_layout(
        xaxis_title="Price / night",
        yaxis_title="Listings",
        legend_title="Room type",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(clean_plotly(fig_hist, 330), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Avg price by market (replaces Treemap) ────────────────────────────────
    # Horizontal bar is easier to read than a treemap for a ranked list.
    st.markdown('<div class="section-card"><h3>Avg price by market</h3>', unsafe_allow_html=True)
    st.caption("Top 10 markets ranked by average nightly price.")

    mkt = (
        filtered.groupby("market", as_index=False)["price"]
        .agg(avg_price="mean", listings="count")
        .sort_values("avg_price", ascending=True)
        .tail(10)                # keep top-10 after sorting ascending → tail
    )
    fig_bar = px.bar(
        mkt,
        x="avg_price",
        y="market",
        orientation="h",
        color="avg_price",
        color_continuous_scale=[ACCENT, BRAND],
        text="avg_price",
        hover_data={"listings": True, "avg_price": ":$,.0f"},
        labels={"avg_price": "Avg price ($/night)", "market": ""},
    )
    fig_bar.update_traces(texttemplate="$%{text:.0f}", textposition="outside")
    fig_bar.update_layout(
        coloraxis_showscale=False,
        xaxis=dict(showgrid=False, title=""),
        margin=dict(r=50),
    )
    st.plotly_chart(clean_plotly(fig_bar, 270), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# ─── Row 2: Best-value listings table ─────────────────────────────────────────
# Filter to listings with ≥ 5 reviews so value_index is statistically meaningful.
st.markdown('<div class="section-card"><h3>Best-value listings</h3>', unsafe_allow_html=True)
st.caption(
    "**Value index** = (review score ÷ price) × 100.  "
    "Higher = more quality per dollar.  "
    "Only listings with **≥ 5 reviews** are shown to avoid unreliable scores."
)

value = filtered[filtered["number_of_reviews"] >= 5].copy()

if value.empty:
    st.info("No listings match the current filters with ≥ 5 reviews. Try relaxing the filters.")
else:
    value["value_index"] = (
        value["review_rating"].fillna(value["review_rating"].median()) / value["price"]
    ) * 100

    cols = [
        "name", "market", "room_type", "price",
        "review_rating", "number_of_reviews", "accommodates", "value_index",
    ]

    st.dataframe(
        value.sort_values(["value_index", "number_of_reviews"], ascending=[False, False])[cols]
        .head(25)
        .style.format(
            {
                "price":          "${:,.0f}",
                "review_rating":  "{:,.0f}",
                "value_index":    "{:,.1f}",
            }
        )
        .bar(subset=["value_index"], color="#ff385c", vmin=0),
        use_container_width=True,
        hide_index=True,
    )

st.markdown("</div>", unsafe_allow_html=True)
