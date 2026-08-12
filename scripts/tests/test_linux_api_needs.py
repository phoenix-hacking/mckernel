#!/usr/bin/env python3
"""Fail-closed tests for the frozen Linux API-needs manifest."""

import ast
import copy
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import linux_api_needs as api_needs  # noqa: E402


class ApiNeedsFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory = api_needs.read_json(REPO_ROOT / api_needs.INVENTORY_PATH)
        cls.source_lock = api_needs.read_json(REPO_ROOT / api_needs.SOURCE_LOCK_PATH)
        cls.manifest = api_needs.read_json(REPO_ROOT / api_needs.OUTPUT_PATH)


class GoldenManifestTests(ApiNeedsFixture):
    def test_generated_manifest_is_complete_and_current(self) -> None:
        api_needs.verify_inventory_replay(REPO_ROOT, self.inventory)
        generated = api_needs.build_manifest(self.inventory, self.source_lock)
        api_needs.validate_manifest(
            generated, self.inventory, self.source_lock
        )
        self.assertEqual(generated, self.manifest)

        import_edges = api_needs.linux_import_edges(self.inventory)
        unique_imports = {
            symbol for symbols in import_edges.values() for symbol in symbols
        }
        lookup_sites = api_needs.dynamic_lookup_sites(self.inventory)
        unique_lookups = {
            symbol
            for symbols in lookup_sites.values()
            for symbol in symbols
        }
        kallsyms_audit = api_needs.audited_kallsyms_surface(
            REPO_ROOT, self.inventory
        )
        unique_lookups.update(
            row["symbol"] for row in kallsyms_audit["forwarded_static_names"]
        )
        self.assertFalse(unique_imports & unique_lookups)
        self.assertEqual(
            self.manifest["coverage"]["by_lookup_kind"],
            {
                "module_import": len(unique_imports),
                "dynamic_kallsyms": len(unique_lookups),
            },
        )
        self.assertEqual(
            self.manifest["coverage"]["consumer_edges"]["module_import"],
            sum(len(symbols) for symbols in import_edges.values()),
        )
        self.assertEqual(
            self.manifest["coverage"]["dynamic_kallsyms_source_sites"],
            sum(
                len(sites)
                for symbols in lookup_sites.values()
                for sites in symbols.values()
            ),
        )
        self.assertEqual(
            self.manifest["coverage"]["kallsyms_forwarded_static_name_sites"],
            len(kallsyms_audit["forwarded_static_names"]),
        )
        self.assertEqual(
            self.manifest["coverage"]["kallsyms_unresolved_computed_name_sites"],
            0,
        )

    def test_inter_module_imports_are_excluded_not_silently_reowned(self) -> None:
        binary_modules = self.inventory["binary_capture"]["modules"]
        excluded = {
            (module, edge["symbol"])
            for module, details in binary_modules.items()
            for edge in details["inter_module_imports"]
        }
        included = {
            (module, need["symbol"])
            for need in self.manifest["needs"]
            if need["lookup_kind"] == "module_import"
            for module in need["owner"]["consuming_modules"]
        }
        all_imports = {
            (module, symbol)
            for module, details in binary_modules.items()
            for symbol in details["imports"]
        }
        self.assertFalse(excluded & included)
        self.assertEqual(included | excluded, all_imports)

        provider_exports = {
            module: {row["name"] for row in details["exports"]}
            for module, details in binary_modules.items()
        }
        for consumer, symbol in excluded:
            providers = {
                edge["provider"]
                for edge in binary_modules[consumer]["inter_module_imports"]
                if edge["symbol"] == symbol
            }
            self.assertTrue(
                any(symbol in provider_exports[provider] for provider in providers)
            )

    def test_every_need_has_owner_provenance_and_honest_classifications(self) -> None:
        ids = set()
        acceptance_ids = set()
        for need in self.manifest["needs"]:
            api_needs.validate_need_shape(need)
            ids.add(need["id"])
            acceptance_ids.add(need["acceptance"]["test_id"])
            self.assertEqual(
                need["owner"]["provider"],
                api_needs.provider_for(need["lookup_kind"], need["symbol"]),
            )
            self.assertTrue(need["owner"]["consuming_modules"])
            self.assertEqual(need["availability"]["rocky_10_2"], "unverified")
            self.assertEqual(need["export"]["rocky_10_2_status"], "unverified")
            self.assertEqual(
                need["configuration"]["status"],
                "requires_selected_config_probe",
            )
            self.assertEqual(
                need["call_context"]["status"],
                "requires_compiler_backed_call_site_audit",
            )
            self.assertEqual(need["acceptance"]["status"], "planned")
            self.assertTrue(need["abstraction"]["family"])
            provenance = need["source_provenance"]
            if need["lookup_kind"] == "module_import":
                self.assertEqual(
                    provenance["binary_capture_sha256"],
                    self.inventory["binary_capture_sha256"],
                )
            else:
                self.assertEqual(
                    provenance["source_capture_sha256"],
                    self.inventory["source_capture_sha256"],
                )
                self.assertEqual(provenance["site_count"], len(provenance["sites"]))
                self.assertEqual(
                    provenance["forwarded_static_site_count"],
                    len(provenance["forwarded_static_sites"]),
                )
                self.assertGreater(
                    provenance["site_count"]
                    + provenance["forwarded_static_site_count"],
                    0,
                )
        self.assertEqual(len(ids), len(self.manifest["needs"]))
        self.assertEqual(len(acceptance_ids), len(self.manifest["needs"]))
        external = {
            need["symbol"]: need["owner"]["provider"]
            for need in self.manifest["needs"]
            if need["owner"]["provider"] != "Linux kernel core"
        }
        self.assertEqual(external, api_needs.OPTIONAL_EXTERNAL_PROVIDERS)

    def test_manifest_is_bound_to_rocky_10_2_source_lock(self) -> None:
        target = self.manifest["target"]
        source_rpm = self.source_lock["source_rpm"]
        self.assertEqual(target["kernel_nvr"], source_rpm["nvr"])
        self.assertEqual(target["source_rpm_sha256"], source_rpm["sha256"])
        self.assertEqual(
            self.manifest["provenance"]["source_lock_sha256"],
            api_needs.sha256_bytes(api_needs.canonical_bytes(self.source_lock)),
        )
        self.assertFalse(self.manifest["readiness"]["credit_eligible"])
        self.assertGreaterEqual(len(self.manifest["readiness"]["blockers"]), 5)

    def test_non_literal_bridge_is_bounded_to_source_proven_static_names(self) -> None:
        audit = self.manifest["kallsyms_exhaustiveness_audit"]
        self.assertEqual(audit["unresolved_computed_names"], [])
        self.assertEqual(len(audit["non_literal_dispatchers"]), 1)
        dispatcher = audit["non_literal_dispatchers"][0]
        self.assertEqual(dispatcher["function"], "mcctrl_arch_kallsyms_lookup_bridge")
        self.assertEqual(dispatcher["unresolved_callers"], 0)
        forwarded = audit["forwarded_static_names"]
        self.assertEqual(dispatcher["resolved_static_callers"], len(forwarded))
        self.assertEqual(
            {row["symbol"] for row in forwarded},
            {"vdso_image_64", "__vvar_page", "hpet_address", "hv_clock"},
        )
        need_symbols = {
            row["symbol"]
            for row in self.manifest["needs"]
            if row["lookup_kind"] == "dynamic_kallsyms"
        }
        self.assertTrue({row["symbol"] for row in forwarded} <= need_symbols)

        for row in forwarded:
            need = next(
                item
                for item in self.manifest["needs"]
                if item["symbol"] == row["symbol"]
            )
            self.assertEqual(need["source_provenance"]["site_count"], 0)
            self.assertEqual(
                need["availability"]["legacy_r0"],
                "requested by source-proven static Rust forwarding through the bounded bridge",
            )
            self.assertEqual(
                need["consumers"][0]["evidence"],
                "source-proven static Rust forwarding through bounded kallsyms bridge",
            )

    def test_generator_and_tests_remain_python_3_6_compatible(self) -> None:
        paths = [Path(api_needs.__file__), Path(__file__)]
        for path in paths:
            source = path.read_text(encoding="utf-8")
            if sys.version_info >= (3, 8):
                try:
                    tree = ast.parse(source, filename=str(path), feature_version=(3, 6))
                except TypeError:
                    tree = ast.parse(source, filename=str(path), feature_version=6)
            else:
                tree = ast.parse(source, filename=str(path))
            self.assertIsNotNone(tree)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                    self.assertNotIn(
                        "annotations", [alias.name for alias in node.names]
                    )
                if isinstance(node, ast.Attribute):
                    self.assertNotIn(node.attr, {"removeprefix", "removesuffix"})
                if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
                    self.assertNotIn(node.value.id, {"dict", "list", "set", "tuple"})
                annotation = None
                if isinstance(node, ast.arg):
                    annotation = node.annotation
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    annotation = node.returns
                elif isinstance(node, ast.AnnAssign):
                    annotation = node.annotation
                if annotation is not None:
                    self.assertFalse(
                        any(
                            isinstance(part, ast.BinOp)
                            and isinstance(part.op, ast.BitOr)
                            for part in ast.walk(annotation)
                        ),
                        "PEP 604 annotation is not Python 3.6 compatible in {0}".format(
                            path
                        ),
                    )

        python36 = shutil.which("python3.6")
        if python36:
            completed = subprocess.run(
                [
                    python36,
                    str(Path(api_needs.__file__)),
                    "--repo",
                    str(REPO_ROOT),
                    "--check",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(
                completed.returncode,
                0,
                completed.stderr.decode("utf-8", errors="replace"),
            )

    def test_repository_paths_reject_escape_and_symlink_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            regular = root / "input.json"
            regular.write_text("{}\n", encoding="utf-8")
            self.assertEqual(
                api_needs.resolve_repository_path(
                    root, Path("input.json"), "test input", True
                ),
                regular,
            )
            link = root / "input-link.json"
            link.symlink_to(regular)
            with self.assertRaises(api_needs.ApiNeedsError):
                api_needs.resolve_repository_path(
                    root, Path("input-link.json"), "test input", True
                )
            with self.assertRaises(api_needs.ApiNeedsError):
                api_needs.resolve_repository_path(
                    root, root.parent / "outside.json", "test output", False
                )


class FailClosedMutationTests(ApiNeedsFixture):
    def resign(self, manifest: dict) -> None:
        manifest["manifest_sha256"] = api_needs.manifest_digest(manifest)

    def test_missing_need_fails_even_if_counts_and_digest_are_recomputed(self) -> None:
        broken = copy.deepcopy(self.manifest)
        broken["needs"].pop(0)
        broken["coverage"] = api_needs.coverage_for(
            broken["needs"], broken["kallsyms_exhaustiveness_audit"]
        )
        self.resign(broken)
        with self.assertRaises(api_needs.ApiNeedsError):
            api_needs.validate_manifest(broken, self.inventory, self.source_lock)

    def test_consumer_reassignment_fails_even_if_digest_is_recomputed(self) -> None:
        broken = copy.deepcopy(self.manifest)
        need = next(
            row
            for row in broken["needs"]
            if row["lookup_kind"] == "module_import"
            and row["owner"]["consuming_modules"] == ["ihk"]
        )
        need["owner"]["consuming_modules"] = ["mcctrl"]
        need["consumers"][0]["module"] = "mcctrl"
        need["consumers"][0]["filename"] = "mcctrl.ko"
        self.resign(broken)
        with self.assertRaises(api_needs.ApiNeedsError):
            api_needs.validate_manifest(broken, self.inventory, self.source_lock)

    def test_target_availability_overclaim_fails_closed(self) -> None:
        broken = copy.deepcopy(self.manifest)
        broken["needs"][0]["availability"]["rocky_10_2"] = "available"
        broken["needs"][0]["export"]["rocky_10_2_status"] = "exported"
        self.resign(broken)
        with self.assertRaises(api_needs.ApiNeedsError):
            api_needs.validate_manifest(broken, self.inventory, self.source_lock)

    def test_binary_import_mutation_cannot_redefine_the_frozen_surface(self) -> None:
        broken = copy.deepcopy(self.inventory)
        binary = broken["binary_capture"]
        binary["modules"]["ihk"]["imports"].append("invented_kernel_symbol")
        binary["modules"]["ihk"]["imports"].sort()
        broken["binary_capture_sha256"] = api_needs.sha256_bytes(
            api_needs.canonical_bytes(binary)
        )
        with self.assertRaises(api_needs.ApiNeedsError):
            api_needs.validate_inventory(broken)

    def test_source_lookup_mutation_cannot_redefine_the_frozen_surface(self) -> None:
        broken = copy.deepcopy(self.inventory)
        site = broken["source_capture"]["modules"]["mcctrl"][
            "dynamic_kallsyms_lookups"
        ][0]
        site["line"] += 1
        broken["source_capture_sha256"] = api_needs.sha256_bytes(
            api_needs.canonical_bytes(broken["source_capture"])
        )
        with self.assertRaises(api_needs.ApiNeedsError):
            api_needs.validate_inventory(broken)

    def test_source_lock_target_mutation_fails(self) -> None:
        broken = copy.deepcopy(self.source_lock)
        broken["target"]["release"] = "10.3"
        with self.assertRaises(api_needs.ApiNeedsError):
            api_needs.build_manifest(self.inventory, broken)

    def test_forwarded_static_name_mutation_fails_even_if_resigned(self) -> None:
        broken = copy.deepcopy(self.manifest)
        broken["kallsyms_exhaustiveness_audit"]["forwarded_static_names"][0][
            "symbol"
        ] = "invented_private_symbol"
        self.resign(broken)
        with self.assertRaises(api_needs.ApiNeedsError):
            api_needs.validate_manifest(broken, self.inventory, self.source_lock)

    def test_manifest_content_mutation_without_resigning_fails(self) -> None:
        broken = copy.deepcopy(self.manifest)
        broken["needs"][0]["symbol"] = "changed"
        with self.assertRaises(api_needs.ApiNeedsError):
            api_needs.validate_manifest(broken, self.inventory, self.source_lock)

    def test_unsupported_computed_kallsyms_argument_fails_closed(self) -> None:
        original = api_needs.text_blob

        def mutated_text(repo, logical_path):
            text = original(repo, logical_path)
            if logical_path == "executer/kernel/mcctrl/driver.c":
                text += (
                    "\nstatic void *invented_lookup(void) {\n"
                    "    return (void *)kallsyms_lookup_name(select_private_name());\n"
                    "}\n"
                )
            return text

        with mock.patch.object(api_needs, "text_blob", side_effect=mutated_text):
            with self.assertRaises(api_needs.ApiNeedsError):
                api_needs.build_manifest(self.inventory, self.source_lock, REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
