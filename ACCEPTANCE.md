# AungMin Movie Recap — Core Usable Version

## Successful upload path

A user selects an MP4, MOV, or WebM video. The browser shows a native preview immediately without waiting for AI or server processing. The user presses Quick Recap. The server accepts the source, analyzes the video, creates a Burmese recap script, generates Myanmar narration, creates synchronized Myanmar subtitles, renders the original-duration video, and returns a verified output URL. The Final panel remains locked until the output URL exists and the output file has a non-zero size.

## Link review path

A user pastes a supported YouTube, TikTok, Bilibili, or RedNote URL. The browser detects the provider and shows an immediate review state. If the provider permits server-side source preparation, Quick Recap can continue. If the provider blocks server download, the review remains visible and the UI gives a clear upload fallback; the app must not show a false final-ready state.

## Output requirements

The rendered video preserves the original source duration and visual sequence. Burmese narration and Myanmar subtitles are the only recap language outputs in the core workflow. Blur is optional. MP4 download is enabled only after verified output bytes are available. Myanmar SRT download is enabled only after a valid script exists. WAV remains explicitly unavailable until a real voice file is verified.

## Timing expectation

Local browser preview is immediate. AI analysis, narration, and full-duration rendering are asynchronous and depend on video length, network, API response time, and server capacity. The application must show progress and a recoverable error rather than promise a fixed one-minute completion for every video.

## Not accepted as complete

A script-only result, an export manifest, a placeholder URL, a `Final MP4 ready` label without verified output bytes, or a provider link that silently fails does not satisfy the core workflow.
