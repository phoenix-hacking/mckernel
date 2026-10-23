#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Offline owner fixtures: fake Docker, private temporary HOST files, no compiler/guest/root.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("private_compile_owner_fixture", HERE / "compile_image_owner.py")
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)
REQUEST = json.loads((HERE / "compile-request.PREPARED.json").read_text())
CID = "a" * 64
P12_CID = "b" * 64


def result(args, out="", err="", code=0):
    return subprocess.CompletedProcess(args, code, out, err)


class FakeDocker:
    client_retirement_unproven = False

    def __init__(self, bound=None, request=None, info=None, exit_code=0, uncertain=False, nonempty=False):
        self.calls = []
        self.exit_code = exit_code
        self.uncertain = uncertain
        self.nonempty = nonempty
        self.client_retirement_unproven = False
        self.removed = False
        self.info = copy.deepcopy(info or effective_info(bound, request))

    def call(self, args, timeout=120, check=True):
        self.calls.append(list(args))
        if args[:2] == ["image", "inspect"]:
            return result(args, json.dumps([{"Id": owner.COMPILE_PROFILE["image_id"], "Architecture": "amd64"}]))
        if args[0] == "inspect":
            return result(args, json.dumps([self.info]))
        if args[0] == "create":
            return result(args, CID + "\n")
        if args[0] == "start":
            self.info["State"] = {"Running": True, "Status": "running", "Pid": 123}
            return result(args)
        if args[0] in ("wait", "stop", "kill"):
            self.info["State"] = {"Running": False, "Status": "exited", "Pid": 0}
            return result(args, str(self.exit_code) + "\n")
        if args[0] == "logs":
            if self.uncertain:
                self.client_retirement_unproven = True
            return result(args, "fake compiler output\n")
        if args[0] == "rm":
            self.removed = True
            return result(args, CID + "\n")
        if args[0] == "ps":
            return result(args, CID + "\n" if self.nonempty else "")
        raise AssertionError("unexpected fake backend command: " + repr(args))


def effective_info(bound=None, request=None):
    config = {"Labels": {"mckernel.owner": owner.COMPILE_PROFILE["owner_nonce"],
                         "mckernel.operation": owner.COMPILE_PROFILE["operation"]},
              "Entrypoint": ["/usr/bin/python3"], "Cmd": owner._compile_command(bound, request) if request else [],
              "User": "1000:1000"}
    host = dict(owner.LIMITS, Privileged=False, ReadonlyRootfs=True, CapDrop=["ALL"], SecurityOpt=["no-new-privileges"],
                Init=True, PidMode="", IpcMode="private", Devices=[], DeviceRequests=[], Binds=None,
                CapAdd=None, CgroupParent="", Tmpfs={"/tmp": "rw,nodev,nosuid,size=256m"})
    mounts = [{"Source": str(src), "Destination": target, "RW": not ro, "Type": "bind"}
              for src, target, ro in owner._compile_mounts(bound)] if bound else []
    return {"Id": CID, "Name": "/" + owner.COMPILE_PROFILE["container_name"], "Image": owner.COMPILE_PROFILE["image_id"],
            "State": {"Running": False, "Status": "created", "Pid": 0}, "Config": config, "HostConfig": host, "Mounts": mounts}


