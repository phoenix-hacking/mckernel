#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Metadata only; retain selected existing command and concrete future observations.
No compiler, build, Docker, root, guest, Git or repeated fixture.
"""
from pathlib import Path
import copy
import hashlib
import json
import shlex
import tarfile

HERE = Path(__file__).resolve().parent
HOST = Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/memory-combined-preparation-1')
BASE = Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1')
MEMORY = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-1/m14-memory')
BUILD = BASE/'full-image-attempt-1/owner-work/output/build'
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'


def bind(path):
    raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def write(path,value):
    with path.open('x') as stream:
        json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')


def main():
    result=json.loads((HOST/'MATERIALIZATION-RESULT.json').read_text())
    assert result['status']=='PASS_COHERENT_IDLE_PLUS_TWO_MEMORY_POSTIMAGE_SOURCE_MATERIALIZATION_ONLY'
    descriptor=BASE/'full-image-attempt-1/owner-work/evidence/artifacts/compile_commands.json'
    rows=json.loads(descriptor.read_text())
    selected=[row for row in rows if row['file']=='/src/arch/x86_64/kernel/memory.c']
    assert len(selected)==1
    row=selected[0];argv=shlex.split(row['command']);oi=argv.index('-o')
    assert argv[0]=='/usr/bin/cc' and argv[-2:]==['-c',row['file']]
    assert argv.count('-DMCKERNEL_RUST_X86_MEMORY_PUBLIC')==1
    actualobject=str(Path(row['directory'])/argv[oi+1])
    tu=argv.copy();tu[oi+1]='/work/memory-cutover-production/memory.c.o'
    pp=argv[:oi]+['-E',row['file']]
    macros=argv[:oi]+['-E','-dM',row['file']]
    work=HOST/'ordinary-selected-memory-tuple-attempt-1'
    source=HOST/'materialized-source'
    def ordinary(parts):
        values=[part.replace('/work/output/build',str(BUILD)).replace('/src',str(source)) for part in parts]
        return ['/usr/bin/gcc-9']+['/usr/lib/gcc/x86_64-linux-gnu/9/include' if part=='/usr/lib/gcc/x86_64-redhat-linux/14/include' else part for part in values[1:]]
    ordinarytu=ordinary(argv);ordinarytu[oi+1]=str(work/'memory.c.o')
    assert Path('/usr/lib/gcc/x86_64-linux-gnu/9/include/stddef.h').is_file()
    prior=json.loads((HERE.parent/'production-consumer-1/PINNED-PRODUCTION-CONSUMER-COMMANDS.json').read_text())
    doc=dict(scope=SCOPE,preparation_only=True,execution_released=False,
        materialized_source=str(source),source_manifest=bind(HOST/'source-inputs.json'),
        source_manifest_canonical_sha256=result['source_manifest_canonical_sha256'],
        source_derivative_sha256=result['source_derivative_sha256'],materialization_sha256=result['materialization_sha256'],
        exact_selected_memory_compile_row=row,compile_descriptor=bind(descriptor),
        ordinary_host_only=dict(compile_grant_received=False,compiler='/usr/bin/gcc-9',
            actual_complete_TU=True,headers=str(BUILD),preprocessor_argv=ordinary(pp),whole_TU_argv=ordinarytu,
            source=str(source/'arch/x86_64/kernel/memory.c'),fresh_output=str(work),
            command=['/usr/bin/taskset','-c','0','/usr/bin/prlimit','--as=2147483648','--cpu=60','--fsize=33554432','--core=0','--nofile=256','--','/usr/bin/timeout','--kill-after=6s','90s','/home/holden/anaconda3/bin/python3','-I','-B',str(HERE/'check_selected_memory_tu.py')],
            required_capture='Existing accepted owned_capture helper 990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8, fresh capture namespace, outer wall90/cleanup6, require direct child joined/group absent/closed streams/error and retirement_error None. Do not infer whole compiler group absence from the inner result.',
            helper_path='/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py',
            proof_scope='Ordinary host GCC9 selected C ABI/layout/preprocessor/relocation evidence only. Compiler and builtin include differ from pinned GCC14; do not label it production acceptance.'),
        pinned_GCC14_production=dict(compile_grant_received=False,container_image=prior['container_image'],
            toolchain=prior['toolchain'],profile=prior['reviewed_heavy_profile'],
            source_mount=dict(host=str(source),container='/src',readonly=True),
            fresh_output_host=str(HOST/'pinned-production-attempt-1/owner-work'),
            configure=prior['configure'],whole_TU=dict(argv=tu,cwd=row['directory']),
            preprocessor=dict(argv=pp,cwd=row['directory']),macro_metadata=dict(argv=macros,cwd=row['directory']),
            production_Rust_and_default_image=prior['default_production_rust_and_image'],
            no_stale_build_output=True,
            gates='Fresh root-owned source/driver/owner manifest bindings, namespace/nonce, independent execution release, shared-heavy lease, positive predecessor retirement, HOST/scratch floors plus full sparse backing gap and planned output/capture/emergency growth. No mutation of frozen10972.'),
        production_observations=[
            dict(argv=['/usr/bin/nm','-u','/work/memory-cutover-production/memory.c.o'],require_unique_import='x86_clear_old_action_bridge'),
            dict(argv=['/usr/bin/readelf','-rW','/work/memory-cutover-production/memory.c.o'],require_relocation='x86_clear_old_action_bridge'),
            dict(argv=['/usr/bin/nm','-u',actualobject],require_unique_import='x86_clear_old_action_bridge',scope='actual generated default consumer, after default image build'),
            dict(argv=['/usr/bin/readelf','-rW',actualobject],require_relocation='x86_clear_old_action_bridge'),
            dict(argv=['/usr/bin/nm','-g','--defined-only','/work/output/build/kernel/rust/mckernel_rust.o'],require_unique_definition='x86_clear_old_action_bridge'),
            dict(argv=['/usr/bin/nm','-g','--defined-only','/work/output/build/kernel/mckernel.img'],require_unique_definition='x86_clear_old_action_bridge'),
            dict(argv=['/usr/bin/nm','-u','/work/output/build/kernel/mckernel.img'],require_stdout='')],
        preserved_idle_observations=str(HERE.parent/'production-consumer-1/PINNED-DEFAULT-CONSUMER-OBSERVATIONS.json'),
        selected_macro='MCKERNEL_RUST_X86_MEMORY_PUBLIC',
        source_gates=['Actual PP selects external Rust callback declaration; both original C definitions excluded.',
            'Actual selected memory.c compiles all 40B/8B argument size/alignment, six field offset and flag witnesses.',
            'Real lib.rs includes x86_memory_helpers and page_helpers; actual CMake fullcrate dependency list contains both unchanged module paths.',
            'No test stub phys_to_page provider: real final provider and default memory/Rust callback owner joined in final artifact.',
            'Fallback full-TU compilation under existing selector remains separate; do not alter selection or claim unused fallback as live source.'],
        debt='C clear_range_l1/l2/l3 callers, private-layout witnesses/declaration, established phys_to_page boundary and effect/allocator/hash/lock implementations remain. Existing Rust decode/action/page-membership helpers are reused, not newly retired.',
        source_review=bind(MEMORY/'SOURCE-REVIEW.md'),fixture_receipt=bind(MEMORY/'fixture-receipt.json'),
        fixture_vectors_reused=129888,fixture_vectors_repeated=0,
        failure_history='Memory fixture first attempt PASS; no memory compile attempt in this preparation. Earlier idle fixture failures and their accepted bounded corrections remain in original evidence and are not replayed.')
    write(HERE/'NEXT-CONSUMER-COMMANDS.json',doc)
    oldcontract=HERE.parent/'production-consumer-1/thin_source_contract.py'
    contract=oldcontract.read_text()
    assert hashlib.sha256(contract.encode()).hexdigest()=='e3dff8198b82805e551614f1c95f103f123211e514e27c444afd9e12ff28e3fa'
    oldschema='mckernel.idle-orchestration-production-consumer-thin-inputs.v1'
    oldhash='7dc3bbf0dca602a1085dab30d304b7a59f9c765acfdc36a0abf744c2dc1a5f31'
    assert contract.count(oldschema)==1 and contract.count(oldhash)==1
    contract=contract.replace(oldschema,'mckernel.idle-and-memory-production-consumer-thin-inputs.v1').replace(oldhash,result['source_manifest_canonical_sha256'])
    with (HERE/'thin_source_contract.py').open('x') as stream:stream.write(contract)
    for name in ('MATERIALIZATION-RESULT.json','admission.json'):
        with (HERE/name).open('xb') as stream:stream.write((HOST/name).read_bytes())
    # Retain only new journal/raw copy receipt. Existing fixture/input authorities
    # and the previous full manifest archive stay referenced, not duplicated.
    archive=HERE/'combined-materialization-evidence.tar.gz'
    with tarfile.open(archive,'x:gz') as tar:
        for name in ('materialization-journal.jsonl','materialization-attempt-1.stdout','materialization-attempt-1.stderr','MATERIALIZATION-RESULT.json','admission.json'):
            tar.add(HOST/name,arcname=name)
    files=[HERE/'prepare_combined.py',HERE/'materialize_combined_generated.py',HERE/'check_selected_memory_tu.py',Path(__file__),
           HERE/'NEXT-CONSUMER-COMMANDS.json',HERE/'thin_source_contract.py',archive,
           MEMORY/'cutover.patch',MEMORY/'SOURCE-REVIEW.md',MEMORY/'REPORT.md',MEMORY/'fixture-receipt.json']
    receipt=dict(scope=SCOPE,status='PASS_COMBINED_SOURCE_AND_COMMAND_PREPARATION_ONLY',
        source_manifest_canonical_sha256=result['source_manifest_canonical_sha256'],
        source_derivative_sha256=result['source_derivative_sha256'],materialization_sha256=result['materialization_sha256'],
        source_copy_seconds=result['seconds'],copy_direct_command_joined_exit0=True,
        source_entries=6959,source_overlay_files_vs_frozen10972=5,new_compiler_runs=0,
        old_memory_vectors_reused=129888,old_idle_vectors_reused=108,old_vectors_repeated=0,
        canonical_source_changed=False,frozen_image_or_build_changed=False,
        prepared_ordinary_check_not_executed=True,production_default_link_and_native_open=True,
        bindings=[bind(path) for path in files])
    write(HERE/'PREPARATION-RECEIPT.json',receipt)
    print(json.dumps(receipt,sort_keys=True))


if __name__=='__main__':
    main()
