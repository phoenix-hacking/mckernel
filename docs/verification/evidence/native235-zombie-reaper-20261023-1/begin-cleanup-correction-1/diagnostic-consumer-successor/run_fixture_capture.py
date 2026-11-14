"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import importlib.util,json,os
D=Path(__file__).resolve().parent;assert os.sched_getaffinity(0)=={6}
P=Path('/home/holden/mckernel/scripts/application-tests/supervisor.py');s=importlib.util.spec_from_file_location('accepted_supervisor',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
argv=['/usr/bin/taskset','-c','6','/usr/bin/prlimit','--as=536870912:536870912','--cpu=30:30','--core=0:0','--fsize=33554432:33554432','--nofile=256:256','--','/home/holden/anaconda3/bin/python3','-I','-B',str(D/'test_consumers.py')]
r=m.run_supervised(argv,cwd=str(D),env={'PATH':'/usr/bin:/bin','HOME':str(D),'TMPDIR':str(D),'LC_ALL':'C'},attempt_dir=str(D/'actual-consumer-fixtures-1'),timeout_seconds=35,cleanup_timeout_seconds=3,stdout_limit_bytes=33554432,stderr_limit_bytes=33554432)
(D/'ACTUAL-CONSUMER-FIXTURE-CAPTURE.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:r.get(k)for k in ('status','elapsed_seconds','wait_status','cleanup_complete')}))
assert r['status']=='COMPLETED'and r['wait_status']==dict(kind='exited',code=0)and r['cleanup_complete']
