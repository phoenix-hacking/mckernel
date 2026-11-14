import unittest

from layer_b_systemd_cgroup_collector import (
    AcceptedObservation, Entry, CgroupObserverError, accept_observation,
    collect_recursive_observation,
)
from layer_b_systemd_cgroup_observer import resolve_systemd_mapping

MOUNT = (b"29 23 0:26 / /sys/fs/cgroup rw - tmpfs tmpfs rw,size=10240k\n"
         b"30 29 0:27 / /sys/fs/cgroup/systemd rw - cgroup cgroup rw,name=systemd\n")
CG = b"7:name=systemd:/user.slice/user-1000.slice\n"


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.mapping = resolve_systemd_mapping(MOUNT, CG,
                                               "/user.slice/user-1000.slice")
        target = self.mapping.filesystem_path
        parent = "/sys/fs/cgroup/systemd/user.slice"
        root = "/sys/fs/cgroup/systemd"
        self.parents = (
            Entry(parent.encode(), 10, 10, "directory", (b"user-1000.slice",)),
            Entry(root.encode(), 10, 11, "directory", (b"user.slice",)),
        )
        self.entries = (
            Entry(target.encode(), 10, 12, "directory", (b"cgroup.procs",)),
            Entry((target + "/cgroup.procs").encode(), 10, 13, "file",
                  procs=b"123\n"),
        )

    def test_freezes_recursive_tree_and_precommand_membership(self):
        accepted = accept_observation(MOUNT, self.mapping, self.entries,
                                      self.parents)
        self.assertIsInstance(accepted, AcceptedObservation)
        self.assertEqual(accepted.pre_command_member_pids, (123,))
        result = collect_recursive_observation(
            MOUNT, accepted, self.entries, self.parents,
            self.mapping.original_control_group, require_retired=False)
        self.assertEqual(result.member_pids, (123,))

    def test_terminal_absence_requires_parent_listing_and_retains_mapping(self):
        accepted = accept_observation(MOUNT, self.mapping, self.entries,
                                      self.parents)
        terminal_parents = (
            Entry(self.parents[0].raw_path, 10, 10, "directory", ()),
            self.parents[1],
        )
        result = collect_recursive_observation(
            MOUNT, accepted, (), terminal_parents, b"")
        self.assertTrue(result.target_absent)
        self.assertEqual(result.mapping, accepted.mapping)

    def test_target_must_be_listed_by_immediate_parent(self):
        bad = (Entry(self.parents[0].raw_path, 10, 10, "directory", ()),
               self.parents[1])
        with self.assertRaises(CgroupObserverError):
            accept_observation(MOUNT, self.mapping, self.entries, bad)

    def test_incomplete_walk_and_sibling_only_walk_rejected(self):
        with self.assertRaises(CgroupObserverError):
            accept_observation(MOUNT, self.mapping, self.entries[:1],
                               self.parents)
        sibling = Entry((self.mapping.filesystem_path + "/sibling").encode(),
                        10, 20, "directory", (b"cgroup.procs",))
        with self.assertRaises(CgroupObserverError):
            accept_observation(MOUNT, self.mapping, (sibling,), self.parents)

    def test_descendant_or_ancestor_overmount_rejected(self):
        accepted = accept_observation(MOUNT, self.mapping, self.entries,
                                      self.parents)
        for point in ("/sys/fs/cgroup/systemd/user.slice",
                      self.mapping.filesystem_path + "/cgroup.procs"):
            mounts = MOUNT + (f"31 30 0:28 / {point} rw - tmpfs tmpfs rw\n").encode()
            with self.subTest(point=point), self.assertRaises(CgroupObserverError):
                collect_recursive_observation(mounts, accepted, self.entries,
                                              self.parents,
                                              self.mapping.original_control_group,
                                              require_retired=False)

    def test_terminal_replacement_and_parent_identity_drift_rejected(self):
        accepted = accept_observation(MOUNT, self.mapping, self.entries,
                                      self.parents)
        with self.assertRaises(CgroupObserverError):
            collect_recursive_observation(
                MOUNT, accepted, self.entries, self.parents,
                "/user.slice/replaced.service", require_retired=False)
        drift = (Entry(self.parents[0].raw_path, 10, 99, "directory",
                       self.parents[0].children), self.parents[1])
        with self.assertRaises(CgroupObserverError):
            collect_recursive_observation(
                MOUNT, accepted, self.entries, drift,
                self.mapping.original_control_group, require_retired=False)

    def test_membership_bytes_are_strict_and_not_double_counted(self):
        malformed = (self.entries[0], Entry(
            self.entries[1].raw_path, 10, 13, "file", procs=b"123\n123\n"))
        with self.assertRaises(CgroupObserverError):
            accept_observation(MOUNT, self.mapping, malformed, self.parents)
        bad_bytes = (self.entries[0], Entry(
            self.entries[1].raw_path, 10, 13, "file", procs=b"12x\n"))
        with self.assertRaises(CgroupObserverError):
            accept_observation(MOUNT, self.mapping, bad_bytes, self.parents)


if __name__ == "__main__":
    unittest.main()
