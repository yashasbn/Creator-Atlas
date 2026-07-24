from datetime import datetime, timezone
from typing import List, Dict, Any

class AnalyticsEngine:
    @staticmethod
    def analyze(channel_data: Dict[str, Any], videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not videos:
            return {
                "avg_views_per_video": 0,
                "avg_likes_per_video": 0,
                "avg_comments_per_video": 0,
                "avg_engagement_rate": 0.0,
                "upload_frequency_days": 0.0,
                "top_posting_day": "Unknown",
                "top_performing_videos": [],
                "recent_upload_trend": "No videos found"
            }

        total_views = sum(v.get("view_count", 0) for v in videos)
        total_likes = sum(v.get("like_count", 0) for v in videos)
        total_comments = sum(v.get("comment_count", 0) for v in videos)
        
        n_videos = len(videos)
        avg_views = total_views / n_videos if n_videos > 0 else 0
        avg_likes = total_likes / n_videos if n_videos > 0 else 0
        avg_comments = total_comments / n_videos if n_videos > 0 else 0

        # Engagement rate = (likes + comments) / total_views
        avg_engagement = ((total_likes + total_comments) / total_views) * 100 if total_views > 0 else 0.0

        # Calculate upload frequency & day distribution
        dates = []
        days_count = {}
        for v in videos:
            pub_str = v.get("published_at")
            if pub_str:
                try:
                    dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                    dates.append(dt)
                    day_name = dt.strftime("%A")
                    days_count[day_name] = days_count.get(day_name, 0) + 1
                except ValueError:
                    pass

        dates.sort()
        frequency_days = 0.0
        if len(dates) > 1:
            total_diff = (dates[-1] - dates[0]).total_seconds() / (24 * 3600)
            frequency_days = round(total_diff / (len(dates) - 1), 1)

        top_day = max(days_count, key=days_count.get) if days_count else "Unknown"

        # Top performing videos (by views)
        sorted_videos = sorted(videos, key=lambda x: x.get("view_count", 0), reverse=True)
        top_performing = [
            {
                "title": v.get("title"),
                "view_count": v.get("view_count"),
                "like_count": v.get("like_count"),
                "published_at": v.get("published_at")
            }
            for v in sorted_videos[:3]
        ]

        # Recent trend (comparing recent 5 to overall average)
        recent_avg = sum(v.get("view_count", 0) for v in videos[:5]) / min(5, n_videos) if n_videos > 0 else 0
        if avg_views > 0:
            ratio = recent_avg / avg_views
            if ratio > 1.2:
                trend = "Trending Upward (+20% above average)"
            elif ratio < 0.8:
                trend = "Trending Downward (-20% below average)"
            else:
                trend = "Stable Performance"
        else:
            trend = "Stable"

        return {
            "avg_views_per_video": round(avg_views),
            "avg_likes_per_video": round(avg_likes),
            "avg_comments_per_video": round(avg_comments),
            "avg_engagement_rate": round(avg_engagement, 2),
            "upload_frequency_days": frequency_days,
            "top_posting_day": top_day,
            "top_performing_videos": top_performing,
            "recent_upload_trend": trend
        }
