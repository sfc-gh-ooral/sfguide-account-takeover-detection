import streamlit as st

import common
import detection

ctx = common.context()
scored = ctx["scored"]
threshold = st.session_state.get("threshold", detection.DEFAULT_THRESHOLD)

st.title("Rule performance")
st.caption("How each rule performs against the synthetic ground-truth labels, which stand in for closed "
           "investigations. Use it to tune weights and the alert threshold.")

perf = detection.rule_performance(scored, threshold, ctx["total_ato"])
last = perf.iloc[-1]
with st.container(horizontal=True):
    st.metric("Confirmed takeovers in the data", ctx["total_ato"], border=True)
    st.metric(f"Caught by alerts (score {threshold}+)", int(last["Confirmed takeovers"]), border=True)
    st.metric("Alert precision", f"{last['Precision']:.0%}" if last["Precision"] is not None else "n/a", border=True)
    st.metric("False alerts", int(last["False positives"]), border=True)

with st.container(border=True):
    st.subheader("By rule")
    st.dataframe(perf, hide_index=True, alt="Customers flagged, confirmed takeovers, false positives, precision and recall per rule",
                 column_config={"Precision": st.column_config.NumberColumn(format="percent"),
                                "Recall": st.column_config.NumberColumn(format="percent")})
    st.caption("Precision: share of flagged customers that were takeovers. Recall: share of all takeovers the rule flagged. "
               "Results are for this synthetic data set only.")

with st.container(border=True):
    st.subheader("Precision and recall by alert threshold")
    rows = []
    for t in range(10, 155, 5):
        a = scored[scored["alert_score"] >= t]
        tp = int(a["confirmed_ato"].sum())
        rows += [{"Threshold": t, "Measure": "Precision", "Value": tp / len(a) if len(a) else None},
                 {"Threshold": t, "Measure": "Recall", "Value": tp / ctx["total_ato"]}]
    st.line_chart(rows, x="Threshold", y="Value", color="Measure", x_label="Alert threshold (score)", y_label="",
                  alt="Alert precision and recall at each threshold")

with st.container(border=True):
    st.subheader("Where the false positives come from")
    st.markdown(
        "- **Takeover sequence** also fires for customers who change their phone and pay a new contractor the same day.\n"
        "- **Impossible travel** fires for corporate VPNs, and when a traveller logs in again after landing.\n"
        "- **New device + country** fires for travellers who buy a local phone.\n"
        "- **Unusual amount** fires for one-off large purchases.\n\n"
        "No single rule is enough; the score rewards combinations, such as a credential change followed by a "
        "new payee from a new device abroad."
    )
