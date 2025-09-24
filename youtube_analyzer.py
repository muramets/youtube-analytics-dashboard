import time
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Union, Any

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
        self.source_video_cache: Dict[str, Dict[str, Union[str, List[str]]]] = {}

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
    def get_video_data(_self, video_ids: List[str]) -> tuple[Dict[str, Dict], float]:
        """Fetch video data from YouTube API in batches with caching."""
        if not video_ids:
            return {}, 0.0

        video_data: Dict[str, Dict] = {}
        failed_batches = 0
        max_retries = 3
        marker = time.time()

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

                    if not data.get("items") and len(batch_ids) <= len(video_data):
                        # Assume cache hit
                        marker = data.get("nextPageToken", "")
                        break

                    for item in data.get("items", []):
                        video_id = item["id"]
                        snippet = item.get("snippet", {})
                        statistics = item.get("statistics", {})
                        live_details = item.get("liveStreamingDetails")

                        is_live = snippet.get("liveBroadcastContent", "none") == "live" or bool(live_details)

                        video_data[video_id] = {
                            "title": snippet.get("title", "Unknown Title"),
                            "description": snippet.get("description", ""),
                            "tags": snippet.get("tags", []),
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

        return video_data, marker

    def fetch_source_video_metadata(self, video_url: str) -> Optional[Dict[str, Union[str, List[str]]]]:
        """Fetch metadata (title, description, tags) for the provided video URL."""
        if not video_url:
            return None

        video_id = video_url.split("v=")[-1]
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            return None

        if video_id in self.source_video_cache:
            return self.source_video_cache[video_id]

        params = {
            "part": "snippet",
            "id": video_id,
            "key": self.api_key,
        }

        try:
            response = self.session.get(self.base_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])
            if not items:
                return None

            snippet = items[0].get("snippet", {})
            metadata = {
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "tags": snippet.get("tags", []),
            }
            self.source_video_cache[video_id] = metadata
            return metadata

        except requests.RequestException as e:
            logger.error(f"Source video metadata fetch failed: {e}")
            st.warning("Unable to load source video metadata.")
            return None

    @staticmethod
    def _normalize_text(text: str) -> List[str]:
        if not text:
            return []
        words = re.findall(r"[a-zA-Z0-9]+", text.lower())
        return words

    def compare_source_with_video(self, source_meta: Dict[str, Union[str, List[str]]],
                                  video_data: Dict[str, Any]) -> Dict[str, str]:
        """Compute overlap metrics between source metadata and a video's metadata."""
        result = {
            "common_title_words": "",
            "common_description_words": "",
            "common_tags": "",
            "different_tags": "",
        }

        if not source_meta:
            return result

        source_title_words = set(self._normalize_text(source_meta.get("title", "")))
        source_description_words = set(self._normalize_text(source_meta.get("description", "")))
        source_tags = set([tag.lower() for tag in source_meta.get("tags", [])])

        # API data might include title/description, otherwise use csv title
        video_title_words = set(self._normalize_text(video_data.get("title", "")))
        video_description_words = set(self._normalize_text(video_data.get("description", "")))
        video_tags = set([tag.lower() for tag in video_data.get("tags", [])])

        result["common_title_words"] = ", ".join(sorted(source_title_words & video_title_words))
        result["common_description_words"] = ", ".join(sorted(source_description_words & video_description_words))
        result["common_tags"] = ", ".join(sorted(source_tags & video_tags))
        result["different_tags"] = ", ".join(sorted(video_tags - source_tags))

        return result

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


