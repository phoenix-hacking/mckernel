import unittest

from layer_b_systemd_cgroup_collector import (
    CgroupObserverError, collect_recursive_observation,
)
from layer_b_systemd_cgroup_observer import resolve_systemd_mapping, verify_pid_membership


MOUNT = (b"29 23 0:26 / /sys/fs/cgroup rw - tmpfs tmpfs rw,size=10240k\n"
         b"30 29 0:27 / /sys/fs/cgroup/systemd rw - cgroup cgroup rw,name=systemd\n")
CG = b"7:name=systemd:/user.slice/user-1000.slice\n"


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.mapping = resolve_systemd_mapping(MOUNT, CG, "/user.slice/user-1000.slice")

    def test_recursive_tree_and_raw_bytes(self):
        paths = (b"/sys/fs/cgroup/systemd/user.slice/user-1000.slice",
                 b"/sys/fs/cgroup/systemd/user.slice/user-1000.slice/cgroup.procs",
                 b"/sys/fs/cgroup/systemd/user.slice/user-1000.slice/odd\xff")
        result = collect_recursive_observation(MOUNT, self.mapping, paths)
        self.assertEqual(result.raw_paths[-1], paths[-1])
        self.assertEqual(result.topology[0].parent_mount_id, 29)

    def test_descendant_and_control_file_overmount_rejected(self):
        for point in ("/sys/fs/cgroup/systemd/user.slice",
                      "/sys/fs/cgroup/systemd/user.slice/user-1000.slice/cgroup.procs"):
            mounts = MOUNT + (f"31 30 0:28 / {point} rw - tmpfs tmpfs rw\n").encode()
            with self.subTest(point=point), self.assertRaises(CgroupObserverError):
                collect_recursive_observation(mounts, self.mapping, (point,))

    def test_opaque_mapping_rejected(self):
        mounts = MOUNT + b"31 30 0:28 mnt:[9] /sys/fs/cgroup/systemd/user.slice rw - nsfs nsfs rw\n"
        with self.assertRaises(CgroupObserverError):
            collect_recursive_observation(mounts, self.mapping, ("/sys/fs/cgroup/systemd/user.slice",))

    def test_precommand_membership_and_terminal_empty_preserve_mapping(self):
        self.assertTrue(verify_pid_membership(CG, self.mapping))
        result = collect_recursive_observation(MOUNT, self.mapping, (self.mapping.filesystem_path,), "")
        self.assertEqual(result.mapping, self.mapping)
        self.assertEqual(result.terminal_control_group, self.mapping.original_control_group)

    def test_replaced_mapping_rejected(self):
        with self.assertRaises(CgroupObserverError):
            collect_recursive_observation(MOUNT, self.mapping, (self.mapping.filesystem_path,), "/user.slice/replaced.service")
        changed = MOUNT.replace(b"30 29", b"31 29")
        with self.assertRaises(CgroupObserverError):
            collect_recursive_observation(changed, self.mapping, (self.mapping.filesystem_path,))


if __name__ == "__main__":
    unittest.main()
