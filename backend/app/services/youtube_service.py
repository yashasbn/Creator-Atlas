import os
import time
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.config import settings
from app.observability.tracer import elapsed_ms, mark_error, tracer, youtube_api_duration, youtube_api_failures

class YouTubeService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.YOUTUBE_API_KEY or os.environ.get("YOUTUBE_API_KEY")
        if not self.api_key:
            raise ValueError("YOUTUBE_API_KEY is not set.")
        self.client = build("youtube", "v3", developerKey=self.api_key)

    def _execute(self, operation: str, request):
        """Trace each Google API RPC without exposing channel values or credentials."""
        started = time.perf_counter()
        with tracer.start_as_current_span(f"youtube.api.{operation}") as span:
            span.set_attribute("rpc.system", "googleapis")
            span.set_attribute("youtube.operation", operation)
            try:
                result = request.execute()
                youtube_api_duration.record(elapsed_ms(started), {"youtube.operation": operation, "outcome": "success"})
                return result
            except Exception as error:
                mark_error(span, error)
                youtube_api_failures.add(1, {"youtube.operation": operation, "error.type": type(error).__name__})
                youtube_api_duration.record(elapsed_ms(started), {"youtube.operation": operation, "outcome": "error"})
                raise

    def resolve_channel_id(self, channel_name: str) -> str:
        handle = channel_name.lstrip("@")
        
        # 1. Try forHandle lookup (1 quota unit)
        try:
            res = self._execute("channels.list.handle", self.client.channels().list(part="id", forHandle=handle))
            if res.get("items"):
                return res["items"][0]["id"]
        except HttpError:
            pass
        
        # 2. Search fallback (100 quota units)
        res = self._execute("search.list.channel", self.client.search().list(part="snippet", q=channel_name, type="channel", maxResults=1))
        if res.get("items"):
            return res["items"][0]["snippet"]["channelId"]
            
        raise ValueError(f"Channel '{channel_name}' not found.")

    def get_channel_details(self, channel_id: str) -> dict:
        res = self._execute("channels.list.details", self.client.channels().list(
            part="snippet,statistics,contentDetails,brandingSettings",
            id=channel_id
        ))
        
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
        playlist_res = self._execute("playlistItems.list", self.client.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=max_results
        ))

        items = playlist_res.get("items", [])
        video_ids = [item["snippet"]["resourceId"]["videoId"] for item in items if "resourceId" in item["snippet"]]

        if not video_ids:
            return []

        # Batch fetch video details
        videos_res = self._execute("videos.list", self.client.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(video_ids)
        ))

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
