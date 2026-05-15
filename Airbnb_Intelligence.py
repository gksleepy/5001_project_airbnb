import streamlit as st


st.set_page_config(
    page_title="Airbnb Intelligence",
    layout="wide",
)

pages = [
    st.Page(
        "pages/1_Price_Map_v3.py",
        title="Airbnb Price Map",
        default=True,
    ),
    st.Page(
        "pages/2_Market_Analytics_v3.py",
        title="Airbnb Market Analytics",
    ),
]

navigation = st.navigation(pages)
navigation.run()
