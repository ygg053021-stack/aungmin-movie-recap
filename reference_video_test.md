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
