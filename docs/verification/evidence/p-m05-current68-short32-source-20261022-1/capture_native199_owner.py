"""Thin data binding of accepted a6ce capture tail; FIRST FOUR operations only."""
import argparse,ast,hashlib,json,os,stat,subprocess,time
from pathlib import Path
BASE=Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/run_fresh8b_capture2.py')
BASE_SHA='a6ce818b1eabea2d13ed811487b88b2b811a4abbdb7dbb6b2cd43058b400e2d1'
p=argparse.ArgumentParser();p.add_argument('--operation',required=True);p.add_argument('--sha256',required=True);a=p.parse_args()
raw=Path(a.operation).read_bytes();assert hashlib.sha256(raw).hexdigest()==a.sha256;op=json.loads(raw)
assert op['role'] in ('observer','summary','original-five-FD-metadata','raw-five-export','current-sdk-owner','native199-owner') and op['cpu']==7 and op['stream_cap_bytes']==33554432
argv=op['argv'];assert isinstance(argv,list) and all(isinstance(x,str) for x in argv)
assert argv[argv.index('-c')+1]=='7' and '--fsize=33554432' in argv
run=Path(op['capture_directory']);assert run.is_absolute() and '..' not in run.parts and not run.exists()
assert run.parent.is_dir() and not any(q.is_symlink() for q in (run.parent,*run.parent.parents))
assert os.getuid()==1000 and 7 in os.sched_getaffinity(0);os.umask(0o077);os.sched_setaffinity(0,{7})
source=BASE.read_bytes();assert hashlib.sha256(source).hexdigest()==BASE_SHA
text=source.decode();tree=ast.parse(text)
# Reuse exact reviewed function bodies without source transformations.
for name in ('write','descriptor'):
 node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
 exec(compile(ast.get_source_segment(text,node),str(BASE),'exec'),globals())
# Only the old admission is omitted. Directwait->streamclose->group->FDhash tail is reused.
start=text.index("stdout=(run/'stdout').open('xb')")
end=text.index('def descriptor(name):',start)
status_start=text.index("status=dict(status='PASS' if rc==0",end)
tail=text[start:end]+text[status_start:]
# Typed CPU label and required direct-join field spelling; no sequencing or capture changes.
tail=tail.replace('cpu6_released','cpu7_released').replace('direct_joined=True','direct_child_joined=True')
proposal={'command':argv};run.mkdir(mode=0o700)
write('case-binding.json',dict(operation_path=a.operation,operation_sha256=a.sha256,base_path=str(BASE),base_sha256=BASE_SHA,profile=op['profile'],role=op['role'],cpu=7))
exec(compile(tail,str(BASE)+'::<bound capture tail>','exec'),globals())
if rc!=0:raise SystemExit(rc)
