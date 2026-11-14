"""Fresh902 command/mount contract bound to the real full-build producer."""
from pathlib import Path
import ast,hashlib,json,os,stat
A=Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1')
REQUEST=dict(path=str(A/'image-request.json'),sha256='902f482227f3510c86a2624fa9f255abb3d0c82996191f4e3ca4c227877765f8')
PRODUCER=dict(path=str(A/'adapters/native_rust_exact_mckernel_image_container_owner.py'),sha256='34963a3efdd93ca7c88a88335c1b597a7084fd83f96fdd473daa4e55df474317')
def checked(ref):
 p=Path(ref['path']);fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  before=os.fstat(fd);assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=64<<20
  with os.fdopen(os.dup(fd),'rb') as f:raw=f.read(before.st_size+1)
  after=os.fstat(fd);named=p.lstat();fields=('st_dev','st_ino','st_mode','st_size','st_mtime_ns','st_ctime_ns')
  assert all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in fields)
  assert len(raw)==before.st_size and hashlib.sha256(raw).hexdigest()==ref['sha256'];return raw
 finally:os.close(fd)

def producer_construct(request):
 """Execute only literal selected argv/mount statements from pinned producer."""
 source=checked(PRODUCER).decode();tree=ast.parse(source);nodes=list(ast.walk(tree))
 command=next(n for n in nodes if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='command' and isinstance(n.value,ast.List) and n.value.elts and isinstance(n.value.elts[0],ast.Constant) and n.value.elts[0].value=='/driver.py')
 mounts=next(n for n in nodes if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='mounts' and isinstance(n.value,ast.List) and n.lineno<command.lineno and n.lineno>command.lineno-40)
 # These exact two conditionals are the producer's optional gitlink additions.
 gitmount=next(n for n in nodes if isinstance(n,ast.If) and n.lineno==mounts.end_lineno+1)
 gitcommand=next(n for n in nodes if isinstance(n,ast.If) and n.lineno==command.end_lineno+1)
 bound={k:Path(request[v]) for k,v in [('source','source_root'),('manifest','source_manifest'),('toolchain','toolchain_manifest'),('driver','driver_path'),('provenance','provenance_path'),('output','output_root')]}
 bound.update(work=Path(request['work_root']),gitlink_manifest=Path(request['gitlink_manifest']) if request.get('gitlink_manifest') else None,gitlink_root=Path(request['gitlink_root']) if request.get('gitlink_root') else None)
 scope=dict(r=request,bound=bound,evidence=Path(request['evidence_root']));module=ast.fix_missing_locations(ast.Module(body=[mounts,gitmount,command,gitcommand],type_ignores=[]));exec(compile(module,'<pinned full producer literal construction>','exec'),scope)
 argv=scope['command'];ms=[(dst,str(src),'bind',not readonly) for src,dst,readonly in scope['mounts']]
 ms +=[(r['container_path'],r['host_path'],'bind',False) for r in request['toolchain_roots']]
 assert not any(a in argv for a in ('--retained-phase-proof','--retained-phase-sha256'))
 return argv,sorted(ms)

def authenticated_layout(request):
 actual=json.loads(checked(REQUEST));assert request==actual,'exact fresh902 request'
 return producer_construct(request)
