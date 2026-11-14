from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('supervisor','/home/holden/mckernel/scripts/application-tests/supervisor.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
argv=['/usr/bin/taskset','--cpu-list','6','/usr/bin/prlimit','--as=536870912','--cpu=30','--core=0','--fsize=134217728','--nofile=256','--','/usr/bin/python3','-I','-B',str(R/'check_runtime_join_expert_correction1.py')]
r=m.run_supervised(argv,cwd=str(R),env={'PATH':'/usr/bin:/bin','HOME':str(R),'TMPDIR':str(R),'LC_ALL':'C'},attempt_dir=str(R/'runtime-join-check-capture-expert-correction1'),timeout_seconds=30,cleanup_timeout_seconds=3,stdout_limit_bytes=8*2**20,stderr_limit_bytes=8*2**20)
with(R/'ACTUAL-RUNTIME-JOIN-CHECK-EXPERT-CORRECTION1.json').open('x')as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(dict(status=r['status'],wait_status=r['wait_status'],cleanup_complete=r['cleanup_complete'],elapsed_seconds=r['elapsed_seconds'])))
assert r['status']=='COMPLETED' and r['cleanup_complete'] and r['wait_status']=={'kind':'exited','code':0}
