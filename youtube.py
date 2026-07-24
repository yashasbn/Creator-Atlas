"""
YouTube Channel Info Fetcher
Fetches public channel details using YouTube Data API v3.


Dependencies:
   pip install google-api-python-client python-dotenv spacy requests
   python -m spacy download en_core_web_sm
"""


import os
import json
import time
from collections import Counter


import requests
import spacy
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv


# Lazy-loaded spaCy model (loaded on first use to avoid import-time cost)
_NLP = None




def _get_nlp():
   """Load and cache the spaCy English model."""
   global _NLP
   if _NLP is None:
       try:
           _NLP = spacy.load("en_core_web_sm")
       except OSError as exc:
           raise RuntimeError(
               "spaCy model 'en_core_web_sm' is not installed. "
               "Run: python -m spacy download en_core_web_sm"
           ) from exc
   return _NLP




def extract_person_name(text: str) -> str | None:
   """
   Extract the most frequently mentioned PERSON entity from text using spaCy NER.
   Ties are broken by first occurrence.


   Args:
       text: Free-form text to scan for person names.


   Returns:
       The chosen person name, or None if no PERSON entity is found.
   """
   if not text or not text.strip():
       return None


   nlp = _get_nlp()
   doc = nlp(text)


   names = [ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON"]
   if not names:
       return None


   counts = Counter(names)
   top_count = counts.most_common(1)[0][1]
   # Preserve first-occurrence order among names tied for the top count
   for name in names:
       if counts[name] == top_count:
           return name
   return names[0]




def _is_relevant_wikipedia_page(data: dict, context_terms: list[str]) -> bool:
   """
   Decide whether a Wikipedia summary is actually about the person we want.


   A page is considered relevant if its title/description/extract mentions
   any of the provided context terms (e.g. the channel handle/title, or
   generic creator terms like 'youtube'/'youtuber').
   """
   haystack = " ".join(
       str(x) for x in [
           data.get("title"),
           data.get("displaytitle"),
           data.get("description"),
           data.get("extract"),
       ] if x
   ).lower()
   if not haystack:
       return False
   return any(term.lower() in haystack for term in context_terms if term)




def fetch_wikipedia_summary(name: str, context_terms: list[str] | None = None) -> dict:
   """
   Query the Wikipedia REST API for a summary of the given name.
   First tries to search for matching pages, then fetches the summary.

   Args:
       name: Person name to look up.
       context_terms: Optional keywords that must appear in the page for it
           to be considered relevant (e.g. channel title, handle, 'youtube').
           If provided and none of them are found in the page's title,
           description, or extract, the result is discarded as 'not_relevant'.

   Returns:
       Dictionary with keys: name, found (bool), and either full page fields
       on success or 'error' describing why the lookup failed
       (not_found, disambiguation, not_relevant, request_error, ...).
   """
   result: dict = {"name": name, "found": False}
   
   # First, try to search for pages matching the name
   search_url = "https://en.wikipedia.org/w/api.php"
   search_params = {
       "action": "query",
       "format": "json",
       "list": "search",
       "srsearch": name,
       "srlimit": 3,  # Limit to top 3 results to reduce requests
       "utf8": 1,
   }
   
   try:
       search_response = requests.get(
           search_url,
           params=search_params,
           headers={"User-Agent": "youtube-channel-info/1.0"},
           timeout=10,
       )
   except requests.RequestException as exc:
       result["error"] = f"request_error: {exc}"
       return result
   
   if search_response.status_code == 429:
       result["error"] = "rate_limited"
       return result
   if not search_response.ok:
       result["error"] = f"http_{search_response.status_code}"
       return result
   
   try:
       search_data = search_response.json()
   except ValueError:
       result["error"] = "invalid_response"
       return result
   
   search_results = search_data.get("query", {}).get("search", [])
   
   # Try to get summary for each search result
   for idx, search_result in enumerate(search_results):
       page_title = search_result.get("title")
       if not page_title:
           continue
       
       # Add a small delay between requests to avoid rate limiting
       if idx > 0:
           time.sleep(0.5)
       
       # Try to fetch the summary for this page
       url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(page_title)}"
       
       try:
           response = requests.get(
               url,
               headers={"User-Agent": "youtube-channel-info/1.0"},
               timeout=10,
           )
       except requests.RequestException:
           continue
       
       if response.status_code == 429:
           result["error"] = "rate_limited"
           return result
       if response.status_code == 404:
           continue
       if not response.ok:
           continue
       
       try:
           data = response.json()
       except ValueError:
           continue
       
       if data.get("type") == "disambiguation":
           continue
       
       # Check if this page is relevant to the context
       if context_terms and not _is_relevant_wikipedia_page(data, context_terms):
           continue
       
       # Found a relevant page, populate the result
       content_urls = data.get("content_urls", {}) or {}
       desktop_urls = content_urls.get("desktop", {}) or {}
       mobile_urls = content_urls.get("mobile", {}) or {}
       thumbnail = data.get("thumbnail") or {}
       original_image = data.get("originalimage") or {}
       coordinates = data.get("coordinates") or {}
       
       result.update(
           {
               "found": True,
               # Core identity
               "type": data.get("type"),
               "title": data.get("title"),
               "displaytitle": data.get("displaytitle"),
               "namespace": (data.get("namespace") or {}).get("text"),
               "wikibase_item": data.get("wikibase_item"),
               "pageid": data.get("pageid"),
               "lang": data.get("lang"),
               "dir": data.get("dir"),
               "revision": data.get("revision"),
               "tid": data.get("tid"),
               "timestamp": data.get("timestamp"),
               "description": data.get("description"),
               "description_source": data.get("description_source"),
               # Text
               "extract": data.get("extract"),
               "extract_html": data.get("extract_html"),
               # Images
               "thumbnail": {
                   "source": thumbnail.get("source"),
                   "width": thumbnail.get("width"),
                   "height": thumbnail.get("height"),
               } if thumbnail else None,
               "original_image": {
                   "source": original_image.get("source"),
                   "width": original_image.get("width"),
                   "height": original_image.get("height"),
               } if original_image else None,
               # Links
               "url": desktop_urls.get("page"),
               "urls": {
                   "desktop": {
                       "page": desktop_urls.get("page"),
                       "revisions": desktop_urls.get("revisions"),
                       "edit": desktop_urls.get("edit"),
                       "talk": desktop_urls.get("talk"),
                   },
                   "mobile": {
                       "page": mobile_urls.get("page"),
                       "revisions": mobile_urls.get("revisions"),
                       "edit": mobile_urls.get("edit"),
                       "talk": mobile_urls.get("talk"),
                   },
                   "api": data.get("api_urls"),
               },
               # Location (present for people with a birthplace, etc.)
               "coordinates": {
                   "lat": coordinates.get("lat"),
                   "lon": coordinates.get("lon"),
               } if coordinates else None,
           }
       )
       return result
   
   # No matching pages found
   result["error"] = "not_found"
   return result


