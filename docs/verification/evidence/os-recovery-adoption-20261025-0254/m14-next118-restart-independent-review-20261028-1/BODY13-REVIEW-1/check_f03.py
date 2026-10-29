"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only F03 BODY13 source and retained HOST evidence; no reruns or inventory.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re
ROOT=Path('/home/holden/mckernel');E=ROOT/'docs/verification/evidence/os-recovery-adoption-20261025-0254'
P=E/'m14-f03-next-runtime-body13-restart-20261028-1';HERE=Path(__file__).resolve().parent
CAPS=[1793253600,1035704.5689393478,1051042.6959879305];seen={}
def ref(p):
    d=Path(p).read_bytes();return dict(path=str(p),bytes=len(d),sha256=hashlib.sha256(d).hexdigest())
def read(p):return json.loads(Path(p).read_bytes())
def exact(v):
    r={k:v[k] for k in ('path','bytes','sha256')};assert ref(v['path'])==r,v['path'];seen[v['path']]=r
def refs(v):
    if isinstance(v,dict):
        if all(k in v for k in ('path','bytes','sha256')):exact(v)
        for x in v.values():refs(x)
    elif isinstance(v,list):
        for x in v:refs(x)
def utc(t):return datetime.fromtimestamp(t,timezone.utc).isoformat(timespec='microseconds')
assert ref(P/'ACTUAL-SOURCE-AND-HOST-HANDOFF.json')['sha256'].startswith('256b2bce')
h=read(P/'ACTUAL-SOURCE-AND-HOST-HANDOFF.json');refs(h)
s=read(h['source_ready']['path']);refs(s)
r=read(h['actual_result']['path']);refs(r)
b=read(r['grant']['path']);refs(b)
assert b['author']=='/root/f03_next' and 'STANDING_HOST_AUTHORIZATION' in b['decision']
assert b['cpu']==6 and b['jobs']==1 and b['AS_bytes']==2147483648 and b['actual_cutoffs']==CAPS
assert b['CPU_seconds']==60 and b['wall_seconds']==90
plan=read(r['plan']['path'])
assert r['status']=='PASS_THREE_COMMAND_HOST_RUST_DEBUG_STORAGE_AND_256_FLAG_PAIRS' and len(r['commands'])==3
timeline=[]
for row,command in zip(r['commands'],plan['commands']):
    assert row['argv']==command['argv'] and row['cwd']==command['cwd']
    assert row['returncode']==row['wait_status']==0 and row['positive_wait4_join']
    assert row['wait4_pid']==row['actor']['pid']==row['actor']['pgrp']==row['actor']['session']
    assert row['parent_streams_closed'] and row['process_group_absent'] and row['child_proc_absent']
    assert row['process_group_members']==[] and row['affinity']==[6]
    assert all(a<b for a,b in zip(row['preentry_clocks_epoch_MONO_BOOT'],CAPS))
    assert Path(row['stderr']).read_bytes()==b''
    folder=Path(row['stdout']).parent;assert read(folder/'result.json')==row
    start=read(folder/'command.json');assert start['argv']==row['argv'] and start['actor']==row['actor']
    if 'new_executable' in row:exact(row['new_executable'])
    timeline.append(dict(index=row['index'],pid=row['actor']['pid'],birth=row['actor']['start'],
                         start_epoch=row['started_epoch'],finish_epoch=row['finished_epoch'],
                         start_UTC=utc(row['started_epoch']),finish_UTC=utc(row['finished_epoch']),
                         exit=0,positive_wait4_join=True,parent_streams_closed=True))
assert Path(r['commands'][-1]['stdout']).read_text().strip()==plan['expected_stdout']
assert ref(P/'ACTUAL-SOURCE-AND-HOST-HANDOFF.json')['sha256']=='256b2bce79efebfd5d60d6b860c8bbce531718989f882c9dd969e578b2435411'
B12=E/'m14-f03-next-runtime-body12-restart-20261028-1';source_map=read(P/'SOURCE-MAP-FROM-BODY12.json');refs(source_map)
logger=(B12/'util-desc-log-entry.Rust.inc').read_text();storage=(P/'debug-storage.Rust.inc').read_text()
Cbase=(ROOT/'kernel/syscall.c').read_text();Rbase=(ROOT/'kernel/rust/syscall_policy.rs').read_text()
original=(B12/'original.C.inc').read_text().rstrip('\n');paired=(B12/'paired.C.inc').read_text().rstrip('\n')
Cpre=Path(source_map['writes'][0]['preimage']['path']).read_text();Rpre=Path(source_map['writes'][1]['preimage']['path']).read_text()
assert Cpre==Cbase.replace(original,paired,1)and Rpre==Rbase+'\n'+logger
old_binding=(B12/'debug.binding.C.inc').read_text();start=old_binding.index('struct ddebug ');end=old_binding.index('};',start)+2;old_storage=old_binding[start:end]
Cpost=Path(source_map['writes'][0]['postimage']['path']).read_text();Rpost=Path(source_map['writes'][1]['postimage']['path']).read_text()
assert Cpost==Cpre.replace(old_storage,'extern struct ddebug f03_util_register_desc_debug_v1[1];',1)
assert Rpost==Rpre+'\n'+storage
assert old_storage not in Cpost and Cpost.count('extern struct ddebug f03_util_register_desc_debug_v1[1];')==1
assert Rpost.count('pub static mut f03_util_register_desc_debug_v1:')==1 and Rpost.count('pub unsafe extern "C" fn syscall_util_register_desc_log_bridge(')==1
assert '#[used]'in storage and '#[link_section="__verbose"]'in storage and 'line_flags:28605'in storage
assert (P/'debug-layout.reused.Rust.inc').read_bytes()==(B12/'debug-layout.reused.Rust.inc').read_bytes()
obj=s['reused_actual_BODY12_object'];exact(obj);assert obj['sha256']=='6ff7fa282d023df29ac05f15aa9814e3448303a9850d2d0284418a1ed2b19820'
assert obj['path']in r['commands'][1]['argv']and obj['path']not in r['commands'][0]['argv']
registry=read(s['origin_reference']['path']);assert registry['records'].count(s['actual_origin'])==1
readback=read(h['actual_Rust_storage_object']['path']);refs(readback)
import struct
class Elf:
 def __init__(self,path):
  self.data=Path(path).read_bytes();h=struct.unpack_from('<16sHHIQQQIHHHHHH',self.data);assert h[0][:6]==b'\x7fELF\x02\x01'and h[2]==62
  self.sections=[struct.unpack_from('<IIQQQQIIQQ',self.data,h[6]+i*h[11])for i in range(h[12])];strsec=self.sections[h[13]];strings=self.data[strsec[4]:strsec[4]+strsec[5]]
  self.names=[self.string(strings,x[0])for x in self.sections];self.tables={};self.symbols=[]
  for i,sec in enumerate(self.sections):
   if sec[1]!=2:continue
   st=self.sections[sec[6]];strings=self.data[st[4]:st[4]+st[5]];rows=[]
   for at in range(sec[4],sec[4]+sec[5],sec[9]):
    n,info,other,index,value,size=struct.unpack_from('<IBBHQQ',self.data,at);row=dict(name=self.string(strings,n),bind=info>>4,type=info&15,index=index,value=value,bytes=size);rows.append(row);self.symbols.append(row)
   self.tables[i]=rows
 @staticmethod
 def string(data,offset):return data[offset:data.index(0,offset)].decode()
