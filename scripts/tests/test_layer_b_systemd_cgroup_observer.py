import json
import unittest

from layer_b_systemd_cgroup_observer import (
    CgroupObserverError, parent_paths, resolve_systemd_mapping,
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


if __name__ == "__main__":
    unittest.main()
