from urllib.parse import parse_qs, urlparse
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from app.ingestion.base_extractor import BaseExtractor
from app.models.knowledge_source import KnowledgeSource


def extract_video_id_from_url(url: str) -> str:
    parsed = urlparse(url) # Slices the url into structured segments 

    if parsed.netloc.endswith("youtu.be"): # netloc is the youtube.com part
        return parsed.path.lstrip("/") # removes / and returns the query

    if parsed.netloc and "youtube.com" in parsed.netloc: # if browser url
        query_params = parse_qs(parsed.query) # query -> removes the ? part from youtube.com and parse_qs -> converts text into clean python dictionary
        if "v" in query_params and query_params["v"]:  # Ex : "v": ["ZkBTTlH7bBU"] -> the unique id
            return query_params["v"][0] 

    return url


class YouTubeExtractor(BaseExtractor):
    def extract(self, source: KnowledgeSource):
        video_id = extract_video_id_from_url(source.metadata["url"])

        yt_api = YouTubeTranscriptApi()
        transcript_data = yt_api.fetch(video_id)

        formatter = TextFormatter()
        clean_text = formatter.format_transcript(transcript_data)

        source.raw_content = clean_text.replace("\n", " ")

        return source