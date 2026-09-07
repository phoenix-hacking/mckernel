#!/usr/bin/env python3

import ast
import copy
import io
import gzip
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "rocky_repository_snapshot_capture.py"
SPEC = importlib.util.spec_from_file_location("snapshot_capture", str(SCRIPT))
snapshot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(snapshot)
SOURCE_COMMIT = subprocess.check_output(
    ["/usr/bin/git", "-C", str(REPO), "rev-parse", "HEAD"],
    stderr=subprocess.STDOUT,
).decode("ascii").strip()
WORKFLOW_REF = (
    "phoenix-hacking/mckernel/"
    ".github/workflows/rocky-repository-snapshot-capture-v2.yml"
    "@refs/heads/codex/rocky-rust-validation"
)
EXECUTION_IDENTITY = {
    "source_commit": SOURCE_COMMIT,
    "workflow_ref": WORKFLOW_REF,
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def deterministic_gzip(data):
    output = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as stream:
        stream.write(data)
    return output.getvalue()


def repomd_xml(objects):
    rows = []
    for row in objects:
        open_fields = ""
        if row.get("open_sha256") is not None:
            open_fields = (
                "<open-checksum type=\"sha256\">{}</open-checksum>"
                "<open-size>{}</open-size>"
            ).format(row["open_sha256"], row["open_size"])
        rows.append(
            (
                "<data type=\"{}\">"
                "<checksum type=\"sha256\">{}</checksum>"
                "{}"
                "<location href=\"{}\"/>"
                "<timestamp>1</timestamp>"
                "<size>{}</size>"
                "</data>"
            ).format(
                row["type"],
                row["sha256"],
                open_fields,
                row["href"],
                row["size"],
            )
        )
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<repomd xmlns=\"http://linux.duke.edu/metadata/repo\">"
        "<revision>10.2</revision>{}</repomd>"
    ).format("".join(rows)).encode("utf-8")


def object_row(data_type, href, compressed, opened=None):
    if opened is None:
        return {
            "href": href,
            "sha256": sha256(compressed),
            "size": len(compressed),
            "type": data_type,
        }
    return {
        "href": href,
        "open_sha256": sha256(opened),
        "open_size": len(opened),
        "sha256": sha256(compressed),
        "size": len(compressed),
        "type": data_type,
    }


