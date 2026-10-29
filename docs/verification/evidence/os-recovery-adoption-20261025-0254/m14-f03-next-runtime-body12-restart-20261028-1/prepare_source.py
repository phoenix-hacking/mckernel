#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private callback source/ABI and fixed ordinary HOST plan preparation only.
"""
import difflib,hashlib,json,struct
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=Path('/home/holden/mckernel')
E=HERE.parent
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def function(source,marker):
 assert source.count(marker)==1,marker
 start=source.index(marker);end=source.index('{',start)+1;depth=1
 while depth:depth+=(source[end]=='{')-(source[end]=='}');end+=1
 return start,end,source[start:end]+'\n'
def main():
 cp=ROOT/'kernel/syscall.c';rp=ROOT/'kernel/rust/syscall_policy.rs';dp=ROOT/'kernel/rust/debug.rs'
 c,r,debug=cp.read_text(),rp.read_text(),dp.read_text()
 assert 'mod f03_util_register_desc_logger_v1 {' not in r
 start,end,original=function(c,'void\nsyscall_util_register_desc_log_bridge(')
 reset_at=c.rfind('#line ',0,start);reset=int(c[reset_at:c.index('\n',reset_at)].split()[1])
 assert c[reset_at-7:reset_at]=='#endif\n' and '#line' not in c[c.index('\n',reset_at)+1:start]
 offset=reset-(c[:reset_at].count('\n')+1)-1;startline=c[:start].count('\n')+1;closeline=c[:end].count('\n')+1
 sites=[number for number,line in enumerate(original.splitlines(),startline) if 'dkprintf(' in line];assert len(sites)==1
 debug_line=sites[0]+offset
 binding=('/* '+SCOPE+' */\nstruct ddebug __attribute__((aligned(8),section("__verbose"))) f03_util_register_desc_debug_v1[1]={\n'+
  '    {.file=__FILE__,.func="syscall_util_register_desc_log_bridge",.line='+str(debug_line)+',.flags=DDEBUG_DEFAULT}\n};\n'+
  'extern void syscall_util_register_desc_log_bridge(int,unsigned long);\n')
 (HERE/'debug.binding.C.inc').write_text(binding)
 paired='#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\n'+binding+'#else\n#line '+str(startline+offset)+'\n'+original+'#endif\n#line '+str(closeline+offset)+'\n'
 postc=c[:start]+paired+c[end:]
 marker='#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nvoid reset_cputime(void);'
 old_next=c[:c.index(marker,end)].count('\n')+1+offset;directive=postc.index('#line '+str(closeline+offset)+'\n',start)
 new_next=closeline+offset+(postc[:postc.index(marker,start)].count('\n')+1)-(postc[:directive].count('\n')+1)-1
 assert new_next==old_next
 (HERE/'original.C.inc').write_text(original);(HERE/'paired.C.inc').write_text(paired)
 (HERE/'original.fixture.C.inc').write_text('#line '+str(startline+offset)+' "kernel/syscall.c"\n'+original)
 (HERE/'binding.fixture.C.inc').write_text('#line 1 "kernel/syscall.c"\n'+binding+'static const unsigned EXPECTED_DEBUG_LINE='+str(debug_line)+';\n')
 entry=(HERE/'util-desc-log-entry.Rust.inc').read_text()
 for relative,before,postimage in [('kernel/syscall.c',c,postc),('kernel/rust/syscall_policy.rs',r,r+'\n'+entry)]:
  (HERE/(Path(relative).name+'.patch')).write_text(''.join(difflib.unified_diff(before.splitlines(True),postimage.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative)))
 _,_,layout=function(debug,'pub struct Ddebug {');(HERE/'debug-layout.reused.Rust.inc').write_text('#[repr(C)]\n'+layout)
 (HERE/'abi.current.rs').write_bytes((ROOT/'kernel/rust/abi.rs').read_bytes())
 _,_,caller=function(r,'pub unsafe extern "C" fn sys_util_register_desc(')
 assert 'syscall_util_register_desc_log_bridge(tid, desc);' in caller
 assert 'fn syscall_util_register_desc_log_bridge(tid: CInt, desc: CULong);' in r
 assert 'pub unsafe extern "C" fn syscall_util_register_desc_log_bridge(' not in r
 (HERE/'caller-existing.Rust.inc').write_text(caller)
 pairs=[('sizeof(struct ddebug)','core::mem::size_of::<Ddebug>()'),('__alignof__(struct ddebug)','core::mem::align_of::<Ddebug>()'),
  ('__builtin_offsetof(struct ddebug,file)','core::mem::offset_of!(Ddebug,file)'),('__builtin_offsetof(struct ddebug,func)','core::mem::offset_of!(Ddebug,func)'),
  ('__builtin_offsetof(struct ddebug,fmt)','core::mem::offset_of!(Ddebug,fmt)'),('__builtin_offsetof(struct ddebug,fmt)+sizeof(const char *)','core::mem::offset_of!(Ddebug,line_flags)'),
  ('sizeof(int)','core::mem::size_of::<CInt>()'),('sizeof(unsigned long)','core::mem::size_of::<CULong>()'),
  ('sizeof(descriptor_logger_t)','core::mem::size_of::<unsafe extern "C" fn(CInt,CULong)>()'),('sizeof f03_util_register_desc_debug_v1/sizeof(struct ddebug)','1')]
 (HERE/'abi.C.inc').write_text('static const unsigned long ABI_C[10]={\n'+',\n'.join('    '+a for a,b in pairs)+'\n};\n')
 witness='\n    #[no_mangle]\n    pub static F03_UTIL_DESC_LOG_ABI:[CULong;10]=[\n'+',\n'.join('        ('+b+') as CULong' for a,b in pairs)+'\n    ];\n'
 (HERE/'entry.fixture.Rust.inc').write_text(entry.rstrip()[:-1]+witness+'}\n')
 (HERE/'lib.fixture.rs').write_text('''#![no_std]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[path="abi.current.rs"] mod abi;
mod debug {include!("debug-layout.reused.Rust.inc");}
mod policy {
 unsafe extern "C" {fn kprintf(format:*const i8,...)->crate::abi::CInt;}
 include!("entry.fixture.Rust.inc");
}
''')
 prior=E/'m14-f03-next-runtime-body11-restart-20261028-1';plan=json.loads((prior/'FIXED-HOST-COMMAND-PLAN.json').read_text())
 for command in plan['commands']:
  command['argv']=[arg.replace(str(prior),str(HERE)) for arg in command['argv']]
  command['purpose']=SCOPE+' Genuine debug metadata and scalar mocked prints only; no actual registration/thread-lookup/descriptor-memory/syscall/hardware/MM/IKC/locks/root/native/Docker/guest effects.'
 argv=plan['commands'][0]['argv'];argv[argv.index('f03_counter_allocate')]='f03_util_desc_logger'
 plan['commands'][0]['label']='00-existing-debug-ABI-Rust-original-global-logger';plan['commands'][1]['label']='01-genuine-debug-macro-original-C-lexical-oracle-link';plan['commands'][2]['label']='02-util-descriptor-log-scalar-and-metadata-equivalence'
 plan['expected_stdout']='PASS util-desc-log genuine-header ABI10; exact lexical metadata pair; 200 C/Rust pairs; debug-gate/int-TID/unsigned-descriptor/global-symbol/full-record oracles'
 plan['requires']='Actual parent BODY12 followup ordinary HOST authorization under inherited standing limits, saved checked source/header/tool bindings and current guardian/account/tightcaps percommand.'
 (HERE/'FIXED-HOST-COMMAND-PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
 accepted=json.loads((E/'CURRENT116-ACCEPTED-ARTIFACT-AND-CURRENTFREE.json').read_text())['actual_new_default_artifact']['generic_C'];assert ref(Path(accepted['path']))==accepted
 raw=Path(accepted['path']).read_bytes();header=struct.unpack_from('<16sHHIQQQIHHHHHH',raw);sections=[struct.unpack_from('<IIQQQQIIQQ',raw,header[6]+i*header[11]) for i in range(header[12])];found=[]
 for section in sections:
  if section[1]!=2:continue
  names=sections[section[6]];names=raw[names[4]:names[4]+names[5]]
  for position in range(section[4],section[4]+section[5],section[9]):
   n,info,other,index,value,size=struct.unpack_from('<IBBHQQ',raw,position)
   if info&15==2 and 0<index<len(sections) and sections[index][2]&2 and names[n:names.index(0,n)]==b'syscall_util_register_desc_log_bridge':found.append(size)
 assert found==[64]
 inputs=[cp,rp,dp,ROOT/'kernel/rust/abi.rs',ROOT/'lib/include/ihk/debug.h',ROOT/'kernel/include/kmsg.h',ROOT/'lib/include/types.h']
 assert cp.read_text()==c and rp.read_text()==r and dp.read_text()==debug,'source changed during preparation'
 report=dict(scope=SCOPE,author='/root/f03_next',status='PRIVATE_UTIL_DESCRIPTOR_LOGGER_READY_FOR_STANDING_HOST_PLAN',selected_target='syscall_util_register_desc_log_bridge',CURRENT116_selected_C_bytes=64,selected_artifact=accepted,source_preimages=[ref(p) for p in inputs],
  reused_Rust='Existing Ddebug layout and accepted raw flag-read idiom; caller declaration/global callback ABI retained; no complete duplicate formatter found.',
  original_global_symbol_preserved=True,caller_unchanged=ref(HERE/'caller-existing.Rust.inc'),
  behavior='One any-nonzero8bit debug gate; exact sys_util_register_desc text/format; copied int TID and unsigned-long descriptor; no lookup, pointer dereference, registration write or new error/resource behavior.',
  fixture_link_alias='Only original C assembly link name changes; C identifier/__func__/original body unchanged, Rust retains real global callback name.',
  metadata=dict(original_records=1,candidate_records=1,logical_line=debug_line,function='syscall_util_register_desc_log_bridge',fmt=None,flags='DDEBUG_DEFAULT',production_registry389='Actual matching linked proof OPEN'),
  line_state=dict(start_physical=startline,close_physical=closeline,offset=offset,original_successor=old_next,candidate_successor=new_next),expected=dict(ABI_words=10,C_Rust_pairs=200),
  new_C_runtime_functions=0,predicted_C_functions_removed=1,actual_compilers=0,actual_fixture_runs=0,canonical_writes=0,default=0,native=0,file_closure=0,
  excludes='All prior BODY/cumulative packets frozen; all held request/endpoint/credential/signal/undefined domains remain excluded.')
 report['files']=[ref(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name not in ['SOURCE-READY.json','SOURCE-CHECKS.json','WORKER-RECORDED-STANDING-HOST-AUTHORIZATION.json','run_granted_host_once.py']]
 (HERE/'SOURCE-READY.json').write_text(json.dumps(report,indent=2)+'\n')
 auth=dict(scope=SCOPE,author='/root/f03_next',decision='WORKER_RECORDED_ACTUAL_PARENT_STANDING_HOST_AUTHORIZATION',
  authority='Actual new /root followup_task to /root/f03_next for BODY12 authorizes ordinary HOST tests under existing profile/aggregate/actual-guard limits; inherited standing authorization retains <=4 fixed commands and one obvious fixture correction. Worker-owned record only, not Root-authored grant.',
  limits_from_parent='CPU6/jobs1/AS2GiB/CPU60/wall90 within aggregate limits; current guardian/account/caps and exact bindings eachcommand; no actual root/Docker/native/locks/network; no semantic/second failure retry.',
  source_ready=ref(HERE/'SOURCE-READY.json'),command_plan=ref(HERE/'FIXED-HOST-COMMAND-PLAN.json'),actual_source_preimage_bindings=report['files']+report['source_preimages'],actual_tools=[ref(Path(plan['commands'][i]['argv'][0]).resolve()) for i in [0,1]],output=str(HERE/'output-STANDING-1'),cpu=6,jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90,maximum_commands=3,parent_maximum_commands=4,
  actual_cutoffs=[1793253600,1035704.5689393478,1051042.6959879305],credit_run_id='7f4af94a83b14cc08f97401f5891d965',cumulative_credit_ceiling='57774.852125',cumulative_spent_floor='22812.3311',source_qualification_outside_runtime_nonce_ledger=True)
 authpath=HERE/'WORKER-RECORDED-STANDING-HOST-AUTHORIZATION.json';authpath.write_text(json.dumps(auth,indent=2)+'\n')
 oldauth=ref(prior/'WORKER-RECORDED-STANDING-HOST-AUTHORIZATION.json')['sha256'];runner=(prior/'run_granted_host_once.py').read_text().replace("GRANT_SHA = '"+oldauth+"'","GRANT_SHA = '"+ref(authpath)['sha256']+"'")
 runner=runner.replace('body11_reviewed_readonly_guardian','body12_reviewed_readonly_guardian').replace('PASS_THREE_COMMAND_HOST_ABI7_AND_72_PAIRS','PASS_THREE_COMMAND_HOST_ABI10_AND_200_PAIRS')
 (HERE/'run_granted_host_once.py').write_text(runner)
 checks=dict(scope=SCOPE,status='PASS_SOURCE_GLOBAL_ABI_METADATA_AND_FIXED_BINDINGS_NO_CHILD_STARTED',source_ready=auth['source_ready'],worker_authorization=ref(authpath),runner=ref(HERE/'run_granted_host_once.py'),guard_calls=0)
 (HERE/'SOURCE-CHECKS.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks))
if __name__=='__main__':main()
