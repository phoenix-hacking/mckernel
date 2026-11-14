#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-prescribed single source-only correction of the unexecuted host argv proposal.
"""
from pathlib import Path
import hashlib
import json
import shlex

D=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-2')
B=Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1')

def main():
    original=json.loads((D/'EXACT-PINNED-HOST-RUST-CANDIDATE.NOT-EXECUTED.json').read_text())
    tokens=shlex.split(original['exact_saved_container_command'])
    assert tokens[:3]==['cd','/work/output/build/kernel','&&']
    suffix=tokens[3:]
    assert suffix[:3]==['/usr/bin/cmake','-E','env']
    operators=('&&','||',';','|','&','>','<','>>','<<')
    assert not any(t in operators or any(c in t for c in '$`\n\r;|&<>') for t in suffix)
    root=Path(original['same_sysroot_host_root'])
    compiler=root/'bin/rustc';compiler_bytes=compiler.read_bytes()
    assert hashlib.sha256(compiler_bytes).hexdigest()==original['pinned_compiler']['sha256']
    work=H/'ordinary-exact-fullcrate-attempt-1'
    out=work/'mckernel_rust.o';source=H/'source-materialization-attempt-2/materialized-source/kernel/rust/lib.rs'
    exact_map={'/nightly/bin/rustc':str(compiler),'/src/kernel/rust/lib.rs':str(source),
        '--emit=obj=/work/output/build/kernel/rust/mckernel_rust.o':'--emit=obj='+str(out)}
    argv=[exact_map.get(t,t) for t in suffix]
    assert all(suffix.count(k)==1 for k in exact_map)
    assert all(a==b or exact_map.get(a)==b for a,b in zip(suffix,argv))
    assert not any('/nightly/' in t or '/src/' in t or '/work/' in t for t in argv)
    codegen=[]
    for i,t in enumerate(suffix):
        if t=='-C' and i+1<len(suffix) and suffix[i+1].startswith('codegen-units='):codegen.append(suffix[i+1])
        if t.startswith('-Ccodegen-units='):codegen.append(t[2:])
    baseline=B/'full-image-attempt-1/owner-work/output/build/kernel/rust/mckernel_rust.o'
    receipt_path=B/'full-image-attempt-1/owner-work/evidence/receipt.json'
    receipt=json.loads(receipt_path.read_text())['artifacts']['mckernel_rust.o']
    assert baseline.stat().st_size==receipt['size']==13599104 and baseline.stat().st_size <= 32<<20
    profile=['/usr/bin/taskset','-c','0','/usr/bin/prlimit','--as=2147483648:2147483648','--cpu=60:60',
        '--fsize=33554432:33554432','--core=0:0','--nofile=256:256','--','/usr/bin/timeout','--kill-after=6s','90s']
    report=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
        status='CORRECTED_EXACT_PINNED_HOST_COMMAND_NOT_ADMITTED_TO_ONE_JOB_PROFILE',
        original_recipe=original['exact_saved_container_command'],validated_prefix=tokens[:3],
        original_container_cwd=tokens[1],explicit_fresh_HOST_cwd=str(work),
        argv_without_shell=argv,prepared_profile_argv=profile+argv,
        semantic_diff={'remove_exact_shell_cwd_prefix':tokens[:3],
            'replace_only_exact_accepted_mount_output_tokens':exact_map,
            'all_other_compiler_sysroot_target_cfg_codegen_flags_unchanged':True,
            'debug_source_output_cwd_paths_differ_no_object_bit_identity_claim':True},
        shell_execution=False,remaining_shell_operators_or_unexpanded_variables=False,
        required_new_output=str(out),output_namespace_created=False,
        compiler_environment_extra={'RUST_MIN_STACK':'2097152'},
        baseline_actual_emitted_object=receipt,baseline_observed_size_bytes=baseline.stat().st_size,
        baseline_within32MiB=True,candidate_object_size_AS_CPU_fit_unobserved=True,
        explicit_production_codegen_units_flags=codegen,production_CGU1_confirmed=codegen==['codegen-units=1'],
        compatible_ordinary_one_job_profile_proven=False,
        decision='Saved production recipe has no explicit CGU1. Do not add CGU1 or assert one-job compatibility; retain exact flags and use the existing pinned4CPU/12GiB operation unless root reviews a separate compatible bounded host grant. No compiler execution until CPU0 SDK prep wholejoin and an explicit grant.',
        capture_helper='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8; require joined group/closed streams if separately granted',
        compiler_executed=False,pinned_container_operation_unchanged=True)
    p=D/'EXACT-PINNED-HOST-RUST-CANDIDATE.CORRECTED.NOT-RELEASED.json'
    with p.open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({'status':report['status'],'baseline_bytes':baseline.stat().st_size,'CGU1_confirmed':report['production_CGU1_confirmed'],'argv_elements':len(argv),'compiler_executed':False}))

if __name__=='__main__':main()
