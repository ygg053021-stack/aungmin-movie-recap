from urllib.parse import parse_qs, urlparse


def youtube_video_id(url: str) -> str:
    parsed = urlparse((url or '').strip())
    host = (parsed.hostname or '').lower().removeprefix('www.')
    parts = [part for part in parsed.path.split('/') if part]
    if host in {'youtu.be'} and parts:
        return parts[0]
    if parts and parts[0] in {'shorts', 'embed', 'live'} and len(parts) > 1:
        return parts[1]
    return parse_qs(parsed.query).get('v', [''])[0]


def fetch_public_transcript(url: str) -> str:
    video_id = youtube_video_id(url)
    if not video_id:
        raise ValueError('A valid YouTube video or Shorts link is required for transcript recap.')
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript = YouTubeTranscriptApi().fetch(video_id, languages=['my', 'en'])
    except Exception as exc:
        raise ValueError('Public captions are unavailable for this YouTube video. Upload the authorized video file to create a recap.') from exc
    lines = [snippet.text.strip() for snippet in transcript if getattr(snippet, 'text', '').strip()]
    if not lines:
        raise ValueError('The YouTube video has no readable public captions.')
    return '\n'.join(lines)
