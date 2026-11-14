import json
import hashlib
from pathlib import Path
import tarfile
import unittest

from layer_b_systemd_cgroup_observer import (
    CgroupObserverError, Mapping, parent_paths, resolve_systemd_mapping,
    verify_pid_membership,
)


MOUNT = (b"29 23 0:26 / /sys/fs/cgroup rw,nosuid,nodev,noexec,relatime - "
         b"tmpfs tmpfs rw,size=10240k\n"
         b"30 29 0:27 / /sys/fs/cgroup/systemd rw,relatime - cgroup cgroup "
         b"rw,name=systemd\n")
CG = b"0::/user.slice\n7:name=systemd:/user.slice/user-1000.slice\n"


class ObserverTests(unittest.TestCase):
    def test_root12_shape_and_membership(self):
        m = resolve_systemd_mapping(MOUNT, CG, "/user.slice/user-1000.slice")
        self.assertEqual(m.mountpoint, "/sys/fs/cgroup/systemd")
        self.assertEqual(m.filesystem_path, "/sys/fs/cgroup/systemd/user.slice/user-1000.slice")
        self.assertTrue(verify_pid_membership(b"7:name=systemd:/user.slice/user-1000.slice\n", m))
        self.assertFalse(verify_pid_membership(b"7:name=systemd:/user.slice/other\n", m))

    def test_mount_root_offset_and_retained_identity(self):
        mount = b"8 7 0:27 /user.slice /cg/systemd rw - cgroup cgroup rw,name=systemd\n"
        cg = b"7:name=systemd:/user.slice/user-1000.slice\n"
        m = resolve_systemd_mapping(mount, cg, "/user.slice/user-1000.slice")
        self.assertEqual(m.hierarchy_path, "/user.slice/user-1000.slice")
        self.assertEqual(m.filesystem_path, "/cg/systemd/user-1000.slice")
        self.assertEqual(json.loads(json.dumps(m.to_dict()))["original_control_group"], "/user.slice/user-1000.slice")
        self.assertTrue(verify_pid_membership(b"7:name=systemd:/user.slice/user-1000.slice\n", m))
        self.assertEqual(parent_paths(m)[-1], "/cg/systemd")

    def test_escaped_fields(self):
        raw = (b"8 7 0:27 / /sys/fs/cgroup/systemd\\040x rw - cgroup cgroup rw,name=systemd\n")
        m = resolve_systemd_mapping(raw, b"7:name=systemd:/x\n", "/x")
        self.assertEqual(m.mountpoint, "/sys/fs/cgroup/systemd x")

    def test_reject_ambiguous_missing_and_bad_control(self):
        two = MOUNT + b"31 29 0:28 / /other rw - cgroup cgroup rw,name=systemd\n"
        for mounts, cg, control in ((two, CG, "/user.slice"), (b"", CG, "/user.slice"),
                                    (MOUNT, b"7:name=systemd:/x/../y\n", "/x"),
                                    (MOUNT, CG, "/other")):
            with self.assertRaises(CgroupObserverError):
                resolve_systemd_mapping(mounts, cg, control)

    def test_malformed_and_traversal_pid_are_not_members(self):
        m = resolve_systemd_mapping(MOUNT, CG, "/user.slice/user-1000.slice")
        self.assertFalse(verify_pid_membership(b"7:name=systemd:/user.slice/../other\n", m))

    def test_empty_controlgroup_later_does_not_erase_identity(self):
        m = resolve_systemd_mapping(MOUNT, CG, "/user.slice/user-1000.slice")
        self.assertEqual(m.original_control_group, "/user.slice/user-1000.slice")
        # The later empty property is intentionally not a new mapping input.
        self.assertEqual(m.to_dict()["filesystem_path"], "/sys/fs/cgroup/systemd/user.slice/user-1000.slice")

    def test_root12_mountinfo_ignores_opaque_non_cgroup_roots(self):
        raw = (b"1 0 0:1 mnt:[4026531840] /run/ns rw - nsfs nsfs rw\n" + MOUNT)
        m = resolve_systemd_mapping(raw, CG, "/user.slice/user-1000.slice")
        self.assertEqual(m.mount_id, 30)

    def test_external_sibling_observer_and_control_pid_membership(self):
        observer = b"7:name=systemd:/user.slice/observer.service\n"
        target = "/user.slice/target.service"
        m = resolve_systemd_mapping(MOUNT, observer, target)
        self.assertEqual(m.filesystem_path, "/sys/fs/cgroup/systemd/user.slice/target.service")
        self.assertTrue(verify_pid_membership(
            b"7:name=systemd:/user.slice/target.service/pre-command\n", m))
        self.assertFalse(verify_pid_membership(observer, m))

    def test_first_two_colons_and_path_bytes_are_retained(self):
        rows = b"7:name=systemd,foo:/user.slice/a:b with spaces\n"
        self.assertEqual(resolve_systemd_mapping(MOUNT, rows, "/user.slice/a:b with spaces").hierarchy_path,
                         "/user.slice/a:b with spaces")

    def test_mount_root_requires_exact_component_containment(self):
        mount = b"8 7 0:27 /user.slice /cg/systemd rw - cgroup cgroup rw,name=systemd\n"
        with self.assertRaises(CgroupObserverError):
            resolve_systemd_mapping(mount, b"7:name=systemd:/user.slice-other/x\n", "/user.slice-other/x")

    def test_stacked_selected_mount_is_rejected(self):
        stacked = MOUNT + b"31 29 0:28 / /sys/fs/cgroup/systemd rw - tmpfs tmpfs rw\n"
        with self.assertRaises(CgroupObserverError):
            resolve_systemd_mapping(stacked, CG, "/user.slice/user-1000.slice")

    def test_reviewer_crlf_membership_is_not_normalized(self):
        m = resolve_systemd_mapping(MOUNT, CG, "/user.slice/user-1000.slice")
        self.assertFalse(verify_pid_membership(
            b"7:name=systemd:/user.slice/user-1000.slice\r\n", m))

    def test_reviewer_nested_mount_covers_parent(self):
        mounted = MOUNT + (b"31 30 0:28 / /sys/fs/cgroup/systemd/user.slice "
                           b"rw - tmpfs tmpfs rw\n")
        with self.assertRaises(CgroupObserverError):
            resolve_systemd_mapping(mounted, CG, "/user.slice/user-1000.slice")

    def test_reviewer_mount_root_equality(self):
        mount = b"8 7 0:27 /user.slice /cg/systemd rw - cgroup cgroup rw,name=systemd\n"
        m = resolve_systemd_mapping(mount, b"7:name=systemd:/user.slice\n", "/user.slice")
        self.assertEqual(m.filesystem_path, "/cg/systemd")
        self.assertEqual(parent_paths(m), ("/cg/systemd",))

    def test_all_representable_path_bytes_remain_distinct(self):
        plain = resolve_systemd_mapping(MOUNT, b"7:name=systemd:/x\n", "/x")
        for byte in range(1, 256):
            if byte in (10, 47):  # LF is the record separator; slash is a component separator.
                continue
            with self.subTest(byte=byte):
                path = b"/x" + bytes([byte])
                control = path.decode("utf-8", "surrogateescape")
                row = b"7:name=systemd:" + path + b"\n"
                m = resolve_systemd_mapping(MOUNT, row, control)
                self.assertEqual(m.hierarchy_path.encode("utf-8", "surrogateescape"), path)
                self.assertTrue(verify_pid_membership(row, m))
                self.assertFalse(verify_pid_membership(row, plain))

    def test_unicode_line_separators_are_not_record_delimiters(self):
        for delimiter in ("\r", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"):
            with self.subTest(delimiter=repr(delimiter)):
                control = "/x" + delimiter + ":tail "
                row = "7:name=systemd:" + control + "\n"
                for data in (row, row.encode("utf-8")):
                    m = resolve_systemd_mapping(MOUNT, data, control)
                    self.assertEqual(m.hierarchy_path, control)
                    self.assertTrue(verify_pid_membership(data, m))

    def test_mountinfo_path_control_bytes_are_preserved(self):
        for character in (b"\r", b"\v", b"\f", b"\x85", b"\xff", "\u2028".encode()):
            with self.subTest(character=character):
                point = b"/cg" + character
                mount = b"8 7 0:27 / " + point + b" rw - cgroup cgroup rw,name=systemd\n"
                m = resolve_systemd_mapping(mount, b"7:name=systemd:/x\n", "/x")
                self.assertEqual(m.filesystem_path.encode("utf-8", "surrogateescape"), point + b"/x")

    def test_target_and_each_parent_covering_mount_are_rejected(self):
        target = "/user.slice/user-1000.slice/target.service"
        m = resolve_systemd_mapping(MOUNT, CG, target)
        for point in parent_paths(m):
            with self.subTest(point=point):
                extra = ("31 30 0:28 / " + point + " rw - tmpfs tmpfs rw\n").encode()
                with self.assertRaises(CgroupObserverError):
                    resolve_systemd_mapping(MOUNT + extra, CG, target)

    def test_normal_ancestors_allowed_but_ancestor_overmount_rejected(self):
        mounts = (b"1 0 0:1 / / rw - ext4 /dev/root rw\n"
                  b"23 1 0:2 / /sys rw - sysfs sysfs rw\n" + MOUNT)
        target = "/user.slice/user-1000.slice"
        self.assertEqual(resolve_systemd_mapping(mounts, CG, target).mount_id, 30)
        for point, parent in (("/", 1), ("/sys", 1), ("/sys/fs/cgroup", 23)):
            with self.subTest(point=point):
                extra = (f"31 {parent} 0:28 / {point} rw - tmpfs tmpfs rw\n").encode()
                with self.assertRaises(CgroupObserverError):
                    resolve_systemd_mapping(mounts + extra, CG, target)

    def test_unrelated_mounts_and_component_prefixes_are_allowed(self):
        for point in ("/sys/fs/cgroup/systemd/user.slice-other", "/other",
                      "/sys/fs/cgroup/systemd/user.slice/user-1000.slice/descendant"):
            with self.subTest(point=point):
                extra = (f"31 30 0:28 / {point} rw - tmpfs tmpfs rw\n").encode()
                self.assertEqual(resolve_systemd_mapping(MOUNT + extra, CG,
                    "/user.slice/user-1000.slice").mount_id, 30)

    def test_nested_overmount_cannot_hide_behind_another_mount(self):
        mounts = MOUNT + (b"31 30 0:28 / /sys/fs/cgroup/systemd/user.slice rw - tmpfs tmpfs rw\n"
                          b"32 31 0:29 / /sys/fs/cgroup/systemd/user.slice/user-1000.slice "
                          b"rw - tmpfs tmpfs rw\n")
        with self.assertRaises(CgroupObserverError):
            resolve_systemd_mapping(mounts, CG, "/user.slice/user-1000.slice")

    def test_root_equality_with_slash_mount_and_offset_descendants(self):
        for root, point, control, expected in (
                ("/", "/", "/", ("/",)),
                ("/", "/cg", "/", ("/cg",)),
                ("/user.slice", "/", "/user.slice", ("/",)),
                ("/user.slice", "/cg", "/user.slice/a/b", ("/cg/a/b", "/cg/a", "/cg"))):
            with self.subTest(root=root, point=point, control=control):
                mount = f"8 7 0:27 {root} {point} rw - cgroup cgroup rw,name=systemd\n"
                m = resolve_systemd_mapping(mount, f"7:name=systemd:{control}\n", control)
                self.assertEqual(parent_paths(m), expected)
                self.assertEqual(m.filesystem_path, expected[0])

    def test_parent_transform_rejects_outside_root(self):
        for control in ("/other", "/user.slice-other", "/"):
            with self.subTest(control=control), self.assertRaises(CgroupObserverError):
                parent_paths(Mapping(8, "/user.slice", "/cg", control, control, "/cg"))

    def test_noncanonical_paths_reject_instead_of_aliasing(self):
        m = resolve_systemd_mapping(MOUNT, CG, "/user.slice/user-1000.slice")
        for path in ("/user.slice/user-1000.slice/", "/user.slice//user-1000.slice", "/user.slice/./user-1000.slice"):
            with self.subTest(path=path):
                self.assertFalse(verify_pid_membership(f"7:name=systemd:{path}\n", m))

    def test_duplicate_ids_cycles_and_same_point_parent_reject(self):
        for mounts in (
                MOUNT + b"30 29 0:28 / /other rw - tmpfs tmpfs rw\n",
                MOUNT.replace(b"29 23", b"29 30"),
                b"29 23 0:26 / /sys/fs/cgroup/systemd rw - tmpfs tmpfs rw\n" + MOUNT.splitlines(keepends=True)[1]):
            with self.subTest(mounts=mounts), self.assertRaises(CgroupObserverError):
                resolve_systemd_mapping(mounts, CG, "/user.slice/user-1000.slice")

    def test_retained_root12_mountinfo_and_external_observer(self):
        archive = Path(__file__).resolve().parents[2] / "docs/verification/evidence/stability-layer-b-native-owner-bootstrap-failure-20260928-12.tar.gz"
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(),
                         "82574a70f22300c92fc01b1a5caaab39c3540b85e780d4b6974d8007fa312056")
        with tarfile.open(archive, "r:gz") as retained:
            data = retained.extractfile("stability-layer-b-native-owner-bootstrap-20260928-12/logs/cgroup-preack-001.json").read()
        self.assertEqual(hashlib.sha256(data).hexdigest(),
                         "bf20da8219cca33130dea2c4f1b41981c562c4a06160c02765c1374c7c202247")
        original = json.loads(data)
        m = resolve_systemd_mapping(original["mountinfo"], original["self_cgroup"], original["control_group"])
        self.assertEqual(m.mount_id, 35)
        self.assertEqual(m.original_control_group, original["control_group"])
        self.assertEqual(m.filesystem_path, "/sys/fs/cgroup/systemd" + original["control_group"])
        self.assertFalse(verify_pid_membership(original["self_cgroup"], m))


if __name__ == "__main__":
    unittest.main()
