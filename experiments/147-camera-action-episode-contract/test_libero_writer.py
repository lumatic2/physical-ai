import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from episode_profile import validate_profile
from libero_writer import LeRobotEpisodeWriter, build_robot_state, discover_wrist_camera_key


REV_A = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
REV_B = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
REV_C = "cccccccccccccccccccccccccccccccccccccccc"


def observation(size=16):
    return {
        "agentview_image": np.zeros((size, size, 3), dtype=np.uint8),
        "robot0_eye_in_hand_image": np.full((size, size, 3), 127, dtype=np.uint8),
        "robot0_eef_pos": np.array([0.1, 0.2, 0.3], dtype=np.float32),
        "robot0_eef_quat": np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32),
        "robot0_gripper_qpos": np.array([0.01, 0.02], dtype=np.float32),
    }


class FakeDataset:
    def __init__(self, **create_kwargs):
        self.create_kwargs = create_kwargs
        self.frames = []
        self.saved_episodes = []
        self.finalized = False

    def add_frame(self, frame):
        self.frames.append(frame)

    def save_episode(self, parallel_encoding=True):
        self.parallel_encoding = parallel_encoding
        self.saved_episodes.append(self.frames)
        self.frames = []

    def clear_episode_buffer(self):
        self.frames = []

    def finalize(self):
        self.finalized = True


class LiberoWriterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.fake = None

        def factory(**kwargs):
            self.fake = FakeDataset(**kwargs)
            return self.fake

        self.writer = LeRobotEpisodeWriter.create(
            root=Path(self.temp.name),
            repo_id="physical-ai/test",
            fps=10,
            image_shape=(16, 16, 3),
            dataset_revision=REV_A,
            environment_revision=REV_B,
            policy_revision=REV_C,
            dataset_factory=factory,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_state_and_wrist_contract(self):
        obs = observation()
        self.assertEqual(discover_wrist_camera_key(obs), "robot0_eye_in_hand_image")
        np.testing.assert_allclose(build_robot_state(obs), [0.1, 0.2, 0.3, 0, 0, 0, 0.01, 0.02])

    def test_records_dual_camera_executed_action_and_valid_sidecar(self):
        self.writer.add_executed_step(
            observation=observation(),
            raw_policy_action=np.arange(7, dtype=np.float32),
            executed_action=np.linspace(-1, 1, 7, dtype=np.float32),
            instruction="pick up the mug",
            request_latency_ms=12.5,
        )
        sidecar_path = self.writer.save_episode(success=True, termination="success", reward=1.0)
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        self.assertEqual(len(self.fake.saved_episodes), 1)
        self.assertFalse(self.fake.parallel_encoding)
        self.assertEqual(set(self.fake.saved_episodes[0][0]), {
            "observation.images.image",
            "observation.images.image2",
            "observation.state",
            "action",
            "task",
        })
        self.assertNotIn("action", sidecar)
        self.assertTrue(validate_profile(self.writer._profile_info(), sidecar, require_provenance=True)["valid"])

    def test_rejects_missing_wrist_camera(self):
        obs = observation()
        obs.pop("robot0_eye_in_hand_image")
        with self.assertRaisesRegex(ValueError, "wrist camera"):
            self.writer.add_executed_step(
                observation=obs,
                raw_policy_action=np.zeros(7),
                executed_action=np.zeros(7),
                instruction="pick",
                request_latency_ms=1.0,
            )

    def test_rejects_non_finite_and_wrong_shape_actions(self):
        with self.assertRaisesRegex(ValueError, "raw_policy_action"):
            self.writer.add_executed_step(
                observation=observation(),
                raw_policy_action=np.array([np.nan] * 7),
                executed_action=np.zeros(7),
                instruction="pick",
                request_latency_ms=1.0,
            )
        with self.assertRaisesRegex(ValueError, "executed_action"):
            self.writer.add_executed_step(
                observation=observation(),
                raw_policy_action=np.zeros(7),
                executed_action=np.zeros(6),
                instruction="pick",
                request_latency_ms=1.0,
            )

    def test_rejects_camera_shape_mismatch_before_dataset_write(self):
        obs = observation()
        obs["robot0_eye_in_hand_image"] = np.zeros((8, 8, 3), dtype=np.uint8)
        with self.assertRaisesRegex(ValueError, "must have shape"):
            self.writer.add_executed_step(
                observation=obs,
                raw_policy_action=np.zeros(7),
                executed_action=np.zeros(7),
                instruction="pick",
                request_latency_ms=1.0,
            )
        self.assertEqual(self.fake.frames, [])

    def test_rejects_timestep_mismatch_before_episode_save(self):
        self.writer.add_executed_step(
            observation=observation(),
            raw_policy_action=np.zeros(7),
            executed_action=np.zeros(7),
            instruction="pick",
            request_latency_ms=1.0,
        )
        self.writer.action_events.clear()
        with self.assertRaisesRegex(ValueError, "timestep count mismatch"):
            self.writer.save_episode(success=False, termination="timeout", reward=0.0)
        self.assertEqual(self.fake.saved_episodes, [])


if __name__ == "__main__":
    unittest.main()
