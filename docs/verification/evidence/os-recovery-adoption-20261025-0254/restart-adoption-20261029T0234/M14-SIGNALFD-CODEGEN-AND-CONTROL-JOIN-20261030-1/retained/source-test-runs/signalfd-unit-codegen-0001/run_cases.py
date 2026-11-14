"Functional McKernel OS/apps and Rust/assembly migration only; no security testing."
import os,json,time,hashlib
from pathlib import Path
r=Path("/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/source-test-runs/signalfd-unit-codegen-0001")
p=Path("/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/m14-eligible-signalfd-unit-1/PROFILE.SOURCE-ONLY.json")
argv=json.loads(p.read_text())["executable_argv_proposal"]
t=Path("/proc/self/stat").read_text().rsplit(")",1)[1].split()
(r/"COMPILER-PREEXEC-OWNER.json").write_text(json.dumps({"pid":os.getpid(),"ppid":int(t[1]),"pgid":os.getpgrp(),"birth":t[19],"at":time.time(),"stage":"IMMEDIATELY_BEFORE_RUSTC_EXEC_NOT_OBSERVED_EXEC","argv_sha256":hashlib.sha256(json.dumps(argv).encode()).hexdigest()})+"\n")
os.execv(argv[0],argv)
