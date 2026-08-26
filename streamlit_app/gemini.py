from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Callable

from .config import MODEL_NAME, SourceInfo
from .media import prepare_quick_media, probe_duration

# The reference app uses gemini-3.7-flash, but a temporary 503 can affect one
# model while another remains available. Keep the reference model in the list
# and try the stable Flash model first for the free-tier path.
MODEL_CANDIDATES = ("gemini-2.5-flash", MODEL_NAME)
MAX_RETRIES = 3
MAX_FILE_PROCESS_SECONDS = 90
ProgressCallback = Callable[[int, str, float], None]


def _get_client(api_key: str):
    if not api_key or not api_key.strip():
        raise ValueError("Google AI Studio API key မထည့်ရသေးပါ။")
    try:
        from google import genai
    except ImportError as exc:
        raise ImportError("google-genai package မရှိသေးပါ။ requirements.txt ကို install ပြီး Streamlit app ကို reboot လုပ်ပါ။") from exc
    return genai.Client(api_key=api_key.strip())


def _error_code(error: Exception) -> str:
    match = re.search(r"\b([45]\d{2})\b", str(error))
    return match.group(1) if match else ""


def _compact_error(error: Exception) -> str:
    text = " ".join(str(error).split())
    if len(text) > 360:
        text = text[:357] + "..."
    return text or error.__class__.__name__


def _is_retryable(error: Exception) -> bool:
    text = str(error).lower()
    code = _error_code(error)
    return code in {"408", "429", "500", "502", "503", "504"} or any(
        token in text
        for token in (
            "unavailable",
            "high demand",
            "temporarily",
            "resource_exhausted",
            "rate limit",
            "too many requests",
            "connection reset",
            "connection aborted",
            "timed out",
            "timeout",
            "closed",
        )
    )


def _retry_delay(error: Exception, attempt: int) -> float:
    text = str(error)
    for pattern in (r"retry(?:\s+in|delay)\s*[:=]?\s*([\d.]+)s", r"retryDelay['\"]?\s*[:=]\s*['\"]([\d.]+)s"):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            try:
                return max(1.0, min(10.0, float(match.group(1)) + 0.35))
            except ValueError:
                pass
    return float(min(8, 2 ** (attempt + 1)))


def _retry_operation(operation: Callable[[], Any], label: str) -> Any:
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            return operation()
        except Exception as exc:
            last_error = exc
            if not _is_retryable(exc) or attempt == MAX_RETRIES - 1:
                break
            time.sleep(_retry_delay(exc, attempt))
    assert last_error is not None
    code = _error_code(last_error)
    suffix = f" ({code})" if code else ""
    raise ValueError(f"Gemini {label} မအောင်မြင်ပါ{suffix}။ { _compact_error(last_error) }") from last_error


def _retry_model_operation(api_key: str, operation: Callable[[Any, str], Any], label: str, client: Any | None = None) -> tuple[Any, str]:
    """Call one model with retries, then fail over without closing the client."""
    failures: list[str] = []
    active_client = client or _get_client(api_key)
    for model in MODEL_CANDIDATES:
        for attempt in range(MAX_RETRIES):
            try:
                return operation(active_client, model), model
            except Exception as exc:
                code = _error_code(exc)
                failures.append(f"{model}{f'/{code}' if code else ''}: {_compact_error(exc)}")
                if "client has been closed" in str(exc).lower():
                    active_client = _get_client(api_key)
                if not _is_retryable(exc) or attempt == MAX_RETRIES - 1:
                    break
                time.sleep(_retry_delay(exc, attempt))
    summary = " | ".join(failures[-4:])
    if any("/401" in item or "/403" in item or "api key" in item.lower() for item in failures):
        raise ValueError("Gemini API key မမှန်ပါ သို့မဟုတ် permission မရှိပါ။ API key ကို Google AI Studio မှာစစ်ပြီး ပြန်ထည့်ပါ။")
    if any("/503" in item or "high demand" in item.lower() or "unavailable" in item.lower() for item in failures):
        raise ValueError(f"Gemini server နှစ်ခုလုံး ခဏအလုပ်များနေပါသည်။ 503 retry နှင့် fallback model များကို စမ်းပြီးပါပြီ။ 30–60 စက္ကန့်စောင့်ပြီး ပြန်စမ်းပါ။ နောက်ဆုံးအခြေအနေ: {summary}")
    raise ValueError(f"Gemini {label} မအောင်မြင်ပါ။ သုံးနိုင်သော model များကို စမ်းပြီးပါပြီ။ နောက်ဆုံးအခြေအနေ: {summary}")