# Load environment variables from .env file
load_dotenv()


# Hardcoded channel name (will be replaced by UI input later)
CHANNEL_NAME = "codebasics"




def get_youtube_client():
   """
   Create and return a YouTube API client.
   Reads API key from YOUTUBE_API_KEY environment variable.
   """
   api_key = os.environ.get("YOUTUBE_API_KEY")
   if not api_key:
       raise ValueError("YOUTUBE_API_KEY environment variable is not set")
  
   return build("youtube", "v3", developerKey=api_key)




def resolve_channel_id(youtube, channel_name: str) -> str | None:
   """
   Resolve a channel name/handle to a channel ID.
  
   Strategy:
   1. First try channels.list with forHandle (1 quota unit)
   2. Fall back to search.list with type=channel (100 quota units)
  
   Args:
       youtube: YouTube API client
       channel_name: Channel name or handle to search for
      
   Returns:
       Channel ID if found, None otherwise
   """
   # Clean up the channel name - remove @ if present for handle lookup
   handle = channel_name.lstrip("@")
  
   # Method 1: Try forHandle lookup (1 quota unit)
   try:
       response = youtube.channels().list(
           part="id",
           forHandle=handle
       ).execute()
      
       if response.get("items"):
           return response["items"][0]["id"]
   except HttpError:
       pass  # Fall through to search method
  
   # Method 2: Fall back to search (100 quota units)
   response = youtube.search().list(
       part="snippet",
       q=channel_name,
       type="channel",
       maxResults=1
   ).execute()
  
   if response.get("items"):
       return response["items"][0]["snippet"]["channelId"]
  
   return None




