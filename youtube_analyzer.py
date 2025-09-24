import time
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Union

import requests
import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YouTubeAnalyzer:
    """YouTube Analytics API wrapper with caching and error handling."""
    
    def __init__(self, api_key: str):
        if not api_key or len(api_key) < 20:
            raise ValueError("Invalid YouTube API key provided")
        
        self.api_key = api_key
        self.base_url = "https://www.googleapis.com/youtube/v3/videos"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'YouTube-Analytics-Dashboard/1.0'
        })

    def extract_video_id(self, traffic_source: str) -> Optional[str]:
        """Extract YouTube video ID from YT_RELATED.{video_id} format."""
        if not traffic_source or not isinstance(traffic_source, str):
            return None
            
        if traffic_source.startswith("YT_RELATED."):
            video_id = traffic_source.replace("YT_RELATED.", "")
            # Basic validation for YouTube video ID format (11 characters, alphanumeric, hyphen, underscore)
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                return video_id
        return None

    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def get_video_data(_self, video_ids: List[str]) -> Dict[str, Dict]:
        """Fetch video data from YouTube API in batches with caching."""
        if not video_ids:
            return {}
        
        video_data: Dict[str, Dict] = {}
        failed_batches = 0
        max_retries = 3

        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i + 50]
            ids_string = ",".join(batch_ids)

            params = {
                "part": "snippet,statistics,liveStreamingDetails",
                "id": ids_string,
                "key": _self.api_key,
            }

            for attempt in range(max_retries):
                try:
                    response = _self.session.get(_self.base_url, params=params, timeout=15)
                    response.raise_for_status()
                    data = response.json()

                    if "error" in data:
                        error_msg = data['error'].get('message', 'Unknown error')
                        logger.error(f"YouTube API error: {error_msg}")
                        st.error(f"YouTube API error: {error_msg}")
                        failed_batches += 1
                        break

                    for item in data.get("items", []):
                        video_id = item["id"]
                        snippet = item.get("snippet", {})
                        statistics = item.get("statistics", {})
                        live_details = item.get("liveStreamingDetails")

                        is_live = snippet.get("liveBroadcastContent", "none") == "live" or bool(live_details)
 
                        video_data[video_id] = {
                            "title": snippet.get("title", "Unknown Title"),
                            "published_at": snippet.get("publishedAt", ""),
                            "view_count": int(statistics.get("viewCount", 0)),
                            "thumbnail_url": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                            "content_type": "Live" if is_live else "Long form",
                        }

                    # Rate limiting
                    time.sleep(0.1)
                    break

                except requests.exceptions.Timeout:
                    logger.warning(f"Timeout on attempt {attempt + 1} for batch {i//50 + 1}")
                    if attempt == max_retries - 1:
                        st.warning(f"Timeout fetching batch {i//50 + 1}, skipping...")
                        failed_batches += 1
                    else:
                        time.sleep(2 ** attempt)  # Exponential backoff

                except requests.exceptions.RequestException as e:
                    logger.error(f"API request failed on attempt {attempt + 1}: {str(e)}")
                    if attempt == max_retries - 1:
                        st.error(f"API request failed after {max_retries} attempts: {str(e)}")
                        failed_batches += 1
                    else:
                        time.sleep(2 ** attempt)

                except Exception as e:
                    logger.error(f"Unexpected error processing video data: {str(e)}")
                    st.error(f"Error processing video data: {str(e)}")
                    failed_batches += 1
                    break

        if failed_batches > 0:
            st.warning(f"Failed to fetch data for {failed_batches} batch(es). Some videos may be missing.")

        return video_data

    def categorize_by_date(self, published_date: str) -> str:
        """Categorize videos by publication date with improved error handling."""
        if not published_date:
            return "Unknown"
            
        try:
            # Handle different ISO format variations
            if published_date.endswith('Z'):
                pub_date = datetime.fromisoformat(published_date.replace("Z", "+00:00"))
            else:
                pub_date = datetime.fromisoformat(published_date)
            
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
                
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse date '{published_date}': {str(e)}")
            return "Unknown"
        except Exception as e:
            logger.error(f"Unexpected error categorizing date '{published_date}': {str(e)}")
            return "Unknown"


