import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_rust_exact_mckernel_image_container_owner as owner
import native_rust_exact_mckernel_image_offline as driver


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def inventory(root):
    result = {}
    root = Path(root)
    for item in sorted(root.rglob("*")):
        relative = str(item.relative_to(root))
        st = item.lstat()
        row = {"mode": st.st_mode & 0o777,
               "type": "directory" if item.is_dir() else "file"}
        if item.is_file():
            row.update(size=st.st_size, sha256=digest(item))
        result[relative] = row
    return result


class FakeDocker:
    def __init__(self, evidence, image):
        self.evidence = Path(evidence)
        self.image = image
        self.name = None
        self.nonce = None
        self.calls = []
        self.info = None
        self.output = None
        self.driver_command = None

    def call(self, args, timeout=120, check=True):
        self.calls.append(list(args))
        if args[:2] == ["image", "inspect"]:
            return subprocess.CompletedProcess(args, 0, json.dumps([{"Id": self.image,
                "Architecture": "amd64"}]), "")
        if args[0] == "create":
            self.name = args[args.index("--name") + 1]
            label = args[args.index("--label") + 1]
            self.nonce = label.split("=", 1)[1]
            self.mounts = []
            for index, item in enumerate(args):
                if item == "--mount":
                    fields = dict(part.split("=", 1) for part in args[index + 1].split(",")
                                  if "=" in part)
                    self.mounts.append({"Type": "bind", "Source": fields["src"],
                                        "Destination": fields["dst"],
                                        "RW": "readonly" not in args[index + 1]})
            image_index = args.index(self.image)
            self.driver_command = args[image_index + 1:]
            work = next(row["Source"] for row in self.mounts if row["Destination"] == "/work")
            self.output = Path(work) / self.driver_command[self.driver_command.index("--output") + 1].rsplit("/", 1)[1]
            self.evidence = Path(work) / self.driver_command[self.driver_command.index("--evidence") + 1].rsplit("/", 1)[1]
            self.info = self._info("created", 0)
            return subprocess.CompletedProcess(args, 0, "fake-container-id\n", "")
        if args[0] == "inspect":
            return subprocess.CompletedProcess(args, 0, json.dumps([self.info]), "")
        if args[0] == "start":
            self.info = self._info("exited", 0)
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[0] == "wait":
            self.evidence.mkdir()
            required = {"mckernel.img": "image", "mckernel.img.map": "map",
                        "CMakeCache.txt": "cache", "compile_commands.json": "compile",
                        "mckernel_rust.o": "rust", "build.make": "make"}
            output_paths = {"mckernel.img": self.output / "build/kernel/mckernel.img",
                            "mckernel.img.map": self.output / "build/kernel/mckernel.img.map",
                            "CMakeCache.txt": self.output / "build/CMakeCache.txt",
                            "compile_commands.json": self.output / "build/compile_commands.json",
                            "mckernel_rust.o": self.output / "build/kernel/rust/mckernel_rust.o",
                            "build.make": self.output / "build/kernel/CMakeFiles/mckernel_rust_obj.dir/build.make"}
            evidence_artifacts = {}
            artifacts = {}
            for name, content in required.items():
                output_path = output_paths[name]; output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(content)
                evidence_path = self.evidence / "artifacts" / name
                evidence_path.parent.mkdir(parents=True, exist_ok=True)
                evidence_path.write_bytes(output_path.read_bytes())
                row = {"path": "/work/evidence/artifacts/" + name,
                       "size": evidence_path.stat().st_size, "mode": 0o644,
                       "sha256": digest(evidence_path)}
                evidence_artifacts[name] = row
                artifacts[name] = {"path": "/work/output/" + str(output_path.relative_to(self.output)),
                                   "size": output_path.stat().st_size,
                                   "mode": 0o644, "sha256": digest(output_path)}
            inventory_rows = {}
            for item in sorted(self.evidence.rglob("*")):
                if item.is_file():
                    inventory_rows[str(item.relative_to(self.evidence))] = {
                        "size": item.stat().st_size, "sha256": digest(item)}
            (self.evidence / "receipt.json").write_text(json.dumps({
                "status": "PASS", "candidate_sha": self.candidate_sha, "ihk_sha": self.ihk_sha,
                "source_manifest_sha256": self.source_manifest_sha256,
                "toolchain_manifest_sha256": self.toolchain_manifest_sha256,
                "inventory": inventory_rows, "evidence_artifacts": evidence_artifacts,
                "artifacts": artifacts,
            }), encoding="utf-8")
            return subprocess.CompletedProcess(args, 0, "0\n", "")
        if args[0] == "logs":
            return subprocess.CompletedProcess(args, 0, "fake container log\n", "")
        raise AssertionError("unexpected fake Docker command: " + repr(args))

    def _info(self, status, pid):
        return {"Name": "/" + self.name, "Image": self.image,
                "Config": {"Labels": {"mckernel.owner": self.nonce},
                           "Entrypoint": ["/usr/bin/python3"], "Cmd": self.driver_command or [],
                           "User": "1000:1000"}, "Mounts": getattr(self, "mounts", []),
                "State": {"Status": status, "Running": status == "running", "Pid": pid},
                "HostConfig": {
                    **owner.LIMITS, "Privileged": False, "ReadonlyRootfs": True,
                    "CapDrop": ["ALL"], "SecurityOpt": ["no-new-privileges"],
                    "Init": True, "IpcMode": "private", "Devices": [],
                    "DeviceRequests": [], "Binds": [], "Volumes": [], "CapAdd": [],
                    "PidMode": "", "UTSMode": "", "UsernsMode": "", "CgroupnsMode": "private",
                    "Tmpfs": {"/tmp": "rw,nodev,nosuid,size=256m"},
                }}


class OwnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "candidate"
        self.source.mkdir()
        (self.source / "ihk").mkdir()
        self.tools = self.root / "tools"
        self.tools.mkdir()
        for name in owner.REQUIRED_TOOLS:
            (self.tools / name).write_text(("rustc nightly fixture\n" if name == "rustc"
                                            else name + " fixture\n"))
        (self.tools / "git").write_text("#!/bin/sh\nexec /usr/bin/git \"$@\"\n")
        (self.tools / "git").chmod(0o755)
        (self.source / "source.rs").write_text("source\n")
        (self.source / "ihk" / "driver.rs").write_text("ihk\n")
        (self.source / "source.rs").chmod(0o644)
        (self.source / "ihk" / "driver.rs").chmod(0o644)
        for repo in (self.source / "ihk", self.source):
            subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "test"], check=True)
        subprocess.run(["git", "-C", str(self.source / "ihk"), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.source / "ihk"), "commit", "-qm", "ihk"], check=True)
        self.ihk = subprocess.check_output(["git", "-C", str(self.source / "ihk"), "rev-parse", "HEAD"], text=True).strip()
        subprocess.run(["git", "-C", str(self.source), "add", "source.rs"], check=True)
        subprocess.run(["git", "-C", str(self.source), "-c", "protocol.file.allow=always",
                        "submodule", "add", "-q", str(self.source / "ihk"), "ihk"], check=True)
        (self.source / ".gitmodules").chmod(0o644)
        subprocess.run(["git", "-C", str(self.source), "commit", "-qm", "source"], check=True)
        self.candidate = subprocess.check_output(["git", "-C", str(self.source), "rev-parse", "HEAD"], text=True).strip()
        self.backup = self.root / "backup"
        shutil.copytree(self.source, self.backup)
        self.kernel = self.root / "kernel"
        self.kernel.mkdir()
        (self.kernel / "Makefile").write_text("kernel\n")
        self.manifest = self.root / "manifest.json"
        self.toolchain = self.root / "toolchain.json"
        self.driver = Path(__file__).resolve().parents[1] / "native_rust_exact_mckernel_image_offline.py"
        self.provenance = Path(__file__).resolve().parents[1] / "native_rust_exact_build_offline.py"
        self.image = "sha256:" + "c" * 64
        self._write_manifests()
        self.work = self.root / "work"
        self.work.mkdir()
        self.work.chmod(0o700)
        self.output = self.work / "output"
        self.evidence = self.work / "evidence"
        self.owner_evidence = self.root / "owner-evidence"
        self.owner_evidence.mkdir()
        self.attempt = self.owner_evidence / "attempt"
        self.common = self.root / "common.lock"
        self.lease = self.root / "lease.json"
        self.old_driver_hash = owner.EXPECTED_DRIVER_SHA256
        self.old_common = owner.COMMON_EXCLUSION
        owner.EXPECTED_DRIVER_SHA256 = digest(self.driver)
        owner.COMMON_EXCLUSION = str(self.common)

    def test_current_exportset_namespace_retires_selfdigest(self):
        current = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-exportset-18.json"
        retired_selfdigest = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-selfdigest-13.json"
        retired = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-runtimeblob-12.json"
        self.assertTrue(current.endswith("exportset-18.json"))
        self.assertIn(
            "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-exportset-17.json",
            owner.RETIRED_COMMON_EXCLUSIONS,
        )
        self.assertIn(
            "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-exportset-16.json",
            owner.RETIRED_COMMON_EXCLUSIONS,
        )
        self.assertNotIn(current, owner.RETIRED_COMMON_EXCLUSIONS)
        self.assertIn(retired_selfdigest, owner.RETIRED_COMMON_EXCLUSIONS)
        self.assertIn(retired, owner.RETIRED_COMMON_EXCLUSIONS)
        self.assertIn(
            "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-lifecyclebinding-10.json",
            owner.RETIRED_COMMON_EXCLUSIONS,
        )
        self.assertIn(
            "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-objtoolbinding-11.json",
            owner.RETIRED_COMMON_EXCLUSIONS,
        )

    def tearDown(self):
        owner.EXPECTED_DRIVER_SHA256 = self.old_driver_hash
        owner.COMMON_EXCLUSION = self.old_common
        self.tmp.cleanup()

    def test_transport_lease_and_signal_primitives_are_reused(self):
        """The image owner must not fork a second Docker/lease implementation."""
        self.assertIs(owner.Docker, owner._HOST_OWNER.Docker)
        self.assertIs(owner.Lease, owner._HOST_OWNER.Lease)
        self.assertIs(owner.Signals, owner._HOST_OWNER.CliSignals)
        self.assertIs(owner._inspect, owner._HOST_OWNER.inspect)
        self.assertIs(owner._retire, owner._HOST_OWNER.retire)

    def test_exact_exclusion_work_root_and_authenticated_import_bindings(self):
        request = self.request()
        self.assertEqual(request["common_exclusion_path"], owner.COMMON_EXCLUSION)
        self.assertEqual(Path(request["work_root"]).stat().st_mode & 0o777, 0o700)
        request["host_owner_sha256"] = "0" * 64
        with self.assertRaisesRegex(owner.OwnerError, "host owner"):
            owner.ImageOwner(request).validate()

    def test_backup_identity_and_inventory_mutations_fail_closed(self):
        request = self.request()
        request["backup_identity"] = dict(request["backup_identity"], inode=0)
        with self.assertRaisesRegex(owner.OwnerError, "source backup identity"):
            owner.ImageOwner(request).validate()
        request = self.request()
        request["backup_inventory"] = dict(request["backup_inventory"])
        request["backup_inventory"]["forged"] = {
            "mode": 0o644, "type": "file", "size": 1, "sha256": "0" * 64}
        with self.assertRaisesRegex(owner.OwnerError, "source backup inventory"):
            owner.ImageOwner(request).validate()

    def test_work_root_and_receipt_overwrite_are_rejected(self):
        request = self.request()
        request["work_root"] = str(self.root)
        with self.assertRaisesRegex(owner.OwnerError, "work/evidence roots overlap|work root"):
            owner.ImageOwner(request).validate()
        request = self.request()
        (self.owner_evidence / owner.OWNER_RECEIPT_NAME).write_text("existing\n")
        with self.assertRaisesRegex(owner.OwnerError, "owner evidence root must be fresh|receipt must be fresh"):
            owner.ImageOwner(request).validate()

    def _write_manifests(self):
        self.manifest.write_text(json.dumps({
            "schema": "mckernel.native-exact-mckernel-image-inputs.v1",
            "candidate_sha": self.candidate, "ihk_sha": self.ihk,
            "gitlinks": {"ihk": self.ihk}, "repository_files": {
                "source.rs": digest(self.source / "source.rs"),
                ".gitmodules": digest(self.source / ".gitmodules"),
                "ihk/driver.rs": digest(self.source / "ihk/driver.rs")},
        }, sort_keys=True))
        self.toolchain.write_text(json.dumps({
            "schema": "mckernel.native-exact-mckernel-image-toolchain.v1",
            "tools": {name: {"path": str(self.tools / name),
                              "sha256": digest(self.tools / name),
                              "version": ("rustc nightly fixture" if name == "rustc"
                                           else name + " fixture")}
                       for name in owner.REQUIRED_TOOLS},
            "kernel_dir": str(self.kernel),
            "kernel_inventory": inventory(self.kernel),
            "toolchain_roots": [{"path": str(self.tools), "inventory": inventory(self.tools)}],
            "path_dirs": [str(self.tools)],
            "linux_probe": {"arch": "x86_64", "release": "fixture",
                            "kernel_dir": str(self.kernel)},
            "environment": {},
        }, sort_keys=True))

    def request(self):
        source_id = owner._identity(self.source)
        return {
            "schema": owner.REQUEST_SCHEMA, "candidate_sha": self.candidate,
            "ihk_sha": self.ihk, "image_id": self.image, "jobs": 2, "timeout": 30,
            "source_root": str(self.source), "source_identity": source_id,
            "backup_root": str(self.backup), "backup_identity": owner._identity(self.backup),
            "backup_inventory": inventory(self.backup),
            "disk_identity": source_id, "source_manifest": str(self.manifest),
            "source_manifest_sha256": digest(self.manifest),
            "toolchain_manifest": str(self.toolchain),
            "toolchain_manifest_sha256": digest(self.toolchain),
            "driver_path": str(self.driver), "driver_sha256": digest(self.driver),
            "provenance_path": str(self.provenance), "provenance_sha256": digest(self.provenance),
            "host_owner_path": str(owner._HOST_OWNER_PATH),
            "host_owner_sha256": digest(owner._HOST_OWNER_PATH),
            "toolchain_roots": [{"path": str(self.tools), "inventory": inventory(self.tools)}],
            "path_dirs": [str(self.tools)], "nightly": {"rustc_version": "rustc nightly fixture"},
            "mounts": {"source": "/src", "manifest": "/inputs.json", "toolchain": "/toolchain.json",
                        "driver": "/driver.py", "provenance": "/native_rust_exact_build_offline.py",
                        "work": "/work"},
            "common_exclusion_path": str(self.common), "lease_path": str(self.lease),
            "owner_evidence_root": str(self.owner_evidence), "attempt_root": str(self.attempt),
            "work_root": str(self.work),
            "output_root": str(self.output), "evidence_root": str(self.evidence),
            "launcher_aggregate_memory_gib": owner.LAUNCHER_AGGREGATE_GIB,
            "memory_backed_bytes": 0, "aggregate_memory_required": owner.LIMITS["Memory"],
            "memory_allocation_roots": [str(self.source)],
            "disk_admission": {"host_root": str(self.root), "scratch_root": str(self.root),
                               "host_device": self.root.stat().st_dev,
                               "scratch_device": self.root.stat().st_dev,
                               "host_free_floor": 16 * 2**30,
                               "scratch_free_floor": 12 * 2**30},
        }

    def test_fake_container_passes_pinned_profile_and_driver_binding(self):
        request = self.request()
        fake = FakeDocker(self.evidence, self.image)
        fake.candidate_sha = self.candidate
        fake.ihk_sha = self.ihk
        fake.source_manifest_sha256 = digest(self.manifest)
        fake.toolchain_manifest_sha256 = digest(self.toolchain)
        result = owner.ImageOwner(request, docker=fake).run()
        self.assertEqual(result["status"], "PASS", result)
        self.assertTrue(result["retired"])
        self.assertTrue(self.lease.exists() is False)
        self.assertTrue(self.common.exists())
        create = next(row for row in fake.calls if row[0] == "create")
        self.assertIn("--network=none", create)
        self.assertIn("--read-only", create)
        self.assertIn("--cap-drop=ALL", create)
        self.assertIn("--security-opt=no-new-privileges", create)
        self.assertIn("--tmpfs", create)
        self.assertIn(str(self.kernel), " ".join(create))
        self.assertFalse(any("/usr/bin/python3" in item for item in
                             fake.calls[-1] if isinstance(item, str)))
        command = next(row for row in fake.calls if row[0] == "create")
        self.assertIn("/driver.py", command)
        self.assertNotIn("/usr/bin/python3", command[command.index(self.image) + 1:])
        self.assertTrue(any("dst=/native_rust_exact_build_offline.py" in item for item in command))
        self.assertTrue(any("dst=/work" in item for item in command))
        self.assertTrue((self.evidence / "receipt.json").is_file())
        self.assertTrue((self.owner_evidence / owner.OWNER_RECEIPT_NAME).is_file())
        self.assertNotEqual((self.evidence / "receipt.json").read_text(),
                            (self.owner_evidence / owner.OWNER_RECEIPT_NAME).read_text())

    def test_driver_hash_and_common_exclusion_fail_closed(self):
        request = self.request()
        request["driver_sha256"] = "0" * 64
        with self.assertRaisesRegex(owner.OwnerError, "driver release hash"):
            owner.ImageOwner(request, docker=FakeDocker(self.evidence, self.image)).validate()
        request = self.request()
        self.common.write_text("held\n")
        with self.assertRaisesRegex(owner.OwnerError, "common exclusion"):
            owner.ImageOwner(request, docker=FakeDocker(self.evidence, self.image)).run()

    def test_v2_owner_admission_and_offline_container_fixture(self):
        """One v2 closure is admitted by the owner and consumed as /out,/nightly.

        The raw /out/source link is deliberately kept in the host closure;
        the offline driver receives no host path in its JSON document.
        """
        out, nightly = self.root / "v2-out", self.root / "v2-nightly"
        (out / "build").mkdir(parents=True)
        shutil.copytree(self.kernel, out / "build", dirs_exist_ok=True)
        release = driver.REPRO_ENV["EXPECTED_KERNEL_RELEASE"]
        for relative, text in {
            ".config": "CONFIG_X86_64=y\nCONFIG_64BIT=y\n",
            "include/config/kernel.release": release + "\n",
            "include/generated/autoconf.h": "#define CONFIG_X86_64 1\n#define CONFIG_64BIT 1\n",
            "include/generated/utsrelease.h": '#define UTS_RELEASE "' + release + '"\n',
        }.items():
            path = out / "build" / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        (out / "source").mkdir()
        (out / "build" / "source").symlink_to("/out/source")
        (nightly / "bin").mkdir(parents=True)
        shutil.copy2(self.tools / "rustc", nightly / "bin/rustc")
        (nightly / "bin/rustc").chmod(0o755)
        # This unbound executable is retained in the mounted closure so the
        # v2 PATH ordering check has a real image-tool shadow to reject.
        shutil.copy2(self.tools / "cc", nightly / "bin/cc")
        (nightly / "bin/cc").chmod(0o755)
        image_tools = {}
        for name in owner.REQUIRED_TOOLS:
            if name == "rustc":
                continue
            lookup = Path("/usr/bin") / name
            self.assertTrue(lookup.exists(), name)
            target = lookup.resolve(strict=True)
            image_tools[name] = {"path": str(lookup), "target": str(target), "sha256": digest(target),
                                 "version": subprocess.check_output([str(target), "--version"], text=True).strip(),
                                 "rpm_nevra": name + "-0:fixture-1.el10.x86_64",
                                 "executable_version": subprocess.check_output([str(target), "--version"], text=True).strip()}
        image_tools["cmake"]["rpm_nevra"] = owner.PINNED_CMAKE_RPM
        mounted = {"rustc": {"path": "/nightly/bin/rustc", "sha256": digest(nightly / "bin/rustc"),
                              "version": "rustc nightly fixture"}}
        closure_out = owner._closure_inventory(out, out, Path("/out"))
        closure_nightly = owner._closure_inventory(nightly, nightly, Path("/nightly"))
        receipt = self.root / "image-receipt.json"
        # Match the producer's durable receipt rather than a hand-written
        # admission stub: downstream validation must consume both observations
        # and both container terminal inspections.
        evidence = {}
        for name in owner._PREPARATION_EVIDENCE:
            payload = (b"same tool observation\n" if name in
                       ("tool-observation.json", "offline-tool-observation.json")
                       else name.encode() + b"\n")
            path = self.root / name
            path.write_bytes(payload)
            evidence[name] = {"size": len(payload), "sha256": digest(path)}
        packages = {descriptor["rpm_nevra"].split("-0:", 1)[0]: descriptor["rpm_nevra"]
                    for descriptor in image_tools.values()}
        packages.update(cmake=owner.PINNED_CMAKE_RPM, rust=owner.PINNED_RUST_RPM)
        receipt_tools = json.loads(json.dumps(image_tools))
        # Producer receipts retain observations for base-provided tools too;
        # rpm is intentionally not an owner-consumed image tool here.
        receipt_tools["rpm"] = {"rpm_nevra": "rpm-0:fixture-1.el10.x86_64",
                                 "executable_version": "rpm fixture"}
        lock_sha = "fd3d7a13e1b8b5d103f7e59d22f17c9e4b99cc937637decaa66749acfae6c802"
        receipt.write_text(json.dumps({"status": "PASS", "image_id": self.image,
                                       "candidate_sha": self.candidate, "retired": True,
                                       "base_image": owner.PREPARER_BASE_IMAGE,
                                       "toolchain_lock_sha256": lock_sha,
                                       "source_free": True, "runtime_network": "none",
                                       "packages": packages, "tools": receipt_tools,
                                       "evidence": evidence}, sort_keys=True))
        self.toolchain.write_text(json.dumps({
            "schema": driver.TOOLCHAIN_SCHEMA_V2,
            "kernel_binding": {"container_root": "/out", "container_kernel_dir": "/out/build",
                               "closure_inventory": closure_out},
            "kernel_inventory": driver._tree_inventory(out / "build", visible_roots={"/out": out, "/nightly": nightly},
                                                         allow_visible_root=True),
            "image_tools": image_tools, "mounted_tools": mounted,
            "toolchain_roots": [{"path": "/out", "inventory": closure_out},
                                {"path": "/nightly", "inventory": closure_nightly}],
            "path_dirs": ["/usr/bin", "/nightly/bin"],
            "linux_probe": {"arch": "x86_64", "release": release, "kernel_dir": "/out/build"},
            "environment": {}}, sort_keys=True))
        request = self.request()
        request.update(toolchain_manifest_sha256=digest(self.toolchain), image_receipt=str(receipt),
                       image_receipt_sha256=digest(receipt),
                       toolchain_lock_sha256=lock_sha,
                       toolchain_roots=[{"host_path": str(out), "container_path": "/out", "inventory": closure_out},
                                        {"host_path": str(nightly), "container_path": "/nightly", "inventory": closure_nightly}],
                       path_dirs=json.loads(self.toolchain.read_text())["path_dirs"],
                       host_git={"path": str(self.tools / "git"), "sha256": digest(self.tools / "git")})
        bound = owner.ImageOwner(request).validate()
        self.assertEqual(bound["kernel_root"], out)
        mismatched_host_git = dict(request, host_git={"path": str(self.tools / "git"),
                                                      "sha256": image_tools["git"]["sha256"]})
        with self.assertRaisesRegex(owner.OwnerError, "v2 host Git hash drift"):
            owner.ImageOwner(mismatched_host_git).validate()
        tools = driver._validate_toolchain(self.toolchain,
                                           container_roots={"/out": out, "/nightly": nightly})
        self.assertEqual(tools["kernel_dir"], str(out / "build"))
        self.assertEqual(str((out / "build" / "source").readlink()), "/out/source")
        fake = FakeDocker(self.evidence, self.image)
        fake.candidate_sha = self.candidate
        fake.ihk_sha = self.ihk
        fake.source_manifest_sha256 = digest(self.manifest)
        fake.toolchain_manifest_sha256 = digest(self.toolchain)
        result = owner.ImageOwner(request, docker=fake).run()
        self.assertEqual(result["status"], "PASS", result)
        destinations = {row["Destination"] for row in fake.mounts}
        self.assertIn("/out", destinations)
        self.assertIn("/nightly", destinations)
        self.assertNotIn(str(nightly), destinations)

    def test_v2_rejects_receipt_network_boolean_and_host_schema_leak(self):
        # The integrated fixture above establishes the positive shape; these
        # are the two reviewer reproductions that previously slipped through.
        self.test_v2_owner_admission_and_offline_container_fixture()
        data = json.loads(self.toolchain.read_text())
        leaked = json.loads(json.dumps(data))
        leaked["kernel_binding"]["host_root"] = str(self.root)
        with self.assertRaisesRegex(owner.OwnerError, "kernel binding schema"):
            owner._validate_kernel_binding(leaked, self.root / "v2-out")
        receipt = self.root / "image-receipt.json"
        receipt_data = json.loads(receipt.read_text())
        receipt_data["runtime_network"] = False
        receipt.write_text(json.dumps(receipt_data, sort_keys=True))
        request = self.request()
        request.update(image_receipt=str(receipt), image_receipt_sha256=digest(receipt),
                       host_git={"path": str(self.tools / "git"), "sha256": digest(self.tools / "git")},
                       toolchain_lock_sha256=receipt_data["toolchain_lock_sha256"])
        with self.assertRaisesRegex(owner.OwnerError, "source-free and offline"):
            owner._validate_v2_image_tools(request, data)
        valid_receipt = json.loads(json.dumps(receipt_data))
        valid_receipt["runtime_network"] = "none"
        receipt.write_text(json.dumps(valid_receipt, sort_keys=True))
        request.pop("toolchain_lock_sha256")
        request["image_receipt_sha256"] = digest(receipt)
        with self.assertRaisesRegex(owner.OwnerError, "toolchain lock differs"):
            owner._validate_v2_image_tools(request, data)
        request["toolchain_lock_sha256"] = "0" * 64
        with self.assertRaisesRegex(owner.OwnerError, "toolchain lock differs"):
            owner._validate_v2_image_tools(request, data)
        request["toolchain_lock_sha256"] = valid_receipt["toolchain_lock_sha256"]
        # Each of these mutations targets a producer assertion that a minimal
        # handcrafted receipt used to omit.  Rebuild the receipt bytes and
        # hash for each case so the check reaches receipt admission itself.
        for field, value, message in (
                ("candidate_sha", "0" * 40, "identity differs"),
                ("retired", False, "identity differs"),
                ("base_image", "rockylinux/rockylinux:10.2", "identity differs"),
                ("packages", {}, "packages missing"),
                ("evidence", {}, "evidence missing")):
            mutated = json.loads(json.dumps(receipt_data))
            mutated["runtime_network"] = "none"
            mutated[field] = value
            receipt.write_text(json.dumps(mutated, sort_keys=True))
            request.update(image_receipt_sha256=digest(receipt))
            with self.assertRaisesRegex(owner.OwnerError, message):
                owner._validate_v2_image_tools(request, data)
        consumed_package_mismatch = json.loads(json.dumps(receipt_data))
        consumed_package_mismatch["runtime_network"] = "none"
        consumed_package_mismatch["packages"] = dict(consumed_package_mismatch["packages"])
        consumed_package_mismatch["packages"]["git"] = "git-0:wrong-1.el10.x86_64"
        receipt.write_text(json.dumps(consumed_package_mismatch, sort_keys=True))
        request.update(image_receipt_sha256=digest(receipt))
        with self.assertRaisesRegex(owner.OwnerError, "package/tool identity differs"):
            owner._validate_v2_image_tools(request, data)
        bad_target = json.loads(json.dumps(data))
        bad_target["image_tools"]["ld"]["target"] = bad_target["image_tools"]["cc"]["target"]
        self.toolchain.write_text(json.dumps(bad_target, sort_keys=True))
        with self.assertRaisesRegex(driver.ImageBuildError, "image tool ld lookup target differs"):
            driver._validate_toolchain(self.toolchain,
                                       container_roots={"/out": self.root / "v2-out",
                                                        "/nightly": self.root / "v2-nightly"})
        shadow = json.loads(json.dumps(data))
        shadow["path_dirs"] = ["/nightly/bin", "/usr/bin"]
        self.toolchain.write_text(json.dumps(shadow, sort_keys=True))
        with self.assertRaisesRegex(driver.ImageBuildError, "PATH tool differs from bound tool: cc"):
            driver._validate_toolchain(self.toolchain,
                                       container_roots={"/out": self.root / "v2-out",
                                                        "/nightly": self.root / "v2-nightly"})

    def test_consumed_exclusions_are_rejected(self):
        request = self.request()
        saved = owner.COMMON_EXCLUSION
        try:
            owner.COMMON_EXCLUSION = next(iter(owner.RETIRED_COMMON_EXCLUSIONS))
            request["common_exclusion_path"] = owner.COMMON_EXCLUSION
            with self.assertRaisesRegex(owner.OwnerError, "common exclusion"):
                owner.ImageOwner(request).validate()
        finally:
            owner.COMMON_EXCLUSION = saved

    def test_identity_and_manifest_mounts_are_required(self):
        request = self.request()
        request["disk_identity"] = dict(request["disk_identity"], inode=0)
        with self.assertRaisesRegex(owner.OwnerError, "disk candidate identity changed"):
            owner.ImageOwner(request, docker=FakeDocker(self.evidence, self.image)).validate()
        request = self.request()
        request["mounts"]["manifest"] = "/wrong.json"
        with self.assertRaisesRegex(owner.OwnerError, "mount manifest"):
            owner.ImageOwner(request, docker=FakeDocker(self.evidence, self.image)).validate()

    def test_fresh_driver_children_and_resource_admission_fail_closed(self):
        request = self.request()
        self.output.mkdir()
        with self.assertRaisesRegex(owner.OwnerError, "output root must be fresh"):
            owner.ImageOwner(request, docker=FakeDocker(self.evidence, self.image)).validate()
        self.output.rmdir()
        request = self.request()
        request["memory_backed_bytes"] = 1
        with self.assertRaisesRegex(owner.OwnerError, "memory-backed"):
            owner.ImageOwner(request, docker=FakeDocker(self.evidence, self.image)).validate()

    def test_authenticated_source_and_provenance_mutations_fail(self):
        request = self.request()
        (self.source / "source.rs").write_text("mutated\n")
        with self.assertRaisesRegex(owner.OwnerError, "authenticated source|inventory"):
            owner.ImageOwner(request, docker=FakeDocker(self.evidence, self.image)).validate()
        (self.source / "source.rs").write_text("source\n")
        request = self.request()
        request["provenance_sha256"] = "0" * 64
        with self.assertRaisesRegex(owner.OwnerError, "provenance"):
            owner.ImageOwner(request, docker=FakeDocker(self.evidence, self.image)).validate()

    def test_fresh_interpreter_rejects_changed_adjacent_dependency(self):
        package = self.root / "fresh-import"
        package.mkdir()
        owner_copy = package / "native_rust_exact_mckernel_image_container_owner.py"
        host_copy = package / "native_rust_exact_build_container_owner.py"
        provenance_copy = package / "native_rust_exact_build_offline.py"
        owner_copy.write_bytes(Path(owner.__file__).read_bytes())
        host_copy.write_bytes(owner._HOST_OWNER_PATH.read_bytes())
        provenance_copy.write_bytes(self.provenance.read_bytes())
        provenance_copy.write_bytes(provenance_copy.read_bytes() + b"\n# mutation\n")
        result = subprocess.run([sys.executable, "-c", "import native_rust_exact_mckernel_image_container_owner"],
                                cwd=package, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("hash mismatch", result.stderr)

    def test_leaf_and_ancestor_symlinks_are_rejected(self):
        request = self.request()
        parent = self.root / "linked-parent"
        parent.symlink_to(self.work, target_is_directory=True)
        request["output_root"] = str(parent / "output")
        with self.assertRaisesRegex(owner.OwnerError, "output root"):
            owner.ImageOwner(request).validate()
        request = self.request()
        linked_evidence = self.root / "evidence-link"
        linked_evidence.symlink_to(self.work, target_is_directory=True)
        request["evidence_root"] = str(linked_evidence)
        with self.assertRaisesRegex(owner.OwnerError, "evidence root"):
            owner.ImageOwner(request).validate()
        request = self.request()
        leaf = self.work / "output-link"
        leaf.symlink_to(self.root, target_is_directory=True)
        request["output_root"] = str(leaf)
        with self.assertRaisesRegex(owner.OwnerError, "output root"):
            owner.ImageOwner(request).validate()

    def test_fifo_artifact_is_rejected_without_opening(self):
        request = self.request()
        fake = FakeDocker(self.evidence, self.image)
        fake.candidate_sha = self.candidate; fake.ihk_sha = self.ihk
        fake.source_manifest_sha256 = digest(self.manifest)
        fake.toolchain_manifest_sha256 = digest(self.toolchain)
        original = fake.call
        def mutate(args, **kwargs):
            result = original(args, **kwargs)
            if args[0] == "wait":
                artifact = self.evidence / "artifacts/mckernel.img"
                artifact.unlink()
                os.mkfifo(artifact)
            return result
        fake.call = mutate
        result = owner.ImageOwner(request, docker=fake).run()
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any(token in result["error"] for token in ("special file", "regular file")))

    def test_effective_profile_mismatch_is_terminal_failure(self):
        request = self.request()
        fake = FakeDocker(self.evidence, self.image)
        fake.candidate_sha = self.candidate; fake.ihk_sha = self.ihk
        fake.source_manifest_sha256 = digest(self.manifest)
        fake.toolchain_manifest_sha256 = digest(self.toolchain)
        original = fake._info
        def bad_info(status, pid):
            info = original(status, pid)
            info["HostConfig"]["ReadonlyRootfs"] = False
            return info
        fake._info = bad_info
        result = owner.ImageOwner(request, docker=fake).run()
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("effective isolation", result["error"])
        self.assertTrue((self.owner_evidence / owner.OWNER_RECEIPT_NAME).is_file())

    def test_driver_inventory_mutation_is_rejected(self):
        request = self.request()
        fake = FakeDocker(self.evidence, self.image)
        fake.candidate_sha = self.candidate; fake.ihk_sha = self.ihk
        fake.source_manifest_sha256 = digest(self.manifest)
        fake.toolchain_manifest_sha256 = digest(self.toolchain)
        original = fake.call
        def mutate(args, **kwargs):
            result = original(args, **kwargs)
            if args[0] == "wait":
                (fake.evidence / "artifacts/mckernel.img").write_text("changed")
            return result
        fake.call = mutate
        result = owner.ImageOwner(request, docker=fake).run()
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("inventory", result["error"])

    def test_postflight_source_mutation_is_rejected(self):
        request = self.request()
        fake = FakeDocker(self.evidence, self.image)
        fake.candidate_sha = self.candidate; fake.ihk_sha = self.ihk
        fake.source_manifest_sha256 = digest(self.manifest)
        fake.toolchain_manifest_sha256 = digest(self.toolchain)
        original = fake.call
        def mutate(args, **kwargs):
            result = original(args, **kwargs)
            if args[0] == "wait":
                (self.source / "source.rs").write_text("postflight mutation\n")
            return result
        fake.call = mutate
        result = owner.ImageOwner(request, docker=fake).run()
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any(token in result["error"] for token in ("changed", "inventory", "source")))

    def test_final_signal_latch_forces_diagnostic_failure(self):
        request = self.request()
        fake = FakeDocker(self.evidence, self.image)
        fake.candidate_sha = self.candidate; fake.ihk_sha = self.ihk
        fake.source_manifest_sha256 = digest(self.manifest)
        fake.toolchain_manifest_sha256 = digest(self.toolchain)
        signals = type("Latched", (), {"requested": 15, "cleaning": False})()
        result = owner.ImageOwner(request, docker=fake, signals=signals).run()
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["interrupted_signal"], 15)

    def test_docker_logs_nonzero_status_is_failure(self):
        class FailingLogs(FakeDocker):
            def call(self, args, **kwargs):
                if args[0] == "logs":
                    return subprocess.CompletedProcess(args, 17, "", "logs failed")
                return super().call(args, **kwargs)

        request = self.request()
        fake = FailingLogs(self.evidence, self.image)
        fake.candidate_sha = self.candidate; fake.ihk_sha = self.ihk
        fake.source_manifest_sha256 = digest(self.manifest)
        fake.toolchain_manifest_sha256 = digest(self.toolchain)
        result = owner.ImageOwner(request, docker=fake).run()
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("logs", result["capture_error"])


if __name__ == "__main__":
    unittest.main()
