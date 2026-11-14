#!/usr/bin/env python3
"""Prepare an exclusive root-test tree and exact Docker command plan; never run it.

The parent owns lock acquisition, bounded Docker commands/inspect, actual tests,
first-failure logging and final archive. Existing container-run.py is read only.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import uuid

WORK = Path("/home/holden/mckernel-work")
REPO = Path("/home/holden/mckernel")
FIXTURES = REPO / "scripts/tests/fixtures/application-collector-v1/linux-sealed-v1"
DOCKER = "/usr/bin/docker"
CGROUP = {
    "/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_period_us": "100000",
    "/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_quota_us": "400000",
    "/sys/fs/cgroup/memory/mckernel-dev/memory.limit_in_bytes": "12884901888",
    "/sys/fs/cgroup/memory/mckernel-dev/memory.use_hierarchy": "1",
    "/sys/fs/cgroup/pids/mckernel-dev/pids.max": "512",
}


def strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def no_constant(value):
    raise ValueError("nonfinite JSON constant: " + value)


def directory(path):
    if not path.is_absolute():
        raise ValueError("absolute directory required")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        for part in path.parts[1:]:
            if part in ("", ".", ".."):
                raise ValueError("canonical directory component required")
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd); fd = next_fd
        result = fd; fd = -1
        return result
    finally:
        if fd >= 0: os.close(fd)


def regular(path, maximum):
    if not path.is_absolute() or path.resolve(strict=True) != path or path.is_symlink():
        raise ValueError("canonical nonsymlink file required")
    parent = directory(path.parent)
    try: fd = os.open(path.name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    finally: os.close(parent)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or not 0 <= before.st_size <= maximum:
            raise ValueError("regular file bound")
        pieces = []; count = 0
        while count <= maximum:
            part = os.read(fd, min(65536, maximum + 1 - count))
            if not part:
                break
            pieces.append(part); count += len(part)
        after = os.fstat(fd)
        keys = ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_size", "st_mtime_ns", "st_ctime_ns")
        if count != before.st_size or any(getattr(before, key) != getattr(after, key) for key in keys):
            raise ValueError("file changed or exceeded bound")
        raw = b"".join(pieces)
        return raw, {"path": str(path), "size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                     "device": before.st_dev, "inode": before.st_ino, "uid": before.st_uid, "gid": before.st_gid,
                     "mode": stat.S_IMODE(before.st_mode)}
    finally:
        os.close(fd)


def write(path, raw, mode):
    parent = directory(path.parent)
    try: fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode, dir_fd=parent)
    finally: os.close(parent)
    try:
        view = memoryview(raw)
        while view:
            n = os.write(fd, view)
            if n <= 0:
                raise OSError("short artifact write")
            view = view[n:]
        os.fchmod(fd, mode)
        os.fsync(fd)
    finally:
        os.close(fd)


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def directory_identity(path):
    fd = directory(path)
    try:
        value = os.fstat(fd)
        return {"device": value.st_dev, "inode": value.st_ino, "uid": value.st_uid, "gid": value.st_gid,
                "mode": stat.S_IMODE(value.st_mode)}
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-root", type=Path, required=True,
                        help="retained pinned build with linux-collector, fixture, sha256-harness")
    parser.add_argument("--attempt-root", type=Path, required=True)
    args = parser.parse_args()
    if os.getuid() != 0 or os.geteuid() != 0:
        parser.error("this preparation requires the parent's already-authorized root terminal")
    root = args.attempt_root
    if (not root.is_absolute() or root.parent != WORK / "scratch" or root.parent.resolve(strict=True) != root.parent or
            re.fullmatch(r"stability-linux-sealed-root-tests-[0-9]{8}-[1-9][0-9]{0,5}", root.name) is None):
        parser.error("fresh dedicated scratch child with stability-linux-sealed-root-tests- prefix required")
    if args.build_root.resolve(strict=True) != args.build_root or not args.build_root.is_dir():
        parser.error("absolute canonical build root required")
    observed_cgroup = {path: Path(path).read_text().strip() for path in CGROUP}
    if observed_cgroup != CGROUP:
        raise ValueError("established parent cgroup differs")
    image_raw, image_identity = regular(WORK / "logs/image-native.json", 4 * 1024 * 1024)
    image_record = json.loads(image_raw, object_pairs_hook=strict_pairs, parse_constant=no_constant)
    image = image_record[0]["Id"]
    if type(image) is not str or len(image) != 71 or not image.startswith("sha256:") or any(c not in "0123456789abcdef" for c in image[7:]):
        raise ValueError("exact native image ID required")
    sources = {"linux-collector": args.build_root / "linux-collector", "fixture": args.build_root / "fixture",
               "sha256-harness": args.build_root / "sha256-harness", "root_inside.py": FIXTURES / "root_inside.py",
               "run_collector_tests.py": FIXTURES / "run_collector_tests.py",
               "supervisor.py": REPO / "scripts/application-tests/supervisor.py"}
    copied = {}
    for name, source in sources.items():
        raw, ident = regular(source, 4 * 1024 * 1024)
        if name in ("linux-collector", "fixture", "sha256-harness") and not (ident["mode"] & 0o111):
            raise ValueError("compiled executable has no execute permission")
        copied[name] = (raw, ident)
    wrapper_raw, wrapper_identity = regular(WORK / "setup/container-run.py", 1024 * 1024)
    helper_raw, helper_identity = regular(Path(__file__).resolve(), 1024 * 1024)
    os.umask(0o077)
    root.mkdir(mode=0o700)
    readonly = root / "inputs"; readonly.mkdir(mode=0o755)
    writable = root / "work"; writable.mkdir(mode=0o700)
    (writable / "tmp").mkdir(mode=0o700)
    nonce = uuid.uuid4().hex
    name = "mckernel-collector-" + nonce
    input_record = {"schema_version": 1, "kind": "linux-sealed-root-profile-inputs", "profile_nonce": nonce,
                    "image": image, "application_acceptance": False, "backend_enabled": False, "files": {},
                    "work_directory": directory_identity(writable), "inputs_directory": directory_identity(readonly)}
    for leaf, (raw, ident) in copied.items():
        mode = 0o755 if leaf in ("linux-collector", "fixture", "sha256-harness") else 0o644
        write(readonly / leaf, raw, mode)
        input_record["files"][leaf] = {"source": ident, "size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "mode": mode}
    write(readonly / "inputs.json", json_bytes(input_record), 0o644)
    write(root / "original-container-run.py", wrapper_raw, 0o600)
    write(root / "root-profile-helper.py", helper_raw, 0o600)
    create = [DOCKER, "create", "--pull=never", "--init", "--name", name, "--label", "mckernel.collector.owner=" + nonce,
              "--cpus=4", "--cpuset-cpus=2-5", "--cgroup-parent=/mckernel-dev", "--memory=12g", "--memory-swap=12g",
              "--pids-limit=512", "--cap-drop=ALL", "--security-opt=no-new-privileges", "--read-only", "--network=none",
              "--user=0:0", "--group-add=0", "--ulimit", "core=0", "--ulimit", "nofile=4096:4096",
              "--tmpfs", "/tmp:rw,nodev,nosuid,size=256m", "--mount", "type=bind,src=" + str(REPO) + ",dst=/workspace,readonly",
              "--mount", "type=bind,src=" + str(readonly) + ",dst=/inputs,readonly",
              "--mount", "type=bind,src=" + str(writable) + ",dst=/work",
              "--env", "TMPDIR=/work/tmp", "--env", "HOME=/tmp", "--env", "PYTHONDONTWRITEBYTECODE=1",
              "--workdir=/work", "--entrypoint=/usr/bin/python3", image, "/inputs/root_inside.py"]
    plan = {"schema_version": 1, "kind": "linux-sealed-root-container-command-plan", "status": "PREPARED_NOT_EXECUTED",
            "application_acceptance": False, "backend_enabled": False, "profile_nonce": nonce, "container_name": name,
            "root": str(root), "image_identity": image_identity, "builder_wrapper_identity": wrapper_identity,
            "helper_identity": helper_identity, "observed_parent_cgroup": observed_cgroup,
            "required_lock": "/run/lock/mckernel-development.lock", "lock_owner": "parent host orchestrator through verified cleanup",
            "scratch_preflight_commands": [["/usr/bin/mountpoint", "-q", str(WORK / "scratch")],
                                            ["/usr/bin/findmnt", "-n", "-o", "LABEL", "--target", str(WORK / "scratch")]],
            "required_scratch_label": "mckernel-scratch", "commands": {
                "image_inspect": [DOCKER, "image", "inspect", image], "create": create,
                "inspect_before_start": [DOCKER, "inspect", name], "start_attach": [DOCKER, "start", "--attach", name],
                "inspect_after_exit": [DOCKER, "inspect", name], "stop_owned": [DOCKER, "stop", "--time=20", name],
                "remove_owned": [DOCKER, "rm", "--force", name], "inspect_removed": [DOCKER, "inspect", name]},
            "command_limits_seconds": {"image_inspect": 15, "create": 30, "inspect_before_start": 15, "start_attach": 300,
                                       "inspect_after_exit": 15, "stop_owned": 30, "remove_owned": 30, "inspect_removed": 15},
            "required_inspect": {"image": image, "owner_label": nonce, "user": "0:0", "group_add": ["0"],
                                 "readonly_rootfs": True, "network_mode": "none", "privileged": False,
                                 "pid_mode": "", "devices": [], "device_requests": [],
                                 "cap_drop": ["ALL"], "no_new_privileges": True, "memory": 12884901888,
                                 "memory_swap": 12884901888, "nano_cpus": 4000000000, "cpuset_cpus": "2-5",
                                 "pids_limit": 512, "cgroup_parent": "/mckernel-dev", "init": True,
                                 "bind_mounts": [{"source": str(REPO), "destination": "/workspace", "rw": False},
                                                 {"source": str(readonly), "destination": "/inputs", "rw": False},
                                                 {"source": str(writable), "destination": "/work", "rw": True}]},
            "mandatory_host_gates": ["strict full inspect validation before start", "no extra binds/devices/privilege flags",
                                     "actual created container ID and owner label must match before every cleanup",
                                     "independent host deadline must stop actual owned container, not only docker client",
                                     "raw Docker command results and full stdout/stderr retained",
                                     "first failure preserved; cleanup failure never becomes PASS",
                                     "stopped container removal and absence verified before lock release",
                                     "full tree archive preserves original uid/gid/mode before optional scoped ownership handoff",
                                     "source and image identities rechecked before actual start and after collection"]}
    write(root / "plan.json", json_bytes(plan), 0o600)
    for current_directory in (readonly, writable, root, root.parent):
        fd = directory(current_directory)
        try: os.fsync(fd)
        finally: os.close(fd)
    for leaf, (_, ident) in copied.items():
        _, after = regular(sources[leaf], 4 * 1024 * 1024)
        if after != ident:
            raise ValueError("source drift after profile preparation; prepared tree remains NOT_EXECUTED")
    if regular(WORK / "setup/container-run.py", 1024 * 1024)[1] != wrapper_identity:
        raise ValueError("original builder wrapper changed during preparation")
    if regular(WORK / "logs/image-native.json", 4 * 1024 * 1024)[1] != image_identity:
        raise ValueError("native image record changed during preparation")
    print(root / "plan.json")


if __name__ == "__main__":
    main()
