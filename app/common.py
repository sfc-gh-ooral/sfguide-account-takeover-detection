"""Shared data context for all pages."""

import os

import streamlit as st

import data_sources as ds
import detection

SAMPLE, LIVE = "Sample data", "Snowflake"


@st.cache_data(ttl="1h", show_spinner="Loading sample data")
def _sample():
    return detection.prepare(ds.sample_frames())


@st.cache_data(ttl="15m", show_spinner="Querying Snowflake")
def _live():
    return detection.prepare(ds.live_frames())


@st.cache_data(ttl="1h", show_spinner="Running detection rules")
def _flags(source: str):
    return detection.evaluate(_live() if source == LIVE else _sample())


def default_mode() -> str:
    return LIVE if os.environ.get("ATO_MODE", "mock").lower() == "live" else SAMPLE


def weights() -> dict:
    if "weights" not in st.session_state:
        st.session_state.weights = dict(detection.DEFAULT_WEIGHTS)
    # Widgets on the alert page write to w_<rule>; read them first so every page scores with current values.
    for key in detection.DEFAULT_WEIGHTS:
        if f"w_{key}" in st.session_state:
            st.session_state.weights[key] = int(st.session_state[f"w_{key}"])
    return st.session_state.weights


def context() -> dict:
    source = SAMPLE
    if st.session_state.get("mode") == LIVE:
        try:
            _flags(LIVE)
            source = LIVE
        except Exception as exc:
            st.session_state["live_error"] = str(exc)
    data = _live() if source == LIVE else _sample()
    scored = detection.score(_flags(source), weights())
    return {"live": source == LIVE, "data": data, "scored": scored,
            "total_ato": int(data["customers"]["confirmed_ato"].sum()),
            "default_weights": weights() == detection.DEFAULT_WEIGHTS}
