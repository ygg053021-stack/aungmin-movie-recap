import React, { ChangeEvent, PointerEvent, useEffect, useMemo, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { trpc } from "@/lib/trpc";
import { canShowFinalOutput, clampTime, detectPlatform, formatTime, getReviewUrl, getYouTubeEmbedUrl, SourcePlatform, SourceState } from "@/lib/editorState";
import { Check, ChevronLeft, ChevronRight, Clapperboard, Download, FileText, FlipHorizontal2, Gauge, KeyRound, Link2, Pause, Play, RotateCcw, Settings2, Sparkles, Subtitles, Upload, Volume2, WandSparkles } from "lucide-react";

const voices = [
  { id: "my-MM-NilarNeural", label: "အမျိုးသမီးအသံ — ကြည်လင်ပြီး တည်ငြိမ်သောဟန်" },
  { id: "my-MM-ThihaNeural", label: "အမျိုးသားအသံ — နက်ရှိုင်းပြီး ရုပ်ရှင်ဆန်သောဟန်" },
];
const styles = ["ရုပ်ရှင်ဆန်သော ဇာတ်ကြောင်းပြောဟန်", "စိတ်လှုပ်ရှားဖွယ် ဇာတ်ကြောင်းပြောဟန်", "တည်ငြိမ်ပြီး ရှင်းလင်းသောဟန်", "လျှို့ဝှက်ဆန်းကြယ်သောဟန်"];

const toSrtTime = (seconds: number) => {
  const safe = Math.max(0, seconds);
  const hours = Math.floor(safe / 3600);
  const minutes = Math.floor((safe % 3600) / 60);
  const secs = Math.floor(safe % 60);
  const millis = Math.round((safe - Math.floor(safe)) * 1000);
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")},${String(millis).padStart(3, "0")}`;
};

const buildMyanmarSrt = (script: string, totalDuration: number) => {
  const lines = script.split(/[။.!?\n]+/).map((line) => line.trim()).filter(Boolean);
  const step = Math.max(totalDuration / Math.max(lines.length, 1), 1);
  return lines.map((line, index) => `${index + 1}\n${toSrtTime(index * step)} --> ${toSrtTime(Math.min(totalDuration || (index + 1) * step, (index + 1) * step))}\n${line}\n`).join("\n");
};

export default function Home() {
  const [brand] = useState(() => localStorage.getItem("amr.brand") || "AungMin Movie Recap");
  const [file, setFile] = useState<File | null>(null);
  const [sourceUrl, setSourceUrl] = useState("");
  const [reviewUrl, setReviewUrl] = useState("");
  const [sourceState, setSourceState] = useState<SourceState>("empty");
  const [sourcePlatform, setSourcePlatform] = useState<SourcePlatform>("Unknown");
  const [sourceMessage, setSourceMessage] = useState("Video upload သို့မဟုတ် public link တစ်ခုထည့်ပါ။");
  const [videoUrl, setVideoUrl] = useState("");
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [flipped, setFlipped] = useState(false);
  const [blurEnabled, setBlurEnabled] = useState(false);
  const [blur, setBlur] = useState({ regions: "auto", frame: "full-duration", x: 28, y: 24, width: 34, height: 20 });
  const [activePanel, setActivePanel] = useState<"source" | "recap" | "voice" | "finish">("source");
  const [apiKey, setApiKey] = useState(() => sessionStorage.getItem("amr.geminiKey") || "");
  const [style, setStyle] = useState(styles[0]);
  const [voice, setVoice] = useState(voices[0].id);
  const [script, setScript] = useState("");
  const [generating, setGenerating] = useState(false);
  const [rendering, setRendering] = useState(false);
  const [exportPrepared, setExportPrepared] = useState(false);
  const [outputUrl, setOutputUrl] = useState<string | null>(null);
  const [outputVerified, setOutputVerified] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const blurDrag = useRef<{ offsetX: number; offsetY: number } | null>(null);
  const generateRecap = trpc.recap.generate.useMutation();
  const prepareExport = trpc.export.prepare.useMutation();
  const progress = duration ? (currentTime / duration) * 100 : 0;
  const subtitleLines = useMemo(() => script.split(/[။.!?\n]+/).map((line) => line.trim()).filter(Boolean).slice(0, 3), [script]);

  useEffect(() => { sessionStorage.setItem("amr.geminiKey", apiKey); }, [apiKey]);
  useEffect(() => () => { if (videoUrl) URL.revokeObjectURL(videoUrl); }, [videoUrl]);

  const onUpload = (event: ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0];
    if (!selected) return;
    if (!selected.type.startsWith("video/")) return toast.error("Video ဖိုင်ကိုသာ ရွေးပါ။");
    if (videoUrl) URL.revokeObjectURL(videoUrl);
    setFile(selected);
    setSourceState("upload-ready");
    setSourcePlatform("Unknown");
    setSourceMessage("Local preview ready. 02 · Recap ကိုရွေးပြီး စတင်နိုင်ပါပြီ။");
    setVideoUrl(URL.createObjectURL(selected));
    setReviewUrl("");
    setCurrentTime(0);
    setExportPrepared(false);
    setOutputUrl(null);
    setOutputVerified(false);
    setActivePanel("source");
    toast.success("Video preview ချက်ချင်းအဆင်သင့်ဖြစ်ပါပြီ။");
  };

  const reviewLink = () => {
    try {
      const parsedUrl = getReviewUrl(sourceUrl);
      setSourceState("fetching");
      const platform = detectPlatform(parsedUrl);
      if (platform === "Unknown") {
        setSourceState("unsupported");
        setSourcePlatform("Unknown");
        setSourceMessage("ဒီ provider ကို မထောက်ပံ့သေးပါ။ YouTube, TikTok, Bilibili သို့မဟုတ် RedNote link သုံးပါ။");
        return;
      }
      setSourcePlatform(platform);
      setReviewUrl(parsedUrl);
      setSourceState("review-ready");
      setSourceMessage(`${platform} browser review ရပါပြီ။ Provider download ခွင့်ပိတ်ထားရင် video file upload လုပ်ပါ။`);
      setFile(null);
      setVideoUrl("");
      setCurrentTime(0);
      setDuration(0);
      setExportPrepared(false);
    setOutputUrl(null);
    setOutputVerified(false);
      toast.success("Link review အဆင်သင့်ဖြစ်ပါပြီ။");
    } catch {
      setSourceState("invalid");
      setSourceMessage("Link format မမှန်ပါ။ http:// သို့မဟုတ် https:// ဖြင့်စသော link ကိုထည့်ပါ။");
      toast.error("http:// သို့မဟုတ် https:// ဖြင့်စသော link ကိုထည့်ပါ။");
    }
  };

  const seek = (value: number) => {
    const next = clampTime(value, duration);
    setCurrentTime(next);
    if (videoRef.current) videoRef.current.currentTime = next;
  };
  const togglePlay = async () => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) { await videoRef.current.play(); setPlaying(true); } else { videoRef.current.pause(); setPlaying(false); }
  };
  const nudge = (amount: number) => seek(currentTime + amount);
  const changeSpeed = (value: number) => { setSpeed(value); if (videoRef.current) videoRef.current.playbackRate = value; };

  const moveBlur = (event: PointerEvent<HTMLDivElement>) => {
    if (!blurEnabled) return;
    const rect = event.currentTarget.parentElement?.getBoundingClientRect();
    if (!rect) return;
    const offset = blurDrag.current || { offsetX: blur.width / 2, offsetY: blur.height / 2 };
    const x = ((event.clientX - rect.left) / rect.width) * 100 - offset.offsetX;
    const y = ((event.clientY - rect.top) / rect.height) * 100 - offset.offsetY;
    setBlur((current) => ({ ...current, x: Math.max(0, Math.min(100 - current.width, x)), y: Math.max(0, Math.min(100 - current.height, y)) }));
  };
  const startBlurDrag = (event: PointerEvent<HTMLDivElement>) => {
    if (!blurEnabled) return;
    const rect = event.currentTarget.parentElement?.getBoundingClientRect();
    if (!rect) return;
    const left = (blur.x / 100) * rect.width;
    const top = (blur.y / 100) * rect.height;
    blurDrag.current = { offsetX: ((event.clientX - rect.left) - left) / rect.width * 100, offsetY: ((event.clientY - rect.top) - top) / rect.height * 100 };
    event.currentTarget.setPointerCapture(event.pointerId);
  };
  const endBlurDrag = () => { blurDrag.current = null; };

  const generateScript = async () => {
    if (!file) return toast.error("AI recap အတွက် video file ကို upload လုပ်ပါ။ Link review တစ်ခုတည်းနဲ့ provider download ပိတ်ထားရင် AI analysis မလုပ်နိုင်ပါ။");
    if (!apiKey) return toast.error("Google AI Studio API key ကို ဒီ session အတွက် ထည့်ပါ။");
    setGenerating(true);
    try {
      const result = await generateRecap.mutateAsync({ language: "Burmese (မြန်မာ)", voiceStyle: style, audioSpeed: "1×", timingBasis: "Original video duration", platform: "YouTube" });
      setScript(result.script);
      setActivePanel("voice");
      toast.success("မြန်မာ recap script ရပါပြီ။");
    } catch {
      toast.error("AI recap မအောင်မြင်ပါ။ Video အတို/ရှင်းလင်းသော MP4 နဲ့ ပြန်စမ်းပါ။");
    } finally { setGenerating(false); }
  };

  const downloadSrt = () => {
    if (!script) return toast.error("မြန်မာ recap script မရှိသေးပါ။");
    const blob = new Blob([buildMyanmarSrt(script, duration)], { type: "application/x-subrip;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "aungmin-myanmar-subtitles.srt";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const renderRecap = async () => {
    if (!file || !script) return toast.error("Video နဲ့ မြန်မာ recap script နှစ်ခုလုံးလိုအပ်ပါတယ်။");
    setRendering(true);
    setExportPrepared(false);
    setOutputUrl(null);
    setOutputVerified(false);
    try {
      const result = await prepareExport.mutateAsync({ requestedFormat: "MP4", platform: "YouTube", ratio: "16:9", voice: { name: voice, style, speed: "1×", timingBasis: "Original video duration" }, subtitles: { font: "Noto Sans Myanmar", size: 34, color: "#ffffff", background: "Transparent", outline: "Soft outline", position: "Bottom" }, overlays: { logo: null, music: null }, blur: blurEnabled ? blur : null });
      if (!result.accepted) throw new Error(result.note || "Export rejected");
      setExportPrepared(true);
      setOutputUrl(result.outputUrl ?? null);
      setOutputVerified(Boolean(result.ready && result.outputUrl));
      setActivePanel("finish");
      toast.success("Export settings ကို လက်ခံပြီးပါပြီ။");
    } catch {
      toast.error("Final MP4 မပြီးသေးပါ။ ပြန်စမ်းရန် render ကို ထပ်နှိပ်ပါ။");
    } finally { setRendering(false); }
  };

  return (
    <main className="editor-app">
      <header className="editor-topbar"><div className="brand-lockup"><span className="brand-mark"><Clapperboard className="h-4 w-4" /></span><strong>{brand}</strong><Badge>EDITOR</Badge></div><div className="top-actions"><span className="desktop-only">BROWSER-SIDE VIDEO STUDIO</span><Button variant="outline" size="icon" aria-label="Settings"><Settings2 className="h-4 w-4" /></Button></div></header>
      <div className="editor-layout">
        <section className="preview-workspace">
          <div className="workspace-heading"><div><span className="eyebrow">SOURCE / PREVIEW MONITOR</span><h1>Shape the story in real time.</h1></div><span className="live-status"><i /> live preview</span></div>
          <div className="preview-frame" style={{ aspectRatio: "16 / 9" }}>
            {videoUrl ? <><video ref={videoRef} src={videoUrl} style={{ transform: flipped ? "scaleX(-1)" : "none" }} onLoadedMetadata={(event) => setDuration(event.currentTarget.duration)} onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)} onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} playsInline />{blurEnabled && <div className="blur-region" onPointerDown={startBlurDrag} onPointerMove={moveBlur} onPointerUp={endBlurDrag} onPointerCancel={endBlurDrag} style={{ left: `${blur.x}%`, top: `${blur.y}%`, width: `${blur.width}%`, height: `${blur.height}%` }}><span>BLUR</span></div>}{subtitleLines[0] && <div className="subtitle-preview">{subtitleLines[0]}</div>}</> : reviewUrl ? <iframe title="Video link review" src={getYouTubeEmbedUrl(reviewUrl) || reviewUrl} allow="autoplay; encrypted-media; picture-in-picture" allowFullScreen /> : <label className="empty-stage"><Upload className="h-6 w-6" /><span>Video file တင်ပါ၊ သို့မဟုတ် link review လုပ်ပါ</span><small>Browser preview က server processing မစောင့်ဘဲ ချက်ချင်းပြမည်</small></label>}
          </div>
          <div className="transport"><Button variant="outline" size="icon" onClick={() => nudge(-5)} disabled={!videoUrl}><ChevronLeft className="h-4 w-4" /></Button><Button className="play-button" size="icon" onClick={togglePlay} disabled={!videoUrl}>{playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}</Button><Button variant="outline" size="icon" onClick={() => nudge(5)} disabled={!videoUrl}><ChevronRight className="h-4 w-4" /></Button><span className="timecode">{formatTime(currentTime)} / {formatTime(duration)}</span><input aria-label="Video timeline" type="range" min="0" max={duration || 1} step="0.01" value={currentTime} onChange={(event) => seek(Number(event.target.value))} style={{ background: `linear-gradient(90deg,#6ee7d8 ${progress}%,rgba(255,255,255,.12) ${progress}%)` }} /><span className="speed-pill">{speed}×</span></div>
          <div className="timeline-strip"><div className="timeline-label"><span>MAIN VIDEO</span><small>{file ? `${file.name} · original duration preserved` : reviewUrl ? "link review mode" : "no source loaded"}</small></div><div className="timeline-track"><span style={{ width: `${Math.max(progress, 4)}%` }} /></div></div>
          <div className="comparison-note"><Check className="h-4 w-4" /> Original video remains available for comparison. Final output keeps the source duration.</div>
        </section>

        <aside className="control-room">
          <div className="control-heading"><div><span className="eyebrow">PRODUCTION CONTROL ROOM</span><p>One page. No hidden state.</p></div><span className="live-status"><i /> 01–04 ready</span></div>
          <nav className="editor-tabs">{(["source", "recap", "voice", "finish"] as const).map((panel, index) => <button key={panel} className={activePanel === panel ? "active" : ""} onClick={() => setActivePanel(panel)}><span>0{index + 1}</span>{panel}</button>)}</nav>

          {activePanel === "source" && <div className="panel-content"><div className="input-mode"><label><input type="file" accept="video/*" onChange={onUpload} /><Upload className="h-4 w-4" /> Upload video</label><span>or</span><div className="link-input"><Link2 className="h-4 w-4" /><Input value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} placeholder="YouTube / TikTok / Bilibili / RedNote link" /><Button onClick={reviewLink}>Review</Button></div></div><div className="control-card"><div className="card-title"><span><KeyRound className="h-4 w-4" /> Google AI Studio API key</span><Badge variant="outline">session only</Badge></div><Input type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder="Paste your Gemini API key" /><small>ဒီ key ကို GitHub ထဲ မသိမ်းပါ။ Browser session ထဲမှာသာထားပါမည်။</small></div><div className="control-card"><div className="card-title"><span>Source status</span><span className="status-text">{sourceState === "upload-ready" ? "UPLOAD READY" : sourceState === "review-ready" ? "REVIEW READY" : sourceState === "fetching" ? "FETCHING" : sourceState === "unsupported" ? "UNSUPPORTED" : sourceState === "invalid" ? "INVALID" : "WAITING"}</span></div><p>{sourceMessage} {sourcePlatform !== "Unknown" && `· ${sourcePlatform}`}</p></div></div>}

          {activePanel === "recap" && <div className="panel-content"><div className="control-card"><div className="card-title"><span><WandSparkles className="h-4 w-4" /> မြန်မာ Recap</span><Badge>QUICK ANALYSIS</Badge></div><label>ဇာတ်ကြောင်းပြောဟန်<select value={style} onChange={(event) => setStyle(event.target.value)}>{styles.map((item) => <option key={item}>{item}</option>)}</select></label><p>Video အသံပါလျှင် audio + visual၊ အသံမပါလျှင် visual scene များကိုသာ အခြေခံမည်။</p><Button className="primary-action" onClick={generateScript} disabled={generating || !file}>{generating ? "မြန်မာ recap ရေးနေသည်…" : "Quick Recap စတင်မယ်"}<Sparkles className="h-4 w-4" /></Button></div>{script && <div className="script-card"><div className="card-title"><span><FileText className="h-4 w-4" /> မြန်မာ recap script</span><Badge variant="outline">EDITABLE</Badge></div><Textarea value={script} onChange={(event) => setScript(event.target.value)} rows={9} /></div>}</div>}

          {activePanel === "voice" && <div className="panel-content"><div className="control-card"><div className="card-title"><span><Volume2 className="h-4 w-4" /> မြန်မာအသံ</span><Badge>BURMESE ONLY</Badge></div><label>Voice profile<select value={voice} onChange={(event) => setVoice(event.target.value)}>{voices.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label><div className="voice-note"><Gauge className="h-4 w-4" /> အသံအမြန်နှုန်း 1× — မူရင်း duration နဲ့ ကိုက်ညီအောင် render မည်</div></div><div className="control-card"><div className="card-title"><span><Subtitles className="h-4 w-4" /> မြန်မာစာတန်းထိုး</span><Badge>MYANMAR ONLY</Badge></div><p>Noto Sans Myanmar · အောက်ခြေ · မူရင်း video duration timeline အတိုင်း</p></div></div>}

          {activePanel === "finish" && <div className="panel-content"><div className="control-card"><div className="card-title"><span><FlipHorizontal2 className="h-4 w-4" /> Authorized edit</span><Badge variant="outline">SOURCE SAFE</Badge></div><label className="switch-row"><span>Horizontal flip</span><input type="checkbox" checked={flipped} onChange={(event) => setFlipped(event.target.checked)} /></label><label className="switch-row"><span>Blur overlay</span><input type="checkbox" checked={blurEnabled} onChange={(event) => setBlurEnabled(event.target.checked)} /></label><div className="speed-row"><span>Playback speed</span>{[0.75, 1, 1.25, 1.5].map((value) => <button key={value} className={speed === value ? "selected" : ""} onClick={() => changeSpeed(value)}>{value}×</button>)}</div><p>Preview edit state က original source duration ကို မဖြတ်ဘဲ final output ထဲကို ဆက်သွားမည်။</p></div><Button className="primary-action" onClick={renderRecap} disabled={rendering || !script || !file}>{rendering ? "Export state စစ်နေသည်…" : "Prepare final recap export"}<Download className="h-4 w-4" /></Button>{exportPrepared && (canShowFinalOutput(outputUrl, outputVerified) ? <div className="ready-card"><Check className="h-5 w-5" /><div><strong>Final output verified</strong><p>MP4 file ကို အတည်ပြုပြီး download လုပ်နိုင်ပါပြီ။</p><div className="export-actions"><a className="secondary-action" href={outputUrl ?? undefined} download="aungmin-final-recap.mp4">Download MP4</a><button className="secondary-action" onClick={downloadSrt}>Download Myanmar SRT</button><span className="secondary-action unavailable" aria-disabled="true">WAV မရသေးပါ — voice render backend လိုအပ်သည်</span></div></div></div> : <div className="ready-card"><Check className="h-5 w-5" /><div><strong>Export request accepted</strong><p>Editing state ကို လက်ခံပြီးပါပြီ။ Actual MP4 rendering backend ချိတ်ပြီးမှ download-ready file ထုတ်မည်။ Myanmar SRT ကို script ရပြီးချိန်တွင် download လုပ်နိုင်ပါသည်။</p><div className="export-actions"><button className="secondary-action" onClick={downloadSrt} disabled={!script}>Download Myanmar SRT</button><button className="secondary-action" disabled>MP4 rendering pending</button><span className="secondary-action unavailable" aria-disabled="true">WAV မရသေးပါ — voice render backend လိုအပ်သည်</span></div></div></div>)}</div>}
        </aside>
      </div>
      <footer className="editor-footer"><span>Use only media you own or have permission to process.</span><span>Myanmar voice · Myanmar subtitle · original duration</span></footer>
    </main>
  );
}