new=Elf(readback['object']['path']);owned=[x for x in new.symbols if x['name']=='f03_util_register_desc_debug_v1'];assert owned==[readback['record']]
record=owned[0];sec=new.sections[record['index']];raw=new.data[sec[4]+record['value']:sec[4]+record['value']+32]
assert new.names[record['index']]=='__verbose'and sec[8]==8 and sec[2]==readback['section_flags']and sec[2]&3==3
assert record['bind']==record['type']==1 and record['bytes']==32
assert raw[16:24]==b'\0'*8 and raw[28:32]==b'\0'*4 and struct.unpack_from('<I',raw,24)[0]==28605
relocations=[];strings={}
for relsec in new.sections:
 if relsec[1]!=4 or relsec[7]!=record['index']:continue
 for at in range(relsec[4],relsec[4]+relsec[5],relsec[9]):
  offset,info,addend=struct.unpack_from('<QQq',new.data,at);typ=info&0xffffffff;sym=new.tables[relsec[6]][info>>32];target=new.sections[sym['index']];begin=target[4]+sym['value']+addend
  strings[offset]=new.string(new.data,begin);relocations.append(dict(offset=offset,type=typ,addend=addend))
assert relocations==readback['pointer_relocations']==[dict(offset=0,type=1,addend=0),dict(offset=8,type=1,addend=22)]
assert strings=={0:'/src/kernel/syscall.c',8:'syscall_util_register_desc_log_bridge'}
assert not any(x['type']==2 and 0<x['index']<len(new.sections)and new.sections[x['index']][2]&2 for x in new.symbols)
old=Elf(obj['path']);assert not any(x['name']=='f03_util_register_desc_debug_v1'and x['index']!=0 for x in old.symbols)
assert any(x['name']=='f03_util_register_desc_debug_v1'and x['index']==0 for x in old.symbols)
assert (P/'original.fixture.C.inc').read_text().split('\n',1)[1]==(B12/'original.C.inc').read_text()
assert 'flag<256' in (P/'driver.c').read_text()and 'pairs!=256'in(P/'driver.c').read_text()
assert 'ABI10 reused; 256 C/Rust flag pairs' in Path(r['commands'][-1]['stdout']).read_text()
result=dict(scope=__doc__.splitlines()[0],status='PASS_F03_BODY13_EXACT_RUST_DEBUG_STORAGE_AND_RETAINED_HOST_ONLY',
            handoff=ref(P/'ACTUAL-SOURCE-AND-HOST-HANDOFF.json'),source_ready=ref(P/'SOURCE-READY.json'),
            actual_result=ref(P/'output-STANDING-1/ACTUAL-HOST-RESULT.json'),verified_byte_references=len(seen),
            byte_references=list(seen.values()),actual_commands_reviewed=3,actual_C_Rust_pairs=256,genuine_ABI_words=10,
            actual_metadata_pairs=1,actual_Rust_owned_record_bytes=32,unchanged_BODY12_object=ref(Path(obj['path'])),timeline=timeline,
            CPU_seconds=sum(x['CPU_seconds'] for x in r['commands']),sum_command_wall_seconds=sum(x['wall_seconds'] for x in r['commands']),
            peak_child_RSS_KiB=max(x['peak_RSS_KiB'] for x in r['commands']),
            reviewer_compiler_fixture_guard_inventory_calls=0,source_edits=0,new_default_artifacts=0,
            new_native_cases=0,new_C_retirements=0,new_file_closures=0,runtime_authority=None)
(HERE/'F03-CHECKS.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:result[k] for k in ['status','verified_byte_references','actual_commands_reviewed','actual_C_Rust_pairs','CPU_seconds','sum_command_wall_seconds','peak_child_RSS_KiB']},sort_keys=True))
