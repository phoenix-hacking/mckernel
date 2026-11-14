"Functional McKernel OS/apps and Rust/assembly migration only; no security testing."
import sys,unittest
sys.path[:0]=["/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-failure-data-correction-1","/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-caller-role-correction-1"]
suite=unittest.defaultTestLoader.loadTestsFromNames(["test_failure_data","test_sudo_role"])
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
