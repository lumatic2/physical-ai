import * as React from "react";
import {
  ArrowUpRight,
  Check,
  Database,
  FileSearch,
  Filter,
  FlaskConical,
  Moon,
  RotateCcw,
  Sun,
  X,
} from "lucide-react";

import {
  ALL_FILTER,
  SUITE_LABELS,
  compactHash,
  summarizeOverview,
  taskOptions,
  validateGeneralizationRegistry,
} from "./generalizationContract.js";
import { FailureExplorer } from "./FailureExplorer.jsx";
import { buildDrilldownUrl } from "./drilldownContract.js";

const REGISTRY_URL = "/assets/generalization-lab/registry.json";

function Outcome({ value }) {
  const success = value === "success";
  return (
    <span className={`gl-outcome ${success ? "is-success" : "is-timeout"}`}>
      {success ? <Check aria-hidden="true" size={13} /> : <X aria-hidden="true" size={13} />}
      {success ? "success" : "timeout"}
    </span>
  );
}

function SummaryBand({ summary }) {
  const stats = [
    { label: "현재 비교 분모", value: `${summary.pairedCells}쌍`, note: `${summary.policyEpisodes}개 recorded episode` },
    { label: "OpenVLA", value: `${summary.openvlaSuccesses} / ${summary.pairedCells}`, note: "success / paired cells" },
    { label: "π0.5-LIBERO", value: `${summary.pi05Successes} / ${summary.pairedCells}`, note: "success / paired cells" },
    {
      label: "관측된 paired 차이",
      value: `${summary.differenceSuccesses >= 0 ? "+" : ""}${summary.differenceSuccesses} / ${summary.pairedCells}`,
      note: "π0.5 minus OpenVLA",
    },
  ];
  return (
    <section aria-labelledby="comparison-summary-title" className="gl-summary-section">
      <div className="gl-section-heading">
        <div>
          <p className="gl-kicker">fixed evidence slice</p>
          <h2 id="comparison-summary-title">비교를 숫자 하나로 줄이지 않습니다</h2>
        </div>
        <p>분모·정책별 raw count·차이를 같은 높이에서 읽습니다.</p>
      </div>
      <dl className="gl-stat-grid">
        {stats.map((stat) => (
          <div key={stat.label}>
            <dt>{stat.label}</dt>
            <dd>{stat.value}</dd>
            <p>{stat.note}</p>
          </div>
        ))}
      </dl>
      <div className="gl-contract-strip" aria-label="공정 비교 계약">
        <span>planned {summary.executionContract.planned_pairs}</span>
        <span>included {summary.executionContract.included_pairs}</span>
        <span>excluded {summary.executionContract.excluded_pairs}</span>
        <span>unmatched {summary.executionContract.unmatched_pairs}</span>
        <span>spec / quality {summary.executionContract.spec_verdict} / {summary.executionContract.quality_verdict}</span>
      </div>
    </section>
  );
}

function FilterBar({ registry, suite, task, onSuiteChange, onTaskChange }) {
  const tasks = taskOptions(registry, suite);
  return (
    <div className="gl-filter-bar" aria-label="비교 범위 필터">
      <div className="gl-filter-label">
        <Filter aria-hidden="true" size={15} />
        <span>범위</span>
      </div>
      <div className="gl-suite-filters" aria-label="suite 선택">
        {[ALL_FILTER, "libero_spatial", "libero_object", "libero_goal"].map((value) => (
          <button
            aria-pressed={suite === value}
            className={suite === value ? "is-active" : ""}
            key={value}
            onClick={() => onSuiteChange(value)}
            type="button"
          >
            {value === ALL_FILTER ? "All suites" : SUITE_LABELS[value]}
          </button>
        ))}
      </div>
      <label className="gl-task-select">
        <span>Task</span>
        <select onChange={(event) => onTaskChange(event.target.value)} value={task}>
          <option value={ALL_FILTER}>All tasks</option>
          {tasks.map((option) => <option key={option.key} value={option.key}>{option.label}</option>)}
        </select>
      </label>
    </div>
  );
}

