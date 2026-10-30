"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
import sys, unittest
sys.path[:0]=["/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-parent-successor-2/test-fixture-correction-1","/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-parent-successor-2","/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-direct-child-successor-3"]
suite=unittest.defaultTestLoader.loadTestsFromNames(["test_parent_source.TestProfile","test_parent_source.TestRetirement","test_parent_source.TestRecovery","test_parent_source.TestBootstrapBytes","test_direct_model","test_direct_ack"])
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