class Fixtures(unittest.TestCase):
    def temp(self):
        context = tempfile.TemporaryDirectory(prefix="fixture-", dir=str(HERE))
        self.addCleanup(context.cleanup)
        return Path(context.name)

    def temporary_profile(self, root):
        profile = copy.deepcopy(owner.COMPILE_PROFILE)
        profile["namespace"] = str(root)
        profile["lease_path"] = str(root / "compile-lease.json")
        profile_patch = patch.object(owner, "COMPILE_PROFILE", profile)
        profile_patch.start()
        self.addCleanup(profile_patch.stop)
        return profile

    def lease_request(self, root):
        self.temporary_profile(root)
        return {"lease_path": str(root / "compile-lease.json"), "compile_operation": owner.COMPILE_PROFILE["operation"]}

    def test_real_prepared_domain_is_unreleased(self):
        owner._validate_compile_domain(REQUEST)
        self.assertIsNone(REQUEST["compile_only_release"])
        self.assertFalse(Path(REQUEST["lease_path"]).exists())

    def test_fixed_domain_profile_jobs_memory_and_outputs(self):
        for key, value in (("compile_operation", "guest"), ("jobs", 4), ("aggregate_memory_required", 12 * 2**30),
                           ("work_root", "/home/holden/mckernel-work/scratch/foreign"), ("lease_path", "/tmp/foreign")):
            changed = dict(REQUEST, **{key: value})
            with self.subTest(key=key), self.assertRaises(owner.OwnerError):
                owner._validate_compile_domain(changed)

    def test_null_release_rejects_before_docker_lease_or_output(self):
        fake = types.SimpleNamespace(call=lambda *args, **kwargs: self.fail("Docker must not be called"))
        with self.assertRaises(owner.OwnerError):
            owner.ImageOwner(REQUEST, docker=fake).run()
        self.assertFalse(Path(REQUEST["lease_path"]).exists())
        self.assertFalse(Path(REQUEST["attempt_root"]).exists())

    def test_real_script_entrypoint_null_admission_refuses_without_effects(self):
        before = {key: Path(REQUEST[key]).exists() for key in ("lease_path", "attempt_root", "output_root", "evidence_root")}
        child = subprocess.run([sys.executable, "-I", "-B", str(HERE / "compile_image_owner.py"),
                                "run", str(HERE / "compile-request.PREPARED.json")],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10,
                               env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "TZ": "UTC"},
                               universal_newlines=True)
        self.assertNotEqual(child.returncode, 0)
        self.assertEqual(child.stdout, "")
        self.assertIn("compile release reference missing or differs", child.stderr)
        self.assertEqual({key: Path(REQUEST[key]).exists() for key in before}, before)
        self.assertFalse(any(before.values()))

    def test_ordinary_file_cannot_supply_root_admission(self):
        root = self.temp()
        path = root / "fake-root.json"
        path.write_text("{}")
        ref = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        with self.assertRaises(owner.OwnerError):
            owner._read_root_document(ref, path, "fixture root admission")

    def test_compile_lease_is_exclusive(self):
        root = self.temp()
        request = self.lease_request(root)
        lease = owner.CompileLease(request)
        lease.acquire()
        original = lease.path.read_bytes()
        with self.assertRaises(FileExistsError):
            owner.CompileLease(request).acquire()
        self.assertEqual(lease.path.read_bytes(), original)
        self.assertEqual(lease.load_owned(), original)

    def test_compile_lease_changed_record_is_retained(self):
        request = self.lease_request(self.temp())
        lease = owner.CompileLease(request)
        lease.acquire()
        lease.path.write_text("{}")
        with self.assertRaises(owner.OwnerError):
            lease.load_owned()
        self.assertTrue(lease.path.exists())

    def test_only_exact_accepted_compile_lease_releases(self):
        root = self.temp()
        native_marker = root / "foreign-native-marker"
        native_marker.write_text("P12 remains owned")
        request = self.lease_request(root)
        lease = owner.CompileLease(request)
        lease.acquire()
        accepted = {"status": "ACCEPTED_COMPILE_ONLY_PHYSICAL_RETIREMENT", "operation": lease.record["operation"],
                    "request_core_sha256": lease.record["request_core_sha256"],
                    "lease_sha256": hashlib.sha256(lease.load_owned()).hexdigest()}
        with self.assertRaises(owner.OwnerError):
            lease.release_accepted(dict(accepted, request_core_sha256="wrong"))
        self.assertTrue(lease.path.exists())
        lease.release_accepted(accepted)
        self.assertFalse(lease.path.exists())
        self.assertEqual(native_marker.read_text(), "P12 remains owned")

    def test_foreign_container_has_no_lifecycle_calls(self):
        info = effective_info()
        info["Id"] = P12_CID
        info["Name"] = "/p12-native-fixture"
        client = FakeDocker(info=info)
        with self.assertRaises(owner.OwnerError):
            owner._cleanup_owned_compile(client, self.temp(), CID)
        self.assertEqual([call[0] for call in client.calls], ["inspect"])

    def test_exact_compiler_cleanup_does_not_touch_other_container(self):
        client = FakeDocker(info=effective_info())
        retired = owner._cleanup_owned_compile(client, self.temp(), CID)
        self.assertTrue(retired["retired"])
        self.assertTrue(retired["lease_retained_for_root_acceptance"])
        self.assertTrue(client.removed)
        self.assertEqual(len(retired["absence"]), 3)
        self.assertFalse(any(P12_CID in call for call in client.calls))
        self.assertEqual([call for call in client.calls if call[0] == "rm"], [["rm", CID]])

    def test_uncertain_docker_client_prevents_removal(self):
        client = FakeDocker(info=effective_info(), uncertain=True)
        with self.assertRaises(owner.OwnerError):
            owner._cleanup_owned_compile(client, self.temp(), CID)
        self.assertFalse(client.removed)

    def test_nonempty_absence_is_not_retirement(self):
        client = FakeDocker(info=effective_info(), nonempty=True)
        with self.assertRaises(owner.OwnerError):
            owner._cleanup_owned_compile(client, self.temp(), CID)
        self.assertTrue(client.removed)

    def test_live_admission_age_and_memory(self):
        facts = {"boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
                 "observed_boottime_ns": 10**12, "MemAvailable": 24 * 2**30}
        with patch.object(owner, "_boottime_ns", return_value=10**12), patch.object(owner, "_mem_available", return_value=24 * 2**30):
            self.assertEqual(owner._fresh_compile_resources(facts)["MemAvailable"], 24 * 2**30)
            for changes in ({"observed_boottime_ns": 0}, {"observed_boottime_ns": 10**12 + 1}, {"MemAvailable": 24 * 2**30 - 1}):
                with self.subTest(changes=changes), self.assertRaises(owner.OwnerError):
                    owner._fresh_compile_resources(dict(facts, **changes))
        with patch.object(owner, "_boottime_ns", return_value=10**12), patch.object(owner, "_mem_available", return_value=24 * 2**30 - 1):
            with self.assertRaises(owner.OwnerError):
                owner._fresh_compile_resources(facts)

    def test_p12_config_caps_unchanged_and_read_only(self):
        p12 = effective_info()
        p12.update(Id=P12_CID, Name="/p12-native-fixture", HostConfig=owner.COMPILE_PROFILE["reserved_native_profile"].copy(),
                   State={"Running": True}, Config={"Labels": {"p12.owner": "p12-nonce"}})
        facts = {"P12": {"id": P12_CID, "name": p12["Name"], "owner_label_key": "p12.owner", "owner_label_value": "p12-nonce",
                          "config_sha256": owner._canonical_hash(p12["Config"]), "host_config_sha256": owner._canonical_hash(p12["HostConfig"])}}
        client = FakeDocker(info=p12)
        self.assertTrue(owner._check_live_p12(client, facts)["running"])
        self.assertEqual(client.calls, [["inspect", P12_CID]])
        client.info["HostConfig"]["Memory"] = 4 * 2**30
        with self.assertRaises(owner.OwnerError):
            owner._check_live_p12(client, facts)
        self.assertTrue(all(call[0] == "inspect" for call in client.calls))

    def test_successful_docker_direct_join_checks_own_group(self):
        helper = owner._HOST_OWNER
        client = helper.Docker(self.temp() / "not-used.log")
        process = types.SimpleNamespace(pid=123, returncode=0, poll=lambda: 0)
        with patch.object(client, "_surviving_group_members", return_value=[456]):
            status = {}
            client._retire_client(process, status)
            self.assertTrue(client.client_retirement_unproven)
            self.assertEqual(status["client_survivors"], [456])

    def setup_full_run(self, exit_code=0, uncertain=False):
        root = self.temp()
        self.temporary_profile(root)
        work = root / "owner-work"
        evidence_parent = root / "owner-evidence"
        work.mkdir()
        evidence_parent.mkdir()
        evidence = work / "evidence"
        evidence.mkdir()
        (evidence / "receipt.json").write_text("{}")
        request = {"compile_only_release": {"fake": "fixture-only"}, "lease_path": str(root / "compile-lease.json"),
                   "candidate_sha": "c" * 40, "ihk_sha": "d" * 40, "source_derivative_sha256": "e" * 64,
                   "materialization_sha256": "f" * 64, "image_id": owner.COMPILE_PROFILE["image_id"],
                   "timeout": 60, "memory_backed_bytes": 0, "aggregate_memory_required": 4 * 2**30,
                   "disk_admission": {"host_root": str(root), "scratch_root": str(root)}}
        fake_host = types.SimpleNamespace(check_profile=owner._HOST_OWNER.check_profile,
            measure=lambda *args, **kwargs: {"memory_allocation_memory_backed_bytes": 0, "aggregate_memory_required": 4 * 2**30})
        bound = {"attempt": evidence_parent / "attempt", "owner_evidence": evidence_parent, "evidence": evidence,
                 "output": work / "output", "work": work, "host_owner": fake_host, "source": root / "source",
                 "manifest": root / "inputs.json", "gitlink_manifest": root / "gitlink.json", "gitlink_root": root / "libdwarf",
                 "toolchain": root / "toolchain.json", "driver": root / "driver.py", "provenance": root / "provenance.py",
                 "toolchain_schema": "mckernel.native-exact-mckernel-image-toolchain.v2", "mounts_by_target": {"/out": root / "cache", "/nightly": root / "nightly"},
                 "allocation_roots": [root]}
        client = FakeDocker(bound, request, exit_code=exit_code, uncertain=uncertain)
        obj = owner.ImageOwner(request, docker=client)
        obj.validate = lambda: bound
        for name, replacement in (("_validate_launch_admission", lambda r: {"facts": {}, "release": {}}),
                                  ("_revalidate_inputs", lambda *args: None),
                                  ("_fresh_compile_resources", lambda facts: {"MemAvailable": 24 * 2**30}),
                                  ("_check_live_p12", lambda *args: {"id": P12_CID, "running": True}),
                                  ("_validate_driver_result", lambda *args: None)):
            context = patch.object(owner, name, replacement)
            context.start()
            self.addCleanup(context.stop)
        return root, obj, client

    def test_full_fake_run_success_seals_receipt_and_retains_lease(self):
        root, obj, client = self.setup_full_run()
        answer = obj.run()
        self.assertEqual(answer["status"], "PASS")
        self.assertTrue(answer["retired"])
        self.assertTrue(client.removed)
        self.assertTrue((root / "compile-lease.json").exists())
        self.assertEqual(json.loads((root / "owner-evidence/owner-receipt.json").read_text()), answer)
        self.assertFalse(answer["native_guest_or_heavy_release"])

    def test_full_fake_compile_failure_preserved_after_own_cleanup(self):
        root, obj, client = self.setup_full_run(exit_code=1)
        answer = obj.run()
        self.assertEqual(answer["status"], "FAIL")
        self.assertEqual(answer["exit_code"], 1)
        self.assertIn("offline candidate14 image driver failed", answer["error"])
        self.assertTrue(answer["retired"])
        self.assertTrue((root / "compile-lease.json").exists())

    def test_full_fake_uncertain_client_retains_lease_and_container(self):
        root, obj, client = self.setup_full_run(uncertain=True)
        answer = obj.run()
        self.assertEqual(answer["status"], "FAIL")
        self.assertFalse(answer["retired"])
        self.assertFalse(client.removed)
        self.assertTrue((root / "compile-lease.json").exists())

    def test_release_controller_without_root_acceptance_has_no_docker_effect(self):
        fake = types.SimpleNamespace(call=lambda *args, **kwargs: self.fail("release must not contact Docker"))
        with self.assertRaises(FileNotFoundError):
            owner.release_accepted_compile_lease(REQUEST, fake)


if __name__ == "__main__":
    assert os.sched_getaffinity(0) == {0}, "source-only fixture grant is CPU0 only"
    unittest.main(verbosity=2)
