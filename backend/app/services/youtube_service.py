import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.config import settings

class YouTubeService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.YOUTUBE_API_KEY or os.environ.get("YOUTUBE_API_KEY")
        if not self.api_key:
            raise ValueError("YOUTUBE_API_KEY is not set.")
        self.client = build("youtube", "v3", developerKey=self.api_key)

    def resolve_channel_id(self, channel_name: str) -> str:
        handle = channel_name.lstrip("@")
        
        # 1. Try forHandle lookup (1 quota unit)
        try:
            res = self.client.channels().list(part="id", forHandle=handle).execute()
            if res.get("items"):
                return res["items"][0]["id"]
        except HttpError:
            pass
        
        # 2. Search fallback (100 quota units)
        res = self.client.search().list(part="snippet", q=channel_name, type="channel", maxResults=1).execute()
        if res.get("items"):
            return res["items"][0]["snippet"]["channelId"]
            
        raise ValueError(f"Channel '{channel_name}' not found.")

    def get_channel_details(self, channel_id: str) -> dict:
        res = self.client.channels().list(
            part="snippet,statistics,contentDetails,brandingSettings",
            id=channel_id
        ).execute()
        
        if not res.get("items"):
            raise ValueError(f"Channel ID '{channel_id}' not found.")
            
        ch = res["items"][0]
        snippet = ch.get("snippet", {})
        stats = ch.get("statistics", {})
        content = ch.get("contentDetails", {})
        branding = ch.get("brandingSettings", {}).get("channel", {})

        return {
            "channel_id": channel_id,
            "channel_title": snippet.get("title"),
            "custom_url": snippet.get("customUrl"),
            "description": snippet.get("description"),
            "published_at": snippet.get("publishedAt"),
            "country": snippet.get("country") or branding.get("country"),
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "view_count": int(stats.get("viewCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
            "thumbnails": snippet.get("thumbnails", {}),
            "uploads_playlist_id": content.get("relatedPlaylists", {}).get("uploads")
        }

    def get_recent_videos(self, uploads_playlist_id: str, max_results: int = 20) -> list:
        if not uploads_playlist_id:
            return []
            
        # Get video IDs from uploads playlist
        playlist_res = self.client.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=max_results
        ).execute()

        items = playlist_res.get("items", [])
        video_ids = [item["snippet"]["resourceId"]["videoId"] for item in items if "resourceId" in item["snippet"]]

        if not video_ids:
            return []

        # Batch fetch video details
        videos_res = self.client.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(video_ids)
        ).execute()

        video_list = []
        for v in videos_res.get("items", []):
            snip = v.get("snippet", {})
            st = v.get("statistics", {})
            cd = v.get("contentDetails", {})
            
            video_list.append({
                "video_id": v.get("id"),
                "title": snip.get("title"),
                "description": snip.get("description"),
                "published_at": snip.get("publishedAt"),
                "view_count": int(st.get("viewCount", 0)),
                "like_count": int(st.get("likeCount", 0)),
                "comment_count": int(st.get("commentCount", 0)),
                "duration": cd.get("duration"),
                "tags": snip.get("tags", [])
            })
            
        return video_list
