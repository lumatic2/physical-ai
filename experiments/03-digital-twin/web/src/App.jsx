import * as React from "react";
import { createRoot } from "react-dom/client";
import { Bot, ChevronRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { ENVIRONMENT_PRESETS, GROUNDING_MODES } from "./environmentPresets.js";

import "./index.css";
import "./main.js";

const ROBOTS = [
  {
    id: "unitree-g1",
    name: "Unitree G1 휴머노이드",
    kind: "휴머노이드",
    description: "29자유도 전신 로봇입니다. 학습된 보행 정책과 G1 자세 전환 동작을 비교합니다.",
    experiments: [
      { key: "g1-stand", name: "휴머노이드 정지", description: "G1 휴머노이드가 물리 시뮬레이션에서 가만히 서 있는 기본 상태입니다." },
      { key: "g1-walk", name: "휴머노이드 걷기", description: "학습된 G1 보행 정책을 브라우저에서 실행합니다." },
      { key: "g1-rough-walk", name: "거친 지형 걷기", description: "낮은 턱이 있는 지형에서 G1 보행 정책을 확인합니다." },
      { key: "g1-decoupled-wbc-squat", name: "WBC 스쿼트 재생", description: "시뮬레이터에서 측정한 G1 스쿼트 동작을 자세 변화와 함께 봅니다." },
      { key: "g1-squat-reference-vs-wbc", name: "기준 동작 vs 측정 동작", description: "의도한 스쿼트 기준 동작과 실제 시뮬레이션 동작이 얼마나 다른지 비교합니다." },
    ],
  },
  {
    id: "unitree-go1",
    name: "Unitree Go1 4족",
    kind: "4족 보행",
    description: "12개 actuator를 가진 4족 로봇입니다. 평지 보행과 rough terrain 보행을 비교합니다.",
    experiments: [
      { key: "go1-walk", name: "평지 걷기", description: "학습된 Go1 보행 정책을 실행합니다." },
      { key: "go1-rough-walk", name: "거친 지형 걷기", description: "낮은 턱이 있는 지형에서 Go1 보행 정책을 확인합니다." },
    ],
  },
  {
    id: "spot",
    name: "Boston Dynamics Spot",
    kind: "4족 보행",
    description: "Spot 형상 모델입니다. 보행 정책, 거친 지형, 기본 자세 확인을 나눠 봅니다.",
    experiments: [
      { key: "spot-walk", name: "평지 걷기", description: "학습된 Spot 보행 정책을 실행합니다." },
      { key: "spot-rough-walk", name: "거친 지형 걷기", description: "낮은 턱이 있는 지형에서 Spot 보행 정책을 확인합니다." },
    ],
  },
  {
    id: "barkour",
    name: "Google Barkour",
    kind: "소형 4족",
    description: "history observation을 쓰는 Barkour 보행 정책 ingestion 결과입니다.",
    experiments: [
      { key: "barkour-walk", name: "Barkour 걷기", description: "Barkour 보행 정책을 브라우저에서 실행합니다." },
    ],
  },
  {
    id: "arms-hands",
    name: "로봇 팔과 손",
    kind: "조작 계열",
    description: "팔과 손으로 물체 조작 또는 관절 동작을 보여주는 디지털 트윈입니다.",
    experiments: [
      { key: "so100-stack", name: "SO-100 블록 쌓기", description: "SO-100 로봇 팔이 블록을 옮겨 쌓는 동작을 재생합니다." },
      { key: "panda-sweep", name: "Franka Panda 팔 움직임", description: "7자유도 로봇 팔의 관절 움직임을 보여줍니다." },
      { key: "shadow-hand", name: "Shadow Hand 손가락 움직임", description: "로봇 손의 손가락 굴곡 동작을 보여줍니다." },
    ],
  },
];

const ENVIRONMENT_LABELS = {
  "flat-lab": {
    name: "기본 실험실",
    description: "중립 조명, 기준 바닥, 축 표시",
  },
  "instrumented-lab": {
    name: "계측 실험실",
    description: "높이 band, contact readout, 어두운 측정 배경",
  },
  "rough-terrain": {
    name: "거친 지형 레인",
    description: "curb lane과 terrain boundary를 표시",
  },
};

const GROUNDING_LABELS = {
  "replay-locked": "replay 고정",
  "assisted-fixture": "보조 fixture",
  "physics-contact": "물리 접촉",
  "controller-backed": "controller 근거",
};

const EVIDENCE_LABELS = {
  "closed-loop policy": "학습 정책 실행",
  "qpos replay": "시뮬레이션 동작 재생",
  "telemetry sidecar": "상태 기록 포함",
  "reference compare": "기준 동작과 비교",
  "live stream": "실시간 스트림",
  teleop: "직접 조작 가능",
};

function findRobotForExperiment(expName) {
  return ROBOTS.find((robot) => robot.experiments.some((experiment) => experiment.key === expName)) || ROBOTS[0];
}

function readDemoState() {
  const demo = window.demo;
  if (!demo) return null;
  const safeCall = (call, fallback = null) => {
    try {
      return call() || fallback;
    } catch {
      return fallback;
    }
  };
  const summary = safeCall(() => demo.qaWorkbenchSummary?.(), {});
  const environment = safeCall(() => demo.qaEnvironmentSummary?.(), summary.environment || {});
  return {
    expName: demo.expName,
    meta: demo.currentMeta || {},
    summary,
    environment,
    stream: safeCall(() => demo.qaStreamStatus?.(), null),
  };
}

function App() {
  const [registry, setRegistry] = React.useState(null);
  const [state, setState] = React.useState(() => readDemoState());
  const [loadingExperiment, setLoadingExperiment] = React.useState(null);

  React.useEffect(() => {
    document.documentElement.classList.add("dark");
    fetch("./experiments.json")
      .then((response) => response.json())
      .then(setRegistry)
      .catch(() => setRegistry({ experiments: {} }));

    const refresh = () => setState(readDemoState());
    refresh();
    window.addEventListener("robotics-lab-ready", refresh);
    window.addEventListener("robotics-lab-environment-change", refresh);
    window.addEventListener("robotics-lab-experiment-change", refresh);
    const handleExperimentChange = (event) => {
      setLoadingExperiment(event.detail?.phase === "loading" ? event.detail.experiment : null);
      refresh();
    };
    const handlePopState = () => {
      const expName = new URLSearchParams(window.location.search).get("exp");
      if (expName && window.demo?.switchExperiment) {
        void window.demo.switchExperiment(expName, { updateUrl: false });
      }
    };
    window.addEventListener("robotics-lab-experiment-change", handleExperimentChange);
    window.addEventListener("popstate", handlePopState);
    const timer = window.setInterval(refresh, 500);
    return () => {
      window.removeEventListener("robotics-lab-ready", refresh);
      window.removeEventListener("robotics-lab-environment-change", refresh);
      window.removeEventListener("robotics-lab-experiment-change", refresh);
      window.removeEventListener("robotics-lab-experiment-change", handleExperimentChange);
      window.removeEventListener("popstate", handlePopState);
      window.clearInterval(timer);
    };
  }, []);

  const experiments = registry?.experiments || {};
  const meta = state?.meta || {};
  const summary = state?.summary || {};
  const environment = state?.environment || summary.environment || {};
  const lanes = summary.evidenceLanes || [];
  const presets = Object.values(ENVIRONMENT_PRESETS);
  const selectedRobot = findRobotForExperiment(state?.expName);
  const selectedAction = selectedRobot.experiments.find((experiment) => experiment.key === state?.expName);
  const groundingModes = (environment.groundingControl?.allowedModes || environment.grounding?.allowedModes || [])
    .map((id) => GROUNDING_MODES[id])
    .filter(Boolean);

  function selectEnvironmentPreset(id) {
    if (id === "rough-terrain") {
      const roughAction = selectedRobot.experiments.find((experiment) => /rough/i.test(experiment.key) && experiments[experiment.key]);
      if (roughAction && roughAction.key !== state?.expName) {
        window.demo?.setEnvironmentPreset?.(id);
        navigateTo(roughAction.key);
        return undefined;
      }
    }
    const result = window.demo?.setEnvironmentPreset?.(id);
    setState(readDemoState());
    return result;
  }

  function selectGroundingMode(id) {
    const result = window.demo?.setGroundingMode?.(id);
    setState(readDemoState());
    return result;
  }

  function navigateTo(expName) {
    if (expName === state?.expName || loadingExperiment) return;
    if (window.demo?.switchExperiment) {
      setLoadingExperiment(expName);
      void window.demo.switchExperiment(expName).catch((error) => {
        console.error("experiment switch failed", error);
        setLoadingExperiment(null);
      });
      return;
    }
    const next = new URL(window.location.href);
    next.searchParams.set("exp", expName);
    window.location.href = next.toString();
  }

  return (
    <div className="pointer-events-none fixed inset-0 z-[1200] font-sans text-foreground">
      <div className="pointer-events-auto absolute left-3 top-3 flex max-h-[56vh] w-[min(470px,calc(100vw-1.5rem))] flex-col gap-3 overflow-auto md:left-4 md:top-4 md:max-h-[calc(100vh-2rem)]">
        <Card className="border-border/70 bg-background/88 shadow-2xl backdrop-blur-xl">
          <CardHeader className="gap-2 pb-3">
            <div className="flex items-start justify-between gap-3">
              <div className="flex min-w-0 items-center gap-3">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-border bg-secondary text-secondary-foreground">
                  <Bot aria-hidden="true" />
                </div>
                <div className="min-w-0">
                  <CardTitle className="truncate text-base">Robotics Lab</CardTitle>
                  <CardDescription className="truncate">
                    로봇별 행동을 선택하는 MuJoCo 실험실
                  </CardDescription>
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="rounded-lg border border-border bg-card/70 p-3">
              <div className="text-[0.68rem] font-medium uppercase tracking-wide text-muted-foreground">
                지금 보는 것
              </div>
              <div className="mt-1 text-sm font-medium text-foreground">
                {selectedRobot.name}
              </div>
              <div className="mt-0.5 text-sm text-muted-foreground">
                {loadingExperiment ? "새 행동을 불러오는 중" : (selectedAction?.name || "행동을 준비하는 중")}
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {(lanes.length ? lanes : ["시뮬레이션 준비 중"]).map((lane) => (
                  <Badge key={lane} variant="outline">
                    {EVIDENCE_LABELS[lane] || lane}
                  </Badge>
                ))}
              </div>
            </div>

            <Separator />

            <section className="flex flex-col gap-2">
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  실험실 배경
                </h2>
                <Badge variant="outline">{ENVIRONMENT_LABELS[environment.preset]?.name || "선택 가능"}</Badge>
              </div>
              <div className="grid grid-cols-3 gap-1.5">
                {presets.map((preset) => (
                  <Button
                    key={preset.id}
                    type="button"
                    variant={preset.id === environment.preset ? "secondary" : "outline"}
                    className="h-auto min-h-16 items-start px-2 py-2 text-left text-xs whitespace-normal"
                    onClick={() => selectEnvironmentPreset(preset.id)}
                  >
                    <span className="flex min-w-0 flex-col gap-1">
                      <span className="font-medium leading-tight">{ENVIRONMENT_LABELS[preset.id]?.name || preset.label}</span>
                      <span className="text-[0.68rem] leading-tight text-muted-foreground">
                        {ENVIRONMENT_LABELS[preset.id]?.description || preset.visual?.mood}
                      </span>
                    </span>
                  </Button>
                ))}
              </div>
              <details className="rounded-lg border border-border bg-card/70 p-2 text-xs leading-5 text-muted-foreground">
                <summary className="cursor-pointer font-medium text-foreground">검증 기준 보기</summary>
                <div className="mt-2 grid grid-cols-2 gap-2">
                  <div>
                    <span className="block text-[0.68rem] uppercase tracking-wide">시뮬레이션 방식</span>
                    <span>{GROUNDING_LABELS[environment.groundingMode] || environment.groundingControl?.shortLabel || "준비 중"}</span>
                  </div>
                  <div>
                    <span className="block text-[0.68rem] uppercase tracking-wide">접촉 조건</span>
                    <span>{environment.contactProfile?.intent || "scene 기본값"}</span>
                  </div>
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {groundingModes.map((mode) => (
                    <Button
                      key={mode.id}
                      type="button"
                      variant={mode.id === environment.groundingMode ? "secondary" : "outline"}
                      className="h-auto min-h-8 px-2 py-1 text-xs"
                      onClick={() => selectGroundingMode(mode.id)}
                    >
                      <span className="truncate">{GROUNDING_LABELS[mode.id] || mode.shortLabel}</span>
                    </Button>
                  ))}
                </div>
              </details>
            </section>

            <Separator />

            <section className="hidden flex-col gap-2 md:flex">
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  로봇 선택
                </h2>
                <Badge variant="outline">{selectedRobot.kind}</Badge>
              </div>
              <div className="grid grid-cols-2 gap-1.5">
                {ROBOTS.map((robot) => {
                  const firstAvailable = robot.experiments.find((experiment) => experiments[experiment.key]);
                  if (!firstAvailable) return null;
                  return (
                    <Button
                      key={robot.id}
                      type="button"
                      variant={robot.id === selectedRobot.id ? "secondary" : "outline"}
                      className="h-auto min-h-16 items-start justify-start px-2 py-2 text-left whitespace-normal"
                      disabled={Boolean(loadingExperiment)}
                      onClick={() => navigateTo(firstAvailable.key)}
                    >
                      <span className="min-w-0">
                        <span className="block text-sm font-medium leading-tight">{robot.name}</span>
                        <span className="mt-1 block text-xs leading-tight text-muted-foreground">{robot.kind}</span>
                      </span>
                    </Button>
                  );
                })}
              </div>
              <div className="rounded-lg border border-border bg-card/70 p-2.5">
                <div className="text-sm font-medium text-foreground">{selectedRobot.name}</div>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">{selectedRobot.description}</p>
              </div>
              <div className="flex max-h-[24vh] flex-col gap-1 overflow-auto pr-1">
                <div className="px-1 text-[0.68rem] font-medium uppercase tracking-wide text-muted-foreground">
                  행동 선택
                </div>
                {selectedRobot.experiments.filter((experiment) => experiments[experiment.key]).map((experiment) => (
                  <Button
                    key={experiment.key}
                    type="button"
                    variant={experiment.key === state?.expName ? "secondary" : "ghost"}
                    className="h-auto justify-between gap-3 px-2 py-2 text-left whitespace-normal"
                    disabled={Boolean(loadingExperiment)}
                    onClick={() => navigateTo(experiment.key)}
                  >
                    <span className="flex min-w-0 flex-col gap-1">
                      <span className="text-sm font-medium leading-tight">{experiment.name}</span>
                      <span className="text-xs leading-tight text-muted-foreground">
                        {loadingExperiment === experiment.key ? "전체 페이지를 새로 열지 않고 scene만 교체합니다." : experiment.description}
                      </span>
                    </span>
                    <ChevronRight aria-hidden="true" className="mt-0.5 shrink-0" data-icon="inline-end" />
                  </Button>
                ))}
              </div>
              {selectedAction && (
                <div className="rounded-lg border border-border bg-card/70 p-2.5 text-xs leading-5">
                  <div className="text-[0.68rem] font-medium uppercase tracking-wide text-muted-foreground">
                    현재 행동
                  </div>
                  <div className="font-medium text-foreground">{selectedAction.name}</div>
                  <div className="text-muted-foreground">{selectedAction.description}</div>
                </div>
              )}
            </section>

            <Separator />

            <section className="flex flex-col gap-2 md:hidden">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium text-foreground">
                  {selectedRobot.name || meta.name || summary.title || state?.expName || "Selected twin"}
                </div>
                <div className="truncate text-xs text-muted-foreground">
                  {selectedAction?.name || meta.status || summary.gate || "Workbench ready"}
                </div>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {lanes.slice(0, 2).map((lane) => (
                  <Badge key={lane} variant="outline">
                    {EVIDENCE_LABELS[lane] || lane}
                  </Badge>
                ))}
              </div>
            </section>

            <section className="hidden flex-col gap-3 md:flex">
              <div>
                <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  동작 설명
                </div>
                <p className="mt-1 line-clamp-3 text-sm leading-5 text-foreground md:line-clamp-none">
                  {selectedAction?.description || meta.description || "선택한 로봇 행동을 준비하는 중입니다."}
                </p>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {lanes.map((lane) => (
                  <Badge key={lane} variant="outline">
                    {EVIDENCE_LABELS[lane] || lane}
                  </Badge>
                ))}
              </div>
              <div className="rounded-lg border border-border bg-card/70 p-3 text-xs leading-5 text-muted-foreground">
                {meta.limit || summary.limit || "이 화면은 실제 로봇 영상이 아니라 브라우저에서 실행되는 MuJoCo 디지털 트윈입니다."}
              </div>
            </section>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

createRoot(document.getElementById("ui-root")).render(<App />);
