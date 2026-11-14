#!/usr/bin/env python3
"""Replay the hosted Rust bootstrap with inert installer/download fixtures."""

import ast
import hashlib
from pathlib import Path
import shlex
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/rust-x86_64-validation.yml"
INSTALLER_URL = (
    "https://static.rust-lang.org/rustup/archive/1.29.0/"
    "x86_64-unknown-linux-gnu/rustup-init"
)
LAUNCHER_SHA256 = "4acc9acc76d5079515b46346a485974457b5a79893cfb01112423c89aeb5aa10"
INSTALLER_SIZE = 20838840
RUSTC_VERSION = "rustc 1.95.0-nightly (c04308580 2026-02-18)"
INSTALLER = b'''#!/bin/sh
set -eu
case "${0##*/}" in
  rustup-init)
    printf "installer %s\\n" "$*" >> "$TEST_TRACE"
    mkdir -p "$CARGO_HOME/bin"
    cp -- "$0" "$CARGO_HOME/bin/rustup"
    cp -- "$0" "$CARGO_HOME/bin/rustc"
    if test "${TEST_MUTATE_ON_INSTALL:-0}" = 1; then
      printf "\\n# changed\\n" >> "$CARGO_HOME/bin/rustup"
    fi
    ;;
  rustup)
    printf "rustup %s\\n" "$*" >> "$TEST_TRACE"
    case "$*" in
      "set auto-self-update disable") touch "$CARGO_HOME/update-disabled" ;;
      "toolchain install nightly-2026-02-19 --profile minimal")
        test -f "$CARGO_HOME/update-disabled"
        if test "${TEST_MUTATE_LAUNCHER:-0}" = 1; then
          printf "\\n# changed\\n" >> "$CARGO_HOME/bin/rustc"
        fi
        ;;
      "default nightly-2026-02-19") ;;
      *) exit 33 ;;
    esac
    ;;
  rustc)
    printf "rustc %s\\n" "$*" >> "$TEST_TRACE"
    printf "%s\\n" "$EXPECTED_RUSTC_VERSION"
    ;;
  *) exit 34 ;;
esac
'''


def bootstrap_body():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    step = workflow.split(
        "- name: Prepare non-root validator and pinned nightly\n", 1
    )[1].split("\n      - name:", 1)[0]
    return textwrap.dedent(
        step.split("bash -c '\n", 1)[1].rsplit("\n            '", 1)[0]
    )


class RockyRustupBootstrapTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="rustup-bootstrap-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.trace = self.root / "trace"
        self.download = self.root / "download"
        self.download.write_bytes(INSTALLER)
        self.fake_curl = self.root / "curl"
        self.fake_curl.write_text(
            "#!/bin/sh\nset -eu\n"
            'test "${TEST_DOWNLOAD_FAILURE:-0}" != 1 || exit 22\n'
            'output=""\nurl=""\n'
            'while test "$#" -gt 0; do\n'
            '  if test "$1" = --output; then shift; output="$1"; fi\n'
            '  url="$1"\n  shift\ndone\n'
            'test "$url" = "$TEST_INSTALLER_URL"\n'
            'cp -- "$TEST_DOWNLOAD_SOURCE" "$output"\n',
            encoding="utf-8",
        )
        self.fake_curl.chmod(0o755)
        (self.root / "tmp").mkdir()

    def replay(self, extra_environment=None):
        # Only the network transport and fixture byte identity are substituted;
        # checksum commands, execution order, and launcher checks run unchanged.
        body = bootstrap_body().replace(
            "/usr/bin/curl", shlex.quote(str(self.fake_curl))
        ).replace(LAUNCHER_SHA256, hashlib.sha256(INSTALLER).hexdigest()).replace(
            "= " + str(INSTALLER_SIZE), "= " + str(len(INSTALLER))
        )
        environment = {
            "PATH": "/usr/bin:/bin",
            "CARGO_HOME": str(self.root / "cargo"),
            "RUSTUP_HOME": str(self.root / "rustup"),
            "TMPDIR": str(self.root / "tmp"),
            "RUST_TOOLCHAIN": "nightly-2026-02-19",
            "EXPECTED_RUSTC_VERSION": RUSTC_VERSION,
            "TEST_TRACE": str(self.trace),
            "TEST_INSTALLER_URL": INSTALLER_URL,
            "TEST_DOWNLOAD_SOURCE": str(self.download),
        }
        environment.update(extra_environment or {})
        return subprocess.run(
            ["/bin/bash", "--noprofile", "--norc", "-c", body],
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=15,
        )

    def test_installer_identity_matches_existing_semantic_launcher_pin(self):
        tree = ast.parse(
            (ROOT / "scripts/host_module_failure_semantics_v3.py").read_text(
                encoding="utf-8"
            )
        )
        expected = next(
            ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "EXPECTED_RUST"
                for target in node.targets
            )
        )
        self.assertEqual(LAUNCHER_SHA256, expected["launcher_sha256"])
        self.assertEqual(RUSTC_VERSION, expected["version_first_line"])
        body = bootstrap_body()
        self.assertIn(INSTALLER_URL, body)
        self.assertIn("rustup_init_sha256=" + LAUNCHER_SHA256, body)
        self.assertIn("= " + str(INSTALLER_SIZE), body)
        self.assertNotIn("sh.rustup.rs", body)

    def test_verified_install_disables_self_update_before_toolchain_install(self):
        result = self.replay()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(
            [
                "installer -y --profile minimal --default-toolchain none "
                "--default-host x86_64-unknown-linux-gnu --no-modify-path",
                "rustup set auto-self-update disable",
                "rustup toolchain install nightly-2026-02-19 --profile minimal",
                "rustup default nightly-2026-02-19",
                "rustc --version",
                "rustc -Vv",
            ],
            self.trace.read_text(encoding="utf-8").splitlines(),
        )
        for proxy in ("rustup", "rustc"):
            self.assertEqual(
                INSTALLER, (self.root / "cargo/bin" / proxy).read_bytes()
            )
        self.assertEqual([], list((self.root / "tmp").iterdir()))

    def test_same_size_corrupt_download_is_rejected_before_execution(self):
        self.download.write_bytes(INSTALLER.replace(b"installer", b"corrupted"))
        result = self.replay()
        self.assertNotEqual(0, result.returncode)
        self.assertIn("FAILED", result.stdout)
        self.assertFalse(self.trace.exists())

    def test_wrong_size_download_is_rejected_before_execution(self):
        self.download.write_bytes(INSTALLER + b"\n")
        result = self.replay()
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(self.trace.exists())

    def test_failed_download_is_rejected_before_execution(self):
        result = self.replay({"TEST_DOWNLOAD_FAILURE": "1"})
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(self.trace.exists())

    def test_installed_launcher_mutation_is_rejected_before_compiler_use(self):
        result = self.replay({"TEST_MUTATE_LAUNCHER": "1"})
        self.assertNotEqual(0, result.returncode)
        self.assertIn("FAILED", result.stdout)
        self.assertNotIn("rustc --version", self.trace.read_text(encoding="utf-8"))

    def test_installer_must_publish_exact_launcher_before_rustup_use(self):
        result = self.replay({"TEST_MUTATE_ON_INSTALL": "1"})
        self.assertNotEqual(0, result.returncode)
        self.assertIn("FAILED", result.stdout)
        self.assertNotIn("rustup set", self.trace.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
