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

const GROUPS = [
  ["Humanoids", ["g1-walk", "g1-rough-walk", "g1-controlled-squat", "g1-decoupled-wbc-squat", "g1-squat-reference-vs-wbc", "unitree-g1-headless", "unitree-g1-elastic-stand", "g1-stand"]],
  ["Quadrupeds", ["barkour-walk", "go1-walk", "go1-rough-walk", "spot-walk", "spot-rough-walk", "spot-stand"]],
  ["Arms / hands", ["so100-stack", "panda-sweep", "shadow-hand"]],
  ["Harness checks", ["dummy-arm", "humanoid-settle"]],
];

function readDemoState() {
  const demo = window.demo;
  if (!demo) return null;
  const summary = demo.qaWorkbenchSummary?.() || {};
  const environment = demo.qaEnvironmentSummary?.() || summary.environment || {};
  return {
    expName: demo.expName,
    meta: demo.currentMeta || {},
    summary,
    environment,
    stream: demo.qaStreamStatus?.() || null,
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
      <div className="pointer-events-auto absolute left-3 top-3 flex max-h-[48vh] w-[min(430px,calc(100vw-1.5rem))] flex-col gap-3 overflow-auto md:left-4 md:top-4 md:max-h-[calc(100vh-2rem)]">
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
                    MuJoCo twins, policies, and evidence gates
                  </CardDescription>
                </div>
              </div>
              <Badge variant="secondary" className="shrink-0">
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
                  Environment
                </h2>
                <Badge variant="outline">{environment.claimLevel || "contract"}</Badge>
              </div>
              <div className="grid grid-cols-3 gap-1.5">
                {presets.map((preset) => (
                  <Button
                    key={preset.id}
                    type="button"
                    variant={preset.id === environment.preset ? "secondary" : "outline"}
                    className="h-auto min-h-10 px-2 py-2 text-xs"
                    onClick={() => selectEnvironmentPreset(preset.id)}
                  >
                    <span className="truncate">{preset.label}</span>
                  </Button>
                ))}
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="min-w-0 rounded-lg border border-border bg-card/70 p-2">
                  <div className="text-[0.68rem] font-medium uppercase tracking-wide text-muted-foreground">
                    Grounding
                  </div>
                  <div className="truncate font-medium text-foreground">
                    {environment.groundingControl?.shortLabel || environment.groundingMode || "loading"}
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
                    <span className="truncate">{mode.shortLabel}</span>
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
                  Robot selection
                </h2>
                <Badge variant="outline">{meta.kind || "registered"}</Badge>
              </div>
              <div className="max-h-[12vh] overflow-auto pr-1 md:max-h-[34vh]">
                {GROUPS.map(([label, keys]) => (
                  <div key={label} className="flex flex-col gap-1 pb-2">
                    <div className="px-1 pt-1 text-[0.68rem] font-medium uppercase tracking-wide text-muted-foreground">
                      {label}
                    </div>
                    {keys.filter((key) => experiments[key]).map((key) => (
                      <Button
                        key={key}
                        type="button"
                        variant={key === state?.expName ? "secondary" : "ghost"}
                        className="h-auto justify-between gap-3 px-2 py-2 text-left"
                        onClick={() => navigateTo(key)}
                      >
                        <span className="flex min-w-0 flex-col">
                          <span className="truncate text-sm font-medium">{experiments[key].title || key}</span>
                          <span className="truncate text-xs text-muted-foreground">{key}</span>
                        </span>
                        <ChevronRight aria-hidden="true" data-icon="inline-end" />
                      </Button>
                    ))}
                  </div>
                ))}
              </div>
            </section>

            <Separator />

            <section className="flex flex-col gap-2 md:hidden">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium text-foreground">
                  {meta.name || summary.title || state?.expName || "Selected twin"}
                </div>
                <div className="truncate text-xs text-muted-foreground">
                  {meta.status || summary.gate || "Workbench ready"}
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
