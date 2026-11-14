#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private source preparation only; standing parent authority is recorded by worker.
"""
import difflib,hashlib,json,struct,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=Path('/home/holden/mckernel')
E=HERE.parent
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def function(s,marker):
 assert s.count(marker)==1,marker
 a=s.index(marker);e=s.index('{',a)+1;depth=1
 while depth:depth+=(s[e]=='{')-(s[e]=='}');e+=1
 return a,e,s[a:e]+'\n'
def declaration(s,marker):
 a=s.index(marker);return s[a:s.index(';',a)+1]+'\n'
def main():
 cp=ROOT/'kernel/syscall.c';rp=ROOT/'kernel/rust/syscall_policy.rs'
 c,r=cp.read_text(),rp.read_text()
 assert 'fn f03_perf_event_allocate_v1(' not in r
 start=c.index('static int mc_perf_event_alloc(')
 _,end,_=function(c,'static int\nperf_event_open_alloc_event_bridge(void **event_out, void *attr)')
 original=c[start:end]+'\n'
 last=c.rfind('#line ',0,start);assert c[last:c.index('\n',last)]=='#line 21418' and c[last-7:last]=='#endif\n'
 offset=21418-(c[:last].count('\n')+1)-1
 startline=c[:start].count('\n')+1;closeline=c[:end].count('\n')+1
 binding=(HERE/'perf-allocation-binding.C.inc').read_text()
 selected='#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_SYNC_CHILD_EVENT)\n'
 paired=selected+binding+'#else\n#line '+str(startline+offset)+'\n'+original+'#endif\n#line '+str(closeline+offset)+'\n'
 postc=c[:start]+paired+c[end:]
 nextmarker='static int\nperf_event_open_attr_freq_bridge'
 expected_next=c[:c.index(nextmarker,end)].count('\n')+1+offset
 anchor=postc.index('#line '+str(closeline+offset)+'\n',start)
 actual_next=closeline+offset+(postc[:postc.index(nextmarker,start)].count('\n')+1)-(postc[:anchor].count('\n')+1)-1
 assert expected_next==actual_next
 (HERE/'entry-original.C.inc').write_text(original)
 (HERE/'entry-paired.C.inc').write_text(paired)
 rust_names=['perf_event_alloc_init_body_result','perf_event_alloc_map_body_result','perf_event_alloc_body_result']
 rust_bodies=[];c_bodies=[]
 for name in rust_names:
  # Include the exact original allow attribute with each original Rust body.
  _,_,body=function(r,'pub unsafe extern "C" fn '+name+'(')
  rust_bodies.append('#[no_mangle]\n#[allow(clippy::too_many_arguments)]\n'+body)
  _,_,body=function(c,'SYSCALL_POLICY_HELPER_SCOPE long\n'+name+'(')
  c_bodies.append(body)
 (HERE/'allocator-original.C.inc').write_text('\n'.join(c_bodies))
 original_rust='\n'.join(rust_bodies)
 (HERE/'allocator-original.Rust.inc').write_text(original_rust)
 old='''        extra_config = hw_cache_extra_reg_map(attr_config);
        hw_cache_event_map(attr_config)'''
 new='''        let mapped = hw_cache_event_map(attr_config);
        extra_config = hw_cache_extra_reg_map(attr_config);
        mapped'''
 assert r.count(old)==1 and original_rust.count(old)==1
 fixed_rust=original_rust.replace(old,new,1)
 (HERE/'allocator-candidate.Rust.inc').write_text(fixed_rust)
 entry=(HERE/'perf-alloc-entry.Rust.inc').read_text()
 postrust=r.replace(old,new,1)+'\n'+entry
 for path,before,after in [('kernel/syscall.c',c,postc),('kernel/rust/syscall_policy.rs',r,postrust)]:
  (HERE/(Path(path).name+'.patch')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+path,tofile='b/'+path)))
 # Reuse the entire genuine full-event layout module and attribute ABI verbatim.
 _,_,layout=function(r,'mod f03_sync_child_layout_v2 {')
 (HERE/'event-layout.reused.Rust.inc').write_text('#[cfg(f03_sync_child_event_candidate)]\n'+layout)
 xp=ROOT/'kernel/rust/x86_perfctr.rs';x=xp.read_text()
 _,_,extra=function(x,'pub struct HwPerfEventExtra {')
 (HERE/'extra-layout.reused.Rust.inc').write_text('#[repr(C)]\n'+extra)
 (HERE/'attr-layout.reused.rs').write_bytes((ROOT/'kernel/rust/f03_perf_event_attr_abi.rs').read_bytes())
 (HERE/'abi.current.rs').write_bytes((ROOT/'kernel/rust/abi.rs').read_bytes())
 names=['SyscallPolicyAllocFn','SyscallMckfdFreeFn','SyncChildAtomic64SetFn','PerfEventMapFn','PerfEventValidateFn','PerfExtraRegIdFn','PerfExtraRegMsrFn','PerfExtraRegIdxFn','PerfHwEventInitFn']
 rust_types='\n'.join(line for line in r.splitlines() if any(line.startswith('type '+n+' ') for n in names))+'\n'
 constants='\n'.join(line for line in r.splitlines() if line.startswith(('const EINVAL:','const ENOMEM:','const ENOENT:')))+'\n'
 (HERE/'provider-types.Rust.inc').write_text(rust_types+constants)
 c_names=['syscall_policy_alloc_fn_t','syscall_mckfd_free_fn_t','sync_child_atomic64_set_fn_t','perf_event_map_fn_t','perf_event_validate_fn_t','perf_extra_reg_id_fn_t','perf_extra_reg_msr_fn_t','perf_extra_reg_idx_fn_t','perf_hw_event_init_fn_t']
 typedefs=[]
 for name in c_names:
  position=c.index('(*'+name+')');a=c.rfind('typedef ',0,position)
  typedefs.append(c[a:c.index(';',position)+1]+'\n')
 (HERE/'provider-types.C.inc').write_text(''.join(typedefs))
 # Each word is independently compiled from the real C header and reused Rust layout.
 pairs=[]
 def add(c_expr,r_expr):pairs.append((c_expr,r_expr))
 for ct,rt in [('struct mc_perf_event','FullMcPerfEvent'),('struct perf_event_attr','PerfEventAttr')]:
  add('sizeof('+ct+')','size_of::<'+rt+'>()');add('__alignof__('+ct+')','core::mem::align_of::<'+rt+'>()')
 for cf,rf in [('type','type_'),('config','config'),('sample_period','sampling')]:add('__builtin_offsetof(struct perf_event_attr,'+cf+')','offset_of!(PerfEventAttr,'+rf+')')
 add('__builtin_offsetof(struct perf_event_attr,read_format)+sizeof(unsigned long)','offset_of!(PerfEventAttr,flags)')
 fields=['attr','group_entry','sibling_list','sample_freq','nr_siblings','count','child_count_total','parent','hw.sample_period','hw.last_period','hw.period_left','use_invariant_tsc','hw_config','hw_config_ext','extra_reg.config','extra_reg.reg','extra_reg.idx']
 for f in fields:
  rf='offset_of!(FullMcPerfEvent,'+f+')'
  if '.' in f:
   parent,child=f.split('.');rt='HwPerfEvent' if parent=='hw' else 'HwPerfEventExtra';rf='offset_of!(FullMcPerfEvent,'+parent+')+offset_of!('+rt+','+child+')'
  add('__builtin_offsetof(struct mc_perf_event,'+f+')',rf)
 add('sizeof(struct f03_perf_allocation_binding)','size_of::<PerfAllocationBinding>()');add('__alignof__(struct f03_perf_allocation_binding)','core::mem::align_of::<PerfAllocationBinding>()')
 fields=['alloc_flags','hardware_type','cache_type','raw_type','reference_cycles','allocate','release','atomic_set','hardware_map','cache_map','cache_extra_map','raw_map','validate','extra_id','extra_msr','extra_index','initialize']
 for f in fields:add('__builtin_offsetof(struct f03_perf_allocation_binding,'+f+')','offset_of!(PerfAllocationBinding,'+f+')')
 for c_expr,r_expr in [('IHK_MC_AP_NOWAIT','2'),('PERF_TYPE_HARDWARE','0'),('PERF_TYPE_HW_CACHE','3'),('PERF_TYPE_RAW','4'),('PERF_COUNT_HW_REF_CPU_CYCLES','9'),('sizeof(unsigned long)','size_of::<CULong>()'),('sizeof(long)','size_of::<CLong>()'),('sizeof(int)','size_of::<CInt>()')]:add(c_expr,r_expr)
 assert len(pairs)==52,len(pairs)
 (HERE/'abi.C.inc').write_text('static const unsigned long ABI_C[52]={\n'+',\n'.join('    '+a for a,b in pairs)+'\n};\n')
 witness='\n    #[no_mangle]\n    pub static F03_PERF_ALLOCATION_ABI:[CULong;52]=[\n'+',\n'.join('        ('+b+') as CULong' for a,b in pairs)+'\n    ];\n'
 (HERE/'entry.fixture.Rust.inc').write_text(entry.rstrip()[:-1]+witness+'}\n')
 (HERE/'lib.fixture.rs').write_text('''#![no_std]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[path="abi.current.rs"] mod abi;
#[path="attr-layout.reused.rs"] mod f03_perf_attr_callbacks;
mod x86_perfctr { use crate::abi::{CULong,CInt};include!("extra-layout.reused.Rust.inc"); }
mod policy {
 use core::{ffi::c_void,ptr::{read_volatile,write_volatile}};
 use crate::abi::{CInt,CLong,CULong,SizeT,AbiListHead};
 include!("provider-types.Rust.inc");
 unsafe fn field_ptr<T>(base:*mut u8,offset:SizeT)->*mut T { unsafe{base.add(offset).cast()} }
 include!("allocator-candidate.Rust.inc");
 include!("event-layout.reused.Rust.inc");
 include!("entry.fixture.Rust.inc");
}
''')
 oldbase=E/'m14-f03-next-runtime-body4-restart-20261028-1'
 plan=json.loads((oldbase/'FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json').read_text())
 for command in plan['commands']:
  command['argv']=[v.replace(str(oldbase),str(HERE)) for v in command['argv']]
  command['purpose']=SCOPE+' All allocation/atomic/event-map/hardware callbacks are local HOST mocks; no actual MM/syscall/IKC/hardware/root/native/Docker/guest effects.'
 args=plan['commands'][0]['argv'];args[args.index('f03_util_profile')]='f03_perf_allocation_entry';args[1:1]=['--cfg','f03_sync_child_event_candidate']
 plan['commands'][0]['label']='00-reused-layout-allocator-new-Rust-entry'
 plan['commands'][1]['label']='01-genuine-header-verbatim-C-oracle-link'
 plan['commands'][2]['label']='02-perf-allocation-functional-equivalence'
 plan['expected_stdout']='PASS perf-allocation genuine-header ABI52; 1152 C/Rust pairs plus 4 null-boundary calls; ordered provider/error/publication/free/full-byte oracles'
 plan['status']='WORKER_FIXED_PLAN_UNDER_ACTUAL_PARENT_STANDING_HOST_AUTHORIZATION';plan['executed']=False
 plan['requires']='Actual parent followup_task standing ordinary HOST authorization for body5, saved source/header/tool bindings and fresh per-command guardian/account/caps; no Root-authored grant file is claimed.'
 (HERE/'FIXED-HOST-COMMAND-PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
 accepted=E/'CURRENT116-ACCEPTED-ARTIFACT-AND-CURRENTFREE.json'
 selected=json.loads(accepted.read_text())['actual_new_default_artifact']['generic_C']
 assert ref(Path(selected['path']))==selected
 data=Path(selected['path']).read_bytes();h=struct.unpack_from('<16sHHIQQQIHHHHHH',data);ss=[struct.unpack_from('<IIQQQQIIQQ',data,h[6]+i*h[11]) for i in range(h[12])]
 found=[]
 for sec in ss:
  if sec[1]!=2:continue
  names=ss[sec[6]];names=data[names[4]:names[4]+names[5]]
  for pos in range(sec[4],sec[4]+sec[5],sec[9]):
   n,info,other,index,value,size=struct.unpack_from('<IBBHQQ',data,pos)
   if info&15==2 and index>0 and index<len(ss) and ss[index][2]&2 and names[n:names.index(0,n)]==b'perf_event_open_alloc_event_bridge':found.append(size)
 assert found==[318],found
 inputs=[cp,rp,ROOT/'kernel/rust/abi.rs',ROOT/'kernel/rust/x86_perfctr.rs',ROOT/'kernel/rust/f03_perf_event_attr_abi.rs',ROOT/'kernel/rust/f03_perf_attr_callbacks.rs',ROOT/'lib/include/mc_perf_event.h',ROOT/'lib/include/ihk/cpu.h',ROOT/'kernel/CMakeLists.txt',ROOT/'lib/include/types.h',ROOT/'ihk/cokernel/smp/x86_64/include/ihk/memconst.h']
 assert cp.read_text()==c and rp.read_text()==r,'source changed during preparation'
 report=dict(scope=SCOPE,author='/root/f03_next',status='PRIVATE_PERF_ALLOCATION_SOURCE_READY_FOR_STANDING_HOST_PLAN',
  selected_target='perf_event_open_alloc_event_bridge',CURRENT116_selected_C_bytes=318,selected_object=selected,
  source_preimages=[ref(p) for p in inputs],original_C_helpers=['mc_perf_event_alloc','perf_event_open_alloc_event_bridge'],
  reused_complete_Rust_bodies=rust_names,reused_layout='Existing full f03_sync_child_layout_v2 and genuine perf attribute/extra layout, unchanged',
  narrow_behavior_correction='Cache-event map before cache-extra map as verbatim original C; original Rust discrepancy and candidate retained separately',
  line_state=dict(original_successor=expected_next,candidate_successor=actual_next),
  expected=dict(ABI_words=52,C_Rust_pairs=1152,null_boundary_calls=4),
  actual_compiler_commands=0,actual_fixture_runs=0,canonical_writes=0,default=0,native=0,file_closure=0,
  explicit_C_debt='Existing allocation/free/atomic/map/validate/extra/hw-init providers remain original owners; this entry does not prove their actual hardware or allocator effects',
  excluded=['banked117/118','body3do_munmap','body4util_show','all held credential/request/endpoint/signal/service paths'],
  next_command_plan=ref(HERE/'FIXED-HOST-COMMAND-PLAN.json'))
 report['files']=[ref(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name not in ['SOURCE-READY.json','SOURCE-CHECKS.json','WORKER-RECORDED-STANDING-HOST-AUTHORIZATION.json','run_granted_host_once.py']]
 (HERE/'SOURCE-READY.json').write_text(json.dumps(report,indent=2)+'\n')
 source_ready=ref(HERE/'SOURCE-READY.json');plan_ref=ref(HERE/'FIXED-HOST-COMMAND-PLAN.json')
 tools=[ref(Path(plan['commands'][i]['argv'][0]).resolve()) for i in [0,1]]
 authorization=dict(scope=SCOPE,author='/root/f03_next',decision='WORKER_RECORDED_ACTUAL_PARENT_STANDING_HOST_AUTHORIZATION',
  authority='Actual new /root followup_task to /root/f03_next for body5; the parent explicitly authorized at most4 new fixed ordinary HOST commands after saved checked source/header/tool bindings. This worker record is not a Root-authored grant.',
  limits_from_parent='CPU6/jobs1/AS2GiB/CPU60s/wall90s percommand; genuine-header and all providers mocked; first semantic/oracle failure stops; one obvious fixture/compiler infrastructure correction allowed with original retained; no unchanged retry.',
  source_ready=source_ready,command_plan=plan_ref,actual_source_preimage_bindings=report['files']+report['source_preimages'],actual_tools=tools,
  output=str(HERE/'output-STANDING-1'),cpu=6,jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90,maximum_commands=3,parent_maximum_commands=4,
  actual_cutoffs=[1793253600,1035704.5689393478,1051042.6959879305],credit_run_id='7f4af94a83b14cc08f97401f5891d965',
  cumulative_credit_ceiling='57774.852125',cumulative_spent_floor='22812.3311',source_qualification_outside_runtime_nonce_ledger=True)
 # Exact command paths must match the actual new output namespace.
 for command in plan['commands']:command['argv']=[v.replace(str(HERE/'output-PENDING-ROOT'),authorization['output']) for v in command['argv']]
 (HERE/'FIXED-HOST-COMMAND-PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
 # Rebind source/plan manifest after the namespace correction, before any child.
 report['next_command_plan']=ref(HERE/'FIXED-HOST-COMMAND-PLAN.json')
 report['files']=[ref(Path(row['path'])) for row in report['files']]
 (HERE/'SOURCE-READY.json').write_text(json.dumps(report,indent=2)+'\n')
 authorization['source_ready']=ref(HERE/'SOURCE-READY.json');authorization['command_plan']=ref(HERE/'FIXED-HOST-COMMAND-PLAN.json')
 authorization['actual_source_preimage_bindings']=report['files']+report['source_preimages']
 auth_path=HERE/'WORKER-RECORDED-STANDING-HOST-AUTHORIZATION.json'
 auth_path.write_text(json.dumps(authorization,indent=2)+'\n')
 runner=(E/'m14-f03-next-runtime-body4-restart-20261028-1/run_granted_host_once.py').read_text()
 runner=runner.replace("GRANT = HERE/'ROOT-ORDINARY-HOST-GRANT.json'","GRANT = HERE/'WORKER-RECORDED-STANDING-HOST-AUTHORIZATION.json'")
 runner=runner.replace("GRANT_SHA = 'c9e3741f3f008be008d2019c23c9723865d54193cc59b820fe34b0d24a00b9e2'","GRANT_SHA = '"+ref(auth_path)['sha256']+"'")
 runner=runner.replace("'ROOT_BOUNDED_ORDINARY_HOST_MOCKED_FIXTURE_GRANT'","'WORKER_RECORDED_ACTUAL_PARENT_STANDING_HOST_AUTHORIZATION'")
 runner=runner.replace('body4_reviewed_readonly_guardian','body5_reviewed_readonly_guardian').replace('PASS_THREE_COMMAND_HOST_ABI26_AND_72_PAIRS','PASS_THREE_COMMAND_HOST_ABI52_AND_1152_PAIRS')
 (HERE/'run_granted_host_once.py').write_text(runner)
 checks=dict(scope=SCOPE,status='PASS_PRIVATE_SOURCE_BINDINGS_FIXED_PLAN_SAVED_NO_COMMAND_RUN',source_ready=authorization['source_ready'],worker_authorization=ref(auth_path),runner=ref(HERE/'run_granted_host_once.py'))
 (HERE/'SOURCE-CHECKS.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks))
if __name__=='__main__':main()
