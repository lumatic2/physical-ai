#!/usr/bin/env python3
"""Failure probes for the deterministic GEN5 public registry."""

from __future__ import annotations

import copy
import unittest

from gen_public_index import (
    CLAIM_BOUNDARY,
    PublicIndexError,
    build_registry,
    canonical_bytes,
    default_inputs,
    validate_registry,
)


class PublicIndexTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inputs = default_inputs()
        cls.registry = build_registry(cls.inputs)

    def test_actual_registry_is_byte_deterministic(self) -> None:
        self.assertEqual(canonical_bytes(build_registry(self.inputs)), canonical_bytes(build_registry(self.inputs)))
        self.assertEqual(len(self.registry["cells"]), 60)

    def test_missing_denominator_is_rejected(self) -> None:
        inputs = copy.deepcopy(self.inputs)
        inputs["paired"]["denominator"]["paired_keys"] = 59
        with self.assertRaisesRegex(PublicIndexError, "denominator"):
            build_registry(inputs)

    def test_hidden_exclusion_is_rejected(self) -> None:
        inputs = copy.deepcopy(self.inputs)
        inputs["fairness"]["denominator"]["excluded_pairs"] = 1
        with self.assertRaisesRegex(PublicIndexError, "exclusion drift"):
            build_registry(inputs)

    def test_stale_episode_hash_is_rejected(self) -> None:
        inputs = copy.deepcopy(self.inputs)
        inputs["arm"]["episodes"]["pass"]["cameras"]["main"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(PublicIndexError, "stale public camera hash"):
            build_registry(inputs)

    def test_local_path_or_token_is_rejected(self) -> None:
        for value in ("/home/example/cache/model", "hf_1234567890secret"):
            registry = copy.deepcopy(self.registry)
            registry["cells"][0]["instruction"] = value
            with self.subTest(value=value), self.assertRaisesRegex(PublicIndexError, "unsafe local path or token"):
                validate_registry(registry)

    def test_unsupported_claim_is_rejected(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["supported_claims"].append("This policy is the general winner on a real robot.")
        with self.assertRaisesRegex(PublicIndexError, "unsupported public claim"):
            validate_registry(registry)

    def test_claim_boundary_is_exact(self) -> None:
        self.assertEqual(self.registry["claim_boundary"], CLAIM_BOUNDARY)

    def test_drilldown_urls_bind_source_policy_and_manifest(self) -> None:
        links = [cell for cell in self.registry["cells"] if cell["public_episode"]]
        self.assertEqual(len(links), 2)
        for cell in links:
            url = cell["public_episode"]["public_url"]
            self.assertIn(f"source_cell={cell['cell_id'].replace(':', '%3A')}", url)
            self.assertIn("policy=openvla-libero", url)
            self.assertIn(f"manifest={cell['public_episode']['manifest_sha256']}", url)


if __name__ == "__main__":
    unittest.main()
