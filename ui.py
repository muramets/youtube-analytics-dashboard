from typing import Dict, List, Any, Optional
import logging

import pandas as pd
import streamlit as st

from utils import format_number, format_date

# Configure logging
logger = logging.getLogger(__name__)


def inject_base_css() -> None:
    """Inject base CSS for improved visuals."""
    st.markdown(
        """
<style>
    /* Ensure dataframes stay within centered container */
    .stDataFrame { 
        width: 100%; 
        max-width: 100%;
    }

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

    /* Table header styling */
    div[data-testid="stDataFrame"] table thead th {
        text-align: center !important;
        white-space: normal !important;
    }

    div[data-testid="stDataFrame"] table thead th div[data-testid="columnHeaderCell"] {
        display: flex !important;
        justify-content: center !important;
    }

    div[data-testid="stDataFrame"] table thead th div[data-testid="columnHeaderText"] {
        white-space: normal !important;
        overflow-wrap: anywhere !important;
        text-align: center !important;
        line-height: 1.2 !important;
    }

    div[data-testid="stDataFrame"] table thead th div[data-testid="columnHeaderText"] span {
        white-space: normal !important;
        overflow-wrap: anywhere !important;
    }

    /* Headings */
    h1 { text-align: center; margin-bottom: 0.5rem; }
    h2 { margin-top: 1.5rem; margin-bottom: 0.5rem; }
    
    /* Clean styling for centered containers */
    div[data-testid="stVerticalBlock"] {
        gap: 1rem;
    }
</style>
        """,
        unsafe_allow_html=True,
    )


def display_video_table(
    videos_data: List[Dict[str, Any]],
    category_title: str,
    hide_zero_duration: bool,
) -> None:
    """Display videos in a scrollable dataframe sorted by Views desc.

    Args:
        videos_data: List of video dictionaries containing video information
        category_title: Title for the category section

    Table columns order: Video Title, Views, Avg View Duration, Impressions, CTR (%), Watch Time (hrs), Video URL
    """
    if not videos_data:
        st.info(f"No videos found for {category_title}")
        return

    st.markdown(
        f'<div class="time-period-header">{category_title} ({len(videos_data)} videos)</div>',
        unsafe_allow_html=True,
    )

    # Prepare rows with better error handling
    df_rows: List[Dict[str, Any]] = []
    for video in videos_data:
        try:
            # Get views with priority to API views
            api_views = video.get("api_views", 0)
            csv_views = video.get("csv_views", 0)
            views_value = api_views if api_views and api_views > 0 else csv_views

            # Safely extract other metrics
            impressions = _safe_int_conversion(video.get("impressions", 0))
            ctr = video.get("impressions_ctr", 0) or 0
            watch_time = _safe_float_conversion(video.get("watch_time_hours", 0))

            # Format CTR with error handling
            try:
                ctr_value = float(ctr)
                ctr_display = f"{ctr_value:.2f}%"
            except (ValueError, TypeError):
                ctr_display = "0.00%"

            # Hide rows with zero avg duration if requested
            avg_duration = video.get("average_view_duration", "0:00")
            if hide_zero_duration and (avg_duration in {"0:00", "0", 0, None, "00:00"}):
                continue

            # Validate video ID
            video_id = video.get('video_id', '')
            video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""

            df_rows.append({
                "Video Title": video.get("title", "Unknown"),
                "Views": views_value,
                "Published Date": format_date(video.get("published_at", "")),
                "Avg View Duration": video.get("average_view_duration", "0:00"),
                "Impressions": impressions,
                "CTR (%)": ctr_display,
                "Watch Time (hrs)": watch_time,
                "Video URL": video_url,
            })

        except Exception as e:
            logger.warning(f"Error processing video data: {str(e)}")
            # Add minimal row to avoid breaking the table
            df_rows.append({
                "Video Title": "Error loading video",
                "Views": 0,
                "Avg View Duration": "0:00",
                "Impressions": 0,
                "CTR (%)": "0.00%",
                "Watch Time (hrs)": 0.0,
                "Video URL": "",
            })

    if not df_rows:
        st.warning(f"No valid video data found for {category_title}")
        return

    df = pd.DataFrame(df_rows)
    
    # Enforce column order explicitly
    desired_columns = [
        "Video Title",
        "Views",
        "Published Date",
        "Avg View Duration", 
        "Impressions",
        "CTR (%)",
        "Watch Time (hrs)",
        "Video URL",
    ]
    df = df[desired_columns]
    
    # Sort by Views (handle potential string/numeric mix)
    try:
        df = df.sort_values("Views", ascending=False, key=lambda x: pd.to_numeric(x, errors='coerce').fillna(0))
    except Exception as e:
        logger.warning(f"Error sorting by views: {str(e)}")
        # Fallback to basic sort
        df = df.sort_values("Views", ascending=False)

    # Format numbers for display
    df["Views"] = df["Views"].apply(_format_views_column)
    df["Impressions"] = df["Impressions"].apply(_format_impressions_column)

    visible_rows = min(len(df), 10)
    base_height = 70  # header + padding
    row_height = 38
    table_height = base_height + visible_rows * row_height

    st.dataframe(
        df,
        use_container_width=True,
        height=table_height,
        hide_index=True,
        column_config={
            "Video Title": st.column_config.TextColumn(
                "Video Title", 
                width="large", 
                help="Click on the URL column to open the video"
            ),
            "Views": st.column_config.TextColumn("Views", width="small", help="Total views"),
            "Published Date": st.column_config.TextColumn("Published Date", width="small", help="Video publish date"),
            "Avg View Duration": st.column_config.TextColumn("Avg View Duration", width="small"),
            "Impressions": st.column_config.TextColumn("Impressions", width="small"),
            "CTR (%)": st.column_config.TextColumn("CTR (%)", width="small"),
            "Watch Time (hrs)": st.column_config.NumberColumn(
                "Watch Time (hrs)", 
                width="small", 
                format="%.1f"
            ),
            "Video URL": st.column_config.LinkColumn(
                "Video URL", 
                help="Click to open video on YouTube", 
                width="small", 
                display_text="Open ↗"
            ),
        },
    )


def _safe_int_conversion(value: Any) -> int:
    """Safely convert value to integer."""
    try:
        return int(float(value)) if value is not None else 0
    except (ValueError, TypeError):
        return 0


def _safe_float_conversion(value: Any) -> float:
    """Safely convert value to float."""
    try:
        return float(value) if value is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


def _format_views_column(x: Any) -> str:
    """Format views column values."""
    try:
        return format_number(int(x)) if isinstance(x, (int, float)) and x > 0 else "0"
    except (ValueError, TypeError):
        return "0"


def _format_impressions_column(x: Any) -> str:
    """Format impressions column values."""
    try:
        return format_number(int(x)) if isinstance(x, (int, float)) and x > 0 else "0"
    except (ValueError, TypeError):
        return "0"


