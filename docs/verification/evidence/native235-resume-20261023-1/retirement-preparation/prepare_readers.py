"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Select unchanged accepted admission-reader statements, no execution effects here.
"""
from pathlib import Path
import ast,hashlib,json,os
D=Path(__file__).resolve().parent;assert os.sched_getaffinity(0)=={7}
S=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/fork-v3-matched-process-successor-1/case-235/final-runtime-ready-1/root-live-admission-1/read_only_native235_admission.py');raw=S.read_bytes();assert hashlib.sha256(raw).hexdigest()=='3dd230d35c41011e84b13cecef9ab303586c02ada9b0259fa50487d16d79b05b';s=raw.decode()
prefix=s[:s.index("root=Path('/home/holden/mckernel-work/scratch')")]
# Same completePROC59ef source authentication, direct accepted run() and census
# call; only stop before unrelated native-admission freshness gates.
proc=prefix+"print(json.dumps(dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='CURRENT_FAILED235_COMPLETE_PROC_OBSERVATION',proc=proc),sort_keys=True))\n"
lock=s[s.index("lock=Path('/run/lock/mckernel-development.lock')"):s.index("cid='695989")]
imports="import fcntl,json,os\nfrom pathlib import Path\ndef need(v,m):\n if not v:raise RuntimeError(m)\nneed(os.geteuid()==0,'authenticated root read-only observation')\n"
# Accepted exact lock acquisition and eight-path absence statements; append
# explicit release/close and output after that existing critical section.
mutex=imports+lock+"fcntl.flock(mutex_fd,fcntl.LOCK_UN);os.close(mutex_fd)\nprint(json.dumps(dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PASS_CURRENT_FAILED235_27_4_AND_8_PATH_ABSENCE',lock=[lock.st_dev,lock.st_ino],paths=paths),sort_keys=True))\n"
packet=json.loads((D/'CURRENT-FAILED235-RETIREMENT-PACKET.json').read_text());bound=[]
for name,body in [('readonly_current_proc.py',proc),('readonly_current_mutex_paths.py',mutex)]:
 ast.parse(body);p=D/name;p.write_text(body)
 argv=['/usr/bin/taskset','-c','7','/usr/bin/sudo','-A','/usr/bin/prlimit','--as=2147483648:2147483648','--cpu=30:30','--core=0:0','--fsize=8388608:8388608','--','/usr/bin/python3','-I','-B',str(p.resolve())]
 bound.append(dict(source=dict(path=str(p.resolve()),bytes=len(body.encode()),sha256=hashlib.sha256(body.encode()).hexdigest()),argv=argv,authority='Unchanged selected statements from3dd230d35 retained admission; wrapper output only; fresh exact review required.'))
packet['additional_readonly_observation_commands']=bound
packet['root_readonly_review']=None
(D/'CURRENT-FAILED235-RETIREMENT-PACKET.json').write_text(json.dumps(packet,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(status='PASS_EXTRACTED_READER_SYNTAX_ONLY',sources=[r['source']for r in bound],root_operations=0)))
