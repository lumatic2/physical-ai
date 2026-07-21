import { ArrowRight, GitBranch } from "lucide-react";

const SOURCE_LABELS = {
  sensor: "관찰",
  vlm: "VLM 판단",
  vla: "VLA 행동",
  controller: "제어 실행",
  environment: "환경 결과",
};

function formatVector(values, count = 3) {
  return Array.isArray(values) ? values.slice(0, count).map((value) => Number(value).toFixed(3)).join(" · ") : "—";
}

export function eventSummary(event) {
  const payload = event?.payload || {};
  switch (event?.kind) {
    case "model_input_observation":
      return payload.instruction ? `주 카메라 + “${payload.instruction}”` : "주 카메라 + 언어 지시를 모델 입력으로 기록";
    case "structured_scene_observation":
      return `${payload.target || "target"} → ${payload.destination || "destination"} · ${payload.spatial_summary || "구조화된 장면 관찰"}`;
    case "bounded_skill_selection":
      return `${payload.name} · ${payload.target} → ${payload.destination} · confidence ${Number(payload.confidence).toFixed(2)}`;
    case "action_proposal":
      return `7D action · dxyz ${formatVector(payload.raw_action)} · ${Number(payload.latency_ms || 0).toFixed(0)} ms`;
    case "action_acceptance":
      return `${payload.accepted ? "accepted" : "rejected"} · dxyz ${formatVector(payload.executed_action)}`;
    case "scripted_skill_execution":
      return `${payload.skill?.name} · canonical replay ${payload.actions_executed}/${payload.actions_requested} actions`;
    case "measured_skill_outcome":
    case "measured_environment_outcome":
      return `${payload.success ? "PASS" : "FAIL"} · ${payload.termination} · reward ${payload.reward}`;
    default:
      return event?.kind?.replaceAll("_", " ") || "기록된 event";
  }
}

export function EventTimeline({ events, selectedEvent, onSelect }) {
  if (!events.length) {
    return <p className="arm-event-empty">이 시간축에 표시할 인과 event가 없습니다.</p>;
  }
  return (
    <ol className="arm-event-list" aria-label="관찰 판단 행동 결과 인과 이벤트">
      {events.map((event, index) => (
        <li key={event.id}>
          <button
            type="button"
            className={`arm-event ${selectedEvent?.id === event.id ? "is-selected" : ""}`}
            onClick={() => onSelect(event)}
            aria-pressed={selectedEvent?.id === event.id}
          >
            <span className={`arm-event-source is-${event.source} ${event.source === "environment" ? (event.payload?.success ? "is-pass" : "is-fail") : ""}`.trim()}>{SOURCE_LABELS[event.source] || event.source}</span>
            <strong>{event.kind.replaceAll("_", " ")}</strong>
            <span className="arm-event-summary">{eventSummary(event)}</span>
            <span className="arm-event-meta">
              <GitBranch aria-hidden="true" size={12} /> {event.parents?.length || 0} parent · frame {event.timestep}
            </span>
          </button>
          {index < events.length - 1 ? <ArrowRight className="arm-event-arrow" aria-hidden="true" size={15} /> : null}
        </li>
      ))}
    </ol>
  );
}
