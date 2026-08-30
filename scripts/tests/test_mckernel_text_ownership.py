import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import mckernel_text_ownership as ownership


class TextOwnershipTests(unittest.TestCase):
    def test_subprocess_text_mode_is_compatible_with_python_3_6(self):
        completed = mock.Mock(stdout="output\n")
        with mock.patch.object(ownership.subprocess, "run", return_value=completed) as run:
            self.assertEqual(ownership.run_checked(["tool"]), "output\n")

        _args, kwargs = run.call_args
        self.assertTrue(kwargs["universal_newlines"])
        self.assertNotIn("text", kwargs)

    def test_parse_nm_keeps_only_nonempty_text_symbols(self):
        symbols = ownership.parse_nm(
            "00001000 00000010 T rust_body\n"
            "00002000 00000008 t c_body\n"
            "00003000 00000004 R constant\n"
            "00004000 00000000 T empty\n"
        )
        self.assertEqual(
            [(symbol["name"], symbol["size"]) for symbol in symbols],
            [("rust_body", 16), ("c_body", 8)],
        )

    def test_source_parsing_and_language_classification(self):
        self.assertEqual(ownership.source_path("/repo/kernel/a.rs:42"), "/repo/kernel/a.rs")
        self.assertEqual(ownership.source_path("??:?"), "??")
        self.assertEqual(ownership.classify_source("kernel/a.rs"), "rust")
        self.assertEqual(ownership.classify_source("kernel/a.c"), "c")
        self.assertEqual(ownership.classify_source("arch/entry.S"), "assembly")
        self.assertEqual(ownership.classify_source("??"), "other")

    def test_ci_checkout_source_is_normalized_to_repository_path(self):
        repo = Path("/workspace/mckernel")
        self.assertEqual(
            ownership.repo_relative_source(
                "/__w/mckernel/mckernel/kernel/syscall.c", repo
            ),
            "kernel/syscall.c",
        )
        self.assertEqual(
            ownership.repo_relative_source(
                "/rustc/toolchain/library/core/src/ptr/mod.rs", repo
            ),
            "/rustc/toolchain/library/core/src/ptr/mod.rs",
        )

    def test_attribute_symbols_counts_bytes_and_relativizes_repo_sources(self):
        symbols = [
            {"address": "1000", "size": 16, "name": "r"},
            {"address": "2000", "size": 8, "name": "c"},
            {"address": "3000", "size": 4, "name": "a"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            image = repo / "mckernel.img"
            with mock.patch.object(
                ownership,
                "run_checked",
                return_value=(
                    "r\n{}:9\nc\n{}:10\na\n??:?\n".format(
                        repo / "kernel/rust/a.rs", repo / "kernel/a.c"
                    )
                ),
            ):
                attributed = ownership.attribute_symbols(
                    image, symbols, "addr2line", repo
                )

        languages, raw_languages, sources, duplicates = ownership.summarize_attribution(
            attributed
        )

        self.assertEqual(languages["rust"], 16)
        self.assertEqual(languages["c"], 8)
        self.assertEqual(languages["other"], 4)
        self.assertEqual(raw_languages, languages)
        self.assertEqual(duplicates, [])
        self.assertEqual(sources["kernel/rust/a.rs"], 16)
        self.assertEqual(attributed[2]["source"], "??")

    def test_aliases_count_once_and_must_have_consistent_attribution(self):
        entry = {
            "address": "1000",
            "size": 16,
            "name": "first",
            "source": "kernel/rust/a.rs",
            "language": "rust",
        }
        alias = {**entry, "name": "alias"}
        languages, raw_languages, sources, duplicates = ownership.summarize_attribution(
            [entry, alias]
        )
        self.assertEqual(languages["rust"], 16)
        self.assertEqual(raw_languages["rust"], 32)
        self.assertEqual(sources["kernel/rust/a.rs"], 16)
        self.assertEqual(duplicates, [{"address": "1000", "size": 16, "symbols": 2}])

        conflicting = {**alias, "source": "kernel/a.c", "language": "c"}
        with self.assertRaisesRegex(ValueError, "conflicting source"):
            ownership.summarize_attribution([entry, conflicting])

    def test_parse_nm_rejects_missing_text(self):
        with self.assertRaisesRegex(ValueError, "no non-empty T/t"):
            ownership.parse_nm("1000 10 R data\n")


if __name__ == "__main__":
    unittest.main()
