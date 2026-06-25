import * as React from "react";
import { createRoot } from "react-dom/client";
import { Activity, Bot, Boxes, ChevronRight, FlaskConical } from "lucide-react";

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
    description: "29자유도 전신 로봇입니다. 보행, 자세 전환, 백엔드 trace 검증을 한 로봇 안에서 비교합니다.",
    experiments: [
      { key: "unitree-g1-elastic-stand", name: "보조 fixture 직립", description: "Unitree MuJoCo elastic-band 지원 trace를 브라우저에서 재생합니다." },
      { key: "g1-decoupled-wbc-squat", name: "WBC 스쿼트 재생", description: "측정된 Decoupled WBC squat trace를 자세 깊이 gate와 함께 봅니다." },
      { key: "g1-squat-reference-vs-wbc", name: "기준 동작 vs 측정 rollout", description: "컴파일된 squat reference와 측정 WBC rollout을 비교합니다." },
      { key: "g1-walk", name: "학습 보행 정책", description: "브라우저에서 닫힌루프 joystick 보행 정책을 실행합니다." },
      { key: "g1-rough-walk", name: "거친 지형 보행", description: "낮은 curb terrain에서 보행 정책의 강건성을 확인합니다." },
      { key: "unitree-g1-headless", name: "백엔드 bridge trace", description: "공식 Unitree MuJoCo headless trace를 viewer 계약으로 연결합니다." },
      { key: "g1-controlled-squat", name: "얕은 lowering probe", description: "실패 사례에 가까운 micro-dip probe입니다. squat 성공으로 표시하지 않습니다." },
      { key: "g1-stand", name: "모델 직립 settle", description: "G1 모델 로드와 물리 settle 상태를 확인합니다." },
    ],
  },
  {
    id: "unitree-go1",
    name: "Unitree Go1 4족",
    kind: "4족 보행",
    description: "12개 actuator를 가진 4족 로봇입니다. 평지 보행과 rough terrain 보행을 비교합니다.",
    experiments: [
      { key: "go1-walk", name: "평지 보행 정책", description: "학습된 Go1 joystick 보행 정책을 실행합니다." },
      { key: "go1-rough-walk", name: "거친 지형 보행", description: "curb terrain에서 command robustness를 확인합니다." },
    ],
  },
  {
    id: "spot",
    name: "Boston Dynamics Spot",
    kind: "4족 보행",
    description: "Spot 형상 모델입니다. 보행 정책, rough terrain, settle baseline을 나눠 봅니다.",
    experiments: [
      { key: "spot-walk", name: "평지 보행 정책", description: "Spot closed-loop 보행 정책을 실행합니다." },
      { key: "spot-rough-walk", name: "거친 지형 보행", description: "curb terrain에서 command sweep evidence를 확인합니다." },
      { key: "spot-stand", name: "모델 직립 settle", description: "Spot 모델 로드와 settle baseline입니다." },
    ],
  },
  {
    id: "barkour",
    name: "Google Barkour",
    kind: "소형 4족",
    description: "history observation을 쓰는 Barkour 보행 정책 ingestion 결과입니다.",
    experiments: [
      { key: "barkour-walk", name: "학습 보행 정책", description: "추가 policy를 학습부터 browser QA까지 흡수한 사례입니다." },
    ],
  },
  {
    id: "arms-hands",
    name: "로봇 팔과 손",
    kind: "조작 계열",
    description: "고정 베이스 arm, dexterous hand, 저가형 SO-100 조작 replay를 모아 둔 그룹입니다.",
    experiments: [
      { key: "so100-stack", name: "SO-100 블록 스택", description: "저가형 arm의 scripted pick-and-place replay입니다." },
      { key: "panda-sweep", name: "Franka Panda 관절 sweep", description: "7-DOF arm의 control baseline입니다." },
      { key: "shadow-hand", name: "Shadow Hand finger curl", description: "손가락 굴곡 replay와 joint visualization입니다." },
    ],
  },
  {
    id: "checks",
    name: "검증용 fixture",
    kind: "하네스 점검",
    description: "새 scene과 일반 humanoid loader가 깨지지 않는지 확인하는 회귀 테스트입니다.",
    experiments: [
      { key: "dummy-arm", name: "Dummy 2-link arm", description: "새 scene registry 추가를 검증하는 최소 arm입니다." },
      { key: "humanoid-settle", name: "Generic humanoid settle", description: "G1이 아닌 일반 humanoid scene loader 점검입니다." },
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

function navigateTo(expName) {
  const next = new URL(window.location.href);
  next.searchParams.set("exp", expName);
  window.location.href = next.toString();
}

function App() {
  const [registry, setRegistry] = React.useState(null);
  const [state, setState] = React.useState(() => readDemoState());

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
    const timer = window.setInterval(refresh, 500);
    return () => {
      window.removeEventListener("robotics-lab-ready", refresh);
      window.removeEventListener("robotics-lab-environment-change", refresh);
      window.clearInterval(timer);
    };
  }, []);

  const experiments = registry?.experiments || {};
  const meta = state?.meta || {};
  const summary = state?.summary || {};
  const environment = state?.environment || summary.environment || {};
  const lanes = summary.evidenceLanes || [];
  const contract = summary.stateContract || {};
  const presets = Object.values(ENVIRONMENT_PRESETS);
  const selectedRobot = findRobotForExperiment(state?.expName);
  const selectedAction = selectedRobot.experiments.find((experiment) => experiment.key === state?.expName);
  const groundingModes = (environment.groundingControl?.allowedModes || environment.grounding?.allowedModes || [])
    .map((id) => GROUNDING_MODES[id])
    .filter(Boolean);

  function selectEnvironmentPreset(id) {
    const result = window.demo?.setEnvironmentPreset?.(id);
    setState(readDemoState());
    return result;
  }

  function selectGroundingMode(id) {
    const result = window.demo?.setGroundingMode?.(id);
    setState(readDemoState());
    return result;
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
              <Badge variant="secondary" className="max-w-32 shrink-0 truncate">
                {summary.runtime || "loading"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="grid grid-cols-3 gap-2">
              <Metric icon={Activity} label="State" value={contract.nq ? `qpos[${contract.nq}]` : "loading"} />
              <Metric icon={Boxes} label="Frames" value={contract.frames ? String(contract.frames) : "live"} />
              <Metric icon={FlaskConical} label="Gate" value={summary.gate || "pending"} />
            </div>

            <Separator />

            <section className="flex flex-col gap-2">
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  배경 선택
                </h2>
                <Badge variant="outline">{environment.claimLevel || "contract"}</Badge>
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
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="min-w-0 rounded-lg border border-border bg-card/70 p-2">
                  <div className="text-[0.68rem] font-medium uppercase tracking-wide text-muted-foreground">
                    Grounding
                  </div>
                  <div className="truncate font-medium text-foreground">
                    {GROUNDING_LABELS[environment.groundingMode] || environment.groundingControl?.shortLabel || environment.groundingMode || "loading"}
                  </div>
                </div>
                <div className="min-w-0 rounded-lg border border-border bg-card/70 p-2">
                  <div className="text-[0.68rem] font-medium uppercase tracking-wide text-muted-foreground">
                    Contact
                  </div>
                  <div className="truncate font-medium text-foreground">
                    {environment.contactProfile?.intent || "scene-default"}
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-1.5">
                {groundingModes.map((mode) => (
                  <Button
                    key={mode.id}
                    type="button"
                    variant={mode.id === environment.groundingMode ? "secondary" : "outline"}
                    className="h-auto min-h-9 px-2 py-1.5 text-xs"
                    onClick={() => selectGroundingMode(mode.id)}
                  >
                    <span className="truncate">{GROUNDING_LABELS[mode.id] || mode.shortLabel}</span>
                  </Button>
                ))}
              </div>
              <div className="rounded-lg border border-border bg-card/70 p-2 text-xs leading-5 text-muted-foreground">
                <span className="font-medium text-foreground">
                  {environment.groundingControl?.claimLevel || "claim pending"}
                </span>
                {" · "}
                {environment.groundingControl?.evidenceRequired || "Evidence summary pending."}
              </div>
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
                    onClick={() => navigateTo(experiment.key)}
                  >
                    <span className="flex min-w-0 flex-col gap-1">
                      <span className="text-sm font-medium leading-tight">{experiment.name}</span>
                      <span className="text-xs leading-tight text-muted-foreground">{experiment.description}</span>
                      <span className="text-[0.68rem] leading-tight text-muted-foreground">{experiment.key}</span>
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
                    {lane}
                  </Badge>
                ))}
              </div>
            </section>

            <section className="hidden flex-col gap-3 md:flex">
              <div>
                <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Workbench evidence
                </div>
                <p className="mt-1 line-clamp-3 text-sm leading-5 text-foreground md:line-clamp-none">
                  {meta.description || summary.title || "Loading selected experiment."}
                </p>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {lanes.map((lane) => (
                  <Badge key={lane} variant="outline">
                    {lane}
                  </Badge>
                ))}
              </div>
              <div className="rounded-lg border border-border bg-card/70 p-3 text-xs leading-5 text-muted-foreground">
                {meta.limit || summary.limit || "No limit summary loaded yet."}
              </div>
            </section>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Metric({ icon: Icon, label, value }) {
  return (
    <div className="min-w-0 rounded-lg border border-border bg-card/70 p-2">
      <div className="mb-1 flex items-center gap-1.5 text-[0.68rem] font-medium uppercase tracking-wide text-muted-foreground">
        <Icon aria-hidden="true" />
        <span>{label}</span>
      </div>
      <div className="truncate text-sm font-medium text-foreground">{value}</div>
    </div>
  );
}

createRoot(document.getElementById("ui-root")).render(<App />);
