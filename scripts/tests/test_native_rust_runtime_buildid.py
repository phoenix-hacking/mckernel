"""Check init rendering and shell argument transport, without kernel execution."""

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

from scripts import native_rust_runtime_evidence as evidence
from scripts.tests import test_native_rust_kbuild_link_closure as link_fixtures


REPO_ROOT = Path(__file__).resolve().parents[2]


class NativeRustRuntimeBuildidTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="native-runtime-buildid-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.repo = self.directory / "repo"
        self.template = self.repo / "scripts/native-rust-runtime-init.sh"
        self.template.parent.mkdir(parents=True)
        shutil.copyfile(REPO_ROOT / "scripts/native-rust-runtime-init.sh", self.template)
        self.template.chmod(0o644)
        self.lock_path = self.directory / "stage-lock.json"
        self.fixture = link_fixtures.NativeRustKbuildLinkClosureTests(
            "test_valid_closure_is_exact_canonical_and_credit_forbidden"
        )
        self.lock = self.fixture.make_stage_lock()
        self.write_lock(self.lock)

    def write_lock(self, lock):
        self.lock_path.write_bytes(evidence._link_closure_module.canonical_bytes(lock))
        self.lock_path.chmod(0o644)

    def write_identity(self, value, origin):
        self.lock["compatibility_build_identity"] = self.fixture.make_compatibility_identity(value, origin)
        for item in self.lock["files"]:
            if item["path"] == "ihk-compat-build-id.bin":
                item["sha256"] = self.lock["compatibility_build_identity"]["sha256"]
        self.write_lock(self.lock)

    def render(self, release=None):
        if release is None:
            release = evidence.EXPECTED_KERNEL_RELEASE
        return evidence.render_runtime_init(self.repo, self.lock_path, release)

    def test_renders_exact_git_and_archive_identity_with_no_credit_claim(self):
        for value, origin in (
            ("3114d9e", "ihk-git-short-head"),
            ("1.7.0rc4", "ihk-version-fallback"),
            ("v1.2-rc_3+test", "ihk-version-fallback"),
        ):
            with self.subTest(origin=origin, value=value):
                self.write_identity(value, origin)
                rendered = self.render()
                assignment = b"readonly EXPECTED_IHK_BUILD_ID=" + value.encode("ascii") + b"\n"
                self.assertEqual(1, rendered.count(assignment))
                self.assertIn(b"readonly EXPECTED_KERNEL_RELEASE=" + evidence.EXPECTED_KERNEL_RELEASE.encode("ascii") + b"\n", rendered)
                self.assertNotIn(b"@EXPECTED_", rendered)
                self.assertNotIn(b"\0", rendered)
                self.assertIn(b"technical-capture-unreviewed credit=forbidden", rendered)
                self.assertNotIn(b"credit=eligible", rendered)
                self.assertFalse(self.lock["credit_eligible"])

    def test_exact_single_identity_argument_reaches_all_four_probe_calls(self):
        bash = shutil.which("bash")
        if bash is None:
            self.skipTest("bash unavailable for source-only argument transport check")
        for value, origin in (
            ("3114d9e", "ihk-git-short-head"),
            ("v1.2-rc_3+test", "ihk-version-fallback"),
        ):
            with self.subTest(value=value):
                self.write_identity(value, origin)
                rendered = self.render().decode("ascii")
                assignment = next(line for line in rendered.splitlines() if line.startswith("readonly EXPECTED_IHK_BUILD_ID="))
                calls = [line for line in rendered.splitlines() if line.startswith(('"$MCD0_IOCTL_NATIVE"', '"$MCD0_IOCTL_COMPAT"'))]
                self.assertEqual(4, len(calls))
                self.assertEqual(2, sum(line.startswith('"$MCD0_IOCTL_NATIVE" "$EXPECTED_IHK_BUILD_ID" ||') for line in calls))
                self.assertEqual(2, sum(line.startswith('"$MCD0_IOCTL_COMPAT" "$EXPECTED_IHK_BUILD_ID" ||') for line in calls))
                # Run only the extracted assignment/call lines. The shell
                # function records argv with NUL delimiters; no /dev access,
                # module operation, guest init or real probe is executed.
                program = "\n".join([
                    "set -euo pipefail", assignment,
                    "readonly MCD0_IOCTL_NATIVE=record_argument",
                    "readonly MCD0_IOCTL_COMPAT=record_argument",
                    "record_argument() { [ \"$#\" -eq 1 ] && printf '%s\\0' \"$1\"; }",
                    "fail() { return 1; }", *calls,
                ])
                result = subprocess.run([bash, "-c", program], capture_output=True, check=False)
                self.assertEqual(0, result.returncode, result.stderr)
                payload = value.encode("ascii") + b"\0"
                self.assertEqual(payload * 4, result.stdout)
                self.assertEqual(hashlib.sha256(payload).hexdigest(), self.lock["compatibility_build_identity"]["sha256"])

    def test_rejects_wrong_release_before_rendering(self):
        for release in ("", "6.12.0", evidence.EXPECTED_KERNEL_RELEASE + "\n", "$(false)", 1, None):
            with self.subTest(release=release), self.assertRaisesRegex(evidence.EvidenceError, "kernel release"):
                evidence.render_runtime_init(self.repo, self.lock_path, release)

    def test_rejects_identity_digest_length_and_staged_file_mismatch(self):
        for field, value in (("value", "a1b2c3e"), ("bytes", 7), ("sha256", "d" * 64)):
            changed = copy.deepcopy(self.lock)
            changed["compatibility_build_identity"][field] = value
            self.write_lock(changed)
            with self.subTest(field=field), self.assertRaisesRegex(evidence.EvidenceError, "stage lock is invalid"):
                self.render()
        changed = copy.deepcopy(self.lock)
        for item in changed["files"]:
            if item["path"] == "ihk-compat-build-id.bin":
                item["sha256"] = "e" * 64
        self.write_lock(changed)
        with self.assertRaisesRegex(evidence.EvidenceError, "stage lock is invalid"):
            self.render()

    def test_rejects_shell_metacharacters_even_with_consistent_payload_digests(self):
        for value in ("x;false", "$(false)", "x\ny", "x y", "x\0", "x@y", "", "a" * 41):
            with self.subTest(value=value):
                self.write_identity(value, "ihk-version-fallback")
                with self.assertRaisesRegex(evidence.EvidenceError, "stage lock is invalid"):
                    self.render()

    def test_rejects_noncanonical_or_duplicate_stage_lock_json(self):
        canonical = evidence._link_closure_module.canonical_bytes(self.lock)
        malformed = (
            json.dumps(self.lock).encode("ascii") + b"\n",
            canonical.replace(b'"bytes":8', b'"bytes":8,"bytes":8', 1),
            canonical + b"\n",
        )
        for value in malformed:
            self.assertNotEqual(canonical, value)
            self.lock_path.write_bytes(value)
            with self.subTest(raw=value[:40]), self.assertRaisesRegex(evidence.EvidenceError, "stage lock is invalid"):
                self.render()

    def test_rejects_unreviewed_template_identity(self):
        self.template.write_bytes(self.template.read_bytes() + b"# changed\n")
        with self.assertRaisesRegex(evidence.EvidenceError, "template identity differs"):
            self.render()

    def test_rejects_missing_duplicate_or_unknown_template_placeholders(self):
        original = self.template.read_bytes()
        cases = []
        for marker in (b"@EXPECTED_KERNEL_RELEASE@", b"@EXPECTED_IHK_BUILD_ID@"):
            cases.extend((original.replace(marker, b"missing", 1), original + b"# " + marker + b"\n"))
        cases.append(original + b"# @UNREVIEWED_PLACEHOLDER@\n")
        for template in cases:
            self.template.write_bytes(template)
            with self.subTest(template=template[-50:]), mock.patch.object(
                evidence, "EXPECTED_RUNTIME_INIT_SHA256", hashlib.sha256(template).hexdigest()
            ), self.assertRaisesRegex(evidence.EvidenceError, "placeholder"):
                self.render()

    def test_rejects_stage_lock_and_template_symlink_inputs(self):
        for path in (self.lock_path, self.template):
            with self.subTest(path=path.name):
                target = path.with_suffix(path.suffix + ".real")
                path.rename(target)
                path.symlink_to(target)
                try:
                    with self.assertRaisesRegex(evidence.EvidenceError, "non-symlink"):
                        self.render()
                finally:
                    path.unlink()
                    target.rename(path)

    def test_actual_workflow_renderer_enforces_canonical_release_before_output(self):
        workflow = (REPO_ROOT / ".github/workflows/native-rust-host-modules-exact-runtime.yml").read_text()
        marker = '          python3 - <<\'PY\' > "$INITRAMFS_ROOT/init"\n'
        self.assertEqual(1, workflow.count(marker))
        block = workflow.split(marker, 1)[1].split("          PY\n", 1)[0]
        program = textwrap.dedent(block)
        self.assertIn("from scripts.native_rust_runtime_evidence import render_runtime_init", program)
        self.assertIn('Path.cwd(), evidence / "stage-lock.json", release[:-1]', program)
        environment = dict(os.environ, BUILD_EVIDENCE=str(self.directory), PYTHONDONTWRITEBYTECODE="1")
        release_path = self.directory / "kernel.release"
        exact = evidence.EXPECTED_KERNEL_RELEASE.encode("ascii")
        for raw, succeeds in (
            (exact + b"\n", True), (exact + b"\r\n", False),
            (exact + b"\n\n", False), (exact, False),
            (b"wrong-kernel\n", False), (b"\xff\n", False),
        ):
            with self.subTest(release=raw):
                release_path.write_bytes(raw)
                result = subprocess.run(
                    [sys.executable, "-c", program], cwd=REPO_ROOT, env=environment,
                    capture_output=True, check=False,
                )
                if succeeds:
                    self.assertEqual(0, result.returncode, result.stderr)
                    self.assertEqual(self.render(), result.stdout)
                else:
                    self.assertNotEqual(0, result.returncode)
                    self.assertEqual(b"", result.stdout)


if __name__ == "__main__":
    unittest.main()
