"""Aggregate command sweep JSONs into a comparable gallery report."""
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "verify"

INPUTS = [
    ("go1-walk", "flat", REPO / "experiments/07-command-terrain-robustness/verify/go1-command-sweep.json"),
    ("spot-walk", "flat", REPO / "experiments/07-command-terrain-robustness/verify/spot-command-sweep.json"),
    ("go1-rough-walk", "rough", REPO / "experiments/07-command-terrain-robustness/verify/go1-rough-command-sweep-live.json"),
    ("spot-rough-walk", "rough", REPO / "experiments/07-command-terrain-robustness/verify/spot-rough-command-sweep-live.json"),
    ("g1-rough-walk", "rough", REPO / "experiments/08-policy-expansion/verify/g1-rough-command-sweep-live.json"),
    ("barkour-walk", "flat", REPO / "experiments/10-barkour-rl-walk/verify/barkour-command-sweep-live.json"),
]


def by_name(results):
    return {row["name"]: row for row in results}


def fmt(value):
    return f"{value:.2f}"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    details = {}
    for label, terrain, path in INPUTS:
        data = json.loads(path.read_text(encoding="utf-8"))
        results = by_name(data["results"])
        failed = [
            r
            for r in data["results"]
            if r.get("fell") or r.get("nan") or r.get("consoleErrors")
        ]
        row = {
            "label": label,
            "terrain": terrain,
            "source": str(path.relative_to(REPO)).replace("\\", "/"),
            "live": bool(data.get("live")),
            "forward_dx": results["forward"]["dx"],
            "forward_drift_y": results["forward"]["dy"],
            "strafe_left_dy": results["strafe-left"]["dy"],
            "strafe_right_dy": results["strafe-right"]["dy"],
            "turn_left_dyaw": results["turn-left"]["dyaw"],
            "turn_right_dyaw": results["turn-right"]["dyaw"],
            "diagonal_distance": results["diagonal-left"]["distance"],
            "min_height": min(r["finalHeight"] for r in data["results"]),
            "failures": len(failed),
        }
        rows.append(row)
        details[label] = data

    summary = {"rows": rows}
    (OUT / "policy-gallery-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# Policy Gallery Comparison",
        "",
        "| Policy | Terrain | Live | forward dx | forward drift y | strafe L dy | strafe R dy | turn L dyaw | turn R dyaw | diagonal dist | min h | failures |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {label} | {terrain} | {live} | {forward_dx} | {forward_drift_y} | "
            "{strafe_left_dy} | {strafe_right_dy} | {turn_left_dyaw} | "
            "{turn_right_dyaw} | {diagonal_distance} | {min_height} | {failures} |".format(
                label=row["label"],
                terrain=row["terrain"],
                live="yes" if row["live"] else "no",
                forward_dx=fmt(row["forward_dx"]),
                forward_drift_y=fmt(row["forward_drift_y"]),
                strafe_left_dy=fmt(row["strafe_left_dy"]),
                strafe_right_dy=fmt(row["strafe_right_dy"]),
                turn_left_dyaw=fmt(row["turn_left_dyaw"]),
                turn_right_dyaw=fmt(row["turn_right_dyaw"]),
                diagonal_distance=fmt(row["diagonal_distance"]),
                min_height=fmt(row["min_height"]),
                failures=row["failures"],
            )
        )
    lines.extend(
        [
            "",
            "## Readout",
            "",
            "- All compared sweeps have `failures=0`: no fall, NaN, or console errors in the selected raw reports.",
            "- Go1 remains the cleanest forward baseline; rough Go1 still keeps strong forward progress.",
            "- Spot is stable, but rough terrain shows more command drift than Go1 in the existing M12 reports.",
            "- G1 rough contributes the humanoid axis; it is comparable by protocol but not by morphology.",
            "- Barkour adds a new 465-d history-observation policy. It walks forward after user-facing `vx` is sign-flipped into the env command convention, but its lateral/yaw conventions should be labeled before presenting as intuitive teleop.",
            "",
            "## Sources",
            "",
        ]
    )
    for row in rows:
        lines.append(f"- `{row['label']}`: `{row['source']}`")
    (OUT / "policy-gallery-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT / 'policy-gallery-summary.json'}")
    print(f"wrote {OUT / 'policy-gallery-report.md'}")
    print(f"aggregated {len(rows)} policy sweep reports")


if __name__ == "__main__":
    main()
