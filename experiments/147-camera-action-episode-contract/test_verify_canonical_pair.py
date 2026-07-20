import copy
import unittest

from verify_canonical_pair import evaluate_pair


REV_A = "a" * 40
REV_B = "b" * 40
REV_C = "c" * 40
ACTION_HASH = "d" * 64


def sidecar(*, success, termination, init_state_index, frames):
    return {
        "episode": {"revision": REV_A},
        "producer": {
            "environment": {"name": "libero", "revision": REV_B},
            "policy": {"name": "openvla", "revision": REV_C},
        },
        "rollout": {
            "suite": "libero_spatial",
            "task_id": 0,
            "init_state_index": init_state_index,
            "environment_seed": 0,
            "max_policy_steps": 3,
        },
        "action_events": [
            {"raw_policy_action": [0.0] * 7, "executed_action_sha256": ACTION_HASH}
            for _ in range(frames)
        ],
        "outcome": {"success": success, "termination": termination, "reward": float(success)},
    }


class CanonicalPairTests(unittest.TestCase):
    def setUp(self):
        self.passed = sidecar(success=True, termination="success", init_state_index=0, frames=2)
        self.failed = sidecar(success=False, termination="timeout", init_state_index=1, frames=3)
        self.evidence = {"pass": True, "producer_claim_ready": True, "hashes": {"dataset": "e" * 64}}

    def evaluate(self):
        return evaluate_pair(
            pass_sidecar=self.passed,
            fail_sidecar=self.failed,
            pass_evidence=self.evidence,
            fail_evidence=self.evidence,
        )

    def test_accepts_same_contract_opposite_outcomes(self):
        self.assertTrue(self.evaluate()["pass"])

    def test_rejects_outcome_relabel(self):
        self.failed["outcome"] = copy.deepcopy(self.passed["outcome"])
        self.assertFalse(self.evaluate()["pass"])

    def test_rejects_revision_or_seed_drift(self):
        self.failed["producer"]["policy"]["revision"] = "f" * 40
        self.assertFalse(self.evaluate()["pass"])
        self.failed["producer"]["policy"]["revision"] = REV_C
        self.failed["rollout"]["environment_seed"] = 1
        self.assertFalse(self.evaluate()["pass"])

    def test_rejects_incomplete_action_link(self):
        self.failed["action_events"][0].pop("executed_action_sha256")
        self.assertFalse(self.evaluate()["pass"])


if __name__ == "__main__":
    unittest.main()
