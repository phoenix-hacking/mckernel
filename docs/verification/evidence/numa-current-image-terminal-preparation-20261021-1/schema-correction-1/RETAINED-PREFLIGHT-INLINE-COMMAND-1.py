import ast,hashlib,json,os,resource,stat,subprocess,sys,time
from pathlib import Path
C=Path('/home/holden/mckernel-work/host-preparation/numa-current-image-terminal-preparation-20261021-1/schema-correction-1')
p=C/'OPERATION-readonly-preflight.ACTUAL.json'
raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==sys.argv[1];op=json.loads(raw)
assert op['role']=='readonly-preflight' and op['cpu']==7 and op['stream_cap_bytes']==33554432
assert resource.getrlimit(resource.RLIMIT_CPU)==(-1,-1) and os.getuid()==1000 and 7 in os.sched_getaffinity(0)
argv=op['argv'];assert argv[argv.index('-c')+1]=='7' and '--cpu=unlimited:unlimited' in argv and '--as=2147483648:2147483648' in argv and '--fsize=33554432' in argv
run=Path(op['capture_directory']);assert not run.exists() and run.parent.is_dir() and not any(p.is_symlink() for p in (run.parent,*run.parent.parents))
BASE=Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/run_fresh8b_capture2.py')
source=BASE.read_bytes();assert hashlib.sha256(source).hexdigest()=='a6ce818b1eabea2d13ed811487b88b2b811a4abbdb7dbb6b2cd43058b400e2d1'
text=source.decode();tree=ast.parse(text);os.umask(0o077);os.sched_setaffinity(0,{7})
for name in ('write','descriptor'):
 node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
 exec(compile(ast.get_source_segment(text,node),str(BASE),'exec'),globals())
start=text.index("stdout=(run/'stdout').open('xb')");end=text.index('def descriptor(name):',start);status_start=text.index("status=dict(status='PASS' if rc==0",end)
tail=text[start:end]+text[status_start:];tail=tail.replace('cpu6_released','cpu7_released').replace('direct_joined=True','direct_child_joined=True')
proposal={'command':argv};run.mkdir(mode=0o700)
write('case-binding.json',dict(operation_path=str(p),operation_sha256=sys.argv[1],base_path=str(BASE),base_sha256=hashlib.sha256(source).hexdigest(),profile=op.get('profile'),role=op['role'],cpu=7))
exec(compile(tail,str(BASE)+'::<bound capture tail>','exec'),globals())
if rc!=0:raise SystemExit(rc)
