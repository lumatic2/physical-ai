"""Bundle Barkour policy scene/assets into the web demo tree.

This keeps ADR 0007's rule explicit: runtime MuJoCo model mutations from the
Playground env are baked into the static XML used by mujoco-wasm.
"""
import json
import shutil
from pathlib import Path

import mujoco
import mujoco_playground
from mujoco_playground._src import mjx_env


REPO = Path(__file__).resolve().parents[2]
SCENE_DIR = REPO / "experiments/03-digital-twin/web/assets/scenes/barkour"
ASSETS_DST = SCENE_DIR / "assets"
RUN = Path("/home/<user>/playground-go1/runs/barkour")


def main():
    SCENE_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DST.mkdir(parents=True, exist_ok=True)

    src_root = (
        Path(mujoco_playground.__file__).parent
        / "external_deps/mujoco_menagerie/google_barkour_vb"
    )
    assets = {}
    mjx_env.update_assets(assets, src_root, "*.xml")
    mjx_env.update_assets(assets, src_root / "assets")
    spec = mujoco.MjSpec.from_file(str(src_root / "scene_mjx.xml"), assets=assets)

    for geom in [
        "foot_front_left",
        "foot_hind_left",
        "foot_front_right",
        "foot_hind_right",
    ]:
        spec.add_sensor(
            name=f"{geom}_floor_found",
            type=mujoco.mjtSensor.mjSENS_CONTACT,
            objtype=mujoco.mjtObj.mjOBJ_GEOM,
            objname=geom,
            reftype=mujoco.mjtObj.mjOBJ_GEOM,
            refname="floor",
            intprm=[1, 1, 1],
            datatype=mujoco.mjtDataType.mjDATATYPE_REAL,
            needstage=mujoco.mjtStage.mjSTAGE_ACC,
            dim=1,
        )

    xml = spec.to_xml()
    xml = xml.replace(
        'damping="0.024" armature="0.011"',
        'damping="0.5239" armature="0.011"',
    )
    xml = xml.replace(
        'gainprm="50 0 0" biasprm="0 -50 -0.5"',
        'gainprm="35 0 0" biasprm="0 -35 -0.5"',
    )
    (SCENE_DIR / "scene_barkour_policy.xml").write_text(xml, encoding="utf-8")

    for path in (src_root / "assets").iterdir():
        if path.is_file():
            shutil.copy2(path, ASSETS_DST / path.name)

    for name in ["barkour_policy.onnx", "golden_obs.json", "obs_spec.json"]:
        shutil.copy2(RUN / name, SCENE_DIR / name)

    traj = REPO / "experiments/03-digital-twin/barkour_walk_trajectory.json"
    if not traj.exists():
        model = mujoco.MjModel.from_xml_path(str(SCENE_DIR / "scene_barkour_policy.xml"))
        traj.write_text(
            json.dumps(
                {"fps": 50, "qpos": [model.keyframe("home").qpos.tolist()]},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    print(
        "wrote",
        SCENE_DIR / "scene_barkour_policy.xml",
        "assets",
        len(list(ASSETS_DST.iterdir())),
    )


if __name__ == "__main__":
    main()
