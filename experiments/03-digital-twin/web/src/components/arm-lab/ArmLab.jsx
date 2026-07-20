import * as React from "react";
import {
  Activity,
  Camera,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Database,
  Pause,
  Play,
} from "lucide-react";

import { ResponsiveContentGrid } from "./ResponsiveContentGrid.jsx";
import { TraceChart } from "./TraceChart.jsx";

const REGISTRY_URL = "/assets/arm-lab/registry.json";

function assetUrl(path) {
  return `/assets/arm-lab/${path}`;
}

function formatTime(seconds) {
  const safe = Number.isFinite(seconds) ? Math.max(0, seconds) : 0;
  const minutes = Math.floor(safe / 60);
  return `${minutes}:${(safe % 60).toFixed(1).padStart(4, "0")}`;
}

function compactHash(value) {
  return value ? `${value.slice(0, 8)}…${value.slice(-6)}` : "—";
}

function VideoEvidence({ camera, videoRef, onTimeUpdate, onEnded, primary = false }) {
  return (
    <figure className={`arm-camera ${primary ? "is-primary" : ""}`} data-testid={primary ? "main-camera" : "wrist-camera"}>
      <div className="arm-camera-stage">
        <video
          ref={videoRef}
          src={assetUrl(camera.path)}
          muted
          playsInline
          preload="auto"
          onTimeUpdate={onTimeUpdate}
          onEnded={onEnded}
          aria-label={camera.label}
        />
        <figcaption className="arm-camera-label">
          <Camera aria-hidden="true" size={14} />
          <span>{camera.label}</span>
        </figcaption>
      </div>
      <div className="arm-camera-meta">
        <span>{camera.source_key}</span>
        <span>SHA {compactHash(camera.sha256)}</span>
      </div>
    </figure>
  );
}

