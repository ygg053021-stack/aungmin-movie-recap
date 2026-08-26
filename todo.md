# Project TODO

# Quick Recap speed target — pending implementation

- [ ] Make Quick Recap the primary action after video upload.
- [ ] Use lightweight/bounded media analysis for a concise recap.
- [ ] Keep instant local preview separate from server-side AI/render processing.
- [ ] Generate Myanmar narration and Myanmar subtitle in the Quick Recap path.
- [ ] Add progress, timeout, and retry-safe error handling.
- [ ] Validate practical processing time and document when one-minute completion is not possible.

# Latest priorities — pending implementation

- [ ] Make supported public link loading reliable with FFmpeg and a clear fallback/error state.
- [ ] Restore normal desktop page scrolling while keeping the current responsive design.
- [ ] Reduce recap processing time with lightweight preview, bounded analysis, and progress feedback.
- [ ] Remove unnecessary manual controls and keep one simple blur option only.
- [ ] Keep Myanmar narration voice and Myanmar subtitle as the required output pair.
- [ ] Remove unwanted product toolbar/branding from the app UI where technically controllable.

# Streamlit link-loading fix — pending implementation

- [x] Add `packages.txt` with the Streamlit Cloud FFmpeg system dependency.
- [x] Add source-fetch fallback that avoids multi-format merging when FFmpeg is unavailable.
- [x] Return clear provider/loading errors without exposing secrets or failing the whole page.
- [ ] Validate link preview and final render dependency installation on Streamlit Cloud after the next upload.

# Smooth preview and localization requirements — pending implementation

- [ ] Add true client-side local video preview targeted for near-instant display after upload.
- [ ] Apply speed, flip, text, blur, subtitle, and audio changes immediately without full-page reload.
- [ ] Present narration styles and voice profiles with detailed Burmese descriptions.
- [ ] Add popular Burmese and English subtitle font choices with preview.
- [ ] Preserve synchronized settings between live preview and final render.
- [ ] Add `packages.txt` to the upload package and verify FFmpeg at runtime.
- [ ] Verify the new link fallback with a public authorized test link.
- [ ] Add real subtitle font selectors and wire them to preview and render.


# Confirmed CapCut-like editor build — pending implementation

- [ ] Replace the scrolling Streamlit form with a fixed one-page editor workspace.
- [ ] Show original video immediately after upload or authorized link load.
- [ ] Keep 01 Source, 02 Recap, 03 Voice, and 04 Finish directly selectable.
- [ ] Add live speed and horizontal flip controls with matching render behavior.
- [ ] Add auto edit presets plus manual blur rectangle drag/resize controls.
- [ ] Add manual text/subtitle placement, sizing, timing, and audio controls.
- [ ] Add visual-only analysis for silent video and audio-plus-visual analysis when sound exists.
- [ ] Add Burmese recap narration plus Burmese and English subtitle layers.
- [ ] Add timing alignment with manual timeline correction.
- [ ] Add final recap preview and MP4 download for authorized media.
- [ ] Validate the complete standalone package and prepare one GitHub replacement.


# CapCut-like editor requirements — pending implementation

- [ ] Replace the long scrolling form with a fixed-height one-page editor workspace.
- [ ] Show the selected original video immediately after upload or authorized link load.
- [ ] Keep 01 Source, 02 Recap, 03 Voice, and 04 Finish selectable without page navigation.
- [ ] Add live speed control with immediate preview and rendered output consistency.
- [ ] Add horizontal flip control with immediate preview and rendered output consistency.
- [ ] Add auto editing presets for authorized media and manual override controls.
- [ ] Add manual blur rectangle controls with drag/resize behavior.
- [ ] Add manual text/subtitle placement, sizing, timing, and audio controls.
- [ ] Add original-dialogue transcription with Burmese and English subtitle layers.
- [ ] Add subtitle timing alignment and manual timeline correction controls.
- [ ] Keep original preview and final recap preview visible in the editor workflow.
- [ ] Add rights/permission notice without claiming that edits make copyrighted media copyright-free.


