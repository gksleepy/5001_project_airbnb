import pandas as pd
import plotly.express as px
import streamlit as st

from airbnb_utils import (
    ACCENT,
    BRAND,
    amenity_impact,
    clean_plotly,
    configure_page,
    hero,
    load_airbnb_data,
    safe_df,
    sidebar_filters,
)

configure_page("Market Analytics")

df = load_airbnb_data()
filtered = safe_df(sidebar_filters(df, key_prefix="analytics"))

hero(
    "Market Analytics",
    "Understand room-type economics, what separates superhosts from the rest, and which amenities travel with premium pricing.",
)

# ─── KPI strip ────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)

reviewed   = filtered.dropna(subset=["review_rating"])
superhost_n = filtered["is_superhost"].sum()
superhost_pct = superhost_n / len(filtered) * 100 if len(filtered) else 0
avg_review  = reviewed["review_rating"].mean()
avg_sh      = reviewed[reviewed["is_superhost"] == True]["review_rating"].mean()
avg_reg     = reviewed[reviewed["is_superhost"] == False]["review_rating"].mean()
review_gap  = avg_sh - avg_reg if (avg_sh == avg_sh and avg_reg == avg_reg) else None

room_types_n = filtered["room_type"].nunique()
markets_n    = filtered["market"].nunique()

k1.metric("Listings (filtered)",  f"{len(filtered):,}",
          delta=f"{markets_n} markets", delta_color="off")
k2.metric("Superhost rate",        f"{superhost_pct:.0f}%",
          delta=f"{superhost_n:,} hosts", delta_color="off")
k3.metric("Avg review score",      f"{avg_review:.1f}" if avg_review == avg_review else "—",
          delta="out of 100", delta_color="off")
k4.metric("Superhost vs regular",  f"+{review_gap:.1f} pts" if review_gap else "—",
          delta="score gap", delta_color="off",
          help="Average review score gap: superhost minus regular host")
k5.metric("Room types",            f"{room_types_n}",
          delta="in selection", delta_color="off")

st.divider()

# ─── Row 1: Box plot only (removed redundant grouped bar) ─────────────────────
# Box plot already shows median, IQR, and outliers — the grouped bar added
# nothing new, so we replaced it with a superhost score comparison bar
# that actually tells a different story.

left, right = st.columns([1.25, 1])