function ComparisonTable({ cells, selectedCellId, onSelect }) {
  return (
    <div className="gl-table-frame">
      <table>
        <caption className="sr-only">선택된 범위의 task-state별 OpenVLA와 π0.5 결과</caption>
        <thead>
          <tr>
            <th scope="col">Task · state</th>
            <th scope="col">언어 지시</th>
            <th scope="col">OpenVLA</th>
            <th scope="col">π0.5-LIBERO</th>
            <th scope="col">pair</th>
          </tr>
        </thead>
        <tbody>
          {cells.map((cell) => {
            const open = cell.policies.openvla.outcome;
            const pi = cell.policies.pi05.outcome;
            const selected = cell.cell_id === selectedCellId;
            return (
              <tr aria-selected={selected} className={selected ? "is-selected" : ""} key={cell.cell_id}>
                <td data-label="Task · state">
                  <button onClick={() => onSelect(cell.cell_id)} type="button">
                    <strong>{SUITE_LABELS[cell.suite]} · T{String(cell.task_id).padStart(2, "0")}</strong>
                    <span>state {String(cell.state_index).padStart(2, "0")}</span>
                  </button>
                </td>
                <td data-label="언어 지시"><span className="gl-instruction">{cell.instruction}</span></td>
                <td data-label="OpenVLA"><Outcome value={open} /></td>
                <td data-label="π0.5-LIBERO"><Outcome value={pi} /></td>
                <td data-label="pair">
                  <span className="gl-pair-result">
                    {open === pi ? "same outcome" : pi === "success" ? "π0.5 only" : "OpenVLA only"}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function SelectionEvidence({ cell }) {
  if (!cell) return null;
  const drilldownUrl = cell.public_episode ? buildDrilldownUrl(cell) : null;
  return (
    <aside aria-labelledby="selected-cell-title" className="gl-selection-panel">
      <div>
        <p className="gl-kicker">selected evidence cell</p>
        <h3 id="selected-cell-title">{SUITE_LABELS[cell.suite]} · Task {String(cell.task_id).padStart(2, "0")} · state {String(cell.state_index).padStart(2, "0")}</h3>
        <p>{cell.instruction}</p>
      </div>
      <dl>
        {Object.values(cell.policies).map((policy) => (
          <div key={policy.policy_id}>
            <dt>{policy.policy_id}</dt>
            <dd><Outcome value={policy.outcome} /></dd>
            <dd><code>manifest {compactHash(policy.manifest_sha256)}</code></dd>
          </div>
        ))}
      </dl>
      <p className="gl-selection-note">공개 replay가 있는 cell은 source policy·manifest·camera hash를 검증한 뒤 LAB3 듀얼 카메라 기록으로 이동합니다.</p>
      {drilldownUrl ? (
        <a className="gl-drilldown-link" href={drilldownUrl}>
          이 OpenVLA episode를 듀얼 카메라로 보기 <ArrowUpRight aria-hidden="true" size={14} />
        </a>
      ) : null}
    </aside>
  );
}

export function GeneralizationLab() {
  const [registry, setRegistry] = React.useState(null);
  const [error, setError] = React.useState("");
  const [suite, setSuite] = React.useState(ALL_FILTER);
  const [task, setTask] = React.useState(ALL_FILTER);
  const [selectedCellId, setSelectedCellId] = React.useState(null);
  const [failureSummary, setFailureSummary] = React.useState(null);
  const [theme, setTheme] = React.useState("dark");

  React.useEffect(() => {
    let alive = true;
    fetch(REGISTRY_URL)
      .then((response) => {
        if (!response.ok) throw new Error(`registry ${response.status}`);
        return response.json();
      })
      .then((value) => {
        validateGeneralizationRegistry(value);
        if (alive) setRegistry(value);
      })
      .catch((reason) => alive && setError(`공개 비교 registry를 읽지 못했습니다: ${reason.message}`));
    return () => { alive = false; };
  }, []);

  React.useEffect(() => {
    document.documentElement.classList.toggle("arm-light", theme === "light");
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  const summary = React.useMemo(
    () => (registry ? summarizeOverview(registry, { suite, task }) : null),
    [registry, suite, task],
  );
  const selectedCell = summary?.cells.find((cell) => cell.cell_id === selectedCellId) || null;

  React.useEffect(() => {
    if (!registry || !summary) return;
    window.qaGeneralizationSummary = () => ({
      route: "/generalization-lab.html",
      denominator: registry.denominator,
      visible: {
        paired_cells: summary.pairedCells,
        policy_episodes: summary.policyEpisodes,
        openvla_successes: summary.openvlaSuccesses,
        pi05_successes: summary.pi05Successes,
        difference_successes: summary.differenceSuccesses,
      },
      filters: summary.filters,
      selected_cell_id: selectedCell?.cell_id || null,
      registry_sha256: registry.source_hashes,
      execution_contract: registry.execution_contract,
      claim_boundary: registry.claim_boundary,
      failure_explorer: failureSummary,
    });
  }, [failureSummary, registry, selectedCell, summary]);

  if (error) {
    return (
      <main className="arm-state-page">
        <FileSearch aria-hidden="true" size={28} />
        <h1>비교 증거를 열 수 없습니다</h1>
        <p>{error}</p>
        <button onClick={() => window.location.reload()} type="button">다시 시도</button>
      </main>
    );
  }
  if (!registry || !summary) {
    return (
      <main aria-busy="true" className="arm-state-page">
        <Database aria-hidden="true" className="arm-loading-icon" size={28} />
        <h1>고정된 120개 episode를 확인하는 중</h1>
        <p>registry의 분모와 해시를 먼저 검증합니다.</p>
      </main>
    );
  }

  const changeSuite = (value) => {
    setSuite(value);
    setTask(ALL_FILTER);
    setSelectedCellId(null);
  };

  return (
    <div className="gl-shell">
      <header className="arm-lab-header">
        <a className="arm-brand" href="/">
          <span className="arm-brand-mark"><FlaskConical aria-hidden="true" size={17} /></span>
          PHYSICAL AI LAB
        </a>
        <div className="arm-header-tools">
          <a className="gl-header-link" href="/arm-lab.html">로봇팔 replay <ArrowUpRight aria-hidden="true" size={13} /></a>
          <button
            aria-label={theme === "dark" ? "라이트 모드" : "다크 모드"}
            className="arm-theme-toggle"
            onClick={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
            type="button"
          >
            {theme === "dark" ? <Sun aria-hidden="true" size={16} /> : <Moon aria-hidden="true" size={16} />}
          </button>
        </div>
      </header>

      <main className="gl-main">
        <section className="gl-intro">
          <div>
            <p className="gl-kicker">public generalization laboratory · recorded simulation</p>
            <h1>무엇을, 몇 번,<br />어떻게 비교했는가</h1>
          </div>
          <p>사전 고정한 12개 task와 5개 초기 상태에서 두 VLA를 실행했습니다. 큰 점수 하나보다 분모, 정책별 입력 차이, 성공과 실패의 원 증거를 먼저 보여줍니다.</p>
        </section>

        <SummaryBand summary={summary} />

        <section aria-labelledby="cell-matrix-title" className="gl-matrix-section">
          <div className="gl-section-heading">
            <div>
              <p className="gl-kicker">paired cell matrix</p>
              <h2 id="cell-matrix-title">Task-state 결과를 그대로 봅니다</h2>
            </div>
            <p>고정 60쌍 bootstrap 95% 구간: +{summary.fixedInterval.lower.toFixed(2)} ~ +{summary.fixedInterval.upper.toFixed(4)}</p>
          </div>
          <FilterBar
            onSuiteChange={changeSuite}
            onTaskChange={(value) => { setTask(value); setSelectedCellId(null); }}
            registry={registry}
            suite={suite}
            task={task}
          />
          <div className="gl-result-toolbar">
            <span>{summary.pairedCells} paired cells · {summary.policyEpisodes} episodes 표시</span>
            {(suite !== ALL_FILTER || task !== ALL_FILTER) ? (
              <button onClick={() => changeSuite(ALL_FILTER)} type="button">
                <RotateCcw aria-hidden="true" size={13} /> 필터 초기화
              </button>
            ) : null}
          </div>
          <ComparisonTable cells={summary.cells} onSelect={setSelectedCellId} selectedCellId={selectedCellId} />
          <SelectionEvidence cell={selectedCell} />
        </section>

        <FailureExplorer onSummaryChange={setFailureSummary} registry={registry} />

        <footer className="gl-footer">
          <FlaskConical aria-hidden="true" size={16} />
          <p>{registry.claim_boundary}</p>
          <code>registry {compactHash(registry.source_hashes.paired)}</code>
        </footer>
      </main>
    </div>
  );
}
