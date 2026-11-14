#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
BODY13 moves existing BODY12 debug storage, without adding another logger body.
"""
import difflib,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=Path('/home/holden/mckernel')
E=HERE.parent
B12=E/'m14-f03-next-runtime-body12-restart-20261028-1'
BASE=E/'m14-next118-composition-restart-20261028-1/candidate'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def save(relative,data):
 p=HERE/relative;p.parent.mkdir(parents=True,exist_ok=True)
 if isinstance(data,dict):data=json.dumps(data,indent=2)+'\n'
 p.write_text(data);return ref(p)
def c_string(value):
 assert value.isascii() and not any(c in value for c in ['"','\\','\n','\r','\0'])
 return 'b"'+value+'\\0".as_ptr().cast()'
def main():
 ready=json.loads((B12/'SOURCE-READY.json').read_text());result=json.loads((B12/'output-STANDING-1/ACTUAL-HOST-RESULT.json').read_text())
 assert result['status'].startswith('PASS_') and all(row['returncode']==0 and row['positive_wait4_join'] and row['process_group_absent'] and row['parent_streams_closed'] for row in result['commands'])
 registry_path=E/'F03-cumulative-next-source-1/CURRENT116-REGISTRY-REFERENCE.json';registry=json.loads(registry_path.read_text());assert registry['count']==389
 rows=[row for row in registry['records'] if row['function']=='syscall_util_register_desc_log_bridge'];assert len(rows)==1
 origin=rows[0];assert origin['line']==ready['metadata']['logical_line'] and origin['flags']==origin['padding']==0 and origin['fmt'] is None
 record_source='''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact original C metadata provenance, retained from the accepted registry.
mod f03_util_register_desc_debug_storage_v1 {
    use crate::debug::Ddebug;
    // The C consumer and existing BODY12 logger retain this exact global symbol
    // and repr(C) layout. Static lifetime/writable flags/section membership are
    // unchanged; original update synchronization remains the caller's contract.
    #[used]
    #[no_mangle]
    #[link_section="__verbose"]
    pub static mut f03_util_register_desc_debug_v1:[Ddebug;1]=[Ddebug {
        file:FILE_VALUE,
        func:FUNC_VALUE,
        fmt:core::ptr::null(),
        line_flags:LINE_VALUE,
    }];
}
'''.replace('FILE_VALUE',c_string(origin['file'])).replace('FUNC_VALUE',c_string(origin['function'])).replace('LINE_VALUE',str(origin['line']))
 storage_ref=save('debug-storage.Rust.inc',record_source)
 old_binding=(B12/'debug.binding.C.inc').read_text()
 start=old_binding.index('struct ddebug ');end=old_binding.index('\n};',start)+3
 old_storage=old_binding[start:end]
 new_storage='extern struct ddebug f03_util_register_desc_debug_v1[1];'
 assert old_storage.count('f03_util_register_desc_debug_v1[1]')==1
 new_binding=old_binding[:start]+new_storage+old_binding[end:]
 save('debug.binding.C.inc',new_binding)
 baseline_c=(BASE/'kernel/syscall.c').read_text();baseline_r=(BASE/'kernel/rust/syscall_policy.rs').read_text()
 old_preimages={row['path']:row for row in ready['source_preimages']}
 for relative in ['kernel/syscall.c','kernel/rust/syscall_policy.rs']:
  expected=old_preimages[str(ROOT/relative)];actual=ref(BASE/relative)
  assert {k:actual[k] for k in ['bytes','sha256']}=={k:expected[k] for k in ['bytes','sha256']}
 original=(B12/'original.C.inc').read_text().rstrip('\n');paired=(B12/'paired.C.inc').read_text().rstrip('\n')
 assert baseline_c.count(original)==1
 predecessor_c=baseline_c.replace(original,paired,1)
 logger=(B12/'util-desc-log-entry.Rust.inc').read_text();predecessor_r=baseline_r+'\n'+logger
 assert predecessor_c.count(old_storage)==1
 candidate_c=predecessor_c.replace(old_storage,new_storage,1);candidate_r=predecessor_r+'\n'+record_source
 assert candidate_c.count(new_storage)==1 and old_storage not in candidate_c
 assert candidate_r.count('pub static mut f03_util_register_desc_debug_v1:')==1
 assert candidate_r.count('pub unsafe extern "C" fn syscall_util_register_desc_log_bridge(')==1
 writes=[]
 for relative,before,after in [('kernel/syscall.c',predecessor_c,candidate_c),('kernel/rust/syscall_policy.rs',predecessor_r,candidate_r)]:
  pre=save(Path('predecessor-BODY12')/relative,before);post=save(Path('candidate')/relative,after)
  patch=save(Path('patches-from-BODY12')/(relative.replace('/','__')+'.patch'),''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative)))
  writes.append(dict(relative=relative,preimage=pre,postimage=post,patch=patch,canonical_write_authority=None))
 save('SOURCE-MAP-FROM-BODY12.json',dict(scope=SCOPE,status='PRIVATE_DELTA_DEPENDS_ON_ACCEPTED_BODY12_SELECTION',runtime_authority=None,writes=writes,
  exact_dependency=ref(B12/'SOURCE-READY.json'),frozen118_source_reference=str(BASE),
  code='BODY12 logger unchanged exactly once; only C storage definition becomes extern plus Rust-owned static data.',new_function_ports=0,new_C_storage_definitions=0))
 # Fixtures retain the actual C lexical function, now with the real /src file
 # origin from the accepted registry. The existing logger object is reused.
 startline=ready['line_state']['start_physical']+ready['line_state']['offset']
 save('original.fixture.C.inc','#line '+str(startline)+' "'+origin['file']+'"\n'+(B12/'original.C.inc').read_text())
 save('storage-consumer.C.inc','extern struct ddebug f03_util_register_desc_debug_v1[1];\nstatic const unsigned EXPECTED_DEBUG_LINE='+str(origin['line'])+';\nstatic const char EXPECTED_SOURCE_FILE[]="'+origin['file']+'";\n')
 layout=B12/'debug-layout.reused.Rust.inc';save('debug-layout.reused.Rust.inc',layout.read_text())
 save('lib.storage.rs','''#![no_std]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod debug {include!("debug-layout.reused.Rust.inc");}
include!("debug-storage.Rust.inc");
''')
 old_object=B12/'output-STANDING-1/callbacks.o';old_object_ref=ref(old_object)
 assert '--emit=obj='+str(old_object) in result['commands'][0]['argv']
 plan=json.loads((B12/'FIXED-HOST-COMMAND-PLAN.json').read_text())
 for command in plan['commands']:
  command['argv']=[arg.replace(str(B12),str(HERE)) for arg in command['argv']]
  command['purpose']=SCOPE+' New Rust debug storage and existing BODY12 Rust logger object with genuine C metadata/flag consumer; local mocked prints only, no registration/syscall/MM/IKC/hardware/locks/root/native/Docker/guest effects.'
 args=plan['commands'][0]['argv'];args[args.index('f03_util_desc_logger')]='f03_util_desc_debug_storage'
 args=[arg.replace(str(HERE/'output-STANDING-1/callbacks.o'),str(HERE/'output-STANDING-1/debug-storage.o')).replace(str(HERE/'lib.fixture.rs'),str(HERE/'lib.storage.rs')) for arg in args];plan['commands'][0]['argv']=args
 args=plan['commands'][1]['argv'];position=args.index(str(HERE/'output-STANDING-1/callbacks.o'));args[position]=str(old_object);args.insert(position+1,str(HERE/'output-STANDING-1/debug-storage.o'))
 plan['commands'][0]['label']='00-new-Rust-owned-debug-record-object';plan['commands'][1]['label']='01-genuine-C-consumer-reuse-BODY12-logger-link';plan['commands'][2]['label']='02-C-updater-existing-Rust-logger-storage-ABI'
 plan['expected_stdout']='PASS Rust-owned util-desc debug storage; ABI10 reused; 256 C/Rust flag pairs; exact symbol/metadata/flags/full-record oracles'
 plan['requires']='Actual parent BODY13 ordinary HOST followup plus inherited standing bounds, exact new source/header/tool and reused BODY12 object bindings, current guardian/account/tightcaps eachcommand.'
 save('FIXED-HOST-COMMAND-PLAN.json',plan)
 inputs=[B12/'SOURCE-READY.json',B12/'output-STANDING-1/ACTUAL-HOST-RESULT.json',old_object,layout,registry_path,ROOT/'kernel/rust/debug.rs',ROOT/'lib/include/ihk/debug.h',ROOT/'lib/include/types.h',ROOT/'kernel/include/kmsg.h']
 report=dict(scope=SCOPE,author='/root/f03_next',status='PRIVATE_RUST_DEBUG_STORAGE_READY_FOR_STANDING_HOST_PLAN',
  selected_storage='f03_util_register_desc_debug_v1[1]',predecessor_C_bytes=32,expected_Rust_storage_bytes=32,new_function_ports=0,
  dependency='BODY12 selection must be composed first; packet supplies exact private delta/full postimages, not canonical integration or a duplicate logger body.',
  dependency_map=ref(HERE/'SOURCE-MAP-FROM-BODY12.json'),unchanged_logger=ref(B12/'util-desc-log-entry.Rust.inc'),reused_actual_BODY12_object=old_object_ref,
  actual_origin=origin,origin_reference=ref(registry_path),source_preimages=[ref(p) for p in inputs],
  expected=dict(ABI_words_reused=10,C_Rust_flag_pairs=256,record_size=32,record_alignment=8,record_section='__verbose'),
  storage_source=storage_ref,registry_count_change=0,original_callback_symbol_and_ABI_unchanged=True,
  actual_compilers=0,actual_fixture_runs=0,canonical_writes=0,default=0,native=0,file_closure=0,
  other_packets='BODY3-12 and reviewed cumulative remain unchanged; held domains/credits/window/scratch21/permanent27:4 preserved.')
 report['files']=[ref(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name not in ['SOURCE-READY.json','SOURCE-CHECKS.json','WORKER-RECORDED-STANDING-HOST-AUTHORIZATION.json','run_granted_host_once.py']]
 save('SOURCE-READY.json',report)
 auth=dict(scope=SCOPE,author='/root/f03_next',decision='WORKER_RECORDED_ACTUAL_PARENT_STANDING_HOST_AUTHORIZATION',
  authority='Actual new /root followup_task for BODY13 requests the remaining debug-storage port and ordinary HOST under existing limits; inherited standing <=4 fixed commands and one obvious fixture correction apply. Worker-authored record, not a Root grant.',
  limits_from_parent='CPU6/jobs1/AS2GiB/CPU60/wall90, current actual guardian/account/tightcaps/bindings percommand; new data only and reused logger; no heavy/root/Docker/native/locks/network.',
  source_ready=ref(HERE/'SOURCE-READY.json'),command_plan=ref(HERE/'FIXED-HOST-COMMAND-PLAN.json'),actual_source_preimage_bindings=report['files']+report['source_preimages'],actual_tools=[ref(Path(plan['commands'][i]['argv'][0]).resolve()) for i in [0,1]],
  output=str(HERE/'output-STANDING-1'),cpu=6,jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90,maximum_commands=3,parent_maximum_commands=4,
  actual_cutoffs=[1793253600,1035704.5689393478,1051042.6959879305],credit_run_id='7f4af94a83b14cc08f97401f5891d965',cumulative_credit_ceiling='57774.852125',cumulative_spent_floor='22812.3311',source_qualification_outside_runtime_nonce_ledger=True)
 save('WORKER-RECORDED-STANDING-HOST-AUTHORIZATION.json',auth)
 oldauth=ref(B12/'WORKER-RECORDED-STANDING-HOST-AUTHORIZATION.json')['sha256'];runner=(B12/'run_granted_host_once.py').read_text().replace("GRANT_SHA = '"+oldauth+"'","GRANT_SHA = '"+ref(HERE/'WORKER-RECORDED-STANDING-HOST-AUTHORIZATION.json')['sha256']+"'")
 runner=runner.replace('body12_reviewed_readonly_guardian','body13_reviewed_readonly_guardian').replace('PASS_THREE_COMMAND_HOST_ABI10_AND_200_PAIRS','PASS_THREE_COMMAND_HOST_RUST_DEBUG_STORAGE_AND_256_FLAG_PAIRS')
 save('run_granted_host_once.py',runner)
 checks=dict(scope=SCOPE,status='PASS_PRIVATE_STORAGE_DELTA_AND_REUSED_PREFIX_BINDINGS_NO_CHILD_STARTED',source_ready=auth['source_ready'],worker_authorization=ref(HERE/'WORKER-RECORDED-STANDING-HOST-AUTHORIZATION.json'),guard_calls=0)
 save('SOURCE-CHECKS.json',checks);print(json.dumps(checks))
if __name__=='__main__':main()
