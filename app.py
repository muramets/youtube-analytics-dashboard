import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import re
from typing import Dict, List, Tuple
import time

# Page configuration
st.set_page_config(
    page_title="YouTube Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .video-container {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        background-color: #f9f9f9;
    }
    
    .video-thumbnail {
        width: 120px;
        height: 90px;
        object-fit: cover;
        border-radius: 5px;
    }
    
    .video-title {
        font-size: 16px;
        font-weight: bold;
        color: #1f77b4;
        text-decoration: none;
    }
    
    .video-title:hover {
        text-decoration: underline;
    }
    
    .metric-value {
        font-size: 14px;
        color: #666;
    }
    
    .time-period-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 20px 0 10px 0;
        text-align: center;
        font-size: 20px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

class YouTubeAnalyzer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.googleapis.com/youtube/v3/videos"
    
    def extract_video_id(self, traffic_source: str) -> str:
        """Extract YouTube video ID from YT_RELATED.{video_id} format"""
        if traffic_source.startswith("YT_RELATED."):
            return traffic_source.replace("YT_RELATED.", "")
        return ""
    
    def get_video_data(self, video_ids: List[str]) -> Dict[str, Dict]:
        """Fetch video data from YouTube API in batches"""
        video_data = {}
        
        # Process in batches of 50 (YouTube API limit)
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i+50]
            ids_string = ",".join(batch_ids)
            
            params = {
                'part': 'snippet,statistics',
                'id': ids_string,
                'key': self.api_key
            }
            
            try:
                response = requests.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                for item in data.get('items', []):
                    video_id = item['id']
                    video_data[video_id] = {
                        'title': item['snippet']['title'],
                        'published_at': item['snippet']['publishedAt'],
                        'view_count': int(item['statistics'].get('viewCount', 0)),
                        'thumbnail_url': item['snippet']['thumbnails']['medium']['url']
                    }
                
                # Rate limiting to avoid API quota issues
                time.sleep(0.1)
                
            except requests.exceptions.RequestException as e:
                st.error(f"API request failed: {str(e)}")
            except Exception as e:
                st.error(f"Error processing video data: {str(e)}")
        
        return video_data
    
    def categorize_by_date(self, published_date: str) -> str:
        """Categorize videos by publication date"""
        try:
            pub_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
            now = datetime.now(pub_date.tzinfo)
            
            days_diff = (now - pub_date).days
            
            if days_diff <= 14:
                return "Last 2 weeks"
            elif days_diff <= 28:
                return "2-4 weeks ago"
            elif days_diff <= 90:
                return "1-3 months ago"
            else:
                return "More than 3 months ago"
        except:
            return "Unknown"

def format_duration(duration_str: str) -> str:
    """Format duration string for display"""
    if not duration_str or duration_str == "":
        return "0:00"
    return duration_str

def format_number(num: int) -> str:
    """Format large numbers with K, M, B suffixes"""
    if num >= 1_000_000_000:
        return f"{num/1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    else:
        return str(num)

