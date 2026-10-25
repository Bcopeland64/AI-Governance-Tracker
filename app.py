from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import signal
from typing import Any

import streamlit as st

from tracker import CATEGORIES, SOURCES, fetch_updates


st.set_page_config(
    page_title="Global AI Governance Monitor",
    page_icon="G",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --ink: #e9eff8;
        --muted: #94a3b8;
        --line: rgba(151, 171, 202, .16);
        --accent: #7dd3c7;
    }
    .stApp {
        background:
            radial-gradient(ellipse at 78% 0%, rgba(37, 99, 122, .16), transparent 35%),
            #0b1220;
    }
    [data-testid="stSidebar"] {
        background: #0e1727;
        border-right: 1px solid var(--line);
    }
    [data-testid="stMetric"] {
        background: rgba(18, 30, 49, .78);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 16px 18px;
    }
    [data-testid="stMetricLabel"] p {
        color: var(--muted);
        font-size: .8rem;
    }
    [data-testid="stMetricValue"] {
        color: var(--ink);
    }
    .eyebrow {
        color: var(--accent);
        font-size: .75rem;
        font-weight: 700;
        letter-spacing: .13em;
        text-transform: uppercase;
        margin-bottom: .25rem;
    }
    .hero-title {
        color: var(--ink);
        font-size: clamp(2rem, 4vw, 3.1rem);
        font-weight: 720;
        letter-spacing: -.045em;
        line-height: 1.1;
        margin: 0 0 .5rem;
    }
    .hero-copy {
        color: var(--muted);
        font-size: 1rem;
        max-width: 720px;
    }
    .source-name {
        color: var(--ink);
        font-weight: 650;
        line-height: 1.4;
        min-height: 2.8em;
    }
    div[data-testid="stLinkButton"] a {
        border-radius: 9px;
    }
    hr {
        border-color: var(--line);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

PAGES = ("Overview", "All updates", *CATEGORIES, "Source directory")
SOURCE_BY_NAME = {source.name: source for source in SOURCES}


def _fetch_for_page(page: str) -> tuple[list[dict[str, Any]], dict[str, str], int]:
    sources = SOURCES
    if page in CATEGORIES:
        sources = tuple(source for source in SOURCES if source.category == page)
    updates, failures = _cached_fetch_updates(
        tuple(source.name for source in sources)
    )
    return updates, failures, len(sources)


@st.cache_data(ttl=900, show_spinner=False)
def _cached_fetch_updates(
    source_names: tuple[str, ...],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    return fetch_updates(source_names)


def _within_date_range(
    update: dict[str, Any], days: int
) -> bool:
    published = update["published"]
    if published is None:
        return True
    return published >= datetime.now(timezone.utc) - timedelta(days=days)


def _render_source_cards(sources: tuple[Any, ...]) -> None:
    for start in range(0, len(sources), 2):
        left, right = st.columns(2)
        for column, source in zip((left, right), sources[start : start + 2]):
            with column:
                with st.container(border=True):
                    st.markdown(
                        f'<div class="source-name">{source.name}</div>',
                        unsafe_allow_html=True,
                    )
                    st.caption(source.category)
                    st.link_button(
                        "Open official source",
                        source.url,
                        use_container_width=True,
                    )


def _render_updates(
    updates: list[dict[str, Any]],
    source_names: set[str],
    search_term: str,
    days: int,
    limit: int,
) -> None:
    search = search_term.strip().casefold()
    visible = [
        update
        for update in updates
        if update["source"] in source_names
        and _within_date_range(update, days)
        and (
            not search
            or search in update["title"].casefold()
            or search in update["source"].casefold()
        )
    ]
    if not visible:
        st.info(
            "No matching updates were returned. Try a wider date range or search, "
            "or open the official source directory."
        )
        return

    for update in visible[:limit]:
        source = SOURCE_BY_NAME[update["source"]]
        with st.container(border=True):
            title, link = st.columns([5, 1])
            with title:
                st.markdown(f"**{update['title']}**")
                published = update["published"]
                date_label = (
                    published.strftime("%b %d, %Y")
                    if published
                    else "Date not provided"
                )
                st.caption(f"{update['source']}  ·  {date_label}")
            with link:
                st.link_button("Read", update["url"], use_container_width=True)
            st.caption(f"Official source: {source.url}")


def _render_failures(failures: dict[str, str]) -> None:
    if not failures:
        return
    with st.expander(f"{len(failures)} source feed(s) could not be checked"):
        for name, error in sorted(failures.items()):
            st.warning(f"{name}: {error}")


def _render_category_windows(
    updates: list[dict[str, Any]],
    search_term: str,
    days: int,
) -> None:
    search = search_term.strip().casefold()
    for start in range(0, len(CATEGORIES), 2):
        left, right = st.columns(2, gap="large")
        for column, category in zip(
            (left, right), CATEGORIES[start : start + 2]
        ):
            category_sources = tuple(
                source for source in SOURCES if source.category == category
            )
            source_names = {source.name for source in category_sources}
            category_updates = [
                update
                for update in updates
                if update["source"] in source_names
                and _within_date_range(update, days)
                and (
                    not search
                    or search in update["title"].casefold()
                    or search in update["source"].casefold()
                )
            ]
            with column:
                with st.container(border=True):
                    st.markdown(f"### {category}")
                    st.caption(
                        f"{len(category_sources)} monitored sources · "
                        f"{len(category_updates)} matching updates"
                    )
                    for update in category_updates[:3]:
                        published = update["published"]
                        date_label = (
                            published.strftime("%b %d, %Y")
                            if published
                            else "Date not provided"
                        )
                        st.markdown(f"[{update['title']}]({update['url']})")
                        st.caption(f"{update['source']} · {date_label}")
                    if not category_updates:
                        st.caption("No matching updates in this time window.")
                    st.caption(
                        "Sources: "
                        + " · ".join(source.name for source in category_sources)
                    )


def main() -> None:
    with st.sidebar:
        st.markdown("## GOVERNANCE / SIGNAL")
        st.caption("Global AI policy and standards monitor")
        page = st.radio("Workspace", PAGES, label_visibility="collapsed")
        st.divider()
        st.markdown("**Update filters**")
        days = st.selectbox(
            "Published in the last",
            (7, 30, 90, 365),
            index=1,
            format_func=lambda value: f"{value} days",
        )
        search_term = st.text_input("Search updates", placeholder="e.g. AI Act")
        st.caption("Feeds refresh automatically every 15 minutes.")
        if st.button("Refresh feeds now", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        if os.environ.get("AI_GOVERNANCE_ALLOW_SHUTDOWN") == "1":
            st.divider()
            st.caption("Stopping disconnects all users from this app.")
            if not st.session_state.get("confirm_shutdown", False):
                if st.button(
                    "Stop application",
                    type="secondary",
                    use_container_width=True,
                ):
                    st.session_state.confirm_shutdown = True
                    st.rerun()
            else:
                st.warning("Stop the tracker server for everyone?")
                confirm, cancel = st.columns(2)
                if confirm.button(
                    "Yes, stop",
                    type="primary",
                    use_container_width=True,
                ):
                    os.kill(os.getpid(), signal.SIGTERM)
                if cancel.button("Cancel", use_container_width=True):
                    st.session_state.confirm_shutdown = False
                    st.rerun()

    st.markdown('<div class="eyebrow">GLOBAL POLICY INTELLIGENCE</div>', unsafe_allow_html=True)
    st.markdown(
        '<h1 class="hero-title">AI Governance Monitor</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="hero-copy">One watchlist for international standards, '
        "policy frameworks, safety initiatives, regulation trackers, and "
        "legal intelligence.</p>",
        unsafe_allow_html=True,
    )

    if page == "Source directory":
        selected_category = st.selectbox("Filter by category", ("All categories", *CATEGORIES))
        directory = (
            SOURCES
            if selected_category == "All categories"
            else tuple(
                source for source in SOURCES if source.category == selected_category
            )
        )
        st.caption(f"{len(directory)} organizations and trackers")
        _render_source_cards(directory)
        return

    with st.spinner("Checking monitored sources..."):
        updates, failures, monitored_count = _fetch_for_page(page)

    filtered_updates = [
        update for update in updates if _within_date_range(update, days)
    ]
    successful_sources = monitored_count - len(failures)
    metric_columns = st.columns(3)
    metric_columns[0].metric("Updates found", len(filtered_updates))
    metric_columns[1].metric("Sources monitored", monitored_count)
    metric_columns[2].metric("Feeds checked", f"{successful_sources}/{monitored_count}")

    st.divider()
    if page == "Overview":
        st.subheader("Monitoring windows")
        _render_category_windows(updates, search_term, days)
        st.caption(
            "Search results are discovery signals, not authoritative legal updates. "
            "Confirm changes on the linked official source."
        )
    else:
        category = page if page in CATEGORIES else None
        if category:
            st.subheader(category)
            selected_sources = tuple(
                source for source in SOURCES if source.category == category
            )
            st.caption(
                f"{len(selected_sources)} sources in this monitoring window"
            )
            with st.expander("Official source links"):
                _render_source_cards(selected_sources)
            allowed_names = {source.name for source in selected_sources}
        else:
            st.subheader("All monitored updates")
            allowed_names = {source.name for source in SOURCES}

        _render_updates(updates, allowed_names, search_term, days, 100)
        st.caption(
            "Feed matches are discovery signals. Verify publication details and "
            "legal status with the linked official source."
        )

    _render_failures(failures)
    st.caption(
        f"Last checked: {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')} "
        "| Update results are cached for 15 minutes."
    )


if __name__ == "__main__":
    main()
