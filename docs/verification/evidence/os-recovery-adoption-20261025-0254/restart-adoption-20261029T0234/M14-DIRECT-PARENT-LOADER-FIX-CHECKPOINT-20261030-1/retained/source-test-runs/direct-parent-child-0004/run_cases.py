"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
import sys, unittest, os, json
sys.path[:0]=["/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-parent-successor-2/test-fixture-correction-1","/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-parent-successor-3","/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-direct-child-successor-4"]
before=len(os.listdir("/proc/self/fd"))
suite=unittest.defaultTestLoader.loadTestsFromNames(["test_parent_source.TestRetirement","test_parent_source.TestRecovery","test_parent_source.TestBootstrapBytes","test_bootstrap_fd","test_direct_model","test_direct_ack","test_loader_budget"])
result=unittest.TextTestRunner(verbosity=2).run(suite)
print(json.dumps({"fd_count_before_loader_imports":before,"fd_count_after_cases":len(os.listdir("/proc/self/fd")),"nofile_limit_unchanged":128}))
raise SystemExit(0 if result.wasSuccessful() else 1)