def display_video_table(videos_data: List[Dict], category_title: str):
    """Display videos in a formatted table"""
    if not videos_data:
        st.info(f"No videos found for {category_title}")
        return
    
    st.markdown(f'<div class="time-period-header">{category_title} ({len(videos_data)} videos)</div>', 
                unsafe_allow_html=True)
    
    # Create columns for the table
    col_headers = st.columns([1, 3, 1.5, 1.5, 2, 1.5, 1.5])
    
    with col_headers[0]:
        st.write("**Thumbnail**")
    with col_headers[1]:
        st.write("**Video Title**")
    with col_headers[2]:
        st.write("**Avg View Duration**")
    with col_headers[3]:
        st.write("**Impressions**")
    with col_headers[4]:
        st.write("**CTR (%)**")
    with col_headers[5]:
        st.write("**Views**")
    with col_headers[6]:
        st.write("**Watch Time (hrs)**")
    
    st.markdown("---")
    
    for video in videos_data:
        cols = st.columns([1, 3, 1.5, 1.5, 2, 1.5, 1.5])
        
        with cols[0]:
            if video.get('thumbnail_url'):
                st.image(video['thumbnail_url'], width=120)
            else:
                st.write("No thumbnail")
        
        with cols[1]:
            video_url = f"https://www.youtube.com/watch?v={video['video_id']}"
            st.markdown(f'<a href="{video_url}" target="_blank" class="video-title">{video["title"]}</a>', 
                       unsafe_allow_html=True)
        
        with cols[2]:
            st.write(format_duration(video.get('average_view_duration', '0:00')))
        
        with cols[3]:
            impressions = video.get('impressions', 0)
            st.write(format_number(impressions) if impressions > 0 else "0")
        
        with cols[4]:
            ctr = video.get('impressions_ctr', 0)
            st.write(f"{ctr}%" if ctr > 0 else "0%")
        
        with cols[5]:
            views = video.get('csv_views', 0)
            api_views = video.get('api_views', 0)
            display_views = api_views if api_views > 0 else views
            st.write(format_number(display_views))
        
        with cols[6]:
            watch_time = video.get('watch_time_hours', 0)
            st.write(f"{watch_time}" if watch_time > 0 else "0")
        
        st.markdown("---")

def main():
    st.title("📊 YouTube Analytics Dashboard")
    st.markdown("Upload your YouTube analytics CSV file and analyze video performance by time periods.")
    
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
            st.success("✅ API Key provided")
            # Collapse sidebar after API key is entered
            st.markdown("""
            <script>
                window.parent.document.querySelector('[data-testid="stSidebar"]').style.width = "0px";
            </script>
            """, unsafe_allow_html=True)
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
            
            # Show processing status
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Extract video IDs
            status_text.text("Extracting video IDs...")
            analyzer = YouTubeAnalyzer(api_key)
            
            video_ids = []
            csv_data = {}
            
            for idx, row in data_df.iterrows():
                traffic_source = str(row.iloc[0])  # First column
                video_id = analyzer.extract_video_id(traffic_source)
                
                if video_id:
                    video_ids.append(video_id)
                    csv_data[video_id] = {
                        'video_id': video_id,
                        'impressions': row.iloc[3] if pd.notna(row.iloc[3]) else 0,
                        'impressions_ctr': row.iloc[4] if pd.notna(row.iloc[4]) else 0,
                        'csv_views': row.iloc[5] if pd.notna(row.iloc[5]) else 0,
                        'average_view_duration': row.iloc[6] if pd.notna(row.iloc[6]) else "0:00",
                        'watch_time_hours': row.iloc[7] if pd.notna(row.iloc[7]) else 0
                    }
            
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
                if video_id in video_data and video_id in csv_data:
                    api_data = video_data[video_id]
                    csv_row = csv_data[video_id]
                    
                    category = analyzer.categorize_by_date(api_data['published_at'])
                    
                    combined_video = {
                        **csv_row,
                        'title': api_data['title'],
                        'published_at': api_data['published_at'],
                        'api_views': api_data['view_count'],
                        'thumbnail_url': api_data['thumbnail_url'],
                        'category': category
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
                "More than 3 months ago": []
            }
            
            for video in combined_data:
                category = video['category']
                if category in categories:
                    categories[category].append(video)
            
            # Display summary
            st.header("📈 Analytics Summary")
            summary_cols = st.columns(4)
            
            with summary_cols[0]:
                st.metric("Last 2 weeks", len(categories["Last 2 weeks"]))
            with summary_cols[1]:
                st.metric("2-4 weeks ago", len(categories["2-4 weeks ago"]))
            with summary_cols[2]:
                st.metric("1-3 months ago", len(categories["1-3 months ago"]))
            with summary_cols[3]:
                st.metric("3+ months ago", len(categories["More than 3 months ago"]))
            
            st.markdown("---")
            
            # Display videos by category
            st.header("📺 Video Analysis by Time Periods")
            
            for category_name, videos in categories.items():
                if videos:  # Only show categories with videos
                    display_video_table(videos, category_name)
                    st.markdown("<br>", unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.error("Please make sure your CSV file has the correct format.")

if __name__ == "__main__":
    main()