- [x] Establish premium dark cinematic visual system with deep violet-to-teal gradient, oversized bottom-left typography, upper-right microcopy, asymmetric negative space, and responsive behavior
- [x] Add editable AungMin Movie Recap brand name, logo, favicon, and theme settings
- [x] Add configurable workflow preferences for upload limit, session-versus-retained storage policy, enabled tools, platform formats, and media export options
- [x] Add secure server-side AI configuration without exposing credentials in client code
- [x] Add secure admin access configuration without exposing credentials in client code
- [x] Add persisted non-secret branding and workflow preferences
- [x] Build video upload workspace with progress, file validation, and preview states
- [x] Build platform format selection for YouTube, TikTok, and Facebook outputs
- [x] Build AI recap-script generation workflow with loading, success, and error states
- [x] Build voice selection, voice style, speed, and timing controls
- [x] Build subtitle styling controls and preview
- [x] Build logo and background music overlay controls
- [x] Build blur and editing controls for video overlays
- [x] Build export workflow shell for MP4/WAV/SRT selections, manifest validation, source MP4 action, and SRT download
- [x] Build admin/settings panel with editable configuration sections
- [x] Add Vitest coverage for configuration validation and core workflow contracts
- [x] Verify desktop and mobile layouts with screenshots
- [x] Run typecheck, tests, and production build
- [x] Save release checkpoint after all completed items are marked complete

- [x] Proceed autonomously with sensible defaults: no additional requirement questions, dark cinematic violet-to-teal theme, editable settings, and placeholder-safe branding
- [x] Add a safe no-credential state so the app remains usable until AI secrets are configured
- [x] Keep all user-approved defaults reversible through the settings interface

- [x] Implement real logo upload, favicon upload/application, preview, and persistence for brand assets
- [x] Wire storage policy, enabled-tool toggles, and export preferences to actual app state/config behavior
- [x] Add server-side AI configuration procedures and secure validation without exposing secrets
- [x] Add protected admin access configuration and settings update flow on the server
- [x] Add Vitest tests for settings persistence/contracts, guarded access behavior, upload workflow, and export contracts
- [x] Run and verify pnpm build before marking build-related todo complete

- [x] Implement voice style, playback speed, and timing-basis controls and connect them to recap workflow state
- [x] Expand subtitle controls to include font, color, outline/background, position, and render a live preview
- [x] Add real background music upload/settings and logo overlay placement/behavior controls
- [x] Implement video overlay editing tools for blur regions and frame targeting

- [x] Connect voice style, audio speed, and timing basis to actual recap/export workflow behavior or saved configuration
- [x] Add subtitle outline settings and make live preview reflect font, color, background, position, and outline behavior
- [x] Implement background music settings and logo overlay behavior so controls affect preview/export output
- [x] Build actual blur editing with coordinate selection, frame preview, and output behavior

- [x] Add AI config/status handling on the server with safe readiness state and fallback behavior
- [x] Wire voice style, audio speed, and timing basis into server-side recap/export payload or persisted settings
- [x] Apply subtitle font/position/outline/background choices to a true live preview component
- [x] Make logo and music controls affect on-screen preview and export payload/output
- [x] Add blur region coordinate selection and frame preview/editing UI connected to output behavior

- [x] Load persisted app settings from settings.get into the UI on startup
- [x] Implement real export preference state and a structured export payload contract
- [x] Add Vitest coverage for settings update access control, persistence contracts, upload validation, and export behavior
- [x] Make background music visible in preview and include structured music/logo data in export payload
- [x] Build blur-region coordinate selection and frame preview/editing UI tied to preview/export state

- [x] Replace simulated upload progress with real progress handling or explicitly scope it to local preparation progress
- [x] Implement export manifest procedure that accepts structured payload and drives available browser MP4/SRT actions with WAV readiness status
- [x] Add blur width/height controls and tie the full region editor to preview/export state

