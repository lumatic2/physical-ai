import unittest

from probe_official_viewers import evaluate_metadata


class EvaluateMetadataTests(unittest.TestCase):
    def test_accepts_dual_camera_episode_contract(self):
        info = {
            "features": {
                "observation.images.main": {"dtype": "video"},
                "observation.images.wrist": {"dtype": "video"},
                "observation.state": {"dtype": "float32"},
                "action": {"dtype": "float32"},
                "timestamp": {"dtype": "float32"},
            }
        }
        self.assertTrue(evaluate_metadata(info)["reusable"])

    def test_rejects_single_camera_episode_contract(self):
        info = {
            "features": {
                "observation.images.main": {"dtype": "video"},
                "observation.state": {"dtype": "float32"},
                "action": {"dtype": "float32"},
                "timestamp": {"dtype": "float32"},
            }
        }
        result = evaluate_metadata(info)
        self.assertFalse(result["reusable"])
        self.assertIn("at least two camera features are required", result["rejection_reasons"])

    def test_rejects_missing_action(self):
        info = {
            "features": {
                "observation.images.main": {"dtype": "video"},
                "observation.images.wrist": {"dtype": "video"},
                "observation.state": {"dtype": "float32"},
                "timestamp": {"dtype": "float32"},
            }
        }
        result = evaluate_metadata(info)
        self.assertFalse(result["reusable"])
        self.assertEqual(result["missing_features"], ["action"])


if __name__ == "__main__":
    unittest.main()
