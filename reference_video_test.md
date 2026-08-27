# Supplied reference video test record

Date: 2026-08-27
Source: `/home/ubuntu/upload/5_6075551322629742944.mp4`

## Media metadata

- Duration: 44.071383 seconds
- Video: H.264, 576x768, 30 fps, vertical 3:4 source frame
- Audio: AAC, 44.1 kHz, stereo
- File size: 3,769,196 bytes

## Observable reference behavior

The supplied video is vertical and fills the frame. The edit uses rapid hard cuts between medium shots and close-ups, with the child commonly held in the lower third or center. The source audio is character dialogue rather than an external narrator, with light background music and a phone-ringing sound effect.

Visible subtitles are Simplified Chinese, white, medium-large, bold sans-serif, bottom-centered and slightly above the bottom edge, with a subtle dark outline or shadow. The analysis found no visible blur patch covering original subtitles in this reference. A small static disclaimer-style text block appears in the top-left. A short `???` graphic appears above the parents around 00:22 as a visual cue.

## Frame inspection notes

The contact sheet confirms a 576x768 portrait composition with full-height framing: there is no black letterbox, and the main subjects remain inside the vertical frame. The source includes small vertical white disclaimer text at the upper-left edge. At approximately 22 seconds, the mother and father are visible around the child, and a white Chinese subtitle with a dark outline is centered near the lower edge. The subtitle occupies a compact band and does not cover the entire frame. The video uses the source scene itself as the preview reference; any editor preview must preserve this crop rather than showing a blank white placeholder.

## Implementation implications

This file is a reference for real render verification, not an instruction to change the product workflow. The current app requirements still require Burmese recap narration, optional subtitle/blur overlays, preview/export geometry parity, and a verified final MP4. The supplied source must be tested as a 9:16/vertical input without changing the approved voice stage unexpectedly.

## End-to-end render verification notes

The current 9:16 app-level Finish branch produced a valid 1080x1920, 30 fps H.264/AAC MP4 with a measured duration of 44.070 seconds and a non-zero file size. The real output frame preserved the full-height portrait scene and applied the selected lower blur band without showing a blank preview. The current 16:9 pipeline branch also produced a valid 1920x1080, 30 fps H.264/AAC MP4 with the same measured 44.070-second duration. Because the source is portrait, the landscape output correctly uses a centered portrait image with black side padding rather than distorting the scene.

These results verify the media path and geometry for this supplied file. They do not claim that an automatically generated Burmese script is factually perfect; that remains dependent on the selected AI analysis and the user's script approval step.


## New end-to-end regression findings

The newly supplied source is 576x768 portrait, 30 FPS, AAC stereo, with an exact duration of 44.071383 seconds. The current pipeline produced a valid 1080x1920, 30 FPS MP4 with matching 44.070-second duration and valid H.264/AAC streams.

The visual regression exposed a real subtitle failure: both the app-generated final frame and a direct FFmpeg frame using the generated SRT showed the blurred lower region but no Burmese/English recap subtitle panel. The generated SRT contained Burmese timed segments only because `make_srt()` used the timed-segment branch and did not pair each timed segment with `subtitle_en`. This is a reproduced implementation bug, not a source-video issue. The direct filter test also confirms that the output geometry and blur composition render, isolating the remaining failure to subtitle content/style placement and bilingual timed-caption construction rather than MP4 encoding.


## Subtitle filter isolation

A direct FFmpeg test with a simple English SRT and the default subtitle style rendered the text successfully. A second test with `Alignment=7` and `MarginV=1400` rendered no test text because that top-left ASS alignment placed the event outside the intended visible caption area for the filtered portrait composition. A minimal custom style rendered large text, but its placement overlapped the existing reference-style panel. The current production failure therefore has two separate causes: timed segments did not carry English paired captions, and the ASS `Alignment=7`/percentage-to-`MarginV` mapping is not a valid way to represent a y-position intended as a percentage of the output canvas. The correct fix must use a bottom/center anchored ASS layout or explicit ASS positioning (`\\pos`/per-event style) derived from the same normalized panel geometry, rather than passing a top margin as `MarginV`.