class ContractTests(unittest.TestCase):
    def test_repository_contract_is_valid_and_no_credit(self):
        contract, records = snapshot.check_repository_inputs(REPO)
        self.assertEqual(contract["claims"], snapshot.FALSE_CLAIMS)
        self.assertTrue(all(value is False for value in contract["claims"].values()))
        self.assertEqual(
            contract["execution_identity"], snapshot.EXECUTION_IDENTITY_POLICY
        )
        self.assertEqual(contract["git_authority"], snapshot.GIT_AUTHORITY_POLICY)
        self.assertGreaterEqual(
            contract["limits"]["max_snapshot_tar_bytes"],
            contract["limits"]["max_tar_payload_bytes"],
        )
        self.assertEqual(len(records), 4)

    def test_repository_input_record_schema_is_exact_and_complete(self):
        _, records = snapshot.check_repository_inputs(REPO)
        snapshot.validate_input_records(records)
        for changed in (
            records[:-1],
            [dict(row) for row in records],
        ):
            if len(changed) == len(records):
                changed[0]["size"] = float(changed[0]["size"])
            with self.assertRaises(snapshot.SnapshotError):
                snapshot.validate_input_records(changed)

    def test_deep_json_and_invalid_execution_identity_fail_closed(self):
        deep = (
            "{" + '"level":{' * 80 + '"value":0' + "}" * 80 + "}"
        ).encode("ascii")
        with self.assertRaisesRegex(snapshot.SnapshotError, "nesting"):
            snapshot.strict_json_bytes(deep, "deep fixture")
        with self.assertRaisesRegex(snapshot.SnapshotError, "source commit"):
            snapshot.validate_execution_identity("A" * 40, WORKFLOW_REF)
        with self.assertRaisesRegex(snapshot.SnapshotError, "workflow ref"):
            snapshot.validate_execution_identity(
                SOURCE_COMMIT,
                "phoenix-hacking/other/.github/workflows/other.yml@refs/heads/main",
            )

    def test_nonfinite_float_and_huge_json_numbers_fail_closed(self):
        for data in (
            b'{"value":NaN}',
            b'{"value":Infinity}',
            b'{"value":-Infinity}',
            b'{"value":2.0}',
            b'{"value":' + (b"9" * 21) + b"}",
        ):
            with self.subTest(data=data), self.assertRaises(snapshot.SnapshotError):
                snapshot.strict_json_bytes(data, "numeric fixture")

    def test_recursive_exact_comparison_rejects_python_numeric_aliases(self):
        expected = {
            "claims": {"tracker_credit": False},
            "results": [True, 2, 7],
        }
        for changed in (
            {"claims": {"tracker_credit": 0}, "results": [True, 2, 7]},
            {"claims": {"tracker_credit": False}, "results": [1, 2, 7]},
            {"claims": {"tracker_credit": False}, "results": [True, 2.0, 7]},
        ):
            with self.subTest(changed=changed), self.assertRaisesRegex(
                snapshot.SnapshotError, "type changed"
            ):
                snapshot.require_exact(changed, expected, "recursive fixture")

    def test_every_contract_leaf_is_compiled_exact_authority(self):
        contract, _ = snapshot.load_contract(REPO)
        self.assertEqual(contract, snapshot.expected_contract())
        leaves = []

        def collect(value, path):
            if isinstance(value, dict):
                for key in sorted(value):
                    collect(value[key], path + (key,))
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    collect(item, path + (index,))
            else:
                leaves.append(path)

        def replace(value, path, replacement):
            target = value
            for component in path[:-1]:
                target = target[component]
            target[path[-1]] = replacement

        collect(contract, ())
        self.assertGreater(len(leaves), 60)
        for path in leaves:
            changed = copy.deepcopy(contract)
            target = contract
            for component in path:
                target = target[component]
            if type(target) is bool:
                replacement = not target
            elif type(target) is int:
                replacement = target + 1
            elif isinstance(target, str):
                replacement = target + "-mutated"
            else:
                self.fail("unhandled contract leaf type: {}".format(type(target)))
            replace(changed, path, replacement)
            with self.subTest(path=path), self.assertRaises(snapshot.SnapshotError):
                snapshot.validate_contract(changed)

    def test_invalid_git_ref_spellings_fail_closed(self):
        for suffix in (
            "refs/heads/.hidden",
            "refs/heads/trailing.",
            "refs/heads/name.lock",
            "refs/heads/a~b",
            "refs/heads/a:b",
            "refs/heads/a?b",
            "refs/heads/a[b",
        ):
            with self.subTest(suffix=suffix), self.assertRaisesRegex(
                snapshot.SnapshotError, "workflow ref"
            ):
                snapshot.validate_execution_identity(
                    SOURCE_COMMIT, snapshot.WORKFLOW_REF_PREFIX + suffix
                )

    def test_path_first_fake_git_cannot_forge_non_repository_authority(self):
        payload = b"forged worktree authority\n"
        commit = "f" * 40
        object_id = "e" * 40
        with tempfile.TemporaryDirectory(prefix="snapshot-fake-git-") as temporary:
            root = Path(temporary)
            repo = root / "not-a-git-repository"
            fakebin = root / "fakebin"
            marker = root / "fake-git-ran"
            repo.mkdir()
            fakebin.mkdir()
            input_path = repo / "input.txt"
            input_path.write_bytes(payload)
            input_path.chmod(0o644)
            fake = fakebin / "git"
            fake.write_text(
                "#!/usr/bin/python3\n"
                "import pathlib\n"
                "import sys\n"
                "args = sys.argv[1:]\n"
                "pathlib.Path({!r}).write_text('executed\\n')\n"
                "payload = b'forged worktree authority\\n'\n"
                "commit = b'f' * 40\n"
                "oid = b'e' * 40\n"
                "if 'rev-parse' in args:\n"
                "    sys.stdout.buffer.write(commit + b'\\n')\n"
                "elif 'ls-tree' in args:\n"
                "    sys.stdout.buffer.write(b'100644 blob ' + oid + b'\\tinput.txt\\0')\n"
                "elif 'ls-files' in args:\n"
                "    sys.stdout.buffer.write(b'100644 ' + oid + b' 0\\tinput.txt\\0')\n"
                "elif 'cat-file' in args and '-t' in args:\n"
                "    sys.stdout.buffer.write(b'blob\\n')\n"
                "elif 'cat-file' in args and '-s' in args:\n"
                "    sys.stdout.buffer.write(str(len(payload)).encode() + b'\\n')\n"
                "elif 'show' in args:\n"
                "    sys.stdout.buffer.write(payload)\n"
                "else:\n"
                "    raise SystemExit(91)\n".format(str(marker)),
                encoding="ascii",
            )
            fake.chmod(0o755)
            record = {
                "path": "input.txt",
                "sha256": sha256(payload),
                "size": len(payload),
            }
            hostile_path = str(fakebin) + ":/usr/bin:/bin"
            with mock.patch.dict(os.environ, {"PATH": hostile_path}, clear=False):
                before = dict(os.environ)
                with self.assertRaisesRegex(
                    snapshot.SnapshotError, "source commit inspection"
                ):
                    snapshot.require_repository_head(repo, commit, [record])
                self.assertEqual(dict(os.environ), before)
            self.assertFalse(marker.exists())

    def test_git_authority_strips_redirection_and_restores_environment(self):
        with tempfile.TemporaryDirectory(prefix="snapshot-git-env-") as temporary:
            root = Path(temporary)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(
                [snapshot.GIT_AUTHORITY_EXECUTABLE, "-C", str(repo), "init", "-q"],
                check=True,
            )
            subprocess.run(
                [
                    snapshot.GIT_AUTHORITY_EXECUTABLE,
                    "-C",
                    str(repo),
                    "config",
                    "user.name",
                    "Snapshot Authority Test",
                ],
                check=True,
            )
            subprocess.run(
                [
                    snapshot.GIT_AUTHORITY_EXECUTABLE,
                    "-C",
                    str(repo),
                    "config",
                    "user.email",
                    "snapshot-authority@example.invalid",
                ],
                check=True,
            )
            payload = b"trusted authority input\n"
            input_path = repo / "input.txt"
            input_path.write_bytes(payload)
            input_path.chmod(0o644)
            subprocess.run(
                [snapshot.GIT_AUTHORITY_EXECUTABLE, "-C", str(repo), "add", "input.txt"],
                check=True,
            )
            subprocess.run(
                [
                    snapshot.GIT_AUTHORITY_EXECUTABLE,
                    "-C",
                    str(repo),
                    "commit",
                    "-q",
                    "-m",
                    "fixture",
                ],
                check=True,
            )
            commit = subprocess.check_output(
                [snapshot.GIT_AUTHORITY_EXECUTABLE, "-C", str(repo), "rev-parse", "HEAD"]
            ).decode("ascii").strip()
            record = {
                "path": "input.txt",
                "sha256": sha256(payload),
                "size": len(payload),
            }
            hostile = {
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "core.worktree",
                "GIT_CONFIG_VALUE_0": "/hostile/worktree",
                "GIT_DIR": "/hostile/git-dir",
                "GIT_EXEC_PATH": "/hostile/git-exec",
                "GIT_INDEX_FILE": "/hostile/index",
                "GIT_SSH": "/hostile/git-ssh",
                "GIT_SSH_COMMAND": "/hostile/git-ssh-command",
                "GIT_WORK_TREE": "/hostile/worktree",
                "LD_LIBRARY_PATH": "/hostile/ld-library",
                "LD_PRELOAD": "/hostile/ld-preload.so",
                "PATH": "/hostile/path",
                "PYTHONHOME": "/hostile/python-home",
                "PYTHONPATH": "/hostile/python-path",
                "SSH_AUTH_SOCK": "/hostile/ssh-agent",
            }
            expected_environment = snapshot.git_authority_environment()
            original_run_checked = snapshot.run_checked
            observed = []

            def inspect_authority(command, label, environment=None):
                self.assertEqual(command[0], snapshot.GIT_AUTHORITY_EXECUTABLE)
                self.assertEqual(environment, expected_environment)
                self.assertEqual(command[1], "--no-pager")
                for value in snapshot.GIT_AUTHORITY_CONFIG:
                    self.assertIn(value, command)
                observed.append((tuple(command), dict(environment)))
                return original_run_checked(command, label, environment)

            with mock.patch.dict(os.environ, hostile, clear=False):
                before = dict(os.environ)
                with mock.patch.object(
                    snapshot, "run_checked", side_effect=inspect_authority
                ):
                    snapshot.require_repository_head(repo, commit, [record])
                self.assertEqual(dict(os.environ), before)
            self.assertGreater(len(observed), 10)
            inherited_names = set(hostile) - set(expected_environment)
            for _, environment in observed:
                self.assertFalse(inherited_names.intersection(environment))

    def test_source_commit_binds_repository_input_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "config", "user.name", "Snapshot Test"],
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "config",
                    "user.email",
                    "snapshot@example.invalid",
                ],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(repo), "config", "core.fileMode", "true"],
                check=True,
            )
            path = repo / "input.txt"
            original = b"committed input\n"
            path.write_bytes(original)
            executable_path = repo / "executable.txt"
            executable = b"committed executable\n"
            executable_path.write_bytes(executable)
            os.chmod(str(executable_path), 0o755)
            subprocess.run(
                ["git", "-C", str(repo), "add", "input.txt", "executable.txt"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(repo), "commit", "-q", "-m", "fixture"],
                check=True,
            )
            commit = subprocess.check_output(
                ["git", "-C", str(repo), "rev-parse", "HEAD"]
            ).decode("ascii").strip()
            record = {
                "path": "input.txt",
                "sha256": sha256(original),
                "size": len(original),
            }
            executable_record = {
                "path": "executable.txt",
                "sha256": sha256(executable),
                "size": len(executable),
            }
            hostile_git_environment = {
                "GIT_ALTERNATE_OBJECT_DIRECTORIES": "/nonexistent/alternates",
                "GIT_CEILING_DIRECTORIES": "/nonexistent/ceiling",
                "GIT_COMMON_DIR": "/nonexistent/common",
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "core.worktree",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_VALUE_0": "/nonexistent/config-worktree",
                "GIT_DIR": "/nonexistent/git-dir",
                "GIT_GRAFT_FILE": "/nonexistent/grafts",
                "GIT_INDEX_FILE": "/nonexistent/index",
                "GIT_NO_REPLACE_OBJECTS": "",
                "GIT_OBJECT_DIRECTORY": "/nonexistent/objects",
                "GIT_REPLACE_REF_BASE": "refs/review-replacements",
                "GIT_SHALLOW_FILE": "/nonexistent/shallow",
                "GIT_WORK_TREE": "/nonexistent/worktree",
            }
            with mock.patch.dict(os.environ, hostile_git_environment, clear=False):
                snapshot.require_repository_head(
                    repo, commit, [record, executable_record]
                )

            for changed_mode in (0o755, 0o654, 0o645, 0o600, 0o664, 0o4755):
                os.chmod(str(path), changed_mode)
                with self.subTest(mode=oct(changed_mode)), self.assertRaisesRegex(
                    snapshot.SnapshotError, "permission mode"
                ):
                    snapshot.require_repository_head(repo, commit, [record])
                os.chmod(str(path), 0o644)
            os.chmod(str(executable_path), 0o644)
            with self.assertRaisesRegex(snapshot.SnapshotError, "permission mode"):
                snapshot.require_repository_head(
                    repo, commit, [executable_record]
                )
            os.chmod(str(executable_path), 0o755)
            snapshot.require_repository_head(
                repo, commit, [record, executable_record]
            )

            tree_id = subprocess.check_output(
                ["git", "-C", str(repo), "rev-parse", commit + "^{tree}"]
            ).decode("ascii").strip()
            graft_parent = subprocess.run(
                ["git", "-C", str(repo), "commit-tree", tree_id],
                input=b"graft parent\n",
                check=True,
                stdout=subprocess.PIPE,
            ).stdout.decode("ascii").strip()
            graft_path = repo / ".git" / "info" / "grafts"
            graft_path.parent.mkdir(parents=True, exist_ok=True)
            graft_path.write_text(
                "{} {}\n".format(commit, graft_parent), encoding="ascii"
            )
            grafted = subprocess.run(
                ["git", "-C", str(repo), "rev-list", "--parents", "-1", commit],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout.decode("ascii").strip().split()
            self.assertEqual(grafted, [commit, graft_parent])
            original_run_checked = snapshot.run_checked
            graft_environments = []

            def observe_graft_suppression(command, label, environment=None):
                if command and command[0] == snapshot.GIT_AUTHORITY_EXECUTABLE:
                    self.assertEqual(environment, snapshot.git_authority_environment())
                    graft_environments.append(environment)
                return original_run_checked(command, label, environment)

            try:
                with mock.patch.object(
                    snapshot,
                    "run_checked",
                    side_effect=observe_graft_suppression,
                ):
                    snapshot.require_repository_head(repo, commit, [record])
            finally:
                graft_path.unlink()
            self.assertGreater(len(graft_environments), 10)

            original_reader = snapshot.read_regular_bytes

            def replay_after_worktree_mutation(mutate, restore):
                mutated = [False]

                def mutate_after_read(
                    file_path, label, maximum=None, expected_mode=None
                ):
                    data = original_reader(
                        file_path,
                        label,
                        maximum=maximum,
                        expected_mode=expected_mode,
                    )
                    if Path(file_path) == path and not mutated[0]:
                        mutate()
                        mutated[0] = True
                    return data

                try:
                    with mock.patch.object(
                        snapshot,
                        "read_regular_bytes",
                        side_effect=mutate_after_read,
                    ), self.assertRaises(snapshot.SnapshotError):
                        snapshot.require_repository_head(repo, commit, [record])
                finally:
                    restore()
                self.assertTrue(mutated[0])

            replay_after_worktree_mutation(
                lambda: path.write_bytes(b"changed after first worktree read\n"),
                lambda: (path.write_bytes(original), os.chmod(str(path), 0o644)),
            )
            replay_after_worktree_mutation(
                lambda: os.chmod(str(path), 0o600),
                lambda: os.chmod(str(path), 0o644),
            )
            symlink_target = repo / "symlink-target.txt"
            symlink_target.write_bytes(original)
            os.chmod(str(symlink_target), 0o644)

            def replace_with_symlink():
                path.unlink()
                path.symlink_to(symlink_target)

            def restore_regular_input():
                if path.is_symlink():
                    path.unlink()
                path.write_bytes(original)
                os.chmod(str(path), 0o644)

            replay_after_worktree_mutation(
                replace_with_symlink, restore_regular_input
            )

            original_blob = subprocess.check_output(
                ["git", "-C", str(repo), "rev-parse", commit + ":input.txt"]
            ).decode("ascii").strip()
            staged_blob = subprocess.run(
                ["git", "-C", str(repo), "hash-object", "-w", "--stdin"],
                input=b"staged input\n",
                check=True,
                stdout=subprocess.PIPE,
            ).stdout.decode("ascii").strip()

            index_mutated = [False]

            def mutate_after_index_read(command, label, environment=None):
                result = original_run_checked(command, label, environment)
                if "ls-files" in command and not index_mutated[0]:
                    subprocess.run(
                        [
                            "git",
                            "-C",
                            str(repo),
                            "update-index",
                            "--add",
                            "--cacheinfo",
                            "100644," + staged_blob + ",input.txt",
                        ],
                        check=True,
                    )
                    index_mutated[0] = True
                return result

            try:
                with mock.patch.object(
                    snapshot,
                    "run_checked",
                    side_effect=mutate_after_index_read,
                ), self.assertRaisesRegex(snapshot.SnapshotError, "repository index"):
                    snapshot.require_repository_head(repo, commit, [record])
            finally:
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(repo),
                        "update-index",
                        "--add",
                        "--cacheinfo",
                        "100644," + original_blob + ",input.txt",
                    ],
                    check=True,
                )
            self.assertTrue(index_mutated[0])

            loose_blob = (
                repo / ".git" / "objects" / original_blob[:2] / original_blob[2:]
            )
            self.assertTrue(loose_blob.is_file())
            loose_bytes = loose_blob.read_bytes()
            loose_mode = loose_blob.stat().st_mode & 0o7777
            for object_mutation in ("disappear", "corrupt"):
                blob_mutated = [False]

                def mutate_after_blob_read(command, label, environment=None):
                    result = original_run_checked(command, label, environment)
                    if (
                        "show" in command
                        and command[-1] == commit + ":input.txt"
                        and not blob_mutated[0]
                    ):
                        os.chmod(str(loose_blob), loose_mode | 0o200)
                        if object_mutation == "disappear":
                            loose_blob.unlink()
                        else:
                            loose_blob.write_bytes(b"corrupt loose Git object\n")
                        blob_mutated[0] = True
                    return result

                try:
                    with mock.patch.object(
                        snapshot,
                        "run_checked",
                        side_effect=mutate_after_blob_read,
                    ), self.assertRaises(snapshot.SnapshotError):
                        snapshot.require_repository_head(repo, commit, [record])
                finally:
                    loose_blob.parent.mkdir(parents=True, exist_ok=True)
                    if loose_blob.exists():
                        os.chmod(str(loose_blob), loose_mode | 0o200)
                    loose_blob.write_bytes(loose_bytes)
                    os.chmod(str(loose_blob), loose_mode)
                self.assertTrue(blob_mutated[0])

            staged_cases = (
                ("content", "100644", staged_blob),
                ("mode", "100755", original_blob),
                ("type", "120000", staged_blob),
            )
            for name, mode, blob in staged_cases:
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(repo),
                        "update-index",
                        "--add",
                        "--cacheinfo",
                        mode + "," + blob + ",input.txt",
                    ],
                    check=True,
                )
                with self.subTest(staged_case=name), self.assertRaisesRegex(
                    snapshot.SnapshotError, "repository index"
                ):
                    snapshot.require_repository_head(repo, commit, [record])
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(repo),
                        "update-index",
                        "--add",
                        "--cacheinfo",
                        "100644," + original_blob + ",input.txt",
                    ],
                    check=True,
                )
            subprocess.run(
                ["git", "-C", str(repo), "update-index", "--force-remove", "input.txt"],
                check=True,
            )
            with self.assertRaisesRegex(snapshot.SnapshotError, "repository index"):
                snapshot.require_repository_head(repo, commit, [record])
            conflict_rows = (
                "100644 {} 1\tinput.txt\n100644 {} 2\tinput.txt\n".format(
                    original_blob, staged_blob
                )
            ).encode("ascii")
            subprocess.run(
                ["git", "-C", str(repo), "update-index", "--index-info"],
                input=conflict_rows,
                check=True,
            )
            with self.assertRaisesRegex(snapshot.SnapshotError, "repository index"):
                snapshot.require_repository_head(repo, commit, [record])
            subprocess.run(
                ["git", "-C", str(repo), "update-index", "--force-remove", "input.txt"],
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "update-index",
                    "--add",
                    "--cacheinfo",
                    "100644," + original_blob + ",input.txt",
                ],
                check=True,
            )
            snapshot.require_repository_head(repo, commit, [record])

            changed = b"changed input\n"
            path.write_bytes(changed)
            with self.assertRaisesRegex(
                snapshot.SnapshotError, "checked-out repository input"
            ):
                snapshot.require_repository_head(repo, commit, [record])
            changed_record = {
                "path": "input.txt",
                "sha256": sha256(changed),
                "size": len(changed),
            }
            with self.assertRaisesRegex(snapshot.SnapshotError, "source-commit"):
                snapshot.require_repository_head(repo, commit, [changed_record])

            subprocess.run(
                ["git", "-C", str(repo), "add", "input.txt"], check=True
            )
            subprocess.run(
                ["git", "-C", str(repo), "commit", "-q", "-m", "replacement"],
                check=True,
            )
            replacement_commit = subprocess.check_output(
                ["git", "-C", str(repo), "rev-parse", "HEAD"]
            ).decode("ascii").strip()
            subprocess.run(
                ["git", "-C", str(repo), "switch", "-q", "--detach", commit],
                check=True,
            )
            path.write_bytes(changed)

            subprocess.run(
                ["git", "-C", str(repo), "replace", commit, replacement_commit],
                check=True,
            )
            self.assertEqual(
                subprocess.check_output(
                    ["git", "-C", str(repo), "show", commit + ":input.txt"]
                ),
                changed,
            )
            with self.assertRaisesRegex(snapshot.SnapshotError, "source-commit"):
                snapshot.require_repository_head(repo, commit, [changed_record])
            subprocess.run(
                ["git", "-C", str(repo), "replace", "-d", commit],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            replacement_namespace = "refs/review-replacements/"
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "update-ref",
                    replacement_namespace + commit,
                    replacement_commit,
                ],
                check=True,
            )
            custom_replace_environment = os.environ.copy()
            custom_replace_environment["GIT_REPLACE_REF_BASE"] = replacement_namespace
            self.assertEqual(
                subprocess.check_output(
                    ["git", "-C", str(repo), "show", commit + ":input.txt"],
                    env=custom_replace_environment,
                ),
                changed,
            )
            with mock.patch.dict(
                os.environ,
                {"GIT_REPLACE_REF_BASE": replacement_namespace},
                clear=False,
            ), self.assertRaisesRegex(snapshot.SnapshotError, "source-commit"):
                snapshot.require_repository_head(repo, commit, [changed_record])

    def test_any_true_claim_fails_closed(self):
        contract, _ = snapshot.load_contract(REPO)
        changed = copy.deepcopy(contract)
        changed["claims"]["tracker_credit"] = True
        with self.assertRaisesRegex(snapshot.SnapshotError, "claims"):
            snapshot.validate_contract(changed)

    def test_release_key_identity_change_fails_closed(self):
        contract, _ = snapshot.load_contract(REPO)
        changed = copy.deepcopy(contract)
        changed["release_key"]["fingerprint"] = "0" * 40
        with self.assertRaisesRegex(snapshot.SnapshotError, "fingerprint"):
            snapshot.validate_contract(changed)

    def test_tar_limit_widening_fails_closed(self):
        contract, _ = snapshot.load_contract(REPO)
        changed = copy.deepcopy(contract)
        changed["limits"]["max_tar_members"] += 1
        with self.assertRaisesRegex(snapshot.SnapshotError, "snapshot tar limits"):
            snapshot.validate_contract(changed)

    def test_repository_order_change_fails_closed(self):
        contract, _ = snapshot.load_contract(REPO)
        changed = copy.deepcopy(contract)
        changed["repositories"].reverse()
        with self.assertRaisesRegex(snapshot.SnapshotError, "repository set"):
            snapshot.validate_contract(changed)

    def test_checker_and_tests_remain_python_3_6_compatible(self):
        forbidden = (
            "from __future__ import " + "annotations",
            ".is_relative" + "_to(",
            ".remove" + "prefix(",
            ".remove" + "suffix(",
            "missing_" + "ok=",
            "gzip.Bad" + "GzipFile",
        )
        for relative in (
            snapshot.CHECKER_PATH,
            snapshot.TEST_PATH,
        ):
            path = REPO / relative
            source = path.read_text(encoding="utf-8")
            if sys.version_info >= (3, 8):
                try:
                    tree = ast.parse(source, filename=str(path), feature_version=(3, 6))
                except TypeError:
                    tree = ast.parse(source, filename=str(path), feature_version=6)
            else:
                tree = ast.parse(source, filename=str(path))
            self.assertIsNotNone(tree)
            for fragment in forbidden:
                self.assertNotIn(fragment, source)

    def test_workflow_is_manual_only_and_shell_blocks_parse(self):
        import yaml

        workflow_path = REPO / snapshot.WORKFLOW_PATH
        workflow_text = workflow_path.read_text(encoding="utf-8")
        workflow = yaml.safe_load(workflow_text)
        self.assertIsInstance(workflow, dict)
        trigger = workflow.get("on", workflow.get(True))
        self.assertEqual(set(trigger), {"workflow_dispatch"})
        self.assertIn(
            "bzip2 git-core gnupg2 gzip python3 python3-pyyaml tar xz",
            workflow_text.replace("\\\n            ", ""),
        )
        self.assertIn("/usr/bin/python3 -I -B -c 'import yaml'", workflow_text)
        self.assertIn('test "$GITHUB_SHA" = "$EXPECTED_HEAD_SHA"', workflow_text)
        self.assertIn(
            'test "$GITHUB_WORKFLOW_SHA" = "$EXPECTED_HEAD_SHA"', workflow_text
        )
        self.assertEqual(workflow_text.count('--source-commit "$EXPECTED_HEAD_SHA"'), 3)
        self.assertEqual(workflow_text.count('--workflow-ref "$GITHUB_WORKFLOW_REF"'), 3)
        self.assertNotIn(
            "python3 scripts/rocky_repository_snapshot_capture.py", workflow_text
        )
        self.assertEqual(
            workflow_text.count('/usr/bin/python3 -I -B "$committed_checker"'),
            3,
        )
        self.assertEqual(
            workflow_text.count(
                '"$EXPECTED_HEAD_SHA:scripts/rocky_repository_snapshot_capture.py"'
            ),
            2,
        )
        self.assertNotIn('PATH="$PATH"', workflow_text)
        self.assertEqual(workflow_text.count("/usr/bin/git --no-pager"), 2)
        self.assertEqual(workflow_text.count("GIT_ATTR_NOSYSTEM=1"), 2)
        self.assertEqual(workflow_text.count("GIT_CONFIG_GLOBAL=/dev/null"), 2)
        self.assertEqual(workflow_text.count("GIT_GRAFT_FILE=/dev/null"), 2)
        self.assertEqual(workflow_text.count("GIT_NO_REPLACE_OBJECTS=1"), 2)
        self.assertEqual(workflow_text.count("GIT_CONFIG_NOSYSTEM=1"), 2)
        self.assertEqual(workflow_text.count("GIT_OPTIONAL_LOCKS=0"), 2)
        self.assertEqual(workflow_text.count("core.fsmonitor=false"), 2)
        self.assertEqual(workflow_text.count("core.hooksPath=/dev/null"), 2)
        self.assertEqual(workflow_text.count("core.sshCommand=/usr/bin/false"), 2)
        self.assertEqual(workflow_text.count("XDG_CONFIG_HOME=/nonexistent"), 2)
        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                script = step.get("run")
                if script:
                    completed = subprocess.run(
                        ["bash", "-n"],
                        input=script.encode("utf-8"),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    self.assertEqual(
                        completed.returncode,
                        0,
                        completed.stderr.decode("utf-8", "replace"),
                    )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkout = root / "checkout"
            checkout.mkdir()
            subprocess.run(["git", "-C", str(checkout), "init", "-q"], check=True)
            subprocess.run(
                ["git", "-C", str(checkout), "config", "user.name", "Bootstrap Test"],
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(checkout),
                    "config",
                    "user.email",
                    "bootstrap@example.invalid",
                ],
                check=True,
            )
            for relative_text in sorted(set(snapshot.REQUIRED_INPUTS.values())):
                relative = Path(relative_text)
                destination = checkout / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((REPO / relative).read_bytes())
                os.chmod(str(destination), 0o644)
            subprocess.run(["git", "-C", str(checkout), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(checkout), "commit", "-q", "-m", "fixture"],
                check=True,
            )
            commit = subprocess.check_output(
                ["git", "-C", str(checkout), "rev-parse", "HEAD"]
            ).decode("ascii").strip()
            committed_checker = root / "committed-checker.py"
            committed_checker.write_bytes(
                subprocess.check_output(
                    [
                        "git",
                        "-C",
                        str(checkout),
                        "show",
                        commit + ":" + snapshot.CHECKER_PATH.as_posix(),
                    ]
                )
            )

            def run_committed_check():
                return subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(committed_checker),
                        "--repo",
                        str(checkout),
                        "--check",
                        "--source-commit",
                        commit,
                        "--workflow-ref",
                        WORKFLOW_REF,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

            clean = run_committed_check()
            self.assertEqual(clean.returncode, 0, clean.stderr.decode("utf-8"))
            worktree_checker = checkout / snapshot.CHECKER_PATH
            exact_checker = worktree_checker.read_bytes()
            worktree_checker.write_bytes(
                exact_checker + b"\n# uncommitted self-modification\n"
            )
            self.assertNotEqual(run_committed_check().returncode, 0)
            worktree_checker.write_bytes(exact_checker)
            workflow_input = checkout / snapshot.WORKFLOW_PATH
            workflow_input.write_bytes(
                workflow_input.read_bytes() + b"\n# staged workflow mutation\n"
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(checkout),
                    "add",
                    snapshot.WORKFLOW_PATH.as_posix(),
                ],
                check=True,
            )
            self.assertNotEqual(run_committed_check().returncode, 0)


