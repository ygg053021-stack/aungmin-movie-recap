import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .media import prepare_quick_media, probe_duration
from .config import SourceInfo, MODEL_NAME

def upload_to_gemini(api_key: str, media_path: str) -> str:
    size = os.path.getsize(media_path)
    suffix = Path(media_path).suffix.lower()
    mime = {".webm": "video/webm", ".mov": "video/quicktime", ".mkv": "video/x-matroska"}.get(suffix, "video/mp4")
    start_payload = json.dumps({}).encode("utf-8")
    start = Request(
        "https://generativelanguage.googleapis.com/upload/v1beta/files",
        data=start_payload,
        headers={
            "x-goog-api-key": api_key.strip(),
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(size),
            "X-Goog-Upload-Header-Content-Type": mime,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(start, timeout=60) as response:
            upload_url = response.headers.get("X-Goog-Upload-URL")
        if not upload_url:
            raise ValueError("Gemini did not return a file upload URL.")
        with open(media_path, "rb") as media:
            put = Request(
                upload_url,
                data=media.read(),
                headers={
                    "Content-Length": str(size),
                    "X-Goog-Upload-Offset": "0",
                    "X-Goog-Upload-Command": "upload, finalize",
                    "Content-Type": mime,
                },
                method="POST",
            )
            with urlopen(put, timeout=600) as response:
                data = json.loads(response.read().decode("utf-8"))
        return data.get("file", {}).get("uri", "")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:700]
        raise ValueError(f"Gemini video upload failed ({exc.code}). {detail}") from exc
    except URLError as exc:
        raise ValueError("Gemini video upload could not be reached. Try a shorter video.") from exc


def extract_gemini_text(data: dict) -> str:
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    return "\n".join(part.get("text", "") for part in parts if part.get("text")).strip()


def generate_recap_bundle(api_key: str, source: SourceInfo, media_path: str, style: str, detail: str, speed: float, flipped: bool) -> dict:
    quick_path = prepare_quick_media(media_path)
    file_uri = upload_to_gemini(api_key, quick_path)
    duration = probe_duration(quick_path)
    target = "၅၀၀ မှ ၇၀၀" if duration else "တိုတောင်းပြီး အဓိကအချက်များပါဝင်သည့်"
    prompt = f"""ပေးထားသော video ကို အစမှအဆုံး သေချာကြည့်ပါ။ Video မှာ အသံမရှိလျှင် မြင်ကွင်းများကိုသာ အခြေခံပါ။ အသံရှိလျှင် audio/dialogue နဲ့ visual scene နှစ်ခုလုံးကို ပေါင်းစပ်ပါ။ Video ကို speed {speed:.2f}x ဖြင့်ပြင်ထားပြီး {"ဘယ်ညာ flip ပြင်ထားသည်" if flipped else "မူရင်းဦးတည်ချက်အတိုင်းဖြစ်သည်"}။

မြန်မာ movie recap narrator စာမူကို ဖန်တီးပါ။ မူရင်းမှာမပါတဲ့အချက် မထည့်ပါနှင့်။ Scene အစဉ်မလွဲပါနှင့်။ ဇာတ်ကောင်အမည်ကို တိကျစွာသုံးပါ။ ဇာတ်ကောင်အမည်နေရာတွင် မင်း၊ မင်း၏၊ မင်းတို့၊ မင်းရဲ့ ဟူသော နာမ်စားများ မသုံးပါနှင့်။ Output သည် မြန်မာစာဖြင့်သာ ဖြစ်ရမည်။ TTS ဖတ်ရန် သဘာဝကျသော ပုဒ်ဖြတ်ပုဒ်ရပ် သုံးပါ။ Target length သည် Quick Recap အတွက် ၅၀၀ မှ ၇၀၀ မြန်မာစာလုံးဝန်းကျင် ဖြစ်ရမည်။ တစ်မိနစ်ခန့်အတွင်း ဖတ်ပြီးဆုံးနိုင်အောင် တိုတောင်းစွာရေးပါ။ Narration style သည် {style} ဖြစ်ရမည်။ Detail level သည် {detail} ဖြစ်ရမည်။

JSON တစ်ခုတည်းကိုသာ ပြန်ပေးပါ။ Markdown မသုံးပါနှင့်။ JSON key နှစ်ခုကို အောက်ပါအတိုင်း တိတိကျကျသုံးပါ:
{{"recap_bn":"မြန်မာ recap narration စာမူ","subtitle_bn":"မြန်မာစာတန်းထိုးရန် စာမူ"}}
"""
    payload = {
        "contents": [{"parts": [{"text": prompt}, {"file_data": {"mime_type": "video/mp4", "file_uri": file_uri}}]}],
        "generationConfig": {"temperature": 0.15, "maxOutputTokens": 4500},
    }
    request = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"x-goog-api-key": api_key.strip(), "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=150) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:700]
        raise ValueError(f"Gemini analysis failed ({exc.code}). {detail}") from exc
    except URLError as exc:
        raise ValueError("Gemini could not be reached while analyzing the video.") from exc
    text = extract_gemini_text(data)
    if not text:
        raise ValueError("Gemini returned no text. Try a shorter public or uploaded video.")
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE | re.DOTALL)
    try:
        bundle = json.loads(cleaned)
    except json.JSONDecodeError:
        bundle = {"recap_bn": text, "subtitle_bn": text, "subtitle_en": ""}
    recap = str(bundle.get("recap_bn", "")).strip()
    if not recap:
        raise ValueError("Gemini returned an empty recap. Try another valid video.")
    return {
        "recap_bn": recap,
        "subtitle_bn": str(bundle.get("subtitle_bn", recap)).strip(),
        "subtitle_en": str(bundle.get("subtitle_en", "")).strip(),
    }


