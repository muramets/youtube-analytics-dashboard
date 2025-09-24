import streamlit as st
import pandas as pd
import time

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
 
 

def main():
    # Add container for centered content
    st.title("📊 YouTube Analytics Dashboard")
    st.markdown("<p style='text-align: center; color: #666; margin-bottom: 2rem;'>Upload your YouTube analytics CSV file and analyze video performance by time periods</p>", unsafe_allow_html=True)
    
    # Sidebar for API key
    with st.sidebar:
        st.header("🔑 Configuration")
        
        # API Key input
        api_key = st.text_input(
            "Enter YouTube API Key:",
            type="password",
            help="Get your API key from Google Cloud Console"
        )
        
        if api_key:
            if len(api_key) < 20:  # Basic validation
                st.error("❌ API key seems too short. Please check your key.")
                st.stop()
            st.success("✅ API Key provided")
        else:
            st.warning("⚠️ Please enter your YouTube API key to continue")
            st.stop()
    
    # File upload
    st.header("📁 Upload CSV File")
    uploaded_file = st.file_uploader(
        "Choose your YouTube analytics CSV file",
        type="csv",
        help="Upload the CSV file exported from YouTube Analytics"
    )
    
    if uploaded_file is not None:
        try:
            # Read CSV file
            df = pd.read_csv(uploaded_file)
            
            # Display file info
            st.success(f"✅ File uploaded successfully! Found {len(df)} rows.")
            
            # Skip header and total rows (first 2 rows)
            data_df = df.iloc[2:].copy()
            
            if len(data_df) == 0:
                st.error("No data rows found in the CSV file.")
                st.stop()
                
            # Validate CSV structure
            if len(data_df.columns) < 8:
                st.error(f"CSV file has insufficient columns. Expected at least 8, found {len(data_df.columns)}")
                st.error("Please ensure you're uploading a valid YouTube Analytics export file.")
                st.stop()
            
            # Show processing status
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Extract video IDs
            status_text.text("Extracting video IDs...")
            analyzer = YouTubeAnalyzer(api_key)
            
            video_ids = []
            csv_data = {}
            
            for idx, row in data_df.iterrows():
                try:
                    traffic_source = str(row.iloc[0])  # First column
                    video_id = analyzer.extract_video_id(traffic_source)
                    
                    if video_id:
                        video_ids.append(video_id)
                        csv_data[video_id] = {
                            'video_id': video_id,
                            'impressions': int(row.iloc[3]) if pd.notna(row.iloc[3]) and row.iloc[3] else 0,
                            'impressions_ctr': float(row.iloc[4]) if pd.notna(row.iloc[4]) and row.iloc[4] else 0.0,
                            'csv_views': int(row.iloc[5]) if pd.notna(row.iloc[5]) and row.iloc[5] else 0,
                            'average_view_duration': str(row.iloc[6]) if pd.notna(row.iloc[6]) and row.iloc[6] else "0:00",
                            'watch_time_hours': float(row.iloc[7]) if pd.notna(row.iloc[7]) and row.iloc[7] else 0.0
                        }
                except (IndexError, ValueError, TypeError) as e:
                    st.warning(f"Skipping row {idx}: {str(e)}")
                    continue
            
            progress_bar.progress(25)
            status_text.text(f"Found {len(video_ids)} videos. Fetching data from YouTube API...")
            
            if not video_ids:
                st.error("No valid YouTube video IDs found in the CSV file.")
                st.stop()
            
            # Fetch video data from YouTube API
            video_data = analyzer.get_video_data(video_ids)
            progress_bar.progress(75)
            
            # Combine CSV data with API data
            status_text.text("Processing and categorizing videos...")
            combined_data = []
            
            for video_id in video_ids:
                if video_id in csv_data:
                    csv_row = csv_data[video_id]
                    
                    # Check if we have API data for this video
                    if video_id in video_data:
                        api_data = video_data[video_id]
                        category = analyzer.categorize_by_date(api_data['published_at'])
                        
                        combined_video = {
                            **csv_row,
                            'title': api_data.get('title', 'Unknown Title'),
                            'published_at': api_data.get('published_at', ''),
                            'api_views': api_data.get('view_count', 0),
                            'thumbnail_url': api_data.get('thumbnail_url', ''),
                            'category': category
                        }
                    else:
                        # Video not found in API, use default values
                        combined_video = {
                            **csv_row,
                            'title': f'Video ID: {video_id}',
                            'published_at': '',
                            'api_views': 0,
                            'thumbnail_url': '',
                            'category': 'Unknown'
                        }
                    
                    combined_data.append(combined_video)
            
            progress_bar.progress(100)
            status_text.text("✅ Processing complete!")
            time.sleep(1)
            progress_bar.empty()
            status_text.empty()
            
            # Categorize videos by time periods
            categories = {
                "Last 2 weeks": [],
                "2-4 weeks ago": [],
                "1-3 months ago": [],
                "More than 3 months ago": [],
                "Unknown": []  # Add Unknown category
            }
            
            for video in combined_data:
                category = video.get('category', 'Unknown')
                if category in categories:
                    categories[category].append(video)
                else:
                    # Fallback to Unknown if category is not recognized
                    categories['Unknown'].append(video)
            
            # Display summary
            st.header("📈 Analytics Summary")
            
            # Filter out empty categories for metrics
            non_empty_categories = [(name, videos) for name, videos in categories.items() if videos]
            
            if non_empty_categories:
                # Create columns based on non-empty categories
                summary_cols = st.columns(min(len(non_empty_categories), 5))  # Max 5 columns
                
                for idx, (category_name, videos) in enumerate(non_empty_categories[:5]):
                    with summary_cols[idx]:
                        # Shorten category names for display
                        display_name = category_name.replace(" ago", "").replace("More than ", "3+ ")
                        st.metric(display_name, len(videos))
            
            st.markdown("---")
            
            # Display videos by category
            st.header("📺 Video Analysis by Time Periods")
            
            # Check if there are any videos to display
            has_videos = any(len(videos) > 0 for videos in categories.values())
            
            if has_videos:
                for category_name, videos in categories.items():
                    if videos:  # Only show categories with videos
                        display_video_table(videos, category_name)
            else:
                st.warning("No videos found to analyze. Please check your CSV file format.")
            
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.error("Please make sure your CSV file has the correct format.")

if __name__ == "__main__":
    main()