- [x] Add Vitest test that settings.update rejects non-admin callers
- [x] Add Vitest tests for settings get/update persistence values
- [x] Add testable upload validation helper and oversize/accepted file tests
- [x] Relabel local file progress clearly as preparation progress rather than network upload progress

- [x] Add explicit configurable media export options in settings/workflow state and connect them to the export contract/UI
- [x] Add settings get/update round-trip tests for brandName, uploadLimitMb, storagePolicy, enabledTools, and defaultPlatform

- [x] Add manifest-backed WAV readiness/download behavior instead of a standalone placeholder toast
- [x] Route SRT export through the validated export procedure
- [x] Make MP4, SRT, and WAV buttons consume one consistent export preparation result

- [x] Add mocked-DB admin settings.update then settings.get round-trip test for saved brand and workflow preferences
- [x] Add companion test for successful admin settings persistence behavior

- [x] Remove all visible Manus AI/platform branding from the user-facing AungMin Movie Recap experience
- [x] Add a clear independent app identity/configuration layer for title, logo, favicon, and metadata
- [x] Add a maintainer guide mapping one-feature-at-a-time edits to safe files and commands
- [x] Add a change-safe workflow note covering branch/checkpoint, preview, tests, rollback, and publish separation
- [x] Verify the public-facing experience contains no unintended Manus label or template placeholder

- [x] Confirm URL-first source flow: paste supported link, detect platform, fetch source, then enable recap
- [x] Define source-link states: empty, invalid, unsupported, fetching, fetched, blocked, and failed
- [x] Define final-preview gate: processing must finish before MP4/WAV/SRT export actions become available

# React browser editor migration — pending

- [x] Replace the Streamlit-only interaction model with a browser-side React editor shell.
- [x] Add instant local video preview with native playback controls.
- [x] Add timeline seek, small forward/back controls, and drag-based edit state.
- [x] Add YouTube/Shorts review embed without waiting for server download.
- [x] Preserve original video duration and source preview state.
- [x] Keep Burmese recap, Myanmar voice, Myanmar subtitles, and final export status separate.
- [x] Add tests for editor state transitions and final-output readiness.
- [x] Verify the rendered editor on desktop and mobile before packaging.

# React editor verification gaps — pending

- [x] Implement true blur drag lifecycle with pointer down/move/up and persistent coordinates.
- [x] Connect Finish flow to a real full-duration render/output service or keep readiness explicitly unverified.
- [x] Add client-side tests for upload/link review state transitions and verified final-output readiness.

# React UI verification follow-up — pending

- [x] Add client-side component-flow tests for upload-ready, review-ready, invalid-link, and panel transitions.
- [x] Wire canShowFinalOutput into Home.tsx so ready UI requires a verified output URL.
- [x] Add a client test proving ready UI appears only after verified output readiness.

# Test discovery correction — pending

- [x] Include client .tsx test files in Vitest discovery.
- [x] Run Home.test.tsx in the real pnpm test suite and verify the source/panel flows.
- [x] Add and run a Home component test for the verified-output UI gate.

# Verified output UI test correction — pending

- [x] Add and execute the Home finish-flow test that distinguishes export accepted from final output verified.

# Verified output branch — pending

- [x] Add a real or explicitly injected verified-output transition in Home.tsx.
- [x] Test both export-accepted and final-output-verified UI branches in Home.test.tsx.

# Full-duration media render backend — pending

- [ ] Add a bounded multipart video render endpoint with temporary-file cleanup.
- [ ] Preserve source duration while applying optional flip, blur, and Burmese subtitle overlay.
- [ ] Return a verified output URL only after the rendered MP4 exists and has non-zero size.
- [ ] Wire Home.tsx to upload the selected source and consume the verified output URL.
- [ ] Add render endpoint tests for rejected input and verified output contract.
- [ ] Document runtime requirements for FFmpeg and hosting limits.

