import streamlit as st

import common

st.set_page_config(page_title="Account Takeover Detection", page_icon=":material/shield_person:", layout="wide")

with st.sidebar:
    st.title(":material/shield_person: Account Takeover Detection")
    st.segmented_control("Data source", [common.SAMPLE, common.LIVE], default=common.default_mode(), key="mode",
                         help="Sample data runs with no Snowflake account. Snowflake mode reads the tables created by sql/.")
    ctx = common.context()
    if st.session_state.get("mode") == common.LIVE and not ctx["live"]:
        st.error(f"Snowflake mode is unavailable: {st.session_state.get('live_error', 'unknown error')}",
                 icon=":material/error:")
        st.caption("Showing sample data instead.")
    st.caption("Synthetic data. Illustrative rules, not production, fraud, security, or compliance advice. "
               "Not an official Snowflake product.")

st.navigation([
    st.Page("app_pages/alerts.py", title="Alert queue", icon=":material/notifications_active:", default=True),
    st.Page("app_pages/case.py", title="Case timeline", icon=":material/timeline:"),
    st.Page("app_pages/rules.py", title="Rule performance", icon=":material/rule:"),
]).run()
