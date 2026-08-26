import asyncio

def stamp(seconds: float) -> str:
    total = max(0, int(seconds))
    return f"00:{total // 60:02d}:{total % 60:02d},000"


def make_srt(bundle: dict, duration: float, path: str, offset: float = 0.0, mode: str = "Burmese + English") -> None:
    bn = [line.strip() for line in bundle.get("subtitle_bn", "").splitlines() if line.strip()]
    en = [line.strip() for line in bundle.get("subtitle_en", "").splitlines() if line.strip()]
    recap = [line.strip() for line in bundle.get("recap_bn", "").splitlines() if line.strip()]
    lines = bn or recap or ["AungMin Movie Recap"]
    chunk = max(3.0, (duration or len(lines) * 4) / len(lines))
    with open(path, "w", encoding="utf-8") as handle:
        for index, line in enumerate(lines, 1):
            start = max(0.0, (index - 1) * chunk + offset)
            end = max(start + 1.0, index * chunk + offset)
            english = en[index - 1] if index - 1 < len(en) else ""
            if mode == "Burmese only": english = ""
            if mode == "English only": line = english or line
            caption = line[:220] + (f"\n{english[:220]}" if english and mode == "Burmese + English" else "")
            handle.write(f"{index}\n{stamp(start)} --> {stamp(end)}\n{caption}\n\n")


def create_voiceover(script: str, path: str, voice_name: str) -> None:
    try:
        import edge_tts
        async def save_audio() -> None:
            await edge_tts.Communicate(script[:8000], voice_name).save(path)
        asyncio.run(save_audio())
    except Exception as exc:
        raise ValueError(f"Voiceover generation failed. Check the selected voice or server connection. {exc}") from exc
