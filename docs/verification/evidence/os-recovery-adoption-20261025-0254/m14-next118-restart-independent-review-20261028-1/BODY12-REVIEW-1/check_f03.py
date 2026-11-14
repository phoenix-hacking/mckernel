"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only F03 BODY12 source and retained HOST evidence; no reruns or inventory.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re
ROOT=Path('/home/holden/mckernel');E=ROOT/'docs/verification/evidence/os-recovery-adoption-20261025-0254'
P=E/'m14-f03-next-runtime-body12-restart-20261028-1';HERE=Path(__file__).resolve().parent
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
assert ref(P/'ACTUAL-SOURCE-AND-HOST-HANDOFF.json')['sha256'].startswith('0c39c52b')
h=read(P/'ACTUAL-SOURCE-AND-HOST-HANDOFF.json');refs(h)
s=read(h['source_ready']['path']);refs(s)
r=read(h['actual_result']['path']);refs(r)
b=read(r['grant']['path']);refs(b)
assert b['author']=='/root/f03_next' and 'STANDING_HOST_AUTHORIZATION' in b['decision']
assert b['cpu']==6 and b['jobs']==1 and b['AS_bytes']==2147483648 and b['actual_cutoffs']==CAPS
assert b['CPU_seconds']==60 and b['wall_seconds']==90
plan=read(r['plan']['path'])
assert r['status']=='PASS_THREE_COMMAND_HOST_ABI10_AND_200_PAIRS' and len(r['commands'])==3
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
assert ref(P/'ACTUAL-SOURCE-AND-HOST-HANDOFF.json')['sha256']=='0c39c52ba6fe7348331647e1f37c875f3be3d720610f23cf5c80f42cd624357e'
original=(P/'original.C.inc').read_text();canonical=(ROOT/'kernel/syscall.c').read_text();policy=(ROOT/'kernel/rust/syscall_policy.rs').read_text()
assert canonical.count(original)==1
fixture_original=(P/'original.fixture.C.inc').read_text();marker=re.match(r'#line (\d+) "kernel/syscall.c"\n',fixture_original);assert marker and fixture_original[marker.end():]==original
sites=[int(marker[1])+i for i,line in enumerate(original.splitlines())if'dkprintf('in line]
binding=(P/'debug.binding.C.inc').read_text();assert sites==[28605]==[int(v)for v in re.findall(r'\.line=(\d+),\.flags=DDEBUG_DEFAULT',binding)]
assert '.file=__FILE__,.func="syscall_util_register_desc_log_bridge"'in binding and '.fmt='not in binding
production=(P/'util-desc-log-entry.Rust.inc').read_text();fixture=(P/'entry.fixture.Rust.inc').read_text()
assert fixture.split('\n    #[no_mangle]\n    pub static F03_UTIL_DESC_LOG_ABI:')[0].rstrip('\n')+'\n}\n'==production
assert 'pub unsafe extern "C" fn syscall_util_register_desc_log_bridge(tid:CInt,descriptor:CULong)'in production
assert 'read_volatile(addr_of!((*record).line_flags))>>24!=0'in production
assert (P/'debug-layout.reused.Rust.inc').read_text() in (ROOT/'kernel/rust/debug.rs').read_text()
assert 'fn syscall_util_register_desc_log_bridge(tid: CInt, desc: CULong);'in policy
assert (P/'caller-existing.Rust.inc').read_text() in policy
assert 'current_thread_ptr'not in production and 'uti_desc)'not in production
assert '__asm__("c_reference_syscall_util_register_desc_log_bridge")'in(P/'driver.c').read_text()
assert '#define syscall_util_register_desc_log_bridge'not in(P/'driver.c').read_text()
registry=E/'F03-cumulative-next-source-1/CURRENT116-REGISTRY-REFERENCE.json'
assert ref(registry)['sha256']=='af46e443770080fa9712c196233517bf7a9a8363d3d82659bd2ec4964d2402a2'
selected=[x for x in read(registry)['records']if x['function']=='syscall_util_register_desc_log_bridge']
assert selected==[dict(file='/src/kernel/syscall.c',function='syscall_util_register_desc_log_bridge',fmt=None,line=28605,flags=0,padding=0)]
result=dict(scope=__doc__.splitlines()[0],status='PASS_F03_BODY12_EXACT_UTIL_DESC_LOG_SOURCE_AND_RETAINED_HOST_ONLY',
            handoff=ref(P/'ACTUAL-SOURCE-AND-HOST-HANDOFF.json'),source_ready=ref(P/'SOURCE-READY.json'),
            actual_result=ref(P/'output-STANDING-1/ACTUAL-HOST-RESULT.json'),verified_byte_references=len(seen),
            byte_references=list(seen.values()),actual_commands_reviewed=3,actual_C_Rust_pairs=200,genuine_ABI_words=10,
            actual_metadata_pairs=1,debug_logical_lines=sites,retained_registry_reference=ref(registry),timeline=timeline,
            CPU_seconds=sum(x['CPU_seconds'] for x in r['commands']),sum_command_wall_seconds=sum(x['wall_seconds'] for x in r['commands']),
            peak_child_RSS_KiB=max(x['peak_RSS_KiB'] for x in r['commands']),
            reviewer_compiler_fixture_guard_inventory_calls=0,source_edits=0,new_default_artifacts=0,
            new_native_cases=0,new_C_retirements=0,new_file_closures=0,runtime_authority=None)
(HERE/'F03-CHECKS.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:result[k] for k in ['status','verified_byte_references','actual_commands_reviewed','actual_C_Rust_pairs','CPU_seconds','sum_command_wall_seconds','peak_child_RSS_KiB']},sort_keys=True))
