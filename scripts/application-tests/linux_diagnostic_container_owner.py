#!/usr/bin/env python3
"""Fail-closed owner for the bounded Linux diagnostic container.

The backend is deliberately injectable: production uses DockerBackend while
tests use a recording fake.  No payload command is interpreted by a shell.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

IMAGE = "sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94"
SOURCES = {
    "linux_diagnostic.py": "c9932ce4883b1c23c4fc5df0cdb6b4cbe855c140d38787b6abf960f1d75ee409",
    "runtime_contracts.py": "6d25c35718c056e9ee67dc8c0f132a650d1020a67cb9d9503a36092bba58b13e",
    "supervisor.py": "8b8700175e6673c3a6b652d4a93bd18b56def83dfa3ac4ec821d4ae6c554e873",
}


class OwnerError(RuntimeError):
    pass


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class DockerBackend:
    """Small argv-only Docker adapter; every call is recorded by the owner."""
    def __init__(self, executable="/usr/bin/docker"):
        self.executable = executable

    def call(self, argv, *, timeout=None, capture=True):
        return subprocess.run([self.executable, *argv], check=False,
                              timeout=timeout, capture_output=capture, text=True)


class DiagnosticOwner:
    def __init__(self, root, *, backend=None, nonce=None, clock=time.monotonic):
        self.root = Path(root).resolve()
        self.backend = backend or DockerBackend()
        self.nonce = nonce or uuid.uuid4().hex
        self.clock = clock
        self.name = "mckernel-linux-diagnostic-" + self.nonce
        self.label = "mckernel.linux-diagnostic.owner=" + self.nonce
        self.events = []
        self.container = None
        self.lease = self.root / (".linux-diagnostic-" + self.nonce + ".lease")
        self.journal = self.root / (".linux-diagnostic-" + self.nonce + ".jsonl")

    def _event(self, kind, **fields):
        event = {"event": kind, "monotonic": self.clock(), **fields}
        self.events.append(event)
        # Durable owner journal and live lease are created before container work.
        if self.journal.parent.is_dir():
            with self.journal.open("a", encoding="utf-8") as stream:
                stream.write(_json(event) + "\n")
                stream.flush(); os.fsync(stream.fileno())

    def _call(self, argv, timeout=None):
        self._event("docker_call", argv=list(argv))
        try:
            result = self.backend.call(list(argv), timeout=timeout)
        except Exception as error:
            self._event("backend_failure", error=repr(error))
            raise OwnerError("docker backend failure") from error
        if getattr(result, "returncode", 1) != 0:
            self._event("docker_failure", argv=list(argv), returncode=result.returncode,
                        stdout=getattr(result, "stdout", ""), stderr=getattr(result, "stderr", ""))
            raise OwnerError("docker command failed")
        self._event("docker_result", argv=list(argv), returncode=result.returncode,
                    stdout=getattr(result, "stdout", ""), stderr=getattr(result, "stderr", ""))
        return result

    def _identity(self, path):
        path = Path(path).resolve(strict=True)
        info = path.stat()
        return {"path": str(path), "size": info.st_size, "mode": info.st_mode,
                "uid": info.st_uid, "gid": info.st_gid, "dev": info.st_dev,
                "ino": info.st_ino, "mtime_ns": info.st_mtime_ns,
                "ctime_ns": info.st_ctime_ns, "sha256": sha256(path)}

    def snapshot_sources(self, destination, source_dir):
        """Copy reviewed controller inputs into a private, hash-checked snapshot."""
        destination = Path(destination).resolve()
        destination.mkdir(mode=0o700)
        source_dir = Path(source_dir).resolve(strict=True)
        manifest = {}
        for name, expected_prefix in SOURCES.items():
            source = source_dir / name
            actual = sha256(source)
            if not actual.startswith(expected_prefix):
                raise OwnerError("source hash mismatch: " + name)
            target = destination / name
            with source.open("rb") as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst)
            os.chmod(target, 0o500)
            if sha256(target) != actual:
                raise OwnerError("snapshot changed: " + name)
            manifest[name] = self._identity(target)
        self._event("private_snapshot", manifest=manifest)
        return manifest

    def _create_argv(self, image=IMAGE):
        return ["create", "--pull=never", "--init", "--name", self.name,
                "--label", self.label, "--cpus=4", "--cpuset-cpus=2-5",
                "--cgroup-parent=/mckernel-dev", "--memory=12g", "--memory-swap=12g",
                "--pids-limit=512", "--cap-drop=ALL", "--security-opt=no-new-privileges",
                "--read-only", "--network=none", "--user=1000:1000", "--ulimit", "core=0",
                "--ulimit", "nofile=4096:4096", "--tmpfs", "/tmp:rw,nodev,nosuid,size=256m",
                "--mount", "type=bind,src=" + str(self.root / "snapshot") + ",dst=/snapshot,readonly",
                "--mount", "type=bind,src=" + str(self.root) + ",dst=/work",
                "--env", "TMPDIR=/work/tmp", "--env", "HOME=/tmp",
                "--env", "PYTHONDONTWRITEBYTECODE=1", "--workdir=/work",
                "--entrypoint=/usr/bin/python3", image, "-B",
                "/snapshot/linux_diagnostic.py", "--request", "/work/request.json"]

    def _owned(self):
        result = self._call(["ps", "-aq", "--filter", "name=^" + self.name + "$",
                             "--filter", "label=" + self.label])
        ids = [line for line in result.stdout.splitlines() if line]
        if len(ids) != 1:
            raise OwnerError("owner lookup is ambiguous")
        self.container = ids[0]
        return self.container

    def preflight(self, closure_manifest):
        if not isinstance(closure_manifest, dict) or closure_manifest.get("complete") is not True:
            raise OwnerError("incomplete loader closure")
        seen = set()
        files = closure_manifest.get("files")
        if not isinstance(files, list) or not files:
            raise OwnerError("empty loader closure")
        for item in closure_manifest.get("files", []):
            path = item.get("canonical_path", "") if isinstance(item, dict) else ""
            digest = item.get("sha256", "") if isinstance(item, dict) else ""
            if not path.startswith("/") or path in seen or len(digest) != 64:
                raise OwnerError("invalid closure member")
            seen.add(path)
        self._event("closure_preflight", manifest=closure_manifest)

    def run(self, *, closure_manifest, deadline_seconds=45):
        if not self.root.is_dir() or self.root.is_symlink():
            raise OwnerError("root must be an existing controlled directory")
        if self.root.stat().st_mode & 0o077:
            raise OwnerError("root must be private")
        self.preflight(closure_manifest)
        self.lease.open("x").close()
        # A stale name/label is never adopted.  Zero is the only valid
        # pre-create result; exactly one is required after create.
        existing = self._call(["ps", "-aq", "--filter", "name=^" + self.name + "$",
                               "--filter", "label=" + self.label])
        if existing.stdout.strip():
            raise OwnerError("stale or ambiguous owner container")
        create = self._call(self._create_argv())
        ids = create.stdout.strip().splitlines()
        if len(ids) != 1 or not ids[0].strip() or any(len(x.split()) != 1 for x in ids):
            raise OwnerError("create returned ambiguous container id")
        self.container = ids[0].strip()
        if self._owned() != self.container:
            raise OwnerError("created container owner identity changed")
        self._event("created", container=self.container, name=self.name, label=self.label)
        started = self.clock()
        try:
            self._call(["start", "--attach", self.container], timeout=deadline_seconds)
            inspect = self._call(["inspect", "--format", "{{json .State}}", self.container])
            state = json.loads(inspect.stdout)
            predicates = (state.get("Status") == "exited", state.get("Running") is False,
                          state.get("Paused") is False, state.get("Restarting") is False,
                          state.get("OOMKilled") is False, state.get("Dead") is False,
                          state.get("Error", "") == "", state.get("ExitCode") == 0)
            if not all(predicates):
                raise OwnerError("container exit predicates failed")
            self._event("collector", status="PASS", supervisor_status="COMPLETED",
                        elapsed=self.clock() - started)
        except Exception as error:
            self._event("first_failure", error=str(error))
            raise
        finally:
            failures = []
            for command, timeout in ((["stop", "--time=2", self.container], 3),
                                     (["kill", self.container], 3),
                                     (["rm", "--force", self.container], 10)):
                try:
                    self._call(command, timeout=timeout)
                except Exception as error:
                    failures.append(command[0] + ":" + str(error))
            try:
                absence = self._call(["ps", "-aq", "--filter", "name=^" + self.name + "$",
                                      "--filter", "label=" + self.label])
                if absence.stdout.strip():
                    failures.append("container remains after removal")
            except Exception as error:
                failures.append("absence:" + str(error))
            if failures:
                self._event("cleanup_uncertain", errors=failures, lease_retained=True)
                raise OwnerError("cleanup uncertain: " + ";".join(failures))
            self._event("cleanup", status="complete")
            self.lease.unlink(missing_ok=True)
        return {"status": "PASS", "collector": "PASS", "supervisor": "COMPLETED",
                "container": self.container, "events": self.events}


def run(root, closure_manifest, **kwargs):
    return DiagnosticOwner(root, **kwargs).run(closure_manifest=closure_manifest)