export function ArmLab() {
  const [registry, setRegistry] = React.useState(null);
  const [trace, setTrace] = React.useState(null);
  const [episodeKey, setEpisodeKey] = React.useState("pass");
  const [currentTime, setCurrentTime] = React.useState(0);
  const [playing, setPlaying] = React.useState(false);
  const [error, setError] = React.useState("");
  const mainVideo = React.useRef(null);
  const wristVideo = React.useRef(null);

  const episode = registry?.episodes?.[episodeKey] || null;
  const frames = trace?.frames || [];
  const frameIndex = Math.min(Math.max(0, Math.round(currentTime * (episode?.fps || 10))), Math.max(0, frames.length - 1));
  const frame = frames[frameIndex] || null;

  React.useEffect(() => {
    let alive = true;
    fetch(REGISTRY_URL)
      .then((response) => {
        if (!response.ok) throw new Error(`registry ${response.status}`);
        return response.json();
      })
      .then((value) => alive && setRegistry(value))
      .catch((reason) => alive && setError(`공개 증거 registry를 읽지 못했습니다: ${reason.message}`));
    return () => { alive = false; };
  }, []);

  React.useEffect(() => {
    if (!episode) return undefined;
    let alive = true;
    setTrace(null);
    setCurrentTime(0);
    setPlaying(false);
    fetch(assetUrl(episode.trace.path))
      .then((response) => {
        if (!response.ok) throw new Error(`trace ${response.status}`);
        return response.json();
      })
      .then((value) => alive && setTrace(value))
      .catch((reason) => alive && setError(`상태·행동 trace를 읽지 못했습니다: ${reason.message}`));
    return () => { alive = false; };
  }, [episode]);

  const seek = React.useCallback((nextTime) => {
    const clamped = Math.min(Math.max(0, nextTime), episode?.duration_sec || 0);
    for (const video of [mainVideo.current, wristVideo.current]) {
      if (video && Math.abs(video.currentTime - clamped) > 0.015) video.currentTime = clamped;
    }
    setCurrentTime(clamped);
  }, [episode]);

  const syncFromMain = React.useCallback(() => {
    const main = mainVideo.current;
    const wrist = wristVideo.current;
    if (!main) return;
    if (wrist && Math.abs(wrist.currentTime - main.currentTime) > 0.08) wrist.currentTime = main.currentTime;
    setCurrentTime(main.currentTime);
  }, []);

  const togglePlayback = React.useCallback(async () => {
    if (!mainVideo.current || !wristVideo.current) return;
    if (playing) {
      mainVideo.current.pause();
      wristVideo.current.pause();
      setPlaying(false);
      return;
    }
    if (currentTime >= (episode?.duration_sec || 0) - 0.05) seek(0);
    const results = await Promise.allSettled([mainVideo.current.play(), wristVideo.current.play()]);
    if (results.some((result) => result.status === "rejected")) {
      setError("브라우저가 자동 재생을 차단했습니다. 재생 버튼을 다시 눌러 주세요.");
      return;
    }
    setError("");
    setPlaying(true);
  }, [currentTime, episode, playing, seek]);

  React.useEffect(() => {
    const handleKey = (event) => {
      const target = event.target;
      if (target instanceof HTMLInputElement || target instanceof HTMLButtonElement) return;
      if (event.code === "Space") {
        event.preventDefault();
        void togglePlayback();
      } else if (event.key === "ArrowLeft") {
        seek(currentTime - 1 / (episode?.fps || 10));
      } else if (event.key === "ArrowRight") {
        seek(currentTime + 1 / (episode?.fps || 10));
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [currentTime, episode, seek, togglePlayback]);

  React.useEffect(() => {
    window.qaArmLabSummary = () => ({
      pass: Boolean(registry && trace && episode && mainVideo.current && wristVideo.current),
      schemaVersion: registry?.schema_version || null,
      episode: episodeKey,
      outcome: episode?.outcome || null,
      frame: frameIndex,
      frames: frames.length,
      currentTime,
      mainTime: mainVideo.current?.currentTime ?? null,
      wristTime: wristVideo.current?.currentTime ?? null,
      syncDelta: mainVideo.current && wristVideo.current ? Math.abs(mainVideo.current.currentTime - wristVideo.current.currentTime) : null,
      claimBoundary: registry?.claim_boundary || null,
      cameraContract: registry?.camera_contract || null,
      graphCursorFrame: frameIndex,
    });
    return () => { delete window.qaArmLabSummary; };
  }, [currentTime, episode, episodeKey, frameIndex, frames.length, registry, trace]);

  if (error && !registry) {
    return (
      <main className="arm-state-page">
        <CircleAlert aria-hidden="true" />
        <h1>실험 기록을 열 수 없습니다</h1>
        <p>{error}</p>
        <button type="button" onClick={() => window.location.reload()}>다시 시도</button>
      </main>
    );
  }

  if (!registry || !episode || !trace) {
    return (
      <main className="arm-state-page" aria-live="polite">
        <Activity className="arm-loading-icon" aria-hidden="true" />
        <h1>기록된 실험을 준비하는 중</h1>
        <p>카메라와 상태·행동 시간을 맞추고 있습니다.</p>
      </main>
    );
  }

  return (
    <div className="arm-lab-shell">
      <header className="arm-lab-header">
        <a className="arm-brand" href="/" aria-label="기존 Robotics Lab으로 이동">
          <span className="arm-brand-mark"><Activity aria-hidden="true" size={15} /></span>
          <span>PHYSICAL AI LAB</span>
        </a>
        <div className="arm-header-badges" aria-label="증거 경계">
          <span>RECORDED EVIDENCE</span>
          <span>LIBERO SIMULATION</span>
        </div>
      </header>

      <main className="arm-lab-main">
        <section className="arm-intro" aria-labelledby="arm-lab-title">
          <div>
            <p className="arm-eyebrow">관찰형 로봇팔 실험실 · LAB3</p>
            <h1 id="arm-lab-title">로봇이 보고, 움직이고, 결과를 만든 기록</h1>
            <p className="arm-intro-copy">두 카메라와 상태·행동을 한 시간축에서 움직여 보세요. 이것은 실시간 로봇이 아니라 실제 OpenVLA 실행을 기록한 시뮬레이션 증거입니다.</p>
          </div>
          <div className="arm-episode-switch" role="group" aria-label="에피소드 결과 선택">
            {(["pass", "fail"]).map((key) => (
              <button
                key={key}
                type="button"
                className={key === episodeKey ? "is-active" : ""}
                onClick={() => setEpisodeKey(key)}
                aria-pressed={key === episodeKey}
              >
                <span>{key === "pass" ? "성공 기록" : "실패 기록"}</span>
                <strong>{key.toUpperCase()}</strong>
              </button>
            ))}
          </div>
        </section>

        <section className="arm-instruction" aria-labelledby="instruction-title">
          <div className="arm-section-icon"><Database aria-hidden="true" size={17} /></div>
          <div>
            <p id="instruction-title">언어 지시</p>
            <blockquote lang="en">“{episode.instruction}”</blockquote>
          </div>
          <div className={`arm-outcome ${episode.outcome.success ? "is-pass" : "is-fail"}`}>
            <span>환경 측정 결과</span>
            <strong>{episode.label} · {episode.outcome.termination}</strong>
          </div>
        </section>

        <ResponsiveContentGrid>
          <VideoEvidence
            camera={episode.cameras.main}
            videoRef={mainVideo}
            onTimeUpdate={syncFromMain}
            onEnded={() => setPlaying(false)}
            primary
          />
          <VideoEvidence camera={episode.cameras.wrist} videoRef={wristVideo} />
        </ResponsiveContentGrid>

        <section className="arm-playback" aria-label="공통 재생 제어">
          <div className="arm-playback-buttons">
            <button type="button" onClick={() => seek(currentTime - 1 / episode.fps)} aria-label="한 프레임 뒤로">
              <ChevronLeft aria-hidden="true" size={18} />
            </button>
            <button className="is-primary" type="button" onClick={() => void togglePlayback()} aria-label={playing ? "일시정지" : "재생"}>
              {playing ? <Pause aria-hidden="true" size={18} /> : <Play aria-hidden="true" size={18} />}
              <span>{playing ? "일시정지" : "재생"}</span>
            </button>
            <button type="button" onClick={() => seek(currentTime + 1 / episode.fps)} aria-label="한 프레임 앞으로">
              <ChevronRight aria-hidden="true" size={18} />
            </button>
          </div>
          <label className="arm-scrubber">
            <span className="sr-only">에피소드 시간 이동</span>
            <input
              type="range"
              min="0"
              max={episode.duration_sec}
              step={1 / episode.fps}
              value={currentTime}
              onChange={(event) => seek(Number(event.target.value))}
            />
          </label>
          <div className="arm-time-readout" aria-live="off">
            <span>{formatTime(currentTime)} / {formatTime(episode.duration_sec)}</span>
            <strong>FRAME {String(frameIndex).padStart(3, "0")}</strong>
          </div>
        </section>

        <section className="arm-trace-panel" aria-labelledby="trace-title">
          <div className="arm-panel-heading">
            <div>
              <p className="arm-eyebrow">SYNCHRONIZED TRACE</p>
              <h2 id="trace-title">상태와 행동</h2>
            </div>
            <span>10 Hz · {frames.length} frames</span>
          </div>
          <TraceChart frames={frames} frameIndex={frameIndex} />
          <div className="arm-vector-readout">
            <div>
              <span>말단 위치 eef xyz</span>
              <strong>{frame ? frame.state.slice(0, 3).map((value) => value.toFixed(3)).join(" · ") : "—"}</strong>
            </div>
            <div>
              <span>이동 행동 dxyz</span>
              <strong>{frame ? frame.action.slice(0, 3).map((value) => value.toFixed(3)).join(" · ") : "—"}</strong>
            </div>
            <div>
              <span>그리퍼 명령</span>
              <strong>{frame ? frame.action[6].toFixed(3) : "—"}</strong>
            </div>
          </div>
        </section>

        {error ? <p className="arm-inline-error" role="status">{error}</p> : null}
      </main>
    </div>
  );
}
