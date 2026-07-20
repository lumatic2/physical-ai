import * as React from "react";
import { ExternalLink, FileJson, X } from "lucide-react";

function compactHash(value) {
  return value ? `${value.slice(0, 12)}…${value.slice(-8)}` : "—";
}

function ArtifactLink({ label, artifact }) {
  if (!artifact) return null;
  return (
    <a className="arm-artifact-link" href={`/assets/arm-lab/${artifact.path}`} target="_blank" rel="noreferrer">
      <FileJson aria-hidden="true" size={15} />
      <span><strong>{label}</strong><small>{artifact.path} · {compactHash(artifact.sha256)}</small></span>
      <ExternalLink aria-hidden="true" size={14} />
    </a>
  );
}

export function EvidenceDrawer({ open, onClose, registry, episode, lane, eventDocument, selectedEvent }) {
  const dialogRef = React.useRef(null);
  React.useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog ref={dialogRef} className="arm-evidence-dialog" onClose={onClose} aria-labelledby="evidence-title">
      <div className="arm-drawer-header">
        <div>
          <p className="arm-eyebrow">RAW EVIDENCE</p>
          <h2 id="evidence-title">이 판단은 어디서 왔나</h2>
        </div>
        <button type="button" onClick={onClose} aria-label="증거 서랍 닫기"><X aria-hidden="true" size={19} /></button>
      </div>

      <section className="arm-drawer-section">
        <div className="arm-boundary-badges">
          <span>RECORDED EVIDENCE</span><span>SIMULATION</span><span>{episode.label}</span>
        </div>
        <p>{registry.claim_boundary}</p>
      </section>

      <section className="arm-drawer-section">
        <h3>현재 event</h3>
        <dl className="arm-evidence-kv">
          <div><dt>ID</dt><dd>{selectedEvent?.id || "—"}</dd></div>
          <div><dt>source</dt><dd>{selectedEvent?.source || "—"}</dd></div>
          <div><dt>component</dt><dd>{selectedEvent?.model_or_component?.name || "—"}</dd></div>
          <div><dt>revision</dt><dd><code>{selectedEvent?.model_or_component?.revision || "—"}</code></dd></div>
          <div><dt>parents</dt><dd>{selectedEvent?.parents?.join(", ") || "none"}</dd></div>
          <div><dt>assistance</dt><dd>{selectedEvent?.assistance?.used ? selectedEvent.assistance.source : "none"}</dd></div>
        </dl>
      </section>

      <section className="arm-drawer-section">
        <h3>원문 artifact</h3>
        <div className="arm-artifact-list">
          <ArtifactLink label={`${lane === "direct_vla" ? "Direct VLA" : "VLM → skill"} event stream`} artifact={episode.event_lanes[lane]} />
          <ArtifactLink label="상태·행동 trace" artifact={episode.trace} />
          <ArtifactLink label="LAB1 PASS/FAIL report" artifact={registry.evidence.lab1_pair_report} />
          <ArtifactLink label="LAB2 two-lane report" artifact={registry.evidence.lab2_comparison_report} />
        </div>
      </section>

      <section className="arm-drawer-section">
        <h3>producer revisions</h3>
        <dl className="arm-evidence-kv">
          {Object.entries(registry.generated_from).map(([key, producer]) => (
            <div key={key}><dt>{key}</dt><dd>{typeof producer === "string" ? <code>{producer}</code> : <><span>{producer.name}</span><code>{producer.revision}</code></>}</dd></div>
          ))}
          <div><dt>dataset tree</dt><dd><code>{episode.canonical_dataset_tree_sha256}</code></dd></div>
        </dl>
      </section>

      <section className="arm-drawer-section">
        <h3>공식 source</h3>
        <div className="arm-source-links">
          {registry.sources.map((source) => (
            <a key={source.url} href={source.url} target="_blank" rel="noreferrer">
              <span>{source.name}<small>accessed {source.accessed_at}</small></span><ExternalLink aria-hidden="true" size={14} />
            </a>
          ))}
        </div>
      </section>
    </dialog>
  );
}