# React source and export completeness — pending

- [x] Detect supported platform from YouTube, TikTok, Bilibili, and RedNote URLs.
- [ ] Model and render empty, invalid, unsupported, fetching, fetched, review-ready, blocked, failed, and upload-ready source states.
- [ ] Attempt source preparation before enabling AI recap, while preserving browser review for blocked providers.
- [x] Add actual gated MP4/WAV/SRT export actions or clearly label unavailable actions until verified output exists.

# React package delivery — pending

- [x] Create a maintainable source ZIP without node_modules or generated build output.
- [x] Include exact setup, API-key, and current media-render limitation instructions.
- [x] Verify the ZIP contents and attach the package checkpoint to the user.

# WAV export state correction — pending

- [x] Show a persistent explicit WAV unavailable state in both verified and unverified finish branches.
- [x] Test MP4, Myanmar SRT, and WAV controls in both finish-panel readiness states.

# WAV label consistency — pending

- [x] Use the explicit WAV-unavailable wording in the unverified finish branch.
- [x] Update and rerun both finish-state assertions for the same WAV-unavailable label.

# GitHub React sync — pending

- [x] Clone the user's GitHub repository with gh and inspect the current main branch.
- [x] Create a reversible backup branch/tag reference for the current Streamlit files before replacement.
- [x] Copy the tested React project source into the repository root without node_modules or dist.
- [x] Commit the React source replacement to main with a clear message.
- [x] Verify the remote root contains client, server, shared, package.json, and the React handoff guide.

# GitHub retry attempt — pending

- [x] Recheck the GitHub repository write path after the user requested a retry.
- [x] Preserve or recreate the current Streamlit backup branch before replacing main.
- [x] Retry React source upload through the authenticated repository path.
- [x] Verify the remote root and commit result from the phone-friendly repository view.

# GitHub retry after email verification — pending

- [x] Recheck repository write capability after the GitHub email verification step.
- [x] Confirm or recreate the remote Streamlit backup before replacing main.
- [x] Retry the React source commit through the authorized GitHub path.
- [x] Verify remote main and backup branch contents after the retry.

# GitHub upload retry after unsuspend — pending

- [x] Check the refreshed GitHub API write scope after unsuspending the Manus Connector.
- [x] Confirm or create the remote Streamlit backup branch.
- [x] Commit the tested React source into the selected repository.
- [x] Verify main and backup branches plus the expected root folders.

# Core usable workflow rebuild — pending

- [ ] Define a single successful upload-to-MP4 acceptance path before adding optional features.
- [ ] Add a real server-side media processing contract rather than manifest-only export.
- [ ] Add real Burmese TTS generation and synchronized Myanmar subtitle timing.
- [ ] Preserve the original source duration in the rendered output.
- [ ] Add provider-blocked link review with an explicit upload fallback.
- [ ] Run an end-to-end test with an authorized sample video before calling the app usable.
- [ ] Prepare a phone-friendly deployment path that actually runs the React frontend and backend.

# Latest backend sync — pending

- [ ] Sync the latest accepted project files, including mediaRender.ts and ACCEPTANCE.md, into GitHub main.
- [ ] Verify the new remote commit includes the media backend source and handoff documentation.

# Gemini 503 high-demand recovery — pending

- [x] Fix Gemini 503 high-demand failures with retry/backoff and stable model fallback while preserving the AungMin UI
- [x] Match the reference google-genai SDK request pattern for text analysis and keep errors actionable
- [x] Re-run syntax, unit, Streamlit startup, and real MP4 regression tests after the 503 fix
- [x] Push the verified 503 fix to GitHub main

ရက်စွဲ: 2026-08-26 — user reported live `Gemini analysis failed (503)` high-demand error and requested immediate GitHub fix.

# Gemini client lifecycle error — pending

