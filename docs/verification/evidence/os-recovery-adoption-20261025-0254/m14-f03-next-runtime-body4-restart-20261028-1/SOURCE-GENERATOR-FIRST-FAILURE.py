#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Generate private utility-profile source and check byte bindings; no tool execution.
"""
import difflib
import hashlib
import json
import struct
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=Path('/home/holden/mckernel')
E=HERE.parent
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'

def ref(path):
    data=path.read_bytes()
    return dict(path=str(path),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())

def function(source,marker):
    assert source.count(marker)==1,marker
    start=source.index(marker)
    end=source.index('{',start)+1
    depth=1
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}')
        end+=1
    return start,end,source[start:end]+'\n'

def selected_function(path,name):
    data=path.read_bytes()
    header=struct.unpack_from('<16sHHIQQQIHHHHHH',data)
    assert header[0][:6]==b'\x7fELF\x02\x01'
    sections=[struct.unpack_from('<IIQQQQIIQQ',data,header[6]+i*header[11]) for i in range(header[12])]
    rows=[]
    for section in sections:
        if section[1]!=2:continue
        strings=sections[section[6]]
        strings=data[strings[4]:strings[4]+strings[5]]
        for offset in range(section[4],section[4]+section[5],section[9]):
            n,info,other,index,value,size=struct.unpack_from('<IBBHQQ',data,offset)
            if info&15==2 and 0<index<len(sections) and sections[index][2]&2:
                rows.append(dict(name=strings[n:strings.index(0,n)].decode(),bytes=size))
    assert len(rows)==54
    assert [r for r in rows if r['name']==name]==[dict(name=name,bytes=220)]
    return dict(name=name,bytes=220,selected_generic_C_functions=len(rows))

def main():
    cpath=ROOT/'kernel/syscall.c'
    rpath=ROOT/'kernel/rust/syscall_policy.rs'
    upath=ROOT/'executer/user/rust/syscall_intercept.rs'
    c,rust,user_rust=cpath.read_text(),rpath.read_text(),upath.read_text()
    a,end,original=function(c,'int util_show_syscall_profile()')
    assert 'fn util_show_syscall_profile(' not in rust
    # Existing last unconditional reset fixes both selected/fallback line states.
    last=c.rfind('#line ',0,a)
    reset_line=c[last:c.index('\n',last)]
    assert reset_line=='#line 25457' and c[last-7:last]=='#endif\n'
    assert '#line' not in c[c.index('\n',last)+1:a]
    line_offset=25457-(c[:last].count('\n')+1)-1
    startline=c[:a].count('\n')+1
    closeline=c[:end].count('\n')+1
    paired=('#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\n'
            '/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */\n'
            'extern int util_show_syscall_profile(void);\n'
            '#else\n#line '+str(startline+line_offset)+'\n'+original+
            '#endif\n#line '+str(closeline+line_offset)+'\n')
    postc=c[:a]+paired+c[end:]
    next_marker='int util_thread(struct uti_attr *arg)'
    old_next=c[:c.index(next_marker,end)].count('\n')+1+line_offset
    last_reset=postc.index('#line '+str(closeline+line_offset)+'\n',a)
    new_next=closeline+line_offset+(postc[:postc.index(next_marker,a)].count('\n')+1)-(postc[:last_reset].count('\n')+1)-1
    assert old_next==new_next
    (HERE/'util-profile-original.C.inc').write_text(original)
    (HERE/'util-profile-paired.C.inc').write_text(paired)

    # Reuse exact existing project Rust declarations, including complete fields.
    constants='\n'.join(line for line in user_rust.splitlines()
                        if line.startswith(('const UTI_SZ_SYSCALL_STACK:', 'const UTI_SYSCALL_PROFILE_SLOTS:')))+'\n'
    sa=user_rust.index('#[repr(C)]\nstruct SyscallStruct {')
    ue=user_rust.index('\n#[repr(C)]\nstruct TerminateThreadDesc {',sa)
    declarations=user_rust[sa:ue].rstrip()+'\n'
    reused=constants+declarations
    (HERE/'uti-abi.reused.Rust.inc').write_text(reused)
    template=(HERE/'util-profile-entry.template.Rust.inc').read_text()
    marker='    // SOURCE_GENERATOR_INSERTS_EXACT_REUSED_UTI_ABI_HERE'
    assert template.count(marker)==1
    entry=template.replace(marker,reused.rstrip())
    (HERE/'util-profile-entry.Rust.inc').write_text(entry)
    for path,before,after in [('kernel/syscall.c',c,postc),('kernel/rust/syscall_policy.rs',rust,rust+'\n'+entry)]:
        (HERE/(Path(path).name+'.patch')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+path,tofile='b/'+path)))
    witness='''
    #[no_mangle]
    pub static F03_UTIL_PROFILE_ABI:[c_ulong;26]=[
        core::mem::size_of::<SyscallStruct>() as _,core::mem::align_of::<SyscallStruct>() as _,
        core::mem::offset_of!(SyscallStruct,number) as _,core::mem::offset_of!(SyscallStruct,args) as _,
        core::mem::offset_of!(SyscallStruct,ret) as _,core::mem::offset_of!(SyscallStruct,uti_info) as _,
        core::mem::size_of::<UtiDesc>() as _,core::mem::align_of::<UtiDesc>() as _,
        core::mem::offset_of!(UtiDesc,lctx) as _,core::mem::offset_of!(UtiDesc,rctx) as _,
        core::mem::offset_of!(UtiDesc,mck_tid) as _,core::mem::offset_of!(UtiDesc,key) as _,
        core::mem::offset_of!(UtiDesc,pid) as _,core::mem::offset_of!(UtiDesc,tid) as _,
        core::mem::offset_of!(UtiDesc,uti_info) as _,core::mem::offset_of!(UtiDesc,fd) as _,
        core::mem::offset_of!(UtiDesc,syscall_stack) as _,core::mem::offset_of!(UtiDesc,syscall_stack_top) as _,
        core::mem::offset_of!(UtiDesc,syscalls) as _,core::mem::offset_of!(UtiDesc,syscalls2) as _,
        core::mem::offset_of!(UtiDesc,start_syscall_intercept) as _,UTI_SZ_SYSCALL_STACK as _,
        UTI_SYSCALL_PROFILE_SLOTS as _,core::mem::size_of::<c_int>() as _,
        core::mem::size_of::<c_long>() as _,core::mem::size_of::<c_ulong>() as _,
    ];
'''
    (HERE/'util-profile-entry.fixture.Rust.inc').write_text(entry.rstrip()[:-1]+witness+'}\n')
    (HERE/'abi.current.rs').write_bytes((ROOT/'kernel/rust/abi.rs').read_bytes())
    (HERE/'lib.fixture.rs').write_text('''#![no_std]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[path="abi.current.rs"] mod abi;
mod policy {
    use crate::abi::{CInt,CULong};
    unsafe extern "C" {
        static mut uti_desc:CULong;
        fn kprintf(format:*const i8,...)->CInt;
    }
    include!("util-profile-entry.fixture.Rust.inc");
}
''')
    oldbase=E/'m14-f03-next-runtime-body3-restart-20261028-1'
    plan=json.loads((oldbase/'FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json').read_text())
    for row in plan['commands']:
        row['argv']=[arg.replace(str(oldbase),str(HERE)) for arg in row['argv']]
        row['purpose']=SCOPE+' HOST genuine UTI header and mocked print events only; no actual context/syscall/IKC/MM/hardware/native/Docker/root/guest effects.'
    argv=plan['commands'][0]['argv']
    argv[argv.index('f03_do_munmap_entry')]='f03_util_profile'
    plan['commands'][0]['label']='00-reused-UTI-ABI-new-Rust-profile-body'
    argv=plan['commands'][1]['argv']
    argv.insert(argv.index(str(HERE/'driver.c')),'-I'+str(ROOT/'executer/include'))
    plan['commands'][1]['label']='01-genuine-header-verbatim-C-oracle-link'
    plan['commands'][2]['label']='02-utility-profile-functional-equivalence'
    plan['expected_stdout']='PASS util-profile genuine-header ABI26; 72 C/Rust pairs; exact ordered varargs, signed counts, live reads, descriptor snapshot and full-state oracles'
    plan['requires']='Fresh exact Root ordinary grant after source rebase/tool/header binding and disjoint output; old body3 grant is sealed and never reused.'
    plan['executed']=False
    plan['status']='SOURCE_ONLY_NOT_GRANTED'
    (HERE/'FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json').write_text(json.dumps(plan,indent=2)+'\n')

    accepted_path=E/'CURRENT116-ACCEPTED-ARTIFACT-AND-CURRENTFREE.json'
    accepted=json.loads(accepted_path.read_text())['actual_new_default_artifact']['generic_C']
    assert ref(Path(accepted['path']))==accepted
    frontier=selected_function(Path(accepted['path']),'util_show_syscall_profile')
    previous=json.loads((oldbase/'SOURCE-READY.json').read_text())
    old_preimages={r['path']:r for r in previous['preimages']}
    drift=[dict(path=str(p),previous116=old_preimages[str(p)],current=ref(p))
           for p in [cpath,rpath] if old_preimages[str(p)]!=ref(p)]
    inputs=[cpath,rpath,upath,ROOT/'kernel/rust/abi.rs',ROOT/'executer/include/uti.h',
            ROOT/'kernel/include/kmsg.h',ROOT/'kernel/include/types.h',oldbase/'SOURCE-READY.json',
            E/'m14-f03-next-runtime-body2-source-20261028-1/SETRESUID-HOLD.json']
    assert cpath.read_text()==c and rpath.read_text()==rust and upath.read_text()==user_rust,'Concurrent source changes: require coherent new preimages.'
    report=dict(scope=SCOPE,owner='/root/f03_next',status='PRIVATE_UTILITY_PROFILE_SOURCE_READY_NOT_COMPILED',
                target='util_show_syscall_profile',selected_frontier=frontier,
                selected_artifact_reference=ref(accepted_path),selected_generic_C=accepted,
                source_preimages=[ref(p) for p in inputs],source_drift_from116=drift,
                baseline='Actual canonical118 source preimages; CURRENT116 remains the accepted selected artifact frontier, not a new118 build.',
                reused_Rust='Exact complete SyscallStruct and UtiDesc declarations and slot constants from existing syscall_intercept.rs; no existing complete profile-printing Rust body found.',
                reused_slices=dict(path=str(upath),start=sa,end=ue,sha256=hashlib.sha256(declarations.encode()).hexdigest()),
                preserved_behavior=['capture one descriptor before first print','offloaded header then512ascending slots','other-thread header then512ascending slots',
                                    'zero suppression and full signed long counts','exact int/long variadic ABI','ignore logger errors; return0',
                                    'no descriptor mutation and no new lock/allocation/null/error behavior'],
                retained_contract='Original caller retains live/aligned/initialized foreign descriptor and its original synchronization lifetime; original TODO usercopy debt unchanged.',
                fixture=dict(ABI_words=26,planned_pairs=72,genuine_C_oracle='Verbatim complete selected C function',
                             independent_oracle='Exact ordered format/int/long events plus complete original/decoy bytes; logger mutations check current reads and captured pointer.'),
                line_state=dict(start_physical=startline,close_physical=closeline,offset=line_offset,
                                successor_original=old_next,successor_candidate=new_next),
                predicted_C_function_removal=1,new_C_runtime_functions=0,new_C_data=0,
                excluded=['banked117 perf_mmap','banked118 clear_host_pte','body3 do_munmap','all credentials/SETRESUID-HOLD',
                          'all held service/request/endpoint/signal paths'],
                actual_compilers=0,actual_fixture_runs=0,canonical_writes=0,default_artifacts=0,native=0,file_closures=0,
                caps=dict(UTC_epoch=1793253600,MONO=1035704.5689393478,BOOT=1051042.6959879305,
                          boot_id='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'),
                credit_run='7f4af94a83b14cc08f97401f5891d965',ceiling=57774.852125,spent_floor=22812.3311)
    report['files']=[ref(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name not in ['SOURCE-READY.json','SOURCE-CHECKS.json']]
    (HERE/'SOURCE-READY.json').write_text(json.dumps(report,indent=2)+'\n')
    checks=dict(scope=SCOPE,status='PASS_PRIVATE_SOURCE_BYTE_AND_LINE_CHECKS_ONLY',source_ready=ref(HERE/'SOURCE-READY.json'),
                verified=['actual CURRENT116 selected C220','verbatim current C oracle','unchanged existing Rust UTI declarations',
                          'restored successor logical line','explicit changed118source preimages','three future commands remain UNRUN'],
                compiler_runs=0,fixture_runs=0,guard_calls=0)
    (HERE/'SOURCE-CHECKS.json').write_text(json.dumps(checks,indent=2)+'\n')
    print(json.dumps(checks))

if __name__=='__main__':main()
