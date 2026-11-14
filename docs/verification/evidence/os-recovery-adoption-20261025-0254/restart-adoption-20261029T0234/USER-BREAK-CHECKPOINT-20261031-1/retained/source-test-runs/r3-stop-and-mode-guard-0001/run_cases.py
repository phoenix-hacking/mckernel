"Functional McKernel OS/apps and Rust/assembly migration only; no security testing."
import sys,unittest,importlib.util,json,os
from pathlib import Path
sys.path[:0]=["/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-r3-control-stop-1"]
suite=unittest.defaultTestLoader.loadTestsFromNames(["test_failure_binding"])
result=unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():raise SystemExit(1)
p=Path("/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-direct-child-successor-4/phase0.py")
spec=importlib.util.spec_from_file_location("actual_ancestry_guard",p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
fd,identities=m.open_dir("/usr/bin",True)
print(json.dumps({"status":"PASS_ACTUAL_ORIGINAL_INTERPRETER_ANCESTRY_GUARD","identity":identities[-1],"mode":oct(os.fstat(fd).st_mode&0o7777),"changed_guard":False}))
for owned in reversed(m.HELD):os.close(owned)
