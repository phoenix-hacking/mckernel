#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare private Rust ownership of BODY10's remaining original debug descriptor.
"""
import difflib,hashlib,json,re
from pathlib import Path
ROOT=Path('/home/holden/mckernel');HERE=Path(__file__).resolve().parent
E=ROOT/'docs/verification/evidence/os-recovery-adoption-20261025-0254'
PRIOR=E/'m14-f06-next-runtime-body10-restart-20261028-1'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def bind(path):
 data=path.read_bytes();return {'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def verify(row):
 assert bind(Path(row['path']))==row,row['path']
def dump(name,value):(HERE/name).write_text(json.dumps(value,indent=2)+'\n')
def patch(before,text):
 lines=before.splitlines(True);out=[];position=0;parts=text.splitlines(True);i=2
 while i<len(parts):
  match=re.match(r'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@',parts[i]);assert match,parts[i]
  start=int(match.group(1))-1;out+=lines[position:start];position=start;i+=1
  while i<len(parts)and not parts[i].startswith('@@ '):
   line=parts[i];assert line[0]in' +-'
   if line[0]in' -':assert lines[position]==line[1:],(position,line);position+=1
   if line[0]in' +':out.append(line[1:])
   i+=1
 out+=lines[position:];return ''.join(out)
pre=json.loads((PRIOR/'PREIMAGES.json').read_text())
for row in pre['all_nine_root118_canonical_postimages'].values():verify(row)
for name in ['abi.snapshot.rs','debug.type.snapshot.rs','original-Ddebug.rs.inc','original-prctl-log.c.inc','selected-descriptor.c.inc','oracle-prefix.c.inc','oracle-suffix.c.inc','abi_probe.c','f06_prctl_log.rs','ORIGINAL-DESCRIPTOR-IDENTITY.json','SELECTED-CURRENT116-ARCH-FRONTIER.json']:
 (HERE/name).write_bytes((PRIOR/name).read_bytes())
snapshots={};before10={};after11={}
for relative,name,patchname in [('arch/x86_64/kernel/syscall.c','BASE.syscall.c','arch-selection.patch'),('kernel/CMakeLists.txt','BASE.CMakeLists.txt','cmake-selection.PROPOSAL.patch'),('kernel/rust/lib.rs','BASE.lib.rs','rust-module-selection.patch')]:
 original=(ROOT/relative).read_text();assert original==(PRIOR/name).read_text()
 (HERE/name).write_text(original);snapshots[relative]={'canonical':bind(ROOT/relative),'snapshot':bind(HERE/name)}
 before10[relative]=patch(original,(PRIOR/patchname).read_text())
 (HERE/('BODY10.'+name)).write_text(before10[relative])
descriptor=(HERE/'selected-descriptor.c.inc').read_text()
declaration='extern struct ddebug arch_prctl_log_debug __asm__("mckernel_f06_arch_prctl_debug");\n'
(HERE/'selected-extern.c.inc').write_text(declaration)
old=before10['arch/x86_64/kernel/syscall.c'];assert old.count(descriptor)==1
after11['arch/x86_64/kernel/syscall.c']=old.replace(descriptor,'#ifdef MCKERNEL_RUST_F06_PRCTL_LOG_STORAGE\n'+declaration+'#else\n'+descriptor+'#endif\n')
old=before10['kernel/rust/lib.rs'];after11['kernel/rust/lib.rs']=old+'\n#[cfg(f06_prctl_log_storage_candidate)]\nmod f06_prctl_log_storage;\n'
old=before10['kernel/CMakeLists.txt'];anchor='\t\t\t\t    COMPILE_DEFINITIONS "MCKERNEL_RUST_F06_PRCTL_LOG")\n';assert old.count(anchor)==1
addition='''
\t\t\t\t# Same inherited descriptor; Rust owns its __verbose storage.
\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f06_prctl_log_storage_candidate")
\t\t\t\tlist(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_prctl_log_storage.rs")
\t\t\t\tset_property(SOURCE "${MCKERNEL_F06_C_SOURCE}" APPEND PROPERTY
\t\t\t\t    COMPILE_DEFINITIONS "MCKERNEL_RUST_F06_PRCTL_LOG_STORAGE")
'''
after11['kernel/CMakeLists.txt']=old.replace(anchor,anchor+addition)
for relative,name,patchname in [('arch/x86_64/kernel/syscall.c','syscall.c','arch-selection.patch'),('kernel/CMakeLists.txt','CMakeLists.txt','cmake-selection.PROPOSAL.patch'),('kernel/rust/lib.rs','lib.rs','rust-module-selection.patch')]:
 original=(ROOT/relative).read_text();result=after11[relative];(HERE/('candidate.'+name)).write_text(result)
 for path,before in [(patchname,original),('BODY11-DELTA-ON-BODY10.'+patchname,before10[relative])]:
  (HERE/path).write_text(''.join(difflib.unified_diff(before.splitlines(True),result.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative)))
 snapshots[relative]['proposed_postimage_sha256']=hashlib.sha256(result.encode()).hexdigest()
(HERE/'f06_prctl_log_storage.rs').write_text('''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Preserve the original image-lifetime ddebug record and existing C consumers.
use crate::debug::Ddebug;

// The existing F06 origin producer binds this filename to the actual C command.
// Ddebug's qualified x86 ABI is 32B/align8, with line:24 then flags:8. The
// initializer retains line669, flags0, null fmt and immutable NUL strings.
// C's original flag-update/exclusion contract remains in force; this introduces
// no lock, reference alias, or stronger synchronization/atomicity guarantee.
#[used]
#[link_section="__verbose"]
#[export_name="mckernel_f06_arch_prctl_debug"]
pub static mut ARCH_PRCTL_LOG_DEBUG:Ddebug=Ddebug {
    file:concat!(env!("MCKERNEL_F06_RT_SIGRETURN_ORIGIN"),"\\0").as_ptr().cast(),
    func:b"arch_prctl_log_bridge\\0".as_ptr().cast(),
    fmt:core::ptr::null(),
    line_flags:669,
};
''')
(HERE/'runtime_descriptor.rs').write_text('''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Actual Rust storage plus byte-identical BODY10 callback; no mocks here.
#![no_std]
#![allow(dead_code,unexpected_cfgs)]
#[path="abi.snapshot.rs"]mod abi;
#[path="debug.type.snapshot.rs"]mod debug;
#[path="f06_prctl_log_storage.rs"]mod storage;
#[path="f06_prctl_log.rs"]mod callback;
''')
identity=json.loads((HERE/'ORIGINAL-DESCRIPTOR-IDENTITY.json').read_text());origin=identity['one_selected_record_replaced']['file'];assert origin=='/src/arch/x86_64/kernel/syscall.c'
oracle=(HERE/'oracle-prefix.c.inc').read_text()+'\n'+declaration+'\nvoid arch_prctl_log_bridge(int event,int cpu,unsigned long value) __asm__("original_arch_prctl_log_bridge");\n#line 665 '+json.dumps(origin)+'\n'+(HERE/'original-prctl-log.c.inc').read_text()+'\n'+(HERE/'oracle-suffix.c.inc').read_text()
(HERE/'oracle.c').write_text(oracle)
consumer=(HERE/'abi_probe.c').read_text()+'\n'+declaration+'''
struct ddebug *fixture_selected_descriptor(void){return &arch_prctl_log_debug;}
void fixture_consumer_set_flags(unsigned int flags){arch_prctl_log_debug.flags=flags;}
unsigned int fixture_consumer_read_flags(void){return arch_prctl_log_debug.flags;}
void fixture_consumer_call(int event,int cpu,unsigned long value){arch_prctl_log_bridge(event,cpu,value);}
'''
(HERE/'consumer.c').write_text(consumer)
fixture=(PRIOR/'fixture.rs').read_text().replace('#[path="f06_prctl_log.rs"]mod candidate;','// Selected storage and callback are linked from the actual no_std Rust object.')
fixture=fixture.replace('    fn original_arch_prctl_log_bridge','    fn arch_prctl_log_bridge(event:i32,cpu:i32,value:u64);\n    fn fixture_selected_descriptor()->*mut Ddebug;\n    fn fixture_consumer_set_flags(flags:u32);\n    fn fixture_consumer_read_flags()->u32;\n    fn fixture_consumer_call(event:i32,cpu:i32,value:u64);\n    fn original_arch_prctl_log_bridge')
fixture=fixture.replace('fn original_c_and_rust_prctl_log(){','fn original_c_and_rust_descriptor_ownership(){')
fixture=fixture.replace('    let mut pairs=0;','''    assert_eq!(unsafe{fixture_selected_descriptor()},selected,"genuine C extern imports the one actual Rust owner");
    for flags in [0u32,1,2,128,255]{
        unsafe{fixture_consumer_set_flags(flags);}
        assert_eq!(unsafe{read_volatile(selected.cast::<u8>().add(27))},flags as u8);
        assert_eq!(unsafe{fixture_consumer_read_flags()},flags);
        unsafe{core::ptr::write_volatile(selected.cast::<u8>().add(27),255-flags as u8);}
        assert_eq!(unsafe{fixture_consumer_read_flags()},255-flags);
    }
    unsafe{fixture_consumer_set_flags(0);}
    let mut pairs=0;''')
fixture=fixture.replace('fixture_set_flags(selected,flags);','fixture_consumer_set_flags(flags);')
fixture=fixture.replace('        candidate::arch_prctl_log_bridge(event,cpu,value);','        unsafe{fixture_consumer_call(event,cpu,value);}')
fixture=fixture.replace('functional prctl-log original-C/Rust pairs=','functional actual-Rust-descriptor/C-consumer original-C/Rust pairs=')
(HERE/'fixture.rs').write_text(fixture)
plan10=json.loads((PRIOR/'FUTURE-HOST-COMMANDS.json').read_text());flags=plan10['commands'][0]['argv'][:-4];out=HERE/'future-host-output-1'
rustc=plan10['commands'][2]['argv'][0]
commands=[
 {'purpose':SCOPE+' Compile genuine Rust __verbose storage and unchanged BODY10 callback into one real no_std object.','argv':[rustc,'--edition=2021','--crate-type=lib','--emit=obj','-C','opt-level=2','-C','panic=abort',str(HERE/'runtime_descriptor.rs'),'-o',str(out/'runtime_descriptor.o')]},
 {'purpose':SCOPE+' Genuine header ABI, unchanged original C macro oracle and extern-only C consumer partial-link with the actual Rust object; all output is mocked.','argv':flags+['-std=gnu11','-fno-builtin','-save-temps','-r','-nostdlib','-no-pie','-I',str(HERE),'-x','c',str(HERE/'oracle.c'),str(HERE/'consumer.c'),'-x','none',str(out/'runtime_descriptor.o'),'-o',str(out/'joined.o')]},
 {'purpose':SCOPE+' Compile independent original-C/Rust metadata/zero-padding/flags/output fixture against the actual mixed partial link.','argv':[rustc,'--edition=2021','--test','-C','opt-level=2','-C','link-arg='+str(out/'joined.o'),'-C','link-arg=-no-pie',str(HERE/'fixture.rs'),'-o',str(out/'fixture')]},
 {'purpose':SCOPE+' Run3750 exact metadata, C bitfield/Rust storage, typed logger/output pairs and bidirectional C/Rust address/flag checks; no kernel effects.','argv':[str(out/'fixture'),'--exact','original_c_and_rust_descriptor_ownership','--test-threads=1','--nocapture']},
]
dump('FUTURE-HOST-COMMANDS.json',{'scope':SCOPE,'status':'EXACT4NEW_STANDING_ORDINARY_HOST_COMMANDS_NOT_YET_RUN','cwd':str(HERE),'fresh_output':str(out),'commands':commands,'header_profile_argv_source':bind(PRIOR/'FUTURE-HOST-COMMANDS.json'),'expected_pairs':3750,'environment':{'TMPDIR':str(out/'tmp'),'MCKERNEL_F06_RT_SIGRETURN_ORIGIN':origin},'domain':'Own HOST descriptor storage only; exact original typed int/ulong output; no live kernel/provider/flags or actual hardware/usercopy.','future_default_checks':['Root composes BODY10+BODY11 with frozen cumulative BODY3-9; preserve389-record multiset, actual origin command/line669 and all existing selectors.','Selected/fallback genuine TUs, fullcrate and defaultlink must show one Rust32B __verbose descriptor, no selected C target definition, original C fallback preserved, exact C consumers and no init constructor.','Matching-current registry/native diagnostics/configuration proof required before Cdata or whole-file retirement.'],'original_family_history':'BODY7 save-temps=obj collision and its single correction retained separately; this new command uses reviewed -save-temps spelling, no historical replay.'})
pre['snapshots']=snapshots
pre['snapshots']['kernel/rust/abi.rs']={'canonical':bind(ROOT/'kernel/rust/abi.rs'),'snapshot':bind(HERE/'abi.snapshot.rs')}
pre.update(scope=SCOPE,status='EXACT118_PLUS_BODY10_PRIVATE_RUST_DESCRIPTOR_OWNER_NOT_DEFAULT_ACCEPTANCE',original_body=bind(HERE/'original-prctl-log.c.inc'),retained_object_frontier=bind(HERE/'SELECTED-CURRENT116-ARCH-FRONTIER.json'),descriptor_identity=bind(HERE/'ORIGINAL-DESCRIPTOR-IDENTITY.json'),retained_C_storage_owners=0,retained_C_storage_bytes=0,private_proposed_Rust_storage_owners=1,private_proposed_Rust_storage_bytes=32,data_retirement_claim=False)
dump('PREIMAGES.json',pre)
dump('EXACT-REUSED-PROVIDERS.json',{'scope':SCOPE,'BODY10_callback':{'original':bind(PRIOR/'f06_prctl_log.rs'),'private_copy':bind(HERE/'f06_prctl_log.rs'),'byte_identical':True},'actual_Ddebug':{'source':bind(ROOT/'kernel/rust/debug.rs'),'exact_type':bind(HERE/'original-Ddebug.rs.inc')},'C_oracle_body':{'original':bind(PRIOR/'original-prctl-log.c.inc'),'private_copy':bind(HERE/'original-prctl-log.c.inc'),'byte_identical':True},'metadata_origin':'Existing MCKERNEL_F06_RT_SIGRETURN_ORIGIN producer/environment, no new synthesized filename mechanism.','C_callback_comment':'Frozen BODY10 mentions the qualified C record ABI; BODY11 changes the storage owner while retaining that exact representation/lifetime and code.'})
dump('PARENT-FOLLOWUP-AUTHORITY.RECORDED.json',{'scope':SCOPE,'author':'/root/f06_next','record_kind':'Worker transcript record of actual parent followup, not Root-authored grant','authority':'Resume private F06 whole-file source owner: implement one next genuinely missing body after BODY10, reusing banked BODY3–10/providers. Own new private body11 directory/patch only; no canonical/shared writes or duplicate body. Ordinary HOST checks only existing CPU6/7 jobs1/AS2GiB CPU60/wall90/actual guard, no Docker/heavy/native.','inherited_ordinary_bound':'At most4fixed new commands; one obvious fixture/compiler infrastructure correction within4 preserving original oracle; stop semantic/secondfailure.','no_default_native_file_or_data_retirement_credit':True})
print(json.dumps({'scope':SCOPE,'status':'BODY11_SOURCE_PREPARED','canonical118_unchanged':True,'new_private_Rust_storage_bytes':32,'commands':len(commands)}))
