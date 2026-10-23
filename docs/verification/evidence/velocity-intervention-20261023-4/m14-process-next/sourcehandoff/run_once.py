#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Prepared ordinary source/ABI/parity commands. Root owns admission/execution.
One attempt only; every failed command/capture is preserved, no automatic retry.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import time

OUT=Path(__file__).resolve().parents[1]
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
BASE=Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1')
SOURCE=BASE/'source-materialization-1/materialized-source'
BUILD=BASE/'full-image-attempt-1/owner-work/output/build'
RUSTC='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'


def main():
    parser=argparse.ArgumentParser(description=SCOPE)
    parser.add_argument('--root-grant',required=True,type=Path)
    parser.add_argument('--attempt',required=True,choices=['ordinary-attempt-1','ordinary-bounded-correction-2'])
    args=parser.parse_args()
    grant=json.loads(args.root_grant.read_text())
    ready=OUT/'sourcehandoff/EXECUTABLE-READY.json'
    if grant.get('scope')!=SCOPE or grant.get('ready_sha256')!=hashlib.sha256(ready.read_bytes()).hexdigest():
        raise RuntimeError('Exact root grant missing or stale')
    cpu=grant['ordinary_cpu']
    if os.getuid()!=1000 or os.geteuid()!=1000 or os.sched_getaffinity(0)!={cpu} or cpu not in (6,7):
        raise RuntimeError('Expected root-selected ordinary unprivileged CPU6/CPU7 grant')
    work=OUT/'fixture'/args.attempt
    work.mkdir()
    commands=[]
    result=dict(scope=SCOPE,status='FAIL_PRESERVE_ALL',commands=commands,full_crate_proven=False,
                selected_whole_C_TU_proven=False,default_image_link_proven=False,native_proven=False)
    started=time.monotonic()

    def run(label,argv,timeout=35):
        commands.append(dict(purpose=SCOPE+' '+label,argv=argv))
        (work/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        proc=subprocess.run(argv,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=timeout)
        for stream in ('stdout','stderr'): (work/(label+'.'+stream)).write_text(getattr(proc,stream))
        (work/(label+'.status')).write_text(str(proc.returncode)+'\n')
        if proc.returncode: raise RuntimeError('First failed command: '+label)
        return proc.stdout

    try:
        for relative,expected in json.loads(ready.read_text())['input_sha256'].items():
            if hashlib.sha256((OUT/relative).read_bytes()).hexdigest()!=expected:
                raise RuntimeError('Prepared input drift: '+relative)
        rows=json.loads((BASE/'full-image-attempt-1/owner-work/evidence/artifacts/compile_commands.json').read_text())
        row=next(row for row in rows if row['file']=='/src/kernel/process.c')
        argv=shlex.split(row['command']);flags=argv[1:argv.index('-o')]
        builtin=run('host-gcc-builtin-include',['/usr/bin/gcc','-print-file-name=include']).strip()
        flags=[token.replace('/work/output/build',str(BUILD)).replace('/src',str(SOURCE)) for token in flags]
        flags=[builtin if token=='/usr/lib/gcc/x86_64-redhat-linux/14/include' else token for token in flags]
        (work/'actual-retained-cflags.json').write_text(json.dumps(flags,indent=2)+'\n')
        (work/'header-inputs.json').write_text(json.dumps(dict(
            source=str(SOURCE),build=str(BUILD),diagnostic_only_host_gcc_builtin_substitution=builtin),indent=2)+'\n')
        original=(OUT/'fixture/original_vm_range_insert.ACTUAL-C-BODY.inc').read_text()
        fixture=(OUT/'fixture/parity_fixture.c.inc').read_text().replace(
            '/* ACTUAL ORIGINAL C ENTRY INSERTED HERE */',original.replace(
                'static int vm_range_insert(', 'static int original_vm_range_insert(',1))
        cpath=work/'actual_parity.c'; cpath.write_text(fixture)
        cobj=work/'actual_parity.o'; robj=work/'actual_provider.o'; exe=work/'actual_parity'
        run('actual-original-c-fixture-object',['/usr/bin/gcc',*flags,'-fno-pie','-c',str(cpath),'-o',str(cobj)])
        version=run('rust-version',[RUSTC,'--version'])
        if not version.startswith('rustc 1.92.0 '): raise RuntimeError('Pinned Rust version drift')
        rustflags=['panic=abort','opt-level=2','codegen-units=1','code-model=large','relocation-model=static',
                   'no-redzone=yes','force-frame-pointers=yes','overflow-checks=off','force-unwind-tables=no',
                   'no-vectorize-loops','no-vectorize-slp',
                   'target-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2,-fma']
        run('actual-rust-entry-and-body-object',[RUSTC,'--edition=2021','--crate-type=lib','--emit=obj',
            *[part for flag in rustflags for part in ('-C',flag)],str(OUT/'fixture/actual_provider.rs'),'-o',str(robj)])
        run('actual-parity-link',['/usr/bin/gcc','-no-pie','-Wl,--gc-sections','-Wl,--no-undefined',
                                str(cobj),str(robj),'-o',str(exe)])
        output=run('actual-parity-execute',[str(exe)])
        if 'PASS 1088 actual-original-C/Rust entry comparisons' not in output:
            raise RuntimeError('Expected real-body comparison count missing')
        consumer=OUT/'fixture/actual_default_and_fallback_consumers.c'
        selected=work/'actual_default_consumers.o';fallback=work/'actual_fallback_consumers.o'
        run('actual-default-consumers-object',['/usr/bin/gcc',*flags,'-O0','-fno-pie',
            '-DMCKERNEL_RUST_PROCESS_HELPERS','-c',str(consumer),'-o',str(selected)])
        selectednm=run('actual-default-consumers-symbols',['/usr/bin/nm',str(selected)])
        if ' U vm_range_insert\n' not in selectednm or ' T vm_range_insert\n' in selectednm:
            raise RuntimeError('Selected actual callers do not import Rust entry')
        run('actual-default-consumers-relocations',['/usr/bin/objdump','-dr',str(selected)])
        run('actual-fallback-consumers-object',['/usr/bin/gcc',*flags,'-O0','-fno-pie',
            '-UMCKERNEL_RUST_PROCESS_HELPERS','-c',str(consumer),'-o',str(fallback)])
        fallbacknm=run('actual-fallback-consumers-symbols',['/usr/bin/nm',str(fallback)])
        if ' t vm_range_insert\n' not in fallbacknm or ' U vm_range_insert\n' in fallbacknm:
            raise RuntimeError('Exact old C entry not retained in fallback')
        linked=work/'actual_selected_leaf_link.o'
        run('actual-selected-leaf-link',['/usr/bin/ld','-r','--gc-sections',
            '-u','process_add_range_insert_bridge','-u','process_split_range_insert_bridge',
            str(selected),str(robj),'-o',str(linked)])
        linkednm=run('actual-selected-leaf-symbols',['/usr/bin/nm',str(linked)])
        if sum(line.endswith(' T vm_range_insert') for line in linkednm.splitlines())!=1:
            raise RuntimeError('Final selected leaf does not uniquely define Rust entry')
        undefined=run('actual-selected-leaf-undefined',['/usr/bin/nm','-u',str(linked)])
        if {line.split()[-1] for line in undefined.splitlines()}!={'vm_range_insert_log_bridge','vm_range_insert_dump_bridge'}:
            raise RuntimeError('Unexpected selected-leaf unresolved references')
        result.update(status='PASS_PRIVATE_ACTUAL_ENTRY_BODY_PARITY_REAL_ABI_AND_SELECTED_LEAF_LINK',
            actual_comparisons=1088,real_header_rust_layouts_equal=True,independent_tree_oracle=True,
            exact_return_and_callback_order=True,default_actual_callers_import_rust_entry=True,
            exact_c_fallback_selected=True,selected_leaf_unique_rust_entry=True,
            retained_c_callbacks=['vm_range_insert_log_bridge','vm_range_insert_dump_bridge'])
    except BaseException as error:
        result['error']=repr(error)
    result['elapsed_seconds']=time.monotonic()-started
    (work/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__=='__main__': raise SystemExit(main())
