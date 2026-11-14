"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only BODY5 source/HOST capture reconciliation. No runner/guard imports.
"""
from pathlib import Path
from decimal import Decimal
import hashlib
import json

ROOT=Path('/home/holden/mckernel')
E=ROOT/'docs/verification/evidence/os-recovery-adoption-20261025-0254'
F3=E/'m14-f03-next-runtime-body5-restart-20261028-1'
F6=E/'m14-f06-next-runtime-body5-restart-20261028-1'
HERE=Path(__file__).resolve().parent
CAPS=[1793253600,1035704.5689393478,1051042.6959879305]
seen={}

def ref(path):
    raw=Path(path).read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(path): return json.loads(Path(path).read_bytes())
def exact(item):
    expected={k:item[k] for k in ('path','bytes','sha256')}
    assert ref(item['path'])==expected,item['path']
    seen[item['path']]=expected
def bound(path,sha):
    item=ref(path);assert item['sha256']==sha
    exact(item);return read(path)

h3=bound(F3/'ACTUAL-SOURCE-AND-HOST-HANDOFF.json','1029f29df62fbaac9ba59987f09f43a13bca309fc2ed916801ce2b79ac2c7707')
h6=bound(F6/'ACTUAL-HOST-QUALIFICATION.json','83026e0b4f92b07863fc794bf01af3d267a35ec6ac8f2877f67fc36d3fc45407')
for key in ['source_ready','initial_actual_failure_and_Rust_prefix','correction','actual_remaining_suffix']:
    exact(h3[key])
for key in ['authority_record','worker_exact_bindings','immutable_source_ready','actual_results','preserved_preparation_failure']:
    exact(h6[key])
for item in h6['actual_capture_files']:exact(item)
exact(h6['existing_printer_provider_readback']['binding'])
s3=read(h3['source_ready']['path']);s6=read(h6['immutable_source_ready']['path'])
for item in s3['files']+s3['source_preimages']+s6['files']:exact(item)
old3=read(h3['initial_actual_failure_and_Rust_prefix']['path'])
new3=read(h3['actual_remaining_suffix']['path'])
assert old3['status']=='FIRST_FAILURE_STOPPED_NO_RETRY'
assert new3['status']=='PASS_TWO_COMMAND_CORRECTION_ABI52_AND_1152_PAIRS'
identities3=[];diagnostics3=[]
for stage,receipt in [('initial',old3),('correction',new3)]:
    exact(receipt['grant']);exact(receipt['plan'])
    authority=read(receipt['grant']['path']);plan=read(receipt['plan']['path'])
    assert authority['author']=='/root/f03_next'
    assert authority['decision']=='WORKER_RECORDED_ACTUAL_PARENT_STANDING_HOST_AUTHORIZATION'
    assert 'not a Root-authored grant' in authority['authority']
    assert authority['actual_cutoffs']==CAPS and authority['cpu']==6
    assert authority['credit_run_id']=='7f4af94a83b14cc08f97401f5891d965'
    assert authority['cumulative_credit_ceiling']=='57774.852125'
    assert authority['jobs']==1 and authority['AS_bytes']==2147483648
    for item in authority['actual_source_preimage_bindings']+authority['actual_tools']:exact(item)
    assert receipt['actual_commands_started']==len(receipt['commands'])==2
    for i,row in enumerate(receipt['commands']):
        expected_exit=1 if stage=='initial' and i==1 else 0
        assert row['argv']==plan['commands'][i]['argv'] and row['cwd']==plan['commands'][i]['cwd']
        assert row['returncode']==expected_exit and row['positive_wait4_join']
        assert row['wait4_pid']==row['actor']['pid'] and row['actor']['pid']==row['actor']['pgrp']==row['actor']['session']
        assert row['status']=='JOINED' and row['parent_streams_closed']
        assert row['process_group_absent'] and row['child_proc_absent'] and row['process_group_members']==[]
        assert row['affinity']==[6] and row['limits']['AS_bytes']==2147483648
        assert all(a<b for a,b in zip(row['preentry_clocks_epoch_MONO_BOOT'],CAPS))
        exact(row['stdout_record']);exact(row['stderr_record'])
        capture=Path(row['stdout']).parent
        assert read(capture/'result.json')==row
        start=read(capture/'command.json');assert start['actor']==row['actor'] and start['argv']==row['argv']
        if 'new_executable' in row:exact(row['new_executable'])
        stderr=Path(row['stderr']).read_text()
        if expected_exit:
            assert 'IHK_MC_AP_NOWAIT' in stderr and 'undeclared' in stderr
            diagnostic='PRESERVED_MISSING_GENUINE_HEADER_COMPILE_FAILURE'
        elif stage=='correction' and i==0:
            assert stderr.count('warning:')==1 and '[-Wmisleading-indentation]' in stderr
            assert "if(initialize)append('F');return initialize;" in stderr
            diagnostic='ONE_RETAINED_FIXTURE_INDENTATION_WARNING_NO_BEHAVIOR_CHANGE'
        else:
            assert stderr==''
            diagnostic='EMPTY_STDERR'
        diagnostics3.append(dict(stage=stage,command=i,classification=diagnostic,stderr=row['stderr_record']))
        identities3.append(dict(stage=stage,pid=row['actor']['pid'],birth=row['actor']['start'],
                                exit=expected_exit,positive_wait4_join=True,parent_streams_closed=True))
    if stage=='correction':
        assert Path(receipt['commands'][-1]['stdout']).read_text().strip()==plan['expected_stdout']
assert len(identities3)==h3['exact_compiler_fixture_commands_total']==4
correction=read(h3['correction']['path'])
for key in ['original_result','original_driver','corrected_driver','genuine_missing_header','retained_Rust_object']:exact(correction[key])
original_driver=Path(correction['original_driver']['path']).read_text()
assert original_driver.replace('#include <ihk/memconst.h>\n','#include <ihk/memconst.h>\n#include <ihk/mm.h>\n')==Path(correction['corrected_driver']['path']).read_text()
assert new3['commands'][0]['argv'].count(correction['retained_Rust_object']['path'])==1
assert all('rustc' not in row['argv'][0] for row in new3['commands'])
assert h3['actual_Rust_compiles']==1 and h3['actual_C_link_attempts']==2 and h3['actual_fixture_runs']==1

original_allocator=(F3/'allocator-original.Rust.inc').read_text()
old_order='        extra_config = hw_cache_extra_reg_map(attr_config);\n        hw_cache_event_map(attr_config)\n'
new_order='        let mapped = hw_cache_event_map(attr_config);\n        extra_config = hw_cache_extra_reg_map(attr_config);\n        mapped\n'
assert original_allocator.count(old_order)==1
assert original_allocator.replace(old_order,new_order)==(F3/'allocator-candidate.Rust.inc').read_text()
assert original_allocator in (ROOT/'kernel/rust/syscall_policy.rs').read_text()
assert (F3/'allocator-original.C.inc').read_text() in (ROOT/'kernel/syscall.c').read_text()
assert (F3/'entry-original.C.inc').read_text() in (ROOT/'kernel/syscall.c').read_text()
assert (F3/'entry.fixture.Rust.inc').read_text().split('\n    #[no_mangle]\n    pub static F03_PERF_ALLOCATION_ABI:')[0].rstrip('\n')+'\n}\n'==(F3/'perf-alloc-entry.Rust.inc').read_text()

bindings=read(h6['worker_exact_bindings']['path']);authority=read(h6['authority_record']['path'])
assert bindings['author']=='/root/f06_next'
assert bindings['decision']=='WORKER_EXACT_BINDINGS_UNDER_ACTUAL_PARENT_STANDING_ORDINARY_HOST_AUTHORIZATION'
assert authority['recorded_by']=='/root/f06_next' and 'not a Root-authored grant' in authority['authority']
assert bindings['actual_cutoffs']==CAPS and bindings['cpu']==7 and bindings['jobs']==1
assert bindings['AS_bytes']==2147483648 and bindings['CPU_seconds']==60 and bindings['wall_seconds']==90
for item in bindings['actual_source_bindings']+bindings['actual_tools']:exact(item)
plan6=read(bindings['command_plan']['path']);r6=read(h6['actual_results']['path'])
assert r6['status']=='FOUR_HOST_COMMANDS_PASS' and r6['actual_commands_started']==4
assert r6['grant_sha256']==h6['worker_exact_bindings']['sha256']
pre=read(F6/'PREIMAGES.json')
for item in [pre['source_adoption118'],pre['accepted_artifact_source_adoption116'],pre['original_body'],pre['original_event_defines'],pre['retained_object_frontier']]:exact(item)
for item in list(pre['all_nine_root118_canonical_postimages'].values())+pre['real_header_inputs']:exact(item)
for entry in pre['snapshots'].values():exact(entry['canonical']);exact(entry['snapshot'])
identities6=[]
for i,(row,planned) in enumerate(zip(r6['commands'],plan6['commands'])):
    base=F6/'future-host-output-1'/('command'+str(i))
    assert row['argv']==planned['argv'] and row['cwd']==plan6['cwd']
    assert read(base.with_suffix('.JOINED.json'))==row
    assert row['status']=='PASS' and row['wait4']['exit']==row['wait4']['status']==0
    assert row['wait4']['positive_direct_join'] and row['wait4']['pid']==row['identity']['pid']
    assert row['parent_streams_closed'] and row['child_streams_closed_by_whole_group_absence']
    assert row['group_absent'] and row['group_members']==row['group_scan_errors']==[]
    start,before=read(base.with_suffix('.STARTED.json')),read(base.with_suffix('.PREFLIGHT.json'))
    assert start['identity']==row['identity'] and start['argv']==row['argv']
    assert start['affinity']==[7] and start['AS_limit']==[2147483648]*2 and start['CPU_limit']==[60]*2
    assert before['status']=='PASS' and before['actual_cutoffs']==CAPS
    assert before['guard_sha256'].startswith('48893862') and all(a<b for a,b in zip(before['clocks_epoch_MONO_BOOT'],CAPS))
    assert Decimal(before['credit']['spent'])>=Decimal('22812.3311')
    for item in before['actual_preimages_and_header_inputs_verified']:exact(item)
    assert ref(base.with_suffix('.stdout'))['sha256']==row['stdout_sha256']
    assert ref(base.with_suffix('.stderr'))['sha256']==row['stderr_sha256']
    assert base.with_suffix('.stderr').read_bytes()==b''
    identities6.append(dict(pid=row['identity']['pid'],birth=row['identity']['birth'],exit=0,
                            positive_wait4_join=True,parent_streams_closed=True))
assert len(identities6)==4
assert 'pairs=585; mixed_sequence_calls=5;' in (F6/'future-host-output-1/command3.stdout').read_text()
runner=read(F6/'future-host-output-1/RUNNER-BINDING.json')
assert runner['initial_output_absent'] and ref(runner['runner'])['sha256']==runner['runner_sha256']
assert runner['grant_sha256']==h6['worker_exact_bindings']['sha256']
assert (F6/'original-vdso-setup-log.c.inc').read_text() in (F6/'BASE.syscall.c').read_text()
assert (F6/'original-event-defines.c.inc').read_text() in (F6/'BASE.syscall.c').read_text()
assert '#define ekprintf(fmt, args...) kprintf(fmt, ##args)' in (ROOT/'lib/include/ihk/debug.h').read_text()
assert '#[path = "f06_vdso_setup_log.rs"] mod candidate;' in (F6/'fixture.rs').read_text()

result=dict(scope=__doc__.splitlines()[0],status='PASS_BODY5_EXACT_SOURCE_AND_RETAINED_EIGHT_HOST_COMMANDS',
            handoff_F03=ref(F3/'ACTUAL-SOURCE-AND-HOST-HANDOFF.json'),HOST_F06=ref(F6/'ACTUAL-HOST-QUALIFICATION.json'),
            F03_identities=identities3,F06_identities=identities6,F03_diagnostics=diagnostics3,
            existing_HOST_commands_reviewed=8,successful_HOST_commands=7,preserved_failed_compile_commands=1,
            F03_original_C_Rust_pairs=1152,F03_additional_null_calls=4,F03_ABI_words=52,
            F06_original_C_Rust_pairs=585,F06_mixed_sequence_events=7,F06_mixed_sequence_calls=5,
            exact_Rust_cache_order_correction=True,exact_header_only_fixture_correction=True,
            shared_Rust_helper_is_preexisting_live_consumer=True,new_C_binding_data_remains_explicit_debt=True,
            actual_Root118_postimages_unchanged=9,verified_byte_references=len(seen),byte_references=list(seen.values()),
            reviewer_compiler_fixture_guard_calls=0,canonical_writes=0,new_default_artifacts=0,new_native_cases=0,
            new_C_retirements=0,new_file_closures=0,runtime_authority=None)
(HERE/'CHECKS.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:result[k] for k in ['status','existing_HOST_commands_reviewed','successful_HOST_commands','preserved_failed_compile_commands','verified_byte_references']},sort_keys=True))
