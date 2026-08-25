# AungMin Movie Recap — React Editor Handoff

This project now uses a browser-side React editor rather than the old Streamlit-only form. The main screen is `client/src/pages/Home.tsx`; shared timeline, URL validation, platform detection, source states, and verified-output gating are in `client/src/lib/editorState.ts`.

## Run locally

Use Node.js with the project package manager, then run `pnpm install` and `pnpm dev`. Before committing a change, run `pnpm check`, `pnpm test`, and `pnpm build`.

## Current workflow

A local video file is previewed immediately in the browser. A YouTube, TikTok, Bilibili, or RedNote URL is validated and shown as a browser review when an embed URL is available. Provider download access is separate from browser review; a provider may block server-side download with HTTP 403. The UI therefore does not claim that a blocked link is ready for AI processing.

The recap panel sends the uploaded source metadata and Burmese-only prompt to the configured server procedure. The voice panel presents Burmese voice profiles and the subtitle panel is Myanmar-only. The finish panel preserves the original-duration intent, prepares an export manifest, generates a Myanmar SRT in the browser, and shows an MP4 download only when the server returns both a verified output URL and a ready flag.

## API key handling

The Google AI Studio/Gemini key is entered in the browser session field and is not committed to GitHub. Never place a literal API key in source files, tests, or screenshots.

## Important current limitation

The React editor currently has a real export-state contract and gated actions, but the production FFmpeg/TTS media-encoding service is not yet connected. `Export request accepted` means that the edit manifest was accepted; it does not mean an MP4 was created. `Final output verified` is shown only when a real non-empty output URL and ready flag are returned by the backend.

For production full-duration MP4 output, the next implementation should add a bounded multipart upload/render endpoint, temporary-file cleanup, FFmpeg availability in the runtime image, Burmese TTS generation, and a verified output URL. The source duration must be preserved and the final response must be returned only after the output file exists and has non-zero size.

## Maintainable edit map

| Change | File |
|---|---|
| Editor layout and controls | `client/src/pages/Home.tsx` |
| Timeline/link/source state logic | `client/src/lib/editorState.ts` |
| Editor state tests | `client/src/lib/editorState.test.ts` |
| Browser interaction tests | `client/src/pages/Home.test.tsx` |
| AI and export contracts | `server/routers.ts` |
| Global visual styling | `client/src/index.css` |

Do not commit `node_modules`, `dist`, `.env`, or API keys. Keep changes focused, run the full validation commands, and create a checkpoint before publishing.
