import * as React from "react";
import { AlertTriangle, ArrowUpRight, Braces, CircleHelp, Filter, ShieldAlert } from "lucide-react";

import { ALL_FILTER, SUITE_LABELS, compactHash } from "./generalizationContract.js";
import {
  PATTERN_LABELS,
  POLICY_LABELS,
  failureTaskOptions,
  filterFailureEpisodes,
  formatPredicate,
  representativeFailures,
} from "./failureExplorerContract.js";

function FailureFilters({ registry, filters, onChange }) {
  const tasks = failureTaskOptions(registry, filters.suite);
  const setFilter = (key, value) => onChange({
    ...filters,
    [key]: value,
    ...(key === "suite" ? { task: ALL_FILTER } : {}),
  });
  return (
    <div aria-label="실패 증거 필터" className="gl-failure-filters">
      <div className="gl-failure-filter-title"><Filter aria-hidden="true" size={15} /> 관측 범위</div>
      <label><span>정책</span><select onChange={(event) => setFilter("policy", event.target.value)} value={filters.policy}>
        <option value={ALL_FILTER}>모든 정책</option>
        {Object.entries(POLICY_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select></label>
      <label><span>Suite</span><select onChange={(event) => setFilter("suite", event.target.value)} value={filters.suite}>
        <option value={ALL_FILTER}>모든 suite</option>
        {Object.entries(SUITE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select></label>
      <label><span>Task</span><select onChange={(event) => setFilter("task", event.target.value)} value={filters.task}>
        <option value={ALL_FILTER}>모든 task</option>
        {tasks.map((option) => <option key={option.key} value={option.key}>{option.label}</option>)}
      </select></label>
      <label><span>양상</span><select onChange={(event) => setFilter("pattern", event.target.value)} value={filters.pattern}>
        <option value={ALL_FILTER}>모든 양상</option>
        {Object.entries(PATTERN_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select></label>
    </div>
  );
}

function FailureRow({ row }) {
  return (
    <li className="gl-failure-row">
      <div className="gl-failure-row-heading">
        <span className={`gl-pattern-chip is-${row.patternId}`}>
          {row.patternId === "unknown" ? <CircleHelp aria-hidden="true" size={13} /> : <AlertTriangle aria-hidden="true" size={13} />}
          {PATTERN_LABELS[row.patternId]}
        </span>
        <span>{POLICY_LABELS[row.policyId]}</span>
        <strong>{SUITE_LABELS[row.suite]} · T{String(row.taskId).padStart(2, "0")} · state {String(row.stateIndex).padStart(2, "0")}</strong>
      </div>
      <p>{row.instruction}</p>
      <div className="gl-failure-evidence">
        <span>frame {row.frameRange.start}–{row.frameRange.end}</span>
        <code>{formatPredicate(row.predicates[0])}</code>
        <code>manifest {compactHash(row.manifestSha256)}</code>
        {row.publicEpisode ? <a href={row.publicEpisode.public_url}>dual-camera replay <ArrowUpRight aria-hidden="true" size={12} /></a> : null}
      </div>
    </li>
  );
}

export function FailureExplorer({ registry, onSummaryChange }) {
  const [filters, setFilters] = React.useState({ policy: ALL_FILTER, suite: ALL_FILTER, task: ALL_FILTER, pattern: ALL_FILTER });
  const result = React.useMemo(() => filterFailureEpisodes(registry, filters), [registry, filters]);
  const representatives = React.useMemo(() => representativeFailures(result.rows), [result.rows]);

  React.useEffect(() => {
    onSummaryChange?.({ filters: result.filters, count: result.count, shown: representatives.length });
  }, [onSummaryChange, representatives.length, result.count, result.filters]);

  return (
    <section aria-labelledby="failure-explorer-title" className="gl-failure-section">
      <div className="gl-section-heading">
        <div>
          <p className="gl-kicker">observable failure patterns</p>
          <h2 id="failure-explorer-title">실패를 원인이 아니라 관측된 양상으로 봅니다</h2>
        </div>
        <p>27개 timeout 전부를 포함합니다. 특정 predicate가 맞지 않으면 unknown으로 남깁니다.</p>
      </div>

      <div className="gl-pattern-summary">
        {Object.entries(registry.failure_summary.counts).map(([patternId, count]) => (
          <div key={patternId}>
            <span className={`gl-pattern-chip is-${patternId}`}>{PATTERN_LABELS[patternId]}</span>
            <strong>{count} / {registry.failure_summary.denominator}</strong>
            <p>{registry.failure_summary.definitions[patternId]}</p>
          </div>
        ))}
      </div>

      <aside aria-label="판정하지 않은 실패 양상" className="gl-disabled-patterns">
        <ShieldAlert aria-hidden="true" size={17} />
        <div>
          <strong>판정하지 않은 양상 3개</strong>
          <p>{Object.entries(registry.failure_summary.disabled_patterns).map(([name, reason]) => `${name}: ${reason}`).join(" · ")}</p>
        </div>
      </aside>

      <FailureFilters filters={filters} onChange={setFilters} registry={registry} />
      <div className="gl-failure-result">
        <span>{result.count} failures matched</span>
        <span>{representatives.length} representative evidence rows</span>
      </div>
      {representatives.length ? (
        <ol className="gl-failure-list">{representatives.map((row) => <FailureRow key={`${row.policyId}:${row.cellId}`} row={row} />)}</ol>
      ) : (
        <div className="gl-failure-empty"><Braces aria-hidden="true" size={18} /><p>이 필터 조합에 해당하는 관측 실패가 없습니다.</p></div>
      )}
      <p className="gl-failure-boundary">이 목록은 기록된 simulator trajectory의 판정 가능한 feature만 설명합니다. 계획·지각·모델 내부의 숨은 원인을 진단하지 않습니다.</p>
    </section>
  );
}