- [x] Keep one live google-genai Client through video upload, file polling, and analysis so Streamlit cannot close the client mid-request
- [x] Add a regression test that fails if upload/analysis uses a temporary closed client
- [x] Re-run syntax, unit, SDK import, Streamlit startup, and real MP4 regression tests
- [x] Push the verified client lifecycle fix to GitHub main

ရက်စွဲ: 2026-08-26 — live app reported `Gemini video upload မအောင်မြင်ပါ: Cannot send a request, as the client has been closed.`

# Uploaded reference video matching — pending

- [x] Analyze both uploaded reference videos for duration, frame size, FPS, subtitle placement, blur behavior, logo motion, narration pacing, and speech-cut timing
- [x] Add ten readable Burmese subtitle font choices and selectable font configuration before recap generation
- [x] Add automatic/manual blur for the original Chinese subtitle region and apply it during MP4 rendering
- [x] Match reference-style Burmese subtitle placement, outline, size, and timing without rounded/missing glyphs
- [x] Match reference-style Burmese narration pacing, pauses, and sentence-break timing as closely as the selected voice engine allows
- [x] Add reference-style logo overlay motion/placement controls and preserve existing AungMin design
- [x] Run reference comparison, font rendering, subtitle, audio, and final MP4 regression tests
- [x] Push the verified reference-matching changes to GitHub main

ရက်စွဲ: 2026-08-26 — user supplied two reference videos and requested matching output behavior.

# Live quota, font, and draggable blur recovery — pending

- [x] Replace unavailable `gemini-2.5-flash` fallback with models valid for current API users, including `gemini-3.6-flash`, and make 429 handling quota-aware without repeating the same long error
- [x] Reduce recap latency by avoiding unnecessary retries/preprocessing and show concise elapsed-stage progress
- [x] Make Burmese UI/widget and rendered subtitle fonts reliably readable on Streamlit Cloud without circle/box glyphs
- [x] Add a real preview drag interaction that updates blur X/Y and clearly shows where the blur region moved from/to
- [x] Run quota fallback, font rendering, drag interaction, subtitle, and real MP4 regression tests
- [x] Push the verified live recovery changes to GitHub main

ရက်စွဲ: 2026-08-26 — live screenshots reported `gemini-2.5-flash` 404, `gemini-3.7-flash` 429 quota exceeded, unreadable Burmese glyphs, and slider-only blur controls.

# Supplied TTF and direct-manipulation editor — pending

- [x] Copy and validate the supplied Burmese TTF files, preserving Unicode-safe fonts and readable labels
- [x] Replace the generic font list with the user-supplied TTF presets and use the selected file in FFmpeg subtitles
- [x] Add video preview overlay with pointer drag and visible current X/Y/width/height values
- [x] Add automatic subtitle/blur mode with a manual fallback that writes the exact preview position and size into the render state
- [x] Add manual Burmese subtitle text/size/position preview over the blur region
- [x] Test supplied fonts, drag state, subtitle rendering, and final MP4 output
- [x] Push the supplied-font and direct-editor changes to GitHub main

ရက်စွဲ: 2026-08-26 — user supplied 11 TTF files and requested direct video-overlay blur/subtitle editing.

# Confirmed four-stage workflow rebuild — pending

- [x] Make 01 Source contain upload/link and immediate original preview only
- [x] Make 02 Recap contain Burmese translated/script text only, with editable approval before voice generation
- [x] Make 03 Voice contain Burmese narration/recap generation, original audio replacement, voice profile preview, and regenerate-after-edit flow
- [x] Make 04 Finish consume only the approved No.3 recap video and provide live blur/subtitle/font/size/position/logo finishing
- [x] Ensure final MP4 uses the approved narration and edited visual state without restoring original audio
- [x] Run full four-stage workflow, audio replacement, timing, overlay, font, and MP4 regression tests
- [ ] Push the verified four-stage workflow rebuild to GitHub main

ရက်စွဲ: 2026-08-26 — user confirmed the exact Source → Script → Voice/Recap → Finish workflow and requested GitHub implementation.
