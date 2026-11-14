"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Execute the actual private live_growth reader with fixture-only external observations.
"""
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import importlib.util,json,os,stat
D=Path(__file__).resolve().parent
assert os.sched_getaffinity(0)=={7}
s=importlib.util.spec_from_file_location('private_142',D/'long_transport.accounting-142GiB-proposal.py');t=importlib.util.module_from_spec(s);s.loader.exec_module(t)
SCRATCH='/home/holden/mckernel-work/scratch';BACKING=SCRATCH+'.ext4';UUID='/dev/disk/by-uuid/2a5768c8-718d-4914-bdc0-6b32c5a92a52';OUT='/fixture/host-output'
DEVICE=os.makedev(7,36);HOST=os.makedev(259,2)
class ObservedPath:
    def __init__(self,value):self.value=str(value)
    def __str__(self):return self.value
    def __eq__(self,other):return isinstance(other,ObservedPath) and self.value==other.value
    def stat(self):
        if self.value==SCRATCH:return NS(st_dev=DEVICE)
        if self.value==UUID:return NS(st_mode=stat.S_IFBLK,st_rdev=case['uuid_device'])
        if self.value==OUT:return NS(st_dev=HOST)
        raise AssertionError('unexpected stat '+self.value)
    def resolve(self,strict=False):return self
    def read_text(self):
        assert self.value=='/sys/dev/block/7:36/loop/backing_file'
        return case['loop_backing']+'\n'
def fake_open(path,flags):
    assert str(path)==BACKING and flags==os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC
    return 999
def fake_statvfs(path):
    assert str(path) in (OUT,SCRATCH)
    return NS(f_bavail=(128 if str(path)==OUT else 64)*2**30//4096,f_frsize=4096)
base=dict(size=142*2**30,allocated=100*2**30,uuid_device=DEVICE,loop_backing=BACKING,backing_device=HOST,backing_mode=stat.S_IFREG,gap=42*2**30)
results=[]
for name,updates,error in [
    ('accept142',{},None),
    ('refuse110',dict(size=110*2**30),'exact142GiB'),
    ('refuse143',dict(size=143*2**30),'exact142GiB'),
    ('refuse_wrong_uuid',dict(uuid_device=os.makedev(7,35)),'scratch UUID'),
    ('refuse_wrong_loop_backing',dict(loop_backing='/fixture/wrong.ext4'),'loop backing'),
    ('refuse_wrong_output_geometry',dict(backing_device=DEVICE),'exact142GiB'),
    ('refuse_nonregular_backing',dict(backing_mode=stat.S_IFBLK),'exact142GiB'),
    ('refuse_old110_gap',dict(gap=10*2**30),'full live sparse backing gap'),
]:
    case=dict(base,**updates)
    a=dict(host_floor_bytes=16*2**30,scratch_floor_bytes=12*2**30,remaining_backing_growth_bytes=case['gap'],emergency_bytes=1,campaign_bytes=1,scratch_input_growth_bytes=0)
    closed=[]
    with patch.object(t,'Path',ObservedPath),patch.object(t.os,'open',fake_open),patch.object(t.os,'fstat',lambda fd:NS(st_mode=case['backing_mode'],st_size=case['size'],st_dev=case['backing_device'],st_blocks=case['allocated']//512)),patch.object(t.os,'close',lambda fd:closed.append(fd)),patch.object(t.os,'statvfs',fake_statvfs):
        try:
            got=t.live_growth(a,OUT)
            assert error is None,(name,'unexpected acceptance')
            assert got['host_required_bytes']==62*2**30+2
            results.append(dict(name=name,result='PASS_ACCEPT',host_required_bytes=got['host_required_bytes']))
        except ValueError as exc:
            assert error is not None and error in str(exc),(name,str(exc))
            results.append(dict(name=name,result='PASS_REFUSE',reason=str(exc)))
    if name not in ('refuse_wrong_uuid','refuse_wrong_loop_backing'):assert closed==[999]
assert t.EXTERNAL_CAPTURE_BINDING is None
r=dict(scope=__doc__.splitlines()[0],status='PASS_8_ACTUAL_READER_FIXTURE_OBSERVATIONS_NO_RUNTIME',observations=results,source='long_transport.accounting-142GiB-proposal.py',failed_candidates=0,bounded_corrections=0,native_credit=0,runtime_mutations=0,runtime_release='NOT_RELEASED',limitations='Actual live_growth body; UUID/loop/stat/open/statvfs observations are fixtures. No real root admission or geometry mutation.')
(D/'142GiB-reader-receipt.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:r[k] for k in ('status','failed_candidates','runtime_mutations')}))
