from typing import Dict, List

import pandas as pd
import streamlit as st

from utils import format_number


def inject_base_css() -> None:
    """Inject base CSS to center content and improve visuals."""
    st.markdown(
        """
<style>
    /* Center main content within a max-width container */
    .main > div {
        max-width: 1100px;
        margin: 0 auto;
        padding: 2rem 1.25rem;
    }

    /* Streamlit dataframe container full width, but capped height for scroll */
    .stDataFrame { width: 100%; }

    /* Header chip for time periods */
    .time-period-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 12px 16px;
        border-radius: 10px;
        margin: 16px 0 10px 0;
        text-align: left;
        font-size: 18px;
        font-weight: 700;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
    }

    /* Metric cards */
    div[data-testid="metric-container"] {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 10px;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }

    /* Headings */
    h1 { text-align: center; margin-bottom: 0.5rem; }
    h2 { margin-top: 1.5rem; margin-bottom: 0.5rem; }
</style>
        """,
        unsafe_allow_html=True,
    )


def display_video_table(videos_data: List[Dict], category_title: str) -> None:
    """Display videos in a scrollable dataframe sorted by Views desc.

    Table columns order: Video Title, Views, Avg View Duration, Impressions, CTR (%), Watch Time (hrs), Video URL
    """
    if not videos_data:
        st.info(f"No videos found for {category_title}")
        return

    st.markdown(
        f'<div class="time-period-header">{category_title} ({len(videos_data)} videos)</div>',
        unsafe_allow_html=True,
    )

    # Prepare rows
    df_rows: List[Dict] = []
    for video in videos_data:
        views_value = (
            video.get("api_views", 0) if video.get("api_views", 0) > 0 else video.get("csv_views", 0)
        )
        impressions = video.get("impressions", 0)
        ctr = video.get("impressions_ctr", 0) or 0
        watch_time = video.get("watch_time_hours", 0)

        try:
            ctr_value = float(ctr)
            ctr_display = f"{ctr_value:.2f}%"
        except (ValueError, TypeError):
            ctr_display = "0.00%"

        df_rows.append(
            {
                "Video Title": video.get("title", "Unknown"),
                "Views": views_value,
                "Avg View Duration": video.get("average_view_duration", "0:00"),
                "Impressions": impressions,
                "CTR (%)": ctr_display,
                "Watch Time (hrs)": watch_time,
                "Video URL": f"https://www.youtube.com/watch?v={video.get('video_id', '')}",
            }
        )

    df = pd.DataFrame(df_rows)
    # Enforce column order explicitly
    desired_columns = [
        "Video Title",
        "Views",
        "Avg View Duration",
        "Impressions",
        "CTR (%)",
        "Watch Time (hrs)",
        "Video URL",
    ]
    df = df[desired_columns]
    df = df.sort_values("Views", ascending=False)

    # Format numbers for display
    df["Views"] = df["Views"].apply(lambda x: format_number(int(x)) if isinstance(x, (int, float)) and x > 0 else "0")
    df["Impressions"] = df["Impressions"].apply(
        lambda x: format_number(int(x)) if isinstance(x, (int, float)) and x > 0 else "0"
    )

    st.dataframe(
        df,
        use_container_width=True,
        height=400,
        hide_index=True,
        column_config={
            "Video Title": st.column_config.TextColumn("Video Title", width="large", help="Click on the URL column to open the video"),
            "Views": st.column_config.TextColumn("Views", width="small"),
            "Avg View Duration": st.column_config.TextColumn("Avg View Duration", width="small"),
            "Impressions": st.column_config.TextColumn("Impressions", width="small"),
            "CTR (%)": st.column_config.TextColumn("CTR (%)", width="small"),
            "Watch Time (hrs)": st.column_config.NumberColumn("Watch Time (hrs)", width="small", format="%.1f"),
            "Video URL": st.column_config.LinkColumn("Video URL", help="Click to open video on YouTube", width="small", display_text="Open ↗"),
        },
    )


