from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Callable

from .config import MODEL_NAME, SourceInfo
from .media import prepare_quick_media, probe_duration

# Current stable Gemini endpoints. Do not use gemini-2.5-flash here: the live
# app reported that model as unavailable to new users. 3.6 supports video input;
# 3.5 Flash-Lite is the lower-cost fallback; 3.7 remains the final fallback.
MODEL_CANDIDATES = ("gemini-3.6-flash", "gemini-3.5-flash-lite", MODEL_NAME)
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


def _is_quota_exhausted(error: Exception) -> bool:
    text = str(error).lower()
    return _error_code(error) == "429" and any(token in text for token in ("quota", "resource_exhausted", "current quota", "generativelanguage"))


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
                # A 404 model or project quota exhaustion cannot be fixed by
                # waiting three times. Skip directly to the next valid model.
                if code in {"400", "401", "403", "404"} or _is_quota_exhausted(exc):
                    break
                if not _is_retryable(exc) or attempt == MAX_RETRIES - 1:
                    break
                time.sleep(_retry_delay(exc, attempt))
    summary = " | ".join(failures[-4:])
    if any("/401" in item or "/403" in item or "api key" in item.lower() for item in failures):
        raise ValueError("Gemini API key မမှန်ပါ သို့မဟုတ် permission မရှိပါ။ API key ကို Google AI Studio မှာစစ်ပြီး ပြန်ထည့်ပါ။")
    if any("/429" in item or "quota" in item.lower() or "resource_exhausted" in item.lower() for item in failures):
        raise ValueError(f"Gemini quota ပြည့်နေပါသည်။ Model fallback များကို ချက်ချင်းစမ်းပြီးပါပြီ။ AI Studio Rate limits မှာ quota ပြန်ဖွင့်ချိန်စစ်ပါ သို့မဟုတ် အခြား project API key သုံးပါ။ နောက်ဆုံးအခြေအနေ: {summary}")
    if any("/503" in item or "high demand" in item.lower() or "unavailable" in item.lower() for item in failures):
        raise ValueError(f"Gemini server ခဏအလုပ်များနေပါသည်။ 503 retry နှင့် fallback model များကို စမ်းပြီးပါပြီ။ ခဏစောင့်ပြီး ပြန်စမ်းပါ။ နောက်ဆုံးအခြေအနေ: {summary}")
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


