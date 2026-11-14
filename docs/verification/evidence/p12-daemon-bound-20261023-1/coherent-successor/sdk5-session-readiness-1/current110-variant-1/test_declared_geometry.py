"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual live_growth function with controlled declaration-only filesystem adapters.
No actual Path/statvfs/UUID/loop/backing access; these are contract fixtures, not capacity proof.
"""
from pathlib import Path
import ast,copy,importlib.util,json,os,stat,sys,types
H=Path(__file__).resolve().parent
p=H/'source/long_transport.py';spec=importlib.util.spec_from_file_location('declared110_transport',p);t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
GiB=2**30
# Test-only supplied admission values; no actual dispatcher reserve choice is made.
admission=dict(host_floor_bytes=16*GiB,scratch_floor_bytes=12*GiB,remaining_backing_growth_bytes=4*GiB,emergency_bytes=GiB,campaign_bytes=GiB,scratch_input_growth_bytes=GiB)
required=t.growth_requirements(admission);assert required==dict(host_required_bytes=26*GiB,scratch_required_bytes=15*GiB)
state=dict(size=110*GiB,gap=4*GiB,host=required['host_required_bytes'],scratch=required['scratch_required_bytes'],opens=0,closes=0)
class FakePath:
 def __init__(self,p):self.raw=str(p)
 def __str__(self):return self.raw
 def __eq__(self,other):return isinstance(other,FakePath)and self.raw==other.raw
 def stat(self):
  if self.raw=='/home/holden/mckernel-work/scratch':return types.SimpleNamespace(st_dev=42)
  if self.raw.startswith('/dev/disk/by-uuid/'):return types.SimpleNamespace(st_mode=stat.S_IFBLK|384,st_rdev=42)
  return types.SimpleNamespace(st_dev=99)
 def resolve(self,strict=True):return self
 def read_text(self):
  assert self.raw.startswith('/sys/dev/block/');return '/home/holden/mckernel-work/scratch.ext4\n'
class FakeOS:
 O_RDONLY=os.O_RDONLY;O_NOFOLLOW=os.O_NOFOLLOW;O_CLOEXEC=os.O_CLOEXEC
 @staticmethod
 def major(device):assert device==42;return 1
 @staticmethod
 def minor(device):assert device==42;return 2
 @staticmethod
 def open(path,flags):assert str(path)=='/home/holden/mckernel-work/scratch.ext4';state['opens']+=1;return 9
 @staticmethod
 def close(fd):assert fd==9;state['closes']+=1
 @staticmethod
 def fstat(fd):assert fd==9;return types.SimpleNamespace(st_mode=stat.S_IFREG|384,st_size=state['size'],st_blocks=(state['size']-state['gap'])//512,st_dev=99)
 @staticmethod
 def statvfs(path):return types.SimpleNamespace(f_bavail=state['scratch']if str(path)=='/home/holden/mckernel-work/scratch'else state['host'],f_frsize=1)
ns=dict(t.live_growth.__globals__);ns.update(Path=FakePath,os=FakeOS);actual=types.FunctionType(t.live_growth.__code__,ns,'controlled_actual_live_growth');records=[]
assert actual(admission,'/controlled/HOST/parent')==required;records.append(dict(case='actual_live_growth_accepts_declared110_with_complete_supplied_budgets',supplied_test_only_required_bytes=required))
def reject(name,change,admit=None):
 saved=dict(state);state.update(change);error=None
 try:actual(admission if admit is None else admit,'/controlled/HOST/parent')
 except ValueError as exc:error=str(exc)
 finally:state.clear();state.update(saved)
 assert error is not None;records.append(dict(case=name,error=error))
reject('142geometry_mismatch_refused',dict(size=142*GiB))
reject('insufficient_HOST_by_one_byte_refused',dict(host=required['host_required_bytes']-1))
reject('insufficient_scratch_by_one_byte_refused',dict(scratch=required['scratch_required_bytes']-1))
reject('full_sparse_gap_underbudget_refused',dict(gap=5*GiB))
wrong=dict(admission,host_floor_bytes=15*GiB);reject('HOST_floor_reduction_refused',{},wrong)
wrong=dict(admission,scratch_floor_bytes=11*GiB);reject('scratch_floor_reduction_refused',{},wrong)
wrong=dict(admission,emergency_bytes=0);reject('zero_emergency_refused',{},wrong)
assert state['opens']==state['closes'];assert t.TRANSPORT['logical_growth_bytes']==4*GiB and t.EXTERNAL_CAPTURE_BINDING is None
# 13.1GiB is task context, not a measured fixture fact or admission authority.
# This TEST_ONLY reserve/input vector needs15GiB and must refuse13.1GiB.
reject('task13_1GiB_context_cannot_satisfy_TEST_ONLY15GiB_vector',dict(scratch=int(13.1*GiB)))
result=dict(scope=__doc__.splitlines()[0],status='PASS_ACTUAL_DECLARED110_GEOMETRY_AND_UNCHANGED_GROWTH_CONTRACTS_TEST_ONLY',python=sys.version,declared_geometry_GiB=110,cases=records,actual_capacity=None,actual_storage_admission=None,EXTERNAL_CAPTURE_BINDING=None,capacity_claim=False,actual_probes=0,root=0,Docker=0,guest=0,compiler=0,scratch_formula='12GiB + scratch_input_growth_bytes + emergency_bytes + campaign_bytes',HOST_formula='16GiB + remaining_backing_growth_bytes(full live sparse gap or greater) +4GiBHOSTcapture +emergency_bytes+campaign_bytes',reserve_input_values='Syntheticfixturevector only; no dispatchercurrentreserves chosen/lowered')
with(H/'GEOMETRY-FIXTURE-RESULT.json').open('x')as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))
