# Uploaded reference video analysis

## Video 5_6075551322629742943.mp4

The analyzed clip is approximately 44 seconds, 1080x1920, 9:16 portrait, and approximately 30 FPS. It is a Burmese localization with burned-in Burmese subtitles mainly in the lower third. The subtitle target is bold, rounded Burmese sans-serif, bright yellow, with a thick black outline, medium-large size, and short phrase/word timing that follows the narrator's cadence. Original Chinese text appears around the top-left and bottom-center in places and is partially covered by Burmese overlays or lightly blurred. A circular cat-like logo is visible at top-right, with additional small handle/watermark elements around the frame. A dark blue top bar and occasional lower gradient/bar help separate overlays from the picture.

The narration is Burmese, male, expressive, energetic, and slightly dramatic. It is fast and continuous, uses short punchy sentences, has pauses generally under half a second, and uses pitch changes at sentence breaks. The analysis observed low-volume upbeat/comedic background music and occasional laughter/ding/pop accents. Editing is mainly hard cuts with dead air removed and occasional digital reframing toward faces/important objects.

## Video 5_6075551322629742944.mp4

The analyzed clip is approximately 44 seconds, 1080x1440, 3:4 portrait, and approximately 30 FPS. It contains simplified Chinese burned-in subtitles, bottom-centered, bold sans-serif, white with thin black outline and subtle shadow. Timing follows the Chinese spoken dialogue closely. A small vertical entertainment disclaimer is present in the top-left. No intentional blur, moving logo, or platform watermark was confidently observed in this version. The narration/dialogue is Mandarin Chinese with child, male off-screen, and mother voices, fast comedic pacing, short punchline timing, and short pauses after punchlines. It has low-volume whimsical BGM, phone ring, kitchen ambience, laughter, and possible surprise/ding effects. Editing uses hard cuts between medium-wide and close shots, with warm high-key lighting and saturated colors.

## Implementation target

The two files are not identical: one is a Burmese 9:16 finished-style reference, while the other is a 3:4 Chinese source-style reference. The application should therefore expose a selectable output ratio rather than force both into one crop. The safest default for the requested Burmese recap look is 9:16, 1080x1920 at 30 FPS, with lower-third Burmese subtitles using a readable Myanmar Unicode font, yellow or white text, black outline/shadow, and phrase-level timing generated from the Burmese narration. Chinese text blur should be automatic only when a detected/manual region is provided; otherwise the user should be able to drag a single blur region over the Chinese subtitle area to avoid blurring faces or the whole frame. Logo overlay should be a configurable image with position, opacity, size, and optional slow diagonal/vertical motion, not hardcoded to the reference logo. The final duration must remain equal to the processed source duration.

## Accuracy boundary

Visual placement, typography treatment, blur region, output ratio, logo behavior, and timing strategy can be implemented. Exact voice timbre and word-by-word timing cannot be guaranteed 100% with a free cloud TTS service; they depend on the selected Burmese voice and the generated script. The implementation must not claim that copyright is removed by blur/flip/speed edits; it should only provide user-controlled editing for media the user owns or is authorized to process.

## Current Gemini model and quota findings (2026-08-26)

Google's official Gemini model documentation lists `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash`, and `gemini-3.5-flash-lite` as current stable Gemini 3 endpoints. The official Gemini 3.6 Flash page states that it accepts text, image, video, audio, and PDF inputs and is optimized for speed and lower cost. The live screenshot's `gemini-2.5-flash` 404 therefore indicates that this particular API user/project cannot use that endpoint, even though the public catalog may still list it. Fallback should prioritize current Gemini 3 endpoints and should not retry a 404 model.

Google's rate-limit documentation states that quotas are applied per project, not per API key, and that 429 `RESOURCE_EXHAUSTED` requires waiting/reducing request cost; rotating keys from the same project does not create unlimited quota. Therefore 429 quota errors should skip repeated long retries, move to a valid fallback model once, and show a concise quota message with the AI Studio rate-limit link.

Sources: https://ai.google.dev/gemini-api/docs/models ; https://ai.google.dev/gemini-api/docs/models/gemini-3.6-flash ; https://ai.google.dev/gemini-api/docs/rate-limits