def _normalize_segments(raw: Any, duration: float | None = None) -> list[dict[str, float | str]]:
    if not isinstance(raw, list):
        return []
    limit = max(0.0, float(duration or 0.0))
    normalized: list[dict[str, float | str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            start = max(0.0, float(item.get("start", 0.0)))
            end = max(start, float(item.get("end", 0.0)))
        except (TypeError, ValueError):
            continue
        text_value = str(item.get("text", "")).strip()
        if not text_value or end <= start:
            continue
        if limit:
            start = min(start, limit)
            end = min(end, limit)
        if end - start < 0.5:
            continue
        segment = {"start": start, "end": end, "text": text_value[:1200]}
        english_value = str(item.get("text_en", "")).strip()
        if english_value:
            segment["text_en"] = english_value[:1200]
        normalized.append(segment)
    normalized.sort(key=lambda segment: (float(segment["start"]), float(segment["end"])))
    if not normalized or not limit:
        return normalized
    # Convert model timestamps into one deterministic, gap-free schedule. This
    # schedule is shared by segmented narration and timed subtitles, so an
    # overlap cannot double-mix audio and a gap cannot shift later captions.
    timeline: list[dict[str, float | str]] = []
    cursor = 0.0
    for index, segment in enumerate(normalized):
        start = max(cursor, float(segment["start"]))
        if index == 0:
            start = 0.0
        end = max(start + 0.5, float(segment["end"]))
        if index + 1 < len(normalized):
            next_start = max(0.0, min(limit, float(normalized[index + 1]["start"])))
            end = max(end, next_start)
        end = min(limit, end)
        if end <= start:
            continue
        item = dict(segment)
        item["start"], item["end"] = start, end
        timeline.append(item)
        cursor = end
    if timeline:
        timeline[-1]["end"] = limit
    return timeline


def _parse_bundle(text: str, duration: float | None = None) -> dict:
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
    result = {
        "recap_bn": recap,
        "subtitle_bn": str(bundle.get("subtitle_bn", recap)).strip(),
        "subtitle_en": str(bundle.get("subtitle_en", "")).strip(),
    }
    segments = _normalize_segments(bundle.get("segments"), duration)
    if segments:
        result["segments"] = segments
    return result


def _validate_full_length_bundle(bundle: dict, duration: float | None) -> None:
    """Reject a clearly short or non-scene-aware recap before it reaches TTS."""
    if not duration or duration < 15:
        return
    recap = re.sub(r"\s+", "", str(bundle.get("recap_bn", "")))
    minimum_chars = max(280, int(float(duration) * 10.0))
    if len(recap) < minimum_chars:
        raise ValueError(
            f"Recap script တိုလွန်းပါသည် ({len(recap)} characters)။ "
            f"{minimum_chars} characters အနည်းဆုံးလိုအပ်သောကြောင့် scene အားလုံးပါအောင် ပြန် generate လုပ်ပါ။"
        )
    segments = bundle.get("segments")
    if not isinstance(segments, list) or len(segments) < 4:
        raise ValueError("Scene-aware recap segments မလုံလောက်ပါ။ Video ကို scene အလိုက် ပြန် generate လုပ်ပါ။")
    coverage = sum(max(0.0, float(item.get("end", 0.0)) - float(item.get("start", 0.0))) for item in segments if isinstance(item, dict))
    if coverage < float(duration) * 0.9:
        raise ValueError("Scene timeline သည် video duration ရဲ့ 90% မဖုံးလွှမ်းသေးပါ။ Scene အစအဆုံး ပြန် generate လုပ်ပါ။")
    if any(not isinstance(item, dict) or not str(item.get("text_en", "")).strip() for item in segments):
        raise ValueError("Scene တစ်ခုချင်းစီအတွက် English subtitle translation မပြည့်စုံသေးပါ။")


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
    duration = probe_duration(media_path)
    # A short summary leaves most of the source video without meaningful narration.
    # Request a genuinely full-length recap: Burmese codepoint counts are only a
    # planning heuristic, so the post-parse guard below also rejects clearly short
    # bundles instead of silently padding them with long empty gaps.
    target_chars = max(360, int(duration * 11.5)) if duration else 700
    minimum_chars = max(280, int(duration * 10.0)) if duration else 560
    target = f"{max(minimum_chars, target_chars - 55)} မှ {target_chars + 55}"
    duration_text = f"{duration:.1f} စက္ကန့်" if duration else "မသိရသေးသောကြာချိန်"
    prompt = f"""ပေးထားသော video ကို အစမှအဆုံး သေချာကြည့်ပြီး **{duration_text} အတွင်း အစအဆုံးကို အဓိပ္ပာယ်ရှိစွာ ဖုံးလွှမ်းမည့် full-length narration** ကိုရေးပါ။ Video မှာ အသံမရှိလျှင် မြင်ကွင်းများကိုသာ အခြေခံပါ။ အသံရှိလျှင် audio/dialogue နဲ့ visual scene နှစ်ခုလုံးကို ပေါင်းစပ်ပါ။ Video ကို speed {speed:.2f}x ဖြင့်ပြင်ထားပြီး {"ဘယ်ညာ flip ပြင်ထားသည်" if flipped else "မူရင်းဦးတည်ချက်အတိုင်းဖြစ်သည်"}။

မြန်မာ movie recap narrator စာမူကို ဖန်တီးပါ။ မူရင်းမှာမပါတဲ့အချက် မထည့်ပါနှင့်။ **Video ရဲ့ ပထမ 3 seconds ကို သီးခြားစိတ်ဝင်စားစရာ hook အဖြစ် စတင်ပြီး၊ အဲဒီနောက် scene တစ်ခုချင်းစီရဲ့ လုပ်ဆောင်ချက်၊ တုံ့ပြန်မှု၊ အကြောင်းရင်းနဲ့ ရလဒ်ကို အစမှအဆုံး မကျော်ဘဲ အသေးစိတ်ဖော်ပြပါ။** Video အစ၊ အလယ်၊ အဆုံး ဘယ်အပိုင်းကိုမှ စာကြောင်းတိုနဲ့ ကျော်မသွားပါနှင့်။ Scene အသစ်တိုင်းမှာ အဲဒီ scene ရဲ့ လုပ်ဆောင်ချက်ကို အရင်ပြောပြီး နောက်မှ အဓိပ္ပာယ်/ရလဒ်ကို ပြောပါ။ မြန်မြန်ကျော်သွားတဲ့ scene များကိုလည်း အနည်းဆုံး အဓိက action နဲ့ reaction ပါအောင် ရေးပါ။ ဇာတ်ကောင်အမည်ကို တိကျစွာသုံးပါ။ ဇာတ်ကောင်အမည်နေရာတွင် မင်း၊ မင်း၏၊ မင်းတို့၊ မင်းရဲ့ ဟူသော နာမ်စားများ မသုံးပါနှင့်။ Output သည် မြန်မာစာဖြင့်သာ ဖြစ်ရမည်။ TTS ဖတ်ရန် သဘာဝကျသော ပုဒ်ဖြတ်ပုဒ်ရပ် သုံးပါ။ **Target length သည် {target} မြန်မာစာလုံးဝန်းကျင် ဖြစ်ရမည်။ အနည်းဆုံး {minimum_chars} non-space မြန်မာစာလုံး မပြည့်လျှင် output ကို မပြီးသေးဟု သတ်မှတ်ပြီး ပိုမိုအသေးစိတ် scene coverage ထပ်ရေးပါ။ {duration_text} ထက် စောပြီးမပြီး၊ ပိုပြီးမရှည်အောင် ရေးပါ။ အပိုအကြောင်းအရာ/နိဂုံးချုပ် filler မထည့်ပါနှင့်။** Narration style သည် {style} ဖြစ်ရမည်။ Detail level သည် {detail} ဖြစ်ရမည်။

**segments ကို မဖြစ်မနေ ပြန်ပေးပါ။** အနည်းဆုံး scene ၈ ခု သို့မဟုတ် video duration ၈ စက္ကန့်လျှင် တစ်ခုနှုန်းနီးပါး ခွဲပြီး၊ segment တိုင်းမှာ source `start`/`end` seconds၊ မြန်မာ narration `text` နဲ့ အဓိပ္ပာယ်တူ `text_en` ပါရမည်။ Segments ရဲ့ စုစုပေါင်းအချိန်က video ရဲ့ အနည်းဆုံး 90% ကို ဖုံးလွှမ်းရမည်။

JSON တစ်ခုတည်းကိုသာ ပြန်ပေးပါ။ Markdown မသုံးပါနှင့်။ JSON key များကို အောက်ပါအတိုင်း တိတိကျကျသုံးပါ။ `segments` ထဲက segment တိုင်းတွင် Burmese `text` နှင့် အဓိပ္ပာယ်တူ English `text_en` ကို မဖြစ်မနေထည့်ပါ။ `text_en` သည် Burmese narration ကို တိုက်ရိုက်ဘာသာပြန်ထားခြင်းဖြစ်ပြီး စာကြောင်းအလယ်မှာ မဖြတ်ပါနှင့်။
{{"recap_bn":"မြန်မာ recap narration စာမူ","subtitle_bn":"မြန်မာစာတန်းထိုးရန် စာမူ","subtitle_en":"English translation စာမူ","segments":[{{"start":0,"end":3,"text":"ပထမ ၃ စက္ကန့်အတွက် Burmese hook","text_en":"English translation of the hook"}}]}}"""

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
    bundle = _parse_bundle(text, duration)
    _validate_full_length_bundle(bundle, duration)
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
