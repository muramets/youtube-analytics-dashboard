import streamlit as st
import pandas as pd
import time
from typing import Dict, List, Optional, Tuple, Any

from youtube_analyzer import YouTubeAnalyzer
from ui import inject_base_css, display_video_table

# Page configuration
st.set_page_config(
    page_title="YouTube Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

inject_base_css()


@st.cache_data
def validate_api_key(api_key: str) -> bool:
    """Validate YouTube API key format."""
    return len(api_key) >= 20


def setup_sidebar() -> Optional[str]:
    """Setup sidebar with API key configuration."""
    with st.sidebar:
        st.header("🔑 Configuration")
        
        # API Key input
        api_key = st.text_input(
            "Enter YouTube API Key:",
            type="password",
            help="Get your API key from Google Cloud Console"
        )
        
        if api_key:
            if not validate_api_key(api_key):
                st.error("❌ API key seems too short. Please check your key.")
                return None
            st.success("✅ API Key provided")
            return api_key
        else:
            st.warning("⚠️ Please enter your YouTube API key to continue")
            return None


def validate_csv_structure(df: pd.DataFrame) -> Tuple[bool, str]:
    """Validate CSV file structure and format."""
    if len(df) < 3:  # Need header + total + at least one data row
        return False, "CSV file must have at least 3 rows (header, total, and data)"
    
    # Skip header and total rows
    data_df = df.iloc[2:]
    
    if len(data_df) == 0:
        return False, "No data rows found in the CSV file"
    
    if len(data_df.columns) < 8:
        return False, f"CSV file has insufficient columns. Expected at least 8, found {len(data_df.columns)}"
    
    return True, ""


@st.cache_data(ttl=1800)  # Cache for 30 minutes
def extract_video_data_from_csv(data_df: pd.DataFrame, _analyzer: YouTubeAnalyzer) -> Tuple[List[str], Dict[str, Dict[str, Any]]]:
    """Extract video IDs and data from CSV with caching."""
    video_ids = []
    csv_data = {}
    errors_count = 0
    
    for idx, row in data_df.iterrows():
        try:
            traffic_source = str(row.iloc[0])
            video_id = _analyzer.extract_video_id(traffic_source)
            
            if video_id:
                # Avoid duplicate video IDs
                if video_id not in csv_data:
                    video_ids.append(video_id)
                    csv_data[video_id] = {
                        'video_id': video_id,
                        'impressions': _safe_int_conversion(row.iloc[3]),
                        'impressions_ctr': _safe_float_conversion(row.iloc[4]),
                        'csv_views': _safe_int_conversion(row.iloc[5]),
                        'average_view_duration': str(row.iloc[6]) if pd.notna(row.iloc[6]) and row.iloc[6] else "0:00",
                        'watch_time_hours': _safe_float_conversion(row.iloc[7])
                    }
        except (IndexError, ValueError, TypeError) as e:
            errors_count += 1
            if errors_count <= 5:  # Only show first 5 errors to avoid spam
                st.warning(f"Skipping row {idx}: {str(e)}")
            continue
    
    if errors_count > 5:
        st.warning(f"Skipped {errors_count - 5} additional rows with errors")
    
    return video_ids, csv_data


def _safe_int_conversion(value: Any) -> int:
    """Safely convert value to integer."""
    try:
        return int(float(value)) if pd.notna(value) and value else 0
    except (ValueError, TypeError):
        return 0


def _safe_float_conversion(value: Any) -> float:
    """Safely convert value to float."""
    try:
        return float(value) if pd.notna(value) and value else 0.0
    except (ValueError, TypeError):
        return 0.0


def combine_csv_and_api_data(video_ids: List[str], csv_data: Dict[str, Dict[str, Any]], 
                            video_data: Dict[str, Dict], analyzer: YouTubeAnalyzer) -> List[Dict[str, Any]]:
    """Combine CSV data with YouTube API data."""
    combined_data = []
    
    for video_id in video_ids:
        if video_id in csv_data:
            csv_row = csv_data[video_id]
            
            if video_id in video_data:
                api_data = video_data[video_id]
                category = analyzer.categorize_by_date(api_data['published_at'])
                
                combined_video = {
                    **csv_row,
                    'title': api_data.get('title', 'Unknown Title'),
                    'published_at': api_data.get('published_at', ''),
                    'api_views': api_data.get('view_count', 0),
                    'thumbnail_url': api_data.get('thumbnail_url', ''),
                    'category': category,
                    'content_type': api_data.get('content_type', 'Unknown')
                }
            else:
                # Video not found in API, use default values
                combined_video = {
                    **csv_row,
                    'title': f'Video ID: {video_id}',
                    'published_at': '',
                    'api_views': 0,
                    'thumbnail_url': '',
                    'category': 'Unknown',
                    'content_type': 'Unknown'
                }
            
            combined_data.append(combined_video)
    
    return combined_data


def categorize_videos(combined_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Categorize videos by time periods."""
    categories = {
        "Last 2 weeks": [],
        "2-4 weeks ago": [],
        "1-3 months ago": [],
        "More than 3 months ago": [],
        "Unknown": []
    }
    
    for video in combined_data:
        category = video.get('category', 'Unknown')
        if category in categories:
            categories[category].append(video)
        else:
            categories['Unknown'].append(video)
    
    return categories


def display_summary(categories: Dict[str, List[Dict[str, Any]]]) -> None:
    """Display analytics summary."""
    st.header("📈 Analytics Summary")

    # Filter out empty categories for metrics
    non_empty_categories = [(name, videos) for name, videos in categories.items() if videos]

    if non_empty_categories:
        # Create columns based on non-empty categories
        summary_cols = st.columns(min(len(non_empty_categories), 5))

        for idx, (category_name, videos) in enumerate(non_empty_categories[:5]):
            with summary_cols[idx]:
                # Shorten category names for display
                display_name = category_name.replace(" ago", "").replace("More than ", "3+ ")
                st.metric(display_name, len(videos))


def display_video_analysis(categories: Dict[str, List[Dict[str, Any]]]) -> None:
    """Display video analysis by time periods."""
    hide_zero_duration = st.checkbox(
        "Hide zero view duration",
        value=True,
        help="Hide videos with average view duration equal to zero",
    )
    st.header("📺 Video Analysis by Time Periods")

    # Check if there are any videos to display
    has_videos = any(len(videos) > 0 for videos in categories.values())

    if has_videos:
        for category_name, videos in categories.items():
            if videos:  # Only show categories with videos
                display_video_table(videos, category_name, hide_zero_duration)
    else:
        st.warning("No videos found to analyze. Please check your CSV file format.")


def process_uploaded_files(uploaded_files: List, api_key: str) -> None:
    """Process multiple uploaded CSV files and display combined analysis."""
    total_rows = 0
    all_combined_data: List[Dict[str, Any]] = []
    analyzer: Optional[YouTubeAnalyzer] = None

    try:
        progress_container = st.container()
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()

            for file_index, uploaded_file in enumerate(uploaded_files, start=1):
                status_text.text(f"📄 Processing file {file_index}/{len(uploaded_files)}: {uploaded_file.name}")

                try:
                    df = pd.read_csv(uploaded_file, encoding='utf-8', skiprows=1)
                except UnicodeDecodeError:
                    df = pd.read_csv(uploaded_file, encoding='latin-1', skiprows=1)

                total_rows += len(df)

                is_valid, error_msg = validate_csv_structure(df)
                if not is_valid:
                    st.error(f"❌ {uploaded_file.name}: {error_msg}")
                    st.error("Please ensure you're uploading a valid YouTube Analytics export file.")
                    continue

                if analyzer is None:
                    try:
                        analyzer = YouTubeAnalyzer(api_key)
                    except ValueError as e:
                        st.error(f"❌ API Key Error: {str(e)}")
                        return

                video_ids, csv_data = extract_video_data_from_csv(df, analyzer)

                if not video_ids:
                    st.warning(f"No valid YouTube video IDs found in {uploaded_file.name}.")
                    continue

                status_text.text(f"📡 Fetching API data for {len(video_ids)} videos in {uploaded_file.name}...")
                video_data = analyzer.get_video_data(video_ids)

                combined_data = combine_csv_and_api_data(video_ids, csv_data, video_data, analyzer)
                all_combined_data.extend(combined_data)

                progress = file_index / len(uploaded_files)
                progress_bar.progress(int(progress * 100))

        progress_container.empty()

        if not all_combined_data:
            st.warning("No valid video data found across uploaded files.")
            return

        st.success(f"✅ Processed {len(uploaded_files)} file(s). Total rows: {total_rows}.")

        total_processed = len(all_combined_data)
        api_matched = sum(1 for v in all_combined_data if v.get('api_views', 0) > 0)

        with st.expander("📊 Processing Summary", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Videos Processed", total_processed)
            with col2:
                st.metric("API Data Found", api_matched)
            with col3:
                match_rate = (api_matched / total_processed * 100) if total_processed > 0 else 0
                st.metric("Match Rate", f"{match_rate:.1f}%")

        categories = categorize_videos(all_combined_data)
        display_summary(categories)
        st.markdown("---")
        display_video_analysis(categories)

        if st.button("💾 Download Combined Data as CSV"):
            processed_df = _create_download_dataframe(all_combined_data)
            csv_data = processed_df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv_data,
                file_name="youtube_analytics_combined.csv",
                mime="text/csv"
            )

    except pd.errors.EmptyDataError:
        st.error("❌ One of the uploaded files appears to be empty.")
    except pd.errors.ParserError as e:
        st.error(f"❌ Error parsing CSV file: {str(e)}")
        st.error("Please check that your files are in valid CSV format.")
    except Exception as e:
        st.error(f"❌ Unexpected error processing files: {str(e)}")
        st.error("Please try again or contact support if the issue persists.")


def _create_download_dataframe(combined_data: List[Dict[str, Any]]) -> pd.DataFrame:
    """Create a downloadable dataframe from processed video data."""
    rows = []
    for video in combined_data:
        rows.append({
            'Video ID': video.get('video_id', ''),
            'Title': video.get('title', ''),
            'Published Date': video.get('published_at', ''),
            'Category': video.get('category', ''),
            'CSV Views': video.get('csv_views', 0),
            'API Views': video.get('api_views', 0),
            'Impressions': video.get('impressions', 0),
            'CTR (%)': video.get('impressions_ctr', 0),
            'Avg View Duration': video.get('average_view_duration', ''),
            'Watch Time (hrs)': video.get('watch_time_hours', 0),
            'Video URL': f"https://www.youtube.com/watch?v={video.get('video_id', '')}"
        })
    return pd.DataFrame(rows)


def main():
    """Main application function."""
    # Global styling: center the Streamlit content area
    st.markdown(
        """
        <style>
            .block-container {
                max-width: 1000px !important;
                padding: 2rem 1.5rem 2.5rem !important;
                margin: 0 auto !important;
            }

            div[data-testid="stToolbar"] {
                right: 0.5rem;
            }

            div[data-testid="stSidebar"] section {
                padding-top: 2rem;
                width: 100%;
                max-width: 360px;
            }

            div[data-testid="stSidebarContent"] {
                width: 100% !important;
                max-width: 360px;
                margin: 0 auto;
            }

            div[data-testid="stSidebarContent"] .stTextInput > div > div {
                width: 100%;
            }

            div[data-testid="stSidebarContent"] input {
                width: 100% !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("📊 YouTube Analytics Dashboard")
    st.markdown(
        "<p style='text-align: center; color: #666; margin-bottom: 2rem;'>Upload your YouTube analytics CSV file and analyze video performance by time periods</p>",
        unsafe_allow_html=True,
    )

    # Setup sidebar and get API key
    api_key = setup_sidebar()

    if not api_key:
        # Show message about needing API key before CSV upload
        st.info("👆 Please enter your YouTube API key in the sidebar to continue")
        st.stop()

    # File upload section (only shown after API key validation)
    st.header("📁 Upload CSV File")
    st.markdown("✅ API key validated - you can now upload your CSV file")

    uploaded_files = st.file_uploader(
        "➕ Add CSV files",
        type="csv",
        help="Upload one or more CSV files exported from YouTube Analytics",
        accept_multiple_files=True,
    )

    if uploaded_files:
        process_uploaded_files(uploaded_files, api_key)

if __name__ == "__main__":
    main()
