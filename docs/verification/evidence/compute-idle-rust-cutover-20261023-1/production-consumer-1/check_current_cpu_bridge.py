#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Actual new/existing Rust bridge bodies + REAL abi.rs/cls.rs, ordinary CPU0 only.
Only privileged CPU-ID lookup is a safe C stub; no kernel instructions execute.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shlex
import subprocess

HERE = Path(__file__).resolve().parent
OUT = Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-consumer-1')
SOURCE = OUT / 'materialized-source'
BASE = Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1')
EV = BASE / 'full-image-attempt-1/owner-work/evidence'
BUILD = BASE / 'full-image-attempt-1/owner-work/output/build'
RUSTC = '/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'


def need(ok,message):
    if not ok:
        raise RuntimeError(message)


def main():
    need(os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={0},'ordinary CPU0 grant required')
    work=OUT/'current-cpu-bridge-attempt-1';work.mkdir()
    commands=[]
    result=dict(scope=SCOPE,status='FAIL_PRESERVE_ALL',full_production_crate_compiled=False,
                pinned_production_compile=False,native_CPU_ID_provider_executed=False,
                active_image_changed=False,canonical_source_changed=False)
    def run(label,argv):
        commands.append(dict(label=label,argv=argv,scope=SCOPE))
        (work/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        process=subprocess.run(argv,capture_output=True,text=True,timeout=35,
                               env=dict(os.environ,RUST_MIN_STACK='2097152'))
        for stream in ('stdout','stderr'):(work/(label+'.'+stream)).write_text(getattr(process,stream))
        (work/(label+'.status')).write_text(str(process.returncode)+'\n')
        need(process.returncode==0,'first failed ordinary command: '+label)
        return process.stdout
    try:
        spec=importlib.util.spec_from_file_location('idle_source_items',HERE.parent/'idle-orchestration-1/stage_private.py')
        stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)
        materialization=json.loads((OUT/'MATERIALIZATION-RESULT.json').read_text())
        manifest=json.loads((OUT/'source-inputs.json').read_text())
        paths=('kernel/rust/lib.rs','kernel/rust/abi.rs','kernel/rust/cls.rs',
               'kernel/rust/process_helpers.rs','kernel/rust/sched_helpers.rs','kernel/rust/x86_local.rs')
        sources={path:(SOURCE/path).read_text() for path in paths}
        for path,text in sources.items():
            need(hashlib.sha256(text.encode()).hexdigest()==manifest['materialized_repository_files'][path],
                 'real coherent crate source changed: '+path)
        lib=sources['kernel/rust/lib.rs']
        need(all('mod '+name+';' in lib for name in ('abi','cls','process_helpers','sched_helpers','x86_local')),
             'real default crate module closure')
        bridge=stage.item(sources['kernel/rust/sched_helpers.rs'],'pub unsafe extern "C" fn sched_idle_current_cpu_bridge(')
        existing=stage.item(sources['kernel/rust/process_helpers.rs'],'pub unsafe extern "C" fn process_sched_cpu_local_bridge(')
        existing_cpu=stage.item(sources['kernel/rust/cls.rs'],'pub unsafe extern "C" fn get_cpu_local_var(')
        lookup=stage.item(sources['kernel/rust/cls.rs'],'pub unsafe extern "C" fn get_this_cpu_local_var(')
        provider_names=('get_cpu_local_var','process_sched_cpu_local_bridge','ihk_mc_get_processor_id')
        provider_rows={}
        for inventory in ('symbols.txt','rust-object-symbols.txt'):
            lines=(EV/inventory).read_text().splitlines()
            provider_rows[inventory]={name:[line for line in lines if line.split()[-1:]==[name]] for name in provider_names}
            need(all(len(rows)==1 and rows[0].split()[-2]=='T' for rows in provider_rows[inventory].values()),
                 'existing uniquely defined real Rust/image provider symbols')
        write_sources=dict(scope=SCOPE,source_root=str(SOURCE),materialization_sha256=materialization['materialization_sha256'],
            source_sha256={path:manifest['materialized_repository_files'][path] for path in paths},
            real_crate_module_members=['abi','cls','process_helpers','sched_helpers','x86_local'],
            exact_new_bridge_body=bridge,exact_existing_process_bridge_body=existing,
            exact_existing_cpu_lookup_body=existing_cpu,exact_existing_this_cpu_lookup_body=lookup,
            existing_selected_image_provider_rows=provider_rows,
            production_privileged_CPU_ID='x86_local::ihk_mc_get_processor_id default !mckernel_equivalence branch uses MSR_GS_BASE and gs:0; unchanged, not executed here')
        (OUT/'CURRENT-CPU-REAL-CRATE-CLOSURE.json').write_text(json.dumps(write_sources,indent=2,sort_keys=True)+'\n')
        # abi.rs and cls.rs are included WHOLE from the newly materialized source.
        # Only two bridge functions are extracted to avoid a full kernel crate build.
        mini='#![no_std]\n#[path="'+str(SOURCE/'kernel/rust/abi.rs')+'"] mod abi;\n'
        mini+='#[path="'+str(SOURCE/'kernel/rust/cls.rs')+'"] mod cls;\n'
        mini+='mod process_bridge { use crate::abi::{CInt,CULong,CpuLocalVar};\n'
        mini+='unsafe extern "C" {fn get_cpu_local_var(id:CInt)->*mut CpuLocalVar;}\n#[no_mangle]\n'+existing+'\n}\n'
        mini+='mod idle_bridge {use crate::abi::CInt;\nunsafe extern "C" {fn ihk_mc_get_processor_id()->CInt; fn process_sched_cpu_local_bridge(id:CInt)->usize;}\n#[no_mangle]\n'+bridge+'\n}\n'
        mini+='#[no_mangle] pub extern "C" fn bridge_cpu_local_size()->usize {core::mem::size_of::<abi::CpuLocalVar>()}\n'
        mini+='#[no_mangle] pub extern "C" fn bridge_cpu_local_alignment()->usize {core::mem::align_of::<abi::CpuLocalVar>()}\n'
        rpath=work/'actual_bridge_real_abi_cls.rs';rpath.write_text(mini);robj=work/'actual_bridge_real_abi_cls.o'
        need(run('rust-version',[RUSTC,'--version']).startswith('rustc 1.92.0 '),'ordinary pinned Rust version')
        flags=['panic=abort','opt-level=2','codegen-units=1','code-model=large','relocation-model=static','no-redzone=yes',
               'force-frame-pointers=yes','overflow-checks=off','force-unwind-tables=no','no-vectorize-loops','no-vectorize-slp',
               'target-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2,-fma']
        run('actual-rust-bridge-object',[RUSTC,'--edition=2021','--crate-type=lib','--emit=obj',
             *[part for flag in flags for part in ('-C',flag)],
             '--cfg','native_linux_irq_work_v6_12','--cfg','enable_profile','--cfg','enable_perf','--cfg','enable_rusage',
             str(rpath),'-o',str(robj)])
        (work/'actual_provider_scope.txt').write_text('Whole actual abi.rs/cls.rs included; unreferenced CLS allocator functions are discarded by ordinary host --gc-sections. This is not a whole kernel crate acceptance.\n')
        c='''#include <process.h>
#include <sched_helpers.h>
#include <cls.h>
extern struct cpu_local_var *clv;
extern unsigned long process_sched_cpu_local_bridge(int);
extern unsigned long bridge_cpu_local_size(void);
extern unsigned long bridge_cpu_local_alignment(void);
static struct cpu_local_var cpu_array[6];
static int selected_cpu;
int ihk_mc_get_processor_id(void) { return selected_cpu; }
extern long write(int,const void *,unsigned long);
int main(void) {
 if(bridge_cpu_local_size()!=sizeof(struct cpu_local_var)) return 11;
 if(bridge_cpu_local_alignment()!=__alignof__(struct cpu_local_var)) return 12;
 clv=cpu_array;
 for(int id=0;id<6;id++) {
  selected_cpu=id;
  if((struct cpu_local_var *)sched_idle_current_cpu_bridge()!=&cpu_array[id]) return 21;
  if((struct cpu_local_var *)process_sched_cpu_local_bridge(id)!=&cpu_array[id]) return 22;
  if(get_cpu_local_var(id)!=&cpu_array[id]) return 23;
  if(get_this_cpu_local_var()!=&cpu_array[id]) return 24;
 }
 static const char message[]="PASS 6 current-CPU bridge chains; actual Rust abi.rs/cls.rs and C production type size/alignment\\n";
 if(write(1,message,sizeof(message)-1)!=(long)(sizeof(message)-1)) return 31;
 return 0;
}
'''
        cpath=work/'actual_bridge_consumer.c';cpath.write_text(c);cobj=work/'actual_bridge_consumer.o'
        rows=json.loads((EV/'artifacts/compile_commands.json').read_text())
        original=shlex.split(next(row['command'] for row in rows if row['file']=='/src/kernel/process.c'))
        cflags=original[1:original.index('-o')]
        builtin=run('host-gcc-include',['/usr/bin/gcc','-print-file-name=include']).strip()
        cflags=[part.replace('/work/output/build',str(BUILD)).replace('/src',str(SOURCE)) for part in cflags]
        cflags=[builtin if part=='/usr/lib/gcc/x86_64-redhat-linux/14/include' else part for part in cflags]
        run('actual-bridge-C-consumer',['/usr/bin/gcc',*cflags,'-fno-pie','-ffunction-sections','-fdata-sections','-c',str(cpath),'-o',str(cobj)])
        binary=work/'actual_bridge_chain'
        run('actual-bridge-chain-link',['/usr/bin/gcc','-no-pie','-Wl,--gc-sections','-Wl,--no-undefined',str(cobj),str(robj),'-o',str(binary)])
        output=run('actual-bridge-chain-execute',[str(binary)])
        need('PASS 6 current-CPU bridge chains' in output,'actual bridge case count')
        defined=run('actual-bridge-chain-definitions',['/usr/bin/nm','-g','--defined-only',str(binary)])
        need(all(sum(line.split()[-1:]==[name] for line in defined.splitlines())==1
                 for name in (*provider_names,'sched_idle_current_cpu_bridge','get_this_cpu_local_var')),
             'unique actual linked bridge/provider definitions')
        result.update(status='PASS_REAL_ABI_CLS_AND_EXACT_CURRENT_CPU_BRIDGE_BODY_HOST_LINK',
                      actual_cases=6,real_abi_module_included_whole=True,real_cls_module_included_whole=True,
                      C_Rust_cpu_local_size_alignment_agree=True,existing_selected_image_providers_unique=True,
                      controlled_CPU_ID_boundary=True,unreferenced_CLS_functions_discarded=True,
                      pinned_fullcrate_and_final_default_image_proof_still_pending=True)
    except BaseException as error:
        result['error']=repr(error)
    with (OUT/'CURRENT-CPU-BRIDGE-RESULT-1.json').open('x') as stream:
        json.dump(result,stream,indent=2,sort_keys=True);stream.write('\n')
    print(json.dumps(result,sort_keys=True))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__=='__main__':
    raise SystemExit(main())
