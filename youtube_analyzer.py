import time
from datetime import datetime
from typing import Dict, List

import requests
import streamlit as st


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
        video_data: Dict[str, Dict] = {}

        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i + 50]
            ids_string = ",".join(batch_ids)

            params = {
                "part": "snippet,statistics",
                "id": ids_string,
                "key": self.api_key,
            }

            try:
                response = requests.get(self.base_url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                if "error" in data:
                    st.error(
                        f"YouTube API error: {data['error'].get('message', 'Unknown error')}"
                    )
                    continue

                for item in data.get("items", []):
                    video_id = item["id"]
                    video_data[video_id] = {
                        "title": item["snippet"]["title"],
                        "published_at": item["snippet"]["publishedAt"],
                        "view_count": int(item["statistics"].get("viewCount", 0)),
                        "thumbnail_url": item["snippet"]["thumbnails"].get("medium", {}).get(
                            "url", ""
                        ),
                    }

                time.sleep(0.1)

            except requests.exceptions.RequestException as e:
                st.error(f"API request failed: {str(e)}")
            except Exception as e:
                st.error(f"Error processing video data: {str(e)}")

        return video_data

    def categorize_by_date(self, published_date: str) -> str:
        """Categorize videos by publication date"""
        try:
            pub_date = datetime.fromisoformat(published_date.replace("Z", "+00:00"))
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
        except Exception:
            return "Unknown"