def get_channel_details(youtube, channel_id: str) -> dict:
   """
   Fetch full channel details using channel ID.
  
   Args:
       youtube: YouTube API client
       channel_id: YouTube channel ID
      
   Returns:
       Dictionary with channel details
   """
   response = youtube.channels().list(
       part="snippet,statistics,contentDetails,brandingSettings",
       id=channel_id
   ).execute()
  
   if not response.get("items"):
       raise ValueError(f"Channel with ID '{channel_id}' not found")
  
   channel = response["items"][0]
   snippet = channel.get("snippet", {})
   statistics = channel.get("statistics", {})
   content_details = channel.get("contentDetails", {})
   branding = channel.get("brandingSettings", {}).get("channel", {})
   thumbnails = snippet.get("thumbnails", {})
  
   return {
       "channel_title": snippet.get("title"),
       "channel_id": channel_id,
       "description": snippet.get("description"),
       "custom_url": snippet.get("customUrl"),
       "published_date": snippet.get("publishedAt"),
       "country": snippet.get("country") or branding.get("country"),
       "subscriber_count": statistics.get("subscriberCount"),
       "video_count": statistics.get("videoCount"),
       "view_count": statistics.get("viewCount"),
       "thumbnails": {
           "default": thumbnails.get("default", {}).get("url"),
           "medium": thumbnails.get("medium", {}).get("url"),
           "high": thumbnails.get("high", {}).get("url"),
       },
       "uploads_playlist_id": content_details.get("relatedPlaylists", {}).get("uploads"),
   }




def fetch_channel_info(channel_name: str) -> dict:
   """
   Main function to fetch channel info given a channel name.
  
   Args:
       channel_name: Name or handle of the YouTube channel
      
   Returns:
       Dictionary containing channel details
      
   Raises:
       ValueError: If API key is missing or channel not found
       HttpError: If API request fails (quota exceeded, invalid key, etc.)
   """
   youtube = get_youtube_client()
  
   # Resolve channel name to ID
   channel_id = resolve_channel_id(youtube, channel_name)
   if not channel_id:
       raise ValueError(f"Channel '{channel_name}' not found")
  
   # Fetch full channel details
   details = get_channel_details(youtube, channel_id)


   # Enrich with Wikipedia info about a person mentioned in channel title, custom URL, or description
   # Search in: channel title, custom URL, channel name/handle, and description
   text_to_search = " ".join(filter(None, [
       details.get("channel_title"),
       (details.get("custom_url") or "").lstrip("@"),
       channel_name.lstrip("@"),
       details.get("description"),
       
   ]))
   person_name = extract_person_name(text_to_search)
   
   # If person name not found, try searching for channel title itself
   if person_name is None:
       channel_title = details.get("channel_title")
       if channel_title:
           person_name = channel_title
   
   if person_name is None:
       details["person_info"] = {"found": False, "error": "no_person_found"}
   else:
       # Build context terms so we only accept a Wikipedia page that actually
       # relates to this channel/creator (avoids picking an unrelated person
       # with the same name).
       context_terms = [
           term for term in [
               details.get("channel_title"),
               (details.get("custom_url") or "").lstrip("@"),
               channel_name.lstrip("@"),
               "youtube",
               "youtuber",
           ] if term
       ]
       details["person_info"] = fetch_wikipedia_summary(person_name, context_terms)


   return details




def handle_api_error(error: HttpError) -> str:
   """
   Parse and return a user-friendly error message from HttpError.
   """
   error_reason = ""
   try:
       error_details = json.loads(error.content.decode("utf-8"))
       errors = error_details.get("error", {}).get("errors", [])
       if errors:
           error_reason = errors[0].get("reason", "")
   except (json.JSONDecodeError, KeyError):
       pass
  
   if error_reason == "quotaExceeded":
       return "API quota exceeded. Daily limit of 10,000 units reached. Try again tomorrow."
   elif error.resp.status == 400 and "API key" in str(error.content):
       return "Invalid API key. Please check your YOUTUBE_API_KEY environment variable."
   elif error.resp.status == 403:
       if error_reason == "accessNotConfigured":
           return "YouTube Data API is not enabled for this project. Enable it in Google Cloud Console."
       return f"Access forbidden: {error_reason or 'Check API key permissions'}"
   elif error.resp.status == 404:
       return "Channel not found."
   else:
       return f"API error ({error.resp.status}): {error_reason or error.content.decode('utf-8')}"




if __name__ == "__main__":
   from ui import create_ui
   create_ui()