def _mime_for(path: str) -> str:
    return {".webm": "video/webm", ".mov": "video/quicktime", ".mkv": "video/x-matroska"}.get(Path(path).suffix.lower(), "video/mp4")


def upload_to_gemini(api_key: str, media_path: str, client: Any | None = None) -> Any:
    if not Path(media_path).is_file():
        raise ValueError("Gemini analysis အတွက် video file မတွေ့ပါ။")
    # Keep a strong reference to the client while the SDK request is in flight.
    # A temporary `_get_client(...).files.upload(...)` expression can be
    # garbage-collected by Streamlit between reruns and leaves httpx closed.
    active_client = client or _get_client(api_key)
    uploaded = _retry_operation(lambda: active_client.files.upload(file=str(media_path)), "video upload")
    if not getattr(uploaded, "uri", None):
        raise ValueError("Gemini video upload က file URI မပြန်ပါ။")
    return uploaded


def _state_name(file_obj: Any) -> str:
    state = getattr(file_obj, "state", None)
    name = getattr(state, "name", state)
    return str(name or "").upper()


def wait_for_file_active(api_key: str, uploaded: Any, progress: ProgressCallback | None = None, started: float | None = None, client: Any | None = None) -> Any:
    """Poll the uploaded Gemini file until the API marks it ACTIVE."""
    current = uploaded
    active_client = client or _get_client(api_key)
    file_name = getattr(current, "name", None)
    if not file_name:
        return current
    begin = started or time.monotonic()
    deadline = time.monotonic() + MAX_FILE_PROCESS_SECONDS
    while True:
        state = _state_name(current)
        if state in {"", "ACTIVE", "SUCCEEDED"}:
            return current
        if state in {"FAILED", "ERROR"}:
            raise ValueError("Gemini video file processing failed. Video ကို MP4 အဖြစ်ပြန်တင်ပြီး စမ်းပါ။")
        if time.monotonic() >= deadline:
            raise ValueError("Gemini video processing ကြာမြင့်နေပါသည်။ Video ကို 180 စက္ကန့်အောက် analysis proxy ဖြင့် ပြန်စမ်းပါ။")
        elapsed = time.monotonic() - begin
        if progress:
            progress(22, f"Gemini video ကို ပြင်ဆင်နေသည် ({state or 'PROCESSING'})", begin)
        time.sleep(2)
        current = _retry_operation(lambda: active_client.files.get(name=file_name), "file status check")
        if progress:
            progress(28, "Gemini video processing ပြီးရန် စောင့်နေသည်", begin)


def extract_gemini_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text).strip()
    if isinstance(response, dict):
        parts = response.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        return "\n".join(part.get("text", "") for part in parts if part.get("text")).strip()
    return ""


def _parse_bundle(text: str) -> dict:
    if not text:
        raise ValueError("Gemini က recap စာမူမပြန်ပါ။")
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE | re.DOTALL)
    try:
        bundle = json.loads(cleaned)
    except json.JSONDecodeError:
        bundle = {"recap_bn": text, "subtitle_bn": text, "subtitle_en": ""}
    recap = str(bundle.get("recap_bn", "")).strip()
    if not recap:
        raise ValueError("Gemini က empty recap ပြန်ပါသည်။ Video ကို ပြန်စမ်းပါ။")
    return {
        "recap_bn": recap,
        "subtitle_bn": str(bundle.get("subtitle_bn", recap)).strip(),
        "subtitle_en": str(bundle.get("subtitle_en", "")).strip(),
    }


