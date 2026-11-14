"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Closed adoption of three already accepted helper files; no path search or new body.
"""
from pathlib import Path
import hashlib,importlib.util,os,stat,sys

_PINS={
 'prefix':('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/daemon-sdk7-next-production-criterion-source-1/container64-owner-successor-source-1/joined-task-observer-correction-source-1/prefix_evidence.py',3584,'28cf958ed755fc8ec3dc052fde0484f9770d2be9bcb45cb222dcfc20e3a9f039'),
 'audit':('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/daemon-sdk7-next-production-criterion-source-1/container64-owner-successor-source-1/joined-task-observer-correction-source-1/joined_audit.py',6275,'25552f721ff2f16c9a3c17b390087f3799182337b5685073129f2058d0add57c'),
 'rustio':('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/daemon-sdk7-next-production-criterion-source-1/container64-owner-successor-source-1/joined-task-observer-correction-source-1/rust-output-temp-correction-source-1/rust_output_contract.py',6177,'473b6f2e76b96ada032d42865cd12e24bb866d464f006c573d68c0a85405c357'),
}
_CACHE={}
def need(ok,message):
 if not ok:raise ValueError(message)
def verify_bytes(role,raw):
 need(role in _PINS,'closed accepted helper role required');path,size,digest=_PINS[role]
 need(len(raw)==size and hashlib.sha256(raw).hexdigest()==digest,'accepted helper bytes differ: '+role)
 return path,digest
def helper(role):
 need(role in _PINS,'closed accepted helper role required');value,size,digest=_PINS[role];path=Path(value)
 need(path.resolve(strict=True)==path,'canonical accepted helper path required')
 fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
 try:
  before=os.fstat(fd);need(stat.S_ISREG(before.st_mode) and before.st_nlink==1,'accepted helper regular single-link file required');raw=b''
  while len(raw)<=size:
   part=os.read(fd,size+1-len(raw))
   if not part:break
   raw+=part
  after=os.fstat(fd);linked=path.lstat();fields=('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
  need(all(getattr(before,k)==getattr(after,k)==getattr(linked,k) for k in fields),'accepted helper changed during read')
 finally:os.close(fd)
 verify_bytes(role,raw)
 if role not in _CACHE:
  name='_mckernel_accepted_'+role+'_'+digest[:16]
  spec=importlib.util.spec_from_file_location(name,str(path));need(spec is not None and spec.loader is not None,'accepted helper spec required')
  module=importlib.util.module_from_spec(spec)
  # Execute the verified bytes with the genuine file/spec context; no AST
  # extraction, copied implementation, altered guards or path substitution.
  sys.modules[name]=module
  try:exec(compile(raw,str(path),'exec'),module.__dict__)
  except BaseException:sys.modules.pop(name,None);raise
  _CACHE[role]=module
 module=_CACHE[role]
 need(module.__file__==str(path) and module.__spec__.origin==str(path),'accepted helper context differs')
 return module