## Explicit position follow-up

After adding explicit `\\pos` tags and `original_size=1080x1920`, the final MP4 does show Burmese text, but the text is dramatically oversized and begins near the top instead of sitting inside the intended subtitle panel. A direct FFmpeg test confirms the same behavior. This indicates that the bundled libass script resolution is not matching the output canvas; output-pixel coordinates and font sizes cannot be passed directly as ASS coordinates. The fix must convert output coordinates and font size into the actual ASS PlayRes coordinate system, or use a rasterized Pillow subtitle layer at output resolution. The earlier no-caption issue is fixed, but the visual parity issue remains reproduced and is not ready to mark complete.


## Final ASS render verification

The final ASS pipeline renders visible Burmese and English captions inside the shared subtitle panel. Portrait output is 1080x1920 and landscape output is 1920x1080; both preserve the 44.070-second source duration at 30 FPS with H.264 video and AAC audio. The portrait frame shows Burmese in yellow with black outline and English in white below it. The landscape frame preserves the same normalized subtitle panel and positions the portrait source with black side padding rather than stretching it. The 27-test unittest suite passes after the final caption changes.


## Newly supplied movie short inspection

Source: `TheGangsterMessedwithaMan_butTheyDidn_tKnowHeWasaMafiaBoss__cdrama_kdrama_shorts(480P).mp4`.

Verified media facts: duration 60.000363 seconds; primary video H.264 at 480x854 and 30 FPS; primary audio AAC at 44.1 kHz stereo. The file also contains an MJPEG 1280x720 stream, which must not be mistaken for the primary movie picture during processing.

Speech-to-text returned a full English narration transcript with timestamped beats: 00:00–00:07 a man eats with his girlfriend while gangsters destroy a nearby restaurant table; 00:07–00:11.7 he remains calm; 00:11.7–00:14.9 the leader orders him to leave; 00:14.9–00:21.1 he refuses and says he is still eating while the owner explains; 00:21.1–00:24.8 the leader pushes the owner and mistreats the girlfriend; 00:24.8–00:28.5 the gangsters discover he is a mafia boss; 00:28.5–00:32.2 he defeats the gangsters; 00:32.2–00:34.4 they become frightened; 00:34.4–00:37 the leader calls his older brother; 00:37–00:40.7 the owner urges the man to run; 00:40.7–00:44 he calmly waits; 00:44–00:51 an expensive car arrives with the older brother; 00:51–00:54.3 the gangsters celebrate; 00:54.3–00:59.9 the older brother recognizes the man, beats his own men, and leaves.

The 5-second contact sheet confirms a portrait short-form edit: restaurant exterior and table action in the opening, calm male lead close-ups, gangster/owner reactions, physical confrontation, and a later arrival/reveal beat. The existing on-screen English word captions are part of the supplied reference edit and should not be treated as the Burmese/English subtitle output layer.


## Full-length real render verification

The newly supplied 60.000363-second portrait source was rendered using a detailed 14-segment Burmese recap with a dedicated 0–3 second hook. The continuous narration was accepted without silent script trimming, and the final portrait output measured exactly 60.000000 seconds at 1080x1920 and 30 FPS with H.264 video and AAC audio. The final frame strip shows Burmese yellow captions and English white captions over a separate dark panel, with the portrait source centered and blurred extension above/below.

A second real render enabled the region blur track. It produced a valid 60.000000-second 1080x1920 MP4 with the blur layer and bilingual captions present. The blur region is currently the manually configured normalized region; automatic OCR/keyframe tracking of changing original subtitle regions remains a separate capability and was not claimed as verified by this test.

The full regression suite passes 29 tests after adding the full-length bundle validator. The production prompt now requests a 3-second hook, detailed scene coverage, at least 90% scene timeline coverage, bilingual per-segment text, and a minimum duration-scaled script length; clearly short bundles are rejected before TTS rather than padded as if complete.