with left:
    st.markdown('<div class="section-card"><h3>Price distribution by room type</h3>', unsafe_allow_html=True)
    st.caption("Median line, IQR box, whiskers, and outlier dots. Outliers above $800 are hidden for readability.")

    # Cap Y-axis so the bulk of the distribution is visible
    box_df = filtered[filtered["price"] <= 800].copy()

    fig_box = px.box(
        box_df,
        x="room_type",
        y="price",
        color="room_type",
        points="outliers",
        color_discrete_sequence=[BRAND, ACCENT, "#f7a91e", "#3b8fd9"],
        labels={"price": "Price / night", "room_type": ""},
    )
    fig_box.update_layout(showlegend=False, xaxis_title="", yaxis_title="Price / night")
    st.plotly_chart(clean_plotly(fig_box, 400), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="section-card"><h3>Superhost vs regular — review scores</h3>', unsafe_allow_html=True)
    st.caption("Average score per review dimension. Only listings with ≥ 3 reviews included.")

    # Build comparison across review sub-scores
    sub_cols = {
        "review_cleanliness":    "Cleanliness",
        "review_communication":  "Communication",
        "review_value":          "Value",
        "review_rating":         "Overall",
    }

    rows = []
    for col, label in sub_cols.items():
        if col not in filtered.columns:
            continue
        sub = filtered[filtered["number_of_reviews"] >= 3].dropna(subset=[col])
        for is_sh, group_label in [(True, "Superhost"), (False, "Regular")]:
            avg = sub[sub["is_superhost"] == is_sh][col].mean()
            if avg == avg:          # skip NaN
                rows.append({"dimension": label, "group": group_label, "score": avg})

    if rows:
        comp_df = pd.DataFrame(rows)
        fig_comp = px.bar(
            comp_df,
            x="score",
            y="dimension",
            color="group",
            barmode="group",
            orientation="h",
            text="score",
            color_discrete_map={"Superhost": BRAND, "Regular": ACCENT},
            labels={"score": "Avg score", "dimension": "", "group": ""},
        )
        fig_comp.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig_comp.update_layout(
            xaxis=dict(range=[0, 11], showgrid=False, title="Avg score (0–10)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(r=40),
        )
        st.plotly_chart(clean_plotly(fig_comp, 400), use_container_width=True)
    else:
        st.info("Sub-score columns not found in this dataset.")

    st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# ─── Row 2: Scatter + Amenities ───────────────────────────────────────────────
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown('<div class="section-card"><h3>Review score vs price</h3>', unsafe_allow_html=True)
    st.caption(
        "Each bubble = one listing. Size = number of reviews. "
        "Colour = superhost status. Prices above $800 hidden."
    )

    # Cap price AND require minimum reviews so scatter is readable
    scatter_df = (
        filtered
        .dropna(subset=["review_rating"])
        .query("price <= 800 and number_of_reviews >= 3")
        .copy()
    )

    if scatter_df.empty:
        st.info("No listings match the current filters with ≥ 3 reviews and price ≤ $800.")
    else:
        # Add median lines as reference
        med_price  = scatter_df["price"].median()
        med_review = scatter_df["review_rating"].median()

        fig_scatter = px.scatter(
            scatter_df,
            x="review_rating",
            y="price",
            size="number_of_reviews",
            color="is_superhost",
            hover_name="name",
            hover_data=["market", "room_type", "accommodates"],
            color_discrete_map={True: BRAND, False: ACCENT},
            labels={
                "review_rating": "Review score",
                "price":         "Price / night",
                "is_superhost":  "Superhost",
            },
            size_max=20,
        )
        # Quadrant reference lines
        fig_scatter.add_hline(y=med_price,  line_dash="dot", line_color="gray", opacity=0.5,
                              annotation_text=f"Median ${med_price:.0f}", annotation_position="right")
        fig_scatter.add_vline(x=med_review, line_dash="dot", line_color="gray", opacity=0.5,
                              annotation_text=f"Median {med_review:.0f}", annotation_position="top")
        fig_scatter.update_layout(legend_title="Superhost")
        st.plotly_chart(clean_plotly(fig_scatter, 420), use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown('<div class="section-card"><h3>Amenities — price premium</h3>', unsafe_allow_html=True)
    st.caption("Price premium = median price of listings with this amenity minus overall market median.")

    premium = amenity_impact(filtered, limit=12)
    if premium.empty:
        st.info("Not enough amenity coverage for this filter.")
    else:
        fig_am = px.bar(
            premium.sort_values("premium_vs_median"),
            x="premium_vs_median",
            y="amenity",
            orientation="h",
            color="median_price",
            text="premium_vs_median",
            hover_data={"listings": True, "median_price": ":$,.0f", "avg_price": ":$,.0f"},
            color_continuous_scale=["#00a699", "#f7c05a", "#ff385c"],
            labels={"premium_vs_median": "Price premium vs market median", "amenity": ""},
        )
        fig_am.update_traces(texttemplate="$%{text:.0f}", textposition="outside")
        fig_am.update_layout(
            coloraxis_colorbar_title="Median $",
            xaxis_title="Price premium vs market median ($)",
            margin=dict(r=50),
        )
        st.plotly_chart(clean_plotly(fig_am, 420), use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# ─── Row 3: Performers table ──────────────────────────────────────────────────
st.markdown('<div class="section-card"><h3>Top & bottom performers</h3>', unsafe_allow_html=True)
st.caption(
    "**Revenue signal** = price × (review score ÷ 100) × review-volume factor.  "
    "Combines price, quality, and popularity into one comparable number.  "
    "Only listings with ≥ 5 reviews are included."
)

ranked = (
    filtered
    .dropna(subset=["review_rating"])
    .query("number_of_reviews >= 5")
    .copy()
)

if ranked.empty:
    st.info("No listings with ≥ 5 reviews match the current filters.")
else:
    ranked["revenue_signal"] = (
        ranked["price"]
        * (ranked["review_rating"] / 100)
        * (1 + ranked["number_of_reviews"].clip(0, 100) / 100)
    )

    display_cols = [
        "name", "market", "room_type", "price",
        "review_rating", "number_of_reviews", "is_superhost", "revenue_signal",
    ]

    top_df    = (ranked.sort_values("revenue_signal", ascending=False)[display_cols]
                 .head(10).assign(group="⭐ Top revenue signal"))
    bottom_df = (ranked.sort_values(["review_rating", "number_of_reviews"], ascending=[True, False])[display_cols]
                 .head(10).assign(group="⚠️ Review risk"))

    combined = pd.concat([top_df, bottom_df], ignore_index=True)

    # Tab view — cleaner than one mixed table
    tab_top, tab_bot = st.tabs(["⭐ Top revenue signal", "⚠️ Review risk"])

    with tab_top:
        st.dataframe(
            top_df[display_cols]
            .style.format({"price": "${:,.0f}", "review_rating": "{:,.0f}", "revenue_signal": "{:,.1f}"})
            .bar(subset=["revenue_signal"], color=BRAND, vmin=0),
            use_container_width=True,
            hide_index=True,
        )

    with tab_bot:
        st.dataframe(
            bottom_df[display_cols]
            .style.format({"price": "${:,.0f}", "review_rating": "{:,.0f}", "revenue_signal": "{:,.1f}"})
            .bar(subset=["review_rating"], color="#f7a91e", vmin=0),
            use_container_width=True,
            hide_index=True,
        )

st.markdown("</div>", unsafe_allow_html=True)