class CallerPathTests(unittest.TestCase):
    def run_main(self, arguments):
        if "--capture" in arguments or "--verify-artifact" in arguments:
            arguments = list(arguments) + [
                "--source-commit",
                SOURCE_COMMIT,
                "--workflow-ref",
                WORKFLOW_REF,
            ]
        stderr = io.StringIO()
        with mock.patch.object(sys, "stderr", stderr), mock.patch.object(
            snapshot, "require_repository_head"
        ):
            result = snapshot.main(["--repo", str(REPO)] + arguments)
        return result, stderr.getvalue()

    def test_direct_symlink_output_fails_without_outside_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir()
            output = root / "output"
            output.symlink_to(outside, target_is_directory=True)
            result, error = self.run_main(["--capture", "--output-dir", str(output)])
            self.assertEqual(result, 1)
            self.assertIn("must not be a symlink", error)
            self.assertEqual(list(outside.iterdir()), [])

    def test_symlink_output_parent_fails_without_outside_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir()
            alias = root / "alias"
            alias.symlink_to(outside, target_is_directory=True)
            output = alias / "payload"
            result, error = self.run_main(["--capture", "--output-dir", str(output)])
            self.assertEqual(result, 1)
            self.assertIn("symlink component", error)
            self.assertEqual(list(outside.iterdir()), [])

    def test_symlink_diagnostics_parent_fails_without_outside_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir()
            alias = root / "alias"
            alias.symlink_to(outside, target_is_directory=True)
            output = root / "payload"
            diagnostics = alias / "diagnostics"
            result, error = self.run_main(
                [
                    "--capture",
                    "--output-dir",
                    str(output),
                    "--diagnostics-dir",
                    str(diagnostics),
                ]
            )
            self.assertEqual(result, 1)
            self.assertIn("symlink component", error)
            self.assertFalse(output.exists())
            self.assertEqual(list(outside.iterdir()), [])

    def test_symlink_artifact_fails_without_touching_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir()
            target = outside / "snapshot.tar"
            target.write_bytes(b"not-a-snapshot\n")
            artifact = root / "snapshot.tar"
            artifact.symlink_to(target)
            result, error = self.run_main(["--verify-artifact", str(artifact)])
            self.assertEqual(result, 1)
            self.assertIn("cannot safely open", error)
            self.assertEqual(target.read_bytes(), b"not-a-snapshot\n")
            self.assertEqual(sorted(path.name for path in outside.iterdir()), ["snapshot.tar"])

    def test_output_and_diagnostics_must_not_overlap(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cases = (
                (root / "same", root / "same"),
                (root / "payload", root / "payload" / "diagnostics"),
                (root / "diagnostics" / "payload", root / "diagnostics"),
            )
            for output, diagnostics in cases:
                result, error = self.run_main(
                    [
                        "--capture",
                        "--output-dir",
                        str(output),
                        "--diagnostics-dir",
                        str(diagnostics),
                    ]
                )
                self.assertEqual(result, 1)
                self.assertIn("must not overlap", error)
                self.assertFalse(output.exists())


class RepomdTests(unittest.TestCase):
    def test_parses_every_supported_compression_binding(self):
        opened = b"<metadata>bounded</metadata>\n"
        import bz2
        import lzma

        rows = [
            object_row("primary", "repodata/primary.xml.gz", gzip.compress(opened), opened),
            object_row("filelists", "repodata/filelists.xml.bz2", bz2.compress(opened), opened),
            object_row("other", "repodata/other.xml.xz", lzma.compress(opened), opened),
            object_row("group", "repodata/groups.xml", opened),
        ]
        parsed = snapshot.parse_repomd(repomd_xml(rows), 64)
        self.assertEqual(
            [row["compression"] for row in parsed["objects"]],
            ["gzip", "bzip2", "xz", "none"],
        )

    def test_path_traversal_fails_closed(self):
        data = b"x"
        row = object_row("primary", "repodata/../primary.xml", data)
        with self.assertRaisesRegex(snapshot.SnapshotError, "normalized relative path"):
            snapshot.parse_repomd(repomd_xml([row]), 64)

    def test_encoded_url_traversal_and_duplicate_semantic_children_fail_closed(self):
        contract, _ = snapshot.load_contract(REPO)
        with self.assertRaisesRegex(snapshot.SnapshotError, "HTTPS policy"):
            snapshot.validate_https_url(
                "https://download.rockylinux.org/pub/rocky/%2e%2e/escape",
                contract["network"]["allowed_hosts"],
                "fixture URL",
            )
        handler = snapshot.BoundedRedirectHandler(
            contract["network"]["allowed_hosts"],
            2,
            required_prefix="https://download.rockylinux.org/pub/rocky/10.2/BaseOS/",
        )
        with self.assertRaisesRegex(snapshot.SnapshotError, "base URL"):
            handler.redirect_request(
                None,
                None,
                302,
                "Found",
                {},
                "https://download.rockylinux.org/pub/rocky/10.2/AppStream/escape",
            )

        data = b"primary"
        row = object_row("primary", "repodata/primary.xml", data)
        xml = repomd_xml([row]).replace(
            b"<checksum type=\"sha256\">",
            b"<checksum type=\"sha256\">",
            1,
        ).replace(
            b"</checksum>",
            b"</checksum><checksum type=\"sha256\">" + sha256(data).encode("ascii") + b"</checksum>",
            1,
        )
        with self.assertRaisesRegex(snapshot.SnapshotError, "multiplicity"):
            snapshot.parse_repomd(xml, 64)

        xml = repomd_xml([row]).replace(
            b"<location href=\"repodata/primary.xml\"/>",
            b"<location href=\"repodata/primary.xml\"/>"
            b"<location href=\"repodata/other.xml\"/>",
            1,
        )
        with self.assertRaisesRegex(snapshot.SnapshotError, "multiplicity"):
            snapshot.parse_repomd(xml, 64)

    def test_duplicate_data_type_fails_closed(self):
        data = b"x"
        rows = [
            object_row("primary", "repodata/a.xml", data),
            object_row("primary", "repodata/b.xml", data),
        ]
        with self.assertRaisesRegex(snapshot.SnapshotError, "duplicated"):
            snapshot.parse_repomd(repomd_xml(rows), 64)

    def test_dtd_entities_and_root_attributes_fail_closed(self):
        data = b"primary"
        row = object_row("primary", "repodata/primary.xml", data)
        ordinary = repomd_xml([row])
        self.assertEqual(snapshot.parse_repomd(ordinary, 64)["revision"], "10.2")
        dtd = ordinary.replace(
            b"<repomd ", b'<!DOCTYPE repomd [<!ENTITY x "10.2">]><repomd ', 1
        ).replace(b"<revision>10.2</revision>", b"<revision>&x;</revision>")
        with self.assertRaisesRegex(snapshot.SnapshotError, "DTDs"):
            snapshot.parse_repomd(dtd, 64)
        dtd_text = dtd.decode("utf-8")
        for codec, declaration in (
            ("utf-16", "UTF-16"),
            ("utf-16-le", "UTF-16"),
            ("utf-16-be", "UTF-16"),
            ("utf-32", "UTF-32"),
            ("utf-32-le", "UTF-32"),
            ("utf-32-be", "UTF-32"),
        ):
            encoded = dtd_text.replace("UTF-8", declaration, 1).encode(codec)
            with self.subTest(codec=codec), self.assertRaises(
                snapshot.SnapshotError
            ):
                snapshot.parse_repomd(encoded, 64)
        with self.assertRaisesRegex(snapshot.SnapshotError, "byte-order mark"):
            snapshot.parse_repomd(b"\xef\xbb\xbf" + ordinary, 64)
        with self.assertRaisesRegex(snapshot.SnapshotError, "declare UTF-8"):
            snapshot.parse_repomd(
                ordinary.replace(b'encoding="UTF-8"', b'encoding="ISO-8859-1"'),
                64,
            )
        attributed = ordinary.replace(b"<repomd ", b'<repomd audit="1" ', 1)
        with self.assertRaisesRegex(snapshot.SnapshotError, "root attributes"):
            snapshot.parse_repomd(attributed, 64)

    def test_huge_repomd_integer_fails_closed(self):
        data = b"primary"
        row = object_row("primary", "repodata/primary.xml", data)
        xml = repomd_xml([row]).replace(
            b"<timestamp>1</timestamp>",
            b"<timestamp>" + (b"9" * 5000) + b"</timestamp>",
        )
        with self.assertRaisesRegex(snapshot.SnapshotError, "bounded"):
            snapshot.parse_repomd(xml, 64)

    def test_compressed_object_without_open_binding_fails_closed(self):
        data = gzip.compress(b"x")
        row = object_row("primary", "repodata/primary.xml.gz", data)
        with self.assertRaisesRegex(snapshot.SnapshotError, "open hash"):
            snapshot.parse_repomd(repomd_xml([row]), 64)

    def test_unsupported_compression_fails_closed(self):
        data = b"zchunk"
        row = object_row("primary", "repodata/primary.xml.zck", data, b"x")
        with self.assertRaisesRegex(snapshot.SnapshotError, "unsupported"):
            snapshot.parse_repomd(repomd_xml([row]), 64)

    def test_compressed_and_open_hashes_are_both_verified(self):
        opened = b"<metadata>verified</metadata>\n"
        compressed = gzip.compress(opened)
        row = snapshot.parse_repomd(
            repomd_xml(
                [object_row("primary", "repodata/primary.xml.gz", compressed, opened)]
            ),
            64,
        )["objects"][0]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "primary.xml.gz"
            path.write_bytes(compressed)
            result = snapshot.verify_metadata_object(path, row, 1024, [0, 4096])
            self.assertTrue(result["open_checksum_declared"])
            self.assertEqual(result["verified_open_sha256"], sha256(opened))
            path.write_bytes(compressed + b"tamper")
            with self.assertRaisesRegex(snapshot.SnapshotError, "compressed bytes"):
                snapshot.verify_metadata_object(path, row, 1024, [0, 4096])

    def test_open_byte_limit_is_enforced(self):
        opened = b"x" * 1025
        compressed = gzip.compress(opened)
        row = snapshot.parse_repomd(
            repomd_xml(
                [object_row("primary", "repodata/primary.xml.gz", compressed, opened)]
            ),
            64,
        )["objects"][0]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "primary.xml.gz"
            path.write_bytes(compressed)
            with self.assertRaisesRegex(snapshot.SnapshotError, "byte limit"):
                snapshot.verify_metadata_object(path, row, 1024, [0, 4096])


class DeterministicArtifactTests(unittest.TestCase):
    def setUp(self):
        self.contract, self.input_records = snapshot.check_repository_inputs(REPO)
        self.contract = copy.deepcopy(self.contract)
        self.key = b"synthetic-key-for-offline-unit-test\n"
        self.signature = b"synthetic-signature\n"
        self.opened = b"<metadata>unit-test</metadata>\n"
        self.compressed = deterministic_gzip(self.opened)
        self.object_href = "repodata/unit-primary.xml.gz"
        self.repomd = repomd_xml(
            [object_row("primary", self.object_href, self.compressed, self.opened)]
        )
        self.contract["release_key"]["size"] = len(self.key)
        self.contract["release_key"]["sha256"] = sha256(self.key)
        self.signature_record = {
            "hash_algorithm_id": 8,
            "primary_fingerprint": snapshot.RELEASE_FINGERPRINT,
            "public_key_algorithm_id": 1,
            "signature_fingerprint": snapshot.RELEASE_FINGERPRINT,
            "signature_timestamp": 1,
            "status": "verified",
        }

    def fake_download(self, url, destination, maximum, contract, required_prefix=None):
        if url == snapshot.RELEASE_KEY_URL:
            data = self.key
        elif url.endswith("repodata/repomd.xml.asc"):
            data = self.signature
        elif url.endswith("repodata/repomd.xml"):
            data = self.repomd
        elif url.endswith(self.object_href):
            data = self.compressed
        else:
            raise AssertionError("unexpected URL: {}".format(url))
        if len(data) > maximum:
            raise snapshot.SnapshotError("synthetic download exceeds limit")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return {
            "final_url": url,
            "redirect_count": 0,
            "sha256": sha256(data),
            "size": len(data),
            "url": url,
        }

    def test_capture_is_deterministic_and_offline_verifiable(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            output_one = temporary / "one"
            output_two = temporary / "two"
            diagnostics = temporary / "diagnostics"
            patches = (
                mock.patch.object(snapshot, "download_to_path", self.fake_download),
                mock.patch.object(
                    snapshot,
                    "verify_key_fingerprint_bytes",
                    side_effect=lambda path, fingerprint: fingerprint,
                ),
                mock.patch.object(
                    snapshot,
                    "verify_detached_signature_bytes",
                    return_value=self.signature_record,
                ),
                mock.patch.object(snapshot, "require_repository_head"),
                mock.patch.object(snapshot, "validate_contract"),
            )
            with patches[0], patches[1], patches[2], patches[3], patches[4]:
                first = snapshot.capture_snapshot(
                    REPO,
                    output_one,
                    diagnostics,
                    self.contract,
                    self.input_records,
                    EXECUTION_IDENTITY,
                )
                second = snapshot.capture_snapshot(
                    REPO,
                    output_two,
                    None,
                    self.contract,
                    self.input_records,
                    EXECUTION_IDENTITY,
                )
                verified = snapshot.verify_artifact(
                    REPO,
                    output_one / "snapshot.tar",
                    self.contract,
                    self.input_records,
                    EXECUTION_IDENTITY,
                )
                for changed_identity in (
                    dict(EXECUTION_IDENTITY, source_commit="0" * 40),
                    dict(
                        EXECUTION_IDENTITY,
                        workflow_ref=WORKFLOW_REF.replace(
                            "codex/rocky-rust-validation", "different-ref"
                        ),
                    ),
                ):
                    with self.assertRaisesRegex(
                        snapshot.SnapshotError, "snapshot capture manifest"
                    ):
                        snapshot.verify_artifact(
                            REPO,
                            output_one / "snapshot.tar",
                            self.contract,
                            self.input_records,
                            changed_identity,
                        )
            self.assertEqual(first["snapshot_identity"], second["snapshot_identity"])
            self.assertEqual(
                (output_one / "snapshot.tar").read_bytes(),
                (output_two / "snapshot.tar").read_bytes(),
            )
            self.assertEqual(verified, first)
            report = json.loads((diagnostics / "drift-report.json").read_text())
            self.assertEqual(report["claims"], snapshot.diagnostics_claims())
            self.assertTrue(all(value is False for value in report["claims"].values()))
            self.assertEqual(
                report["observations"]["execution_identity"], EXECUTION_IDENTITY
            )

    def test_public_verify_rejects_manifest_source_commit_not_at_head(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            false_identity = dict(EXECUTION_IDENTITY, source_commit="0" * 40)
            with mock.patch.object(
                snapshot, "download_to_path", self.fake_download
            ), mock.patch.object(
                snapshot,
                "verify_key_fingerprint_bytes",
                side_effect=lambda data, fingerprint: fingerprint,
            ), mock.patch.object(
                snapshot,
                "verify_detached_signature_bytes",
                return_value=self.signature_record,
            ), mock.patch.object(snapshot, "require_repository_head"), mock.patch.object(
                snapshot, "validate_contract"
            ):
                snapshot.capture_snapshot(
                    REPO,
                    output,
                    None,
                    self.contract,
                    self.input_records,
                    false_identity,
                )
            with mock.patch.object(snapshot, "validate_contract"), self.assertRaisesRegex(
                snapshot.SnapshotError, "checked-out source"
            ):
                snapshot.verify_artifact(
                    REPO,
                    output / "snapshot.tar",
                    self.contract,
                    self.input_records,
                    false_identity,
                )

    def test_manifest_numeric_type_aliases_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            patches = (
                mock.patch.object(snapshot, "download_to_path", self.fake_download),
                mock.patch.object(
                    snapshot,
                    "verify_key_fingerprint_bytes",
                    side_effect=lambda data, fingerprint: fingerprint,
                ),
                mock.patch.object(
                    snapshot,
                    "verify_detached_signature_bytes",
                    return_value=self.signature_record,
                ),
                mock.patch.object(snapshot, "require_repository_head"),
                mock.patch.object(snapshot, "validate_contract"),
            )
            with patches[0], patches[1], patches[2], patches[3], patches[4]:
                snapshot.capture_snapshot(
                    REPO,
                    output,
                    None,
                    self.contract,
                    self.input_records,
                    EXECUTION_IDENTITY,
                )
                tree = root / "tree"
                tree.mkdir()
                snapshot.extract_canonical_tar(
                    output / "snapshot.tar", tree, self.contract["limits"]
                )
                manifest_path = tree / "capture-manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="ascii"))
                manifest["claims"] = {key: 0 for key in manifest["claims"]}
                manifest["capture_results"] = {
                    key: 1 for key in manifest["capture_results"]
                }
                snapshot.safe_write_json(manifest_path, manifest)
                crafted = root / "aliased.tar"
                snapshot.create_deterministic_tar(
                    tree, crafted, self.contract["limits"]
                )
                with self.assertRaisesRegex(snapshot.SnapshotError, "type changed"):
                    snapshot.verify_artifact(
                        REPO,
                        crafted,
                        self.contract,
                        self.input_records,
                        EXECUTION_IDENTITY,
                    )

    def test_post_validation_artifact_symlink_swap_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            with mock.patch.object(
                snapshot, "download_to_path", self.fake_download
            ), mock.patch.object(
                snapshot,
                "verify_key_fingerprint_bytes",
                side_effect=lambda data, fingerprint: fingerprint,
            ), mock.patch.object(
                snapshot,
                "verify_detached_signature_bytes",
                return_value=self.signature_record,
            ), mock.patch.object(snapshot, "require_repository_head"), mock.patch.object(
                snapshot, "validate_contract"
            ):
                snapshot.capture_snapshot(
                    REPO,
                    output,
                    None,
                    self.contract,
                    self.input_records,
                    EXECUTION_IDENTITY,
                )
                target = output / "snapshot.tar"
                presented = root / "presented.tar"
                presented.write_bytes(target.read_bytes())
                original_open = snapshot.open_regular_read
                swapped = [False]

                def swap_before_open(path, label):
                    if Path(path) == presented and not swapped[0]:
                        swapped[0] = True
                        presented.unlink()
                        presented.symlink_to(target)
                    return original_open(path, label)

                with mock.patch.object(
                    snapshot, "open_regular_read", side_effect=swap_before_open
                ), self.assertRaises(snapshot.SnapshotError):
                    snapshot.verify_artifact(
                        REPO,
                        presented,
                        self.contract,
                        self.input_records,
                        EXECUTION_IDENTITY,
                    )
                self.assertTrue(presented.is_symlink())

                original_stage = snapshot.independent_stage_directory

                def exercise_parent_swap(name, swap_at_publication):
                    parent = root / (name + "-parent")
                    moved = root / (name + "-moved")
                    outside = root / (name + "-outside")
                    parent.mkdir()
                    outside.mkdir()
                    candidate = parent / "payload"
                    swapped_parent = [False]

                    def swap_parent():
                        parent.rename(moved)
                        parent.symlink_to(outside, target_is_directory=True)
                        swapped_parent[0] = True

                    if swap_at_publication:
                        original_publish = snapshot.publish_capture_files

                        def swap_before_publish(*arguments):
                            swap_parent()
                            return original_publish(*arguments)

                        patcher = mock.patch.object(
                            snapshot,
                            "publish_capture_files",
                            side_effect=swap_before_publish,
                        )
                    else:

                        def swap_before_stage():
                            swap_parent()
                            return original_stage()

                        patcher = mock.patch.object(
                            snapshot,
                            "independent_stage_directory",
                            side_effect=swap_before_stage,
                        )
                    with patcher, self.assertRaises(snapshot.SnapshotError):
                        snapshot.capture_snapshot(
                            REPO,
                            candidate,
                            None,
                            self.contract,
                            self.input_records,
                            EXECUTION_IDENTITY,
                        )
                    self.assertTrue(swapped_parent[0])
                    self.assertEqual(list(outside.iterdir()), [])
                    self.assertFalse((moved / "payload").exists())

                exercise_parent_swap("before-stage", False)
                exercise_parent_swap("before-publish", True)

                leaf_parent = root / "leaf-parent"
                leaf_parent.mkdir()
                leaf_output = leaf_parent / "payload"
                leaf_target = root / "leaf-target"
                leaf_target.write_bytes(b"must remain unchanged\n")
                original_publish = snapshot.publish_capture_files
                leaf_swapped = [False]

                def swap_leaf_before_publish(*arguments):
                    leaf_output.symlink_to(leaf_target)
                    leaf_swapped[0] = True
                    return original_publish(*arguments)

                with mock.patch.object(
                    snapshot,
                    "publish_capture_files",
                    side_effect=swap_leaf_before_publish,
                ), self.assertRaisesRegex(snapshot.SnapshotError, "leaf appeared"):
                    snapshot.capture_snapshot(
                        REPO,
                        leaf_output,
                        None,
                        self.contract,
                        self.input_records,
                        EXECUTION_IDENTITY,
                    )
                self.assertTrue(leaf_swapped[0])
                self.assertEqual(leaf_target.read_bytes(), b"must remain unchanged\n")

                cross_parent = root / "cross-parent-output"
                cross_parent.mkdir()
                cross_output = cross_parent / "payload"
                source_one = root / "source-one"
                source_two = root / "source-two"
                source_one.mkdir()
                source_two.mkdir()
                artifact = source_one / "snapshot.tar"
                checksum = source_two / "snapshot.tar.sha256"
                artifact.write_bytes(b"artifact")
                checksum.write_bytes(b"checksum")
                (
                    validated_output,
                    _,
                    parent_descriptor,
                    parent_identity,
                ) = snapshot.validate_capture_destinations(cross_output, None)
                try:
                    with self.assertRaisesRegex(
                        snapshot.SnapshotError, "one exact source parent"
                    ):
                        snapshot.publish_capture_files(
                            artifact,
                            checksum,
                            validated_output,
                            parent_descriptor,
                            parent_identity,
                        )
                finally:
                    os.close(parent_descriptor)
                self.assertFalse(cross_output.exists())

    def test_total_download_limit_is_applied_before_each_request(self):
        contract = copy.deepcopy(self.contract)
        contract["limits"]["max_total_download_bytes"] = 100
        self.assertEqual(snapshot.remaining_download_limit(contract, 0, 80), 80)
        self.assertEqual(snapshot.remaining_download_limit(contract, 75, 80), 25)
        with self.assertRaisesRegex(snapshot.SnapshotError, "exhausted"):
            snapshot.remaining_download_limit(contract, 100, 80)

    def test_unlisted_extra_payload_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            output = temporary / "output"
            patches = (
                mock.patch.object(snapshot, "download_to_path", self.fake_download),
                mock.patch.object(
                    snapshot,
                    "verify_key_fingerprint_bytes",
                    side_effect=lambda path, fingerprint: fingerprint,
                ),
                mock.patch.object(
                    snapshot,
                    "verify_detached_signature_bytes",
                    return_value=self.signature_record,
                ),
                mock.patch.object(snapshot, "require_repository_head"),
                mock.patch.object(snapshot, "validate_contract"),
            )
            with patches[0], patches[1], patches[2], patches[3], patches[4]:
                snapshot.capture_snapshot(
                    REPO,
                    output,
                    None,
                    self.contract,
                    self.input_records,
                    EXECUTION_IDENTITY,
                )
                tree = temporary / "tree"
                tree.mkdir()
                snapshot.extract_canonical_tar(
                    output / "snapshot.tar", tree, self.contract["limits"]
                )
                extra = tree / "unbound" / "extra.txt"
                extra.parent.mkdir()
                extra.write_bytes(b"extra payload\n")
                manifest_path = tree / "capture-manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="ascii"))
                manifest["payload_files"].append(
                    {
                        "path": "unbound/extra.txt",
                        "sha256": sha256(extra.read_bytes()),
                        "size": extra.stat().st_size,
                    }
                )
                manifest["payload_files"].sort(key=lambda row: row["path"])
                snapshot.safe_write_json(manifest_path, manifest)
                crafted = temporary / "crafted.tar"
                snapshot.create_deterministic_tar(
                    tree, crafted, self.contract["limits"]
                )
                with self.assertRaisesRegex(snapshot.SnapshotError, "path closure"):
                    snapshot.verify_artifact(
                        REPO,
                        crafted,
                        self.contract,
                        self.input_records,
                        EXECUTION_IDENTITY,
                    )

    def test_tar_count_and_byte_limits_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            tree = temporary / "tree"
            tree.mkdir()
            for name in ("a", "b", "c"):
                (tree / name).write_bytes(b"12345")
            artifact = temporary / "snapshot.tar"
            snapshot.create_deterministic_tar(tree, artifact)
            limits = copy.deepcopy(self.contract["limits"])
            limits["max_tar_members"] = 2
            with self.assertRaisesRegex(snapshot.SnapshotError, "member count"):
                snapshot.extract_canonical_tar(artifact, temporary / "count", limits)
            limits = copy.deepcopy(self.contract["limits"])
            limits["max_tar_member_bytes"] = 4
            with self.assertRaisesRegex(snapshot.SnapshotError, "member exceeds"):
                snapshot.extract_canonical_tar(artifact, temporary / "member", limits)
            limits = copy.deepcopy(self.contract["limits"])
            limits["max_tar_payload_bytes"] = 14
            with self.assertRaisesRegex(snapshot.SnapshotError, "payload exceeds"):
                snapshot.extract_canonical_tar(artifact, temporary / "payload", limits)
            with self.assertRaisesRegex(snapshot.SnapshotError, "artifact size"):
                snapshot.validate_artifact_path(artifact, artifact.stat().st_size - 1)

    def test_tar_metadata_is_canonical(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            tree = temporary / "tree"
            tree.mkdir()
            (tree / "b").write_bytes(b"b")
            (tree / "a").write_bytes(b"a")
            artifact = temporary / "snapshot.tar"
            snapshot.create_deterministic_tar(tree, artifact)
            with tarfile.open(str(artifact), "r:") as archive:
                members = archive.getmembers()
            self.assertEqual([member.name for member in members], ["a", "b"])
            for member in members:
                self.assertEqual(
                    (member.mode, member.uid, member.gid, member.mtime),
                    (0o644, 0, 0, 0),
                )


if __name__ == "__main__":
    unittest.main()