def generate_recap_bundle(
    api_key: str,
    source: SourceInfo,
    media_path: str,
    style: str,
    detail: str,
    speed: float,
    flipped: bool,
    progress: ProgressCallback | None = None,
) -> dict:
    started = time.monotonic()
    if progress:
        progress(8, "Video ကို analysis အတွက် ပြင်ဆင်နေသည်", started)
    quick_path = prepare_quick_media(media_path)
    client = _get_client(api_key)
    if progress:
        progress(14, "Gemini ဆီ video တင်နေသည်", started)
    uploaded = upload_to_gemini(api_key, quick_path, client)
    if progress:
        progress(20, "Gemini video file ကို စစ်နေသည်", started)
    active_file = wait_for_file_active(api_key, uploaded, progress, started, client)
    duration = probe_duration(quick_path)
    target = "၅၀၀ မှ ၇၀၀" if duration else "တိုတောင်းပြီး အဓိကအချက်များပါဝင်သည့်"
    prompt = f"""ပေးထားသော video ကို အစမှအဆုံး သေချာကြည့်ပါ။ Video မှာ အသံမရှိလျှင် မြင်ကွင်းများကိုသာ အခြေခံပါ။ အသံရှိလျှင် audio/dialogue နဲ့ visual scene နှစ်ခုလုံးကို ပေါင်းစပ်ပါ။ Video ကို speed {speed:.2f}x ဖြင့်ပြင်ထားပြီး {"ဘယ်ညာ flip ပြင်ထားသည်" if flipped else "မူရင်းဦးတည်ချက်အတိုင်းဖြစ်သည်"}။

မြန်မာ movie recap narrator စာမူကို ဖန်တီးပါ။ မူရင်းမှာမပါတဲ့အချက် မထည့်ပါနှင့်။ Scene အစဉ်မလွဲပါနှင့်။ ဇာတ်ကောင်အမည်ကို တိကျစွာသုံးပါ။ ဇာတ်ကောင်အမည်နေရာတွင် မင်း၊ မင်း၏၊ မင်းတို့၊ မင်းရဲ့ ဟူသော နာမ်စားများ မသုံးပါနှင့်။ Output သည် မြန်မာစာဖြင့်သာ ဖြစ်ရမည်။ TTS ဖတ်ရန် သဘာဝကျသော ပုဒ်ဖြတ်ပုဒ်ရပ် သုံးပါ။ Target length သည် Quick Recap အတွက် {target} မြန်မာစာလုံးဝန်းကျင် ဖြစ်ရမည်။ တစ်မိနစ်ခန့်အတွင်း ဖတ်ပြီးဆုံးနိုင်အောင် တိုတောင်းစွာရေးပါ။ Narration style သည် {style} ဖြစ်ရမည်။ Detail level သည် {detail} ဖြစ်ရမည်။

JSON တစ်ခုတည်းကိုသာ ပြန်ပေးပါ။ Markdown မသုံးပါနှင့်။ JSON key နှစ်ခုကို အောက်ပါအတိုင်း တိတိကျကျသုံးပါ:
{{"recap_bn":"မြန်မာ recap narration စာမူ","subtitle_bn":"မြန်မာစာတန်းထိုးရန် စာမူ"}}"""
    inputs = [
        {"type": "video", "uri": getattr(active_file, "uri", uploaded.uri), "mime_type": getattr(active_file, "mime_type", None) or _mime_for(quick_path)},
        {"type": "text", "text": prompt},
    ]
    if progress:
        progress(32, "Gemini က scene များကို analysis လုပ်နေသည်", started)
    response, used_model = _retry_model_operation(
        api_key,
        lambda client, model: client.interactions.create(
            model=model,
            input=inputs,
            generation_config={"temperature": 0.15, "thinking_level": "low"},
        ),
        "video analysis",
        client,
    )
    text = extract_gemini_text(response)
    bundle = _parse_bundle(text)
    bundle["model"] = used_model
    if progress:
        progress(42, f"မြန်မာ recap script ပြီးပါပြီ ({used_model})", started)
    return bundle


def generate_recap_from_transcript(api_key: str, transcript: str, style: str, detail: str) -> dict:
    if not api_key.strip():
        raise ValueError("Google AI Studio API key မထည့်ရသေးပါ။")
    if not transcript.strip():
        raise ValueError("ဒီ link အတွက် public transcript မတွေ့ပါ။")
    prompt = f"""အောက်ပါ YouTube transcript ကို အခြေခံပြီး မြန်မာ movie recap narrator စာမူရေးပါ။ မူရင်း transcript ထဲမပါတဲ့အချက် မထည့်ပါနှင့်။ Output ကို မြန်မာစာဖြင့်သာရေးပါ။ TTS ဖတ်ရန် သဘာဝကျသော ပုဒ်ဖြတ်ပုဒ်ရပ်သုံးပါ။ Narration style သည် {style} ဖြစ်ရမည်။ Detail level သည် {detail} ဖြစ်ရမည်။

JSON တစ်ခုတည်းကိုသာ ပြန်ပေးပါ။ Markdown မသုံးပါနှင့်။ JSON key နှစ်ခုကို တိတိကျကျသုံးပါ:
{{"recap_bn":"မြန်မာ recap narration စာမူ","subtitle_bn":"မြန်မာစာတန်းထိုးရန် စာမူ"}}

TRANSCRIPT:
{transcript[:50000]}"""
    response, used_model = _retry_model_operation(
        api_key,
        lambda client, model: client.interactions.create(
            model=model,
            input=prompt,
            generation_config={"temperature": 0.15, "thinking_level": "low"},
        ),
        "transcript recap",
    )
    bundle = _parse_bundle(extract_gemini_text(response))
    bundle["model"] = used_model
    return bundle