def generate_recap_from_transcript(api_key: str, transcript: str, style: str, detail: str) -> dict:
    if not api_key.strip():
        raise ValueError("Enter your Google AI Studio API key before generating a recap.")
    if not transcript.strip():
        raise ValueError("No public transcript was found for this link.")
    prompt = f"""အောက်ပါ YouTube transcript ကို အခြေခံပြီး မြန်မာ movie recap narrator စာမူရေးပါ။ မူရင်း transcript ထဲမပါတဲ့အချက် မထည့်ပါနှင့်။ Output ကို မြန်မာစာဖြင့်သာရေးပါ။ TTS ဖတ်ရန် သဘာဝကျသော ပုဒ်ဖြတ်ပုဒ်ရပ်သုံးပါ။ Narration style သည် {style} ဖြစ်ရမည်။ Detail level သည် {detail} ဖြစ်ရမည်။

JSON တစ်ခုတည်းကိုသာ ပြန်ပေးပါ။ Markdown မသုံးပါနှင့်။ JSON key နှစ်ခုကို တိတိကျကျသုံးပါ:
{{"recap_bn":"မြန်မာ recap narration စာမူ","subtitle_bn":"မြန်မာစာတန်းထိုးရန် စာမူ"}}

TRANSCRIPT:
{transcript[:50000]}
"""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.15, "maxOutputTokens": 4500},
    }
    request = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"x-goog-api-key": api_key.strip(), "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=150) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:700]
        raise ValueError(f"Gemini transcript recap failed ({exc.code}). {detail}") from exc
    except URLError as exc:
        raise ValueError("Gemini could not be reached while creating the transcript recap.") from exc
    text = extract_gemini_text(data)
    if not text:
        raise ValueError("Gemini returned no recap for this transcript.")
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE | re.DOTALL)
    try:
        bundle = json.loads(cleaned)
    except json.JSONDecodeError:
        bundle = {"recap_bn": text, "subtitle_bn": text, "subtitle_en": ""}
    recap = str(bundle.get("recap_bn", "")).strip()
    if not recap:
        raise ValueError("Gemini returned an empty transcript recap.")
    return {
        "recap_bn": recap,
        "subtitle_bn": str(bundle.get("subtitle_bn", recap)).strip(),
        "subtitle_en": str(bundle.get("subtitle_en", "")).strip(),
    }
