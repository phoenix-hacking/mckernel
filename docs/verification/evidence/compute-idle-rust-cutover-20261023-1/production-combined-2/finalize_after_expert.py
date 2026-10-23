#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Expert-prescribed compact request correction; never restart source preparation.
No compiler, build, root, Docker, guest or Git operation.
"""
from pathlib import Path
import hashlib
import json
import os

D=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-2')
S=H/'source-materialization-attempt-2'
B=Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'

def canonical(x):return (json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def ref(p):
    b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')


def main():
    pins={
      'native_rust_exact_build_offline.py':'1be3a017e2ae47a0d1ecfcd4e1d22d7d8d569808e495d2b6d055c851d0582ae2',
      'native_rust_exact_mckernel_image_offline.py':'46b426530bbde4054d19af52fc815aece237e20b84031a2594c1575a0dbe5942',
      'native_rust_exact_mckernel_image_container_owner.py':'e95e41a3fe7d3abadf996b16414312cb943627773ce78bf50df2c9039009d4ce',
      'gitlink-inputs.json':'90e47ec6945238a664193ac499672af5d4ebdb9b8f7c07ef7a3384fa42123920'}
    for name,pin in pins.items():assert ref(H/name)['sha256']==pin,'existing generated source drift'
    assert (H/'image-request.STATIC-DATA.json').stat().st_size==32<<20
    # Never read/parse either truncated failed request/manifest. Reconstruct
    # exactly the accepted original plus the unchanged named field transform.
    static=json.loads((B/'image-request.STATIC-DATA.json').read_text())
    manifest=json.loads((S/'source-inputs.json').read_text())
    mh=ref(S/'source-inputs.json')['sha256']
    assert mh=='9b86c84a92133678171b3e476560bcdfc99070f727b9c11c764de7092de8b88c'
    before_keys=('source_root','source_manifest','source_manifest_sha256','source_derivative_sha256','materialization_sha256','driver_path','driver_sha256','provenance_path','provenance_sha256','gitlink_manifest','gitlink_manifest_sha256','work_root','output_root','evidence_root','owner_evidence_root','attempt_root','lease_path','common_exclusion_path','memory_allocation_roots')
    before_fields={k:static[k] for k in before_keys}
    old_attempt=B/'full-image-attempt-1';new_attempt=H/'pinned-full-image-attempt-1'
    for k in ('work_root','output_root','evidence_root','owner_evidence_root','attempt_root','lease_path','common_exclusion_path'):
        assert static[k].startswith(str(old_attempt)+'/')
        static[k]=str(new_attempt)+static[k][len(str(old_attempt)):]
    static.update(source_root=str(S/'materialized-source'),source_manifest=str(S/'source-inputs.json'),
        source_manifest_sha256=mh,source_derivative_sha256=manifest['source_derivative_sha256'],
        materialization_sha256=manifest['materialization_sha256'],
        driver_path=str(H/'native_rust_exact_mckernel_image_offline.py'),driver_sha256=pins['native_rust_exact_mckernel_image_offline.py'],
        provenance_path=str(H/'native_rust_exact_build_offline.py'),provenance_sha256=pins['native_rust_exact_build_offline.py'],
        gitlink_manifest=str(H/'gitlink-inputs.json'),gitlink_manifest_sha256=pins['gitlink-inputs.json'])
    static['memory_allocation_roots']=[str(S/'materialized-source'),str(new_attempt/'owner-work'),str(new_attempt/'owner-evidence'),static['gitlink_root']]
    for k in ('source_identity','disk_identity','backup_identity'):assert static[k] is None
    assert static['disk_admission']['host_device'] is None and static['disk_admission']['scratch_device'] is None
    output=H/'image-request.STATIC-DATA.expert-compact1.json'
    encoded=canonical(static)
    assert len(encoded)<=32<<20,'expert fixed32MiB envelope includes newline'
    fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(encoded);stream.flush();os.fsync(stream.fileno())
    observed=output.read_bytes()
    assert observed==encoded and canonical(json.loads(observed))==observed and json.loads(observed)==static
    static_ref=ref(output)
    write(D/'EXPERT-COMPACT-REQUEST-CORRECTION.json',dict(scope=SCOPE,
        expert='/root/p12_successor_review',prescription='Fresh filename; reconstruct accepted original+identical named field transform only; canonical compact sortedJSON+newline; no limit increase or wholeprepare restart; prebound bytes+exclusive create+fsync+reread exacthash/roundtrip.',
        status='PASS_SOURCE_DATA_SERIALIZATION_ONLY',static_request=static_ref,
        MAX_bytes=32<<20,bytes_measured_before_write=len(encoded),canonical_roundtrip=True,
        source_files_rewritten=False,request_fields_changed_by_encoding=False,
        truncated_request_retained_path=str(H/'image-request.STATIC-DATA.json'),truncated_request_bytes=32<<20,
        source_first_failure=str(H/'materialization.stderr'),request_failure=str(H/'prepare-operation.stderr')))
    write(D/'REQUEST-FIELD-DELTA.json',dict(scope=SCOPE,before=before_fields,
        after={k:static[k] for k in before_keys},inventories_and_toolchain_unchanged=True,
        current_geometry='CURRENT110GiB; pending142growth is not a prerequisite',
        still_unreleased_fields=['source_identity','disk_identity','backup_identity','disk_admission.host_device','disk_admission.scratch_device','fresh all-lane allocation/capacity/physical-predecessor+existing independent one-shot release']))
    binding=json.loads((B/'BUILD-BINDING.json').read_text())
    cohort={name:ref(H/name) for name in pins}
    operation=dict(scope=SCOPE,status='EXACT_CURRENT110_PINNED_OPERATION_PREPARED_FOR_FOCUSED_REVIEW',
        geometry='CURRENT110GiB; pending142growth must not block this operation',execution_released=False,
        one_heavy_operation=True,outer_argv=['/home/holden/anaconda3/bin/python3','-I','-B',
            str(H/'native_rust_exact_mckernel_image_container_owner.py'),str(H/'image-request.FINAL.json')],
        final_request_rule='Start exact expert compact static request. Fill only typed-null current source/disk/backup and host/scratch device identities; bind fresh current110 UUID/loop/backing/aggregate capacity, exact accepted physical predecessor and existing reviewed one-shot shared-heavy release. Do not alter frozen source/toolchain/gitlink pins or inventories. Root publishes exact final request and release before execution.',
        static_request=static_ref,source_manifest=ref(S/'source-inputs.json'),
        source_derivative_sha256=manifest['source_derivative_sha256'],materialization_sha256=manifest['materialization_sha256'],
        production_sources=cohort,unchanged_host_owner=binding['production_four_source_cohort']['fixed_host_owner'],
        toolchain=binding['actual_toolchain'],profile=binding['reviewed_heavy_profile'],
        pinned_inner_commands=binding['exact_inner_commands'],
        additional_actual_compile='One whole selected memory.c TU using its actual generated GCC14 row. Existing configured selected/fallback process TU and native/legacy full Rust gates are preserved/reused; no new vector suite and no extra full Rust compile.',
        required_new_production_observations='Selected memory PP excludes original C old-action/output/phys-to-virt bodies; paired ABI/flag witnesses compile. Actual DEFAULT process/memory objects import/relocate to selected Rust helpers. Actual full Rust object and final image define selected idle/two memory callback providers uniquely, no final undefineds, object identities rechecked through receipt.',
        fresh_output=str(new_attempt),frozen10972_modified=False,canonical_sources_modified=False,
        full_pinned_build_or_native_accepted=False,
        current_prerequisite='Focused independent review of exactly three produced production sources/diffs and compact request data; root fresh admission/release at genuinely free heavy boundary. Yield to eligible critical235/227.',
        exact_host_pinned_Rust_candidate=ref(D/'EXACT-PINNED-HOST-RUST-CANDIDATE.NOT-EXECUTED.json'),
        host_route_decision='Exact compiler+sysroot are retained and path-only substituted argv is prepared;2GiB/CPU60/runtime fit has not been observed. Do not substitute1.92/GCC9 or add CGU1. Current selected operation uses the existing pinned4CPU/12GiB container profile.',
        remaining_after_build='Independent linked-artifact/default-consumer acceptance and matching native idle/clear-range/phys-to-virt behavior. No helper-only, whole-area, whole-kernel or practical35 credit.')
    write(D/'EXACT-PRODUCTION-OPERATION.PROPOSED.json',operation)
    write(D/'PREPARATION-RESULT.json',dict(scope=SCOPE,status='PASS_COHERENT_FIVE_POSTIMAGES_AND_EXACT_PINNED_CHAIN_PREPARATION_ONLY',
        source_manifest_sha256=mh,source_derivative_sha256=manifest['source_derivative_sha256'],materialization_sha256=manifest['materialization_sha256'],
        source_entries=6959,exact_postimages_vs_frozen10972=5,compiler_runs=0,builds=0,root_Docker_guest=0,
        production_default_link_and_native='OPEN',source_copy_seconds=json.loads((S/'MATERIALIZATION-RESULT.json').read_text())['seconds'],
        original_FS8_manifest_EFBIG_and_FS32_pretty_request_EFBIG_retained=True,
        expert_compact_correction=ref(D/'EXPERT-COMPACT-REQUEST-CORRECTION.json'),
        bindings=[ref(D/'EXACT-PRODUCTION-OPERATION.PROPOSED.json'),static_ref,ref(Path(__file__))]))
    print(json.dumps(dict(status='PASS_PREPARED_FOR_REVIEW_ONLY',static_request=static_ref,
        operation=ref(D/'EXACT-PRODUCTION-OPERATION.PROPOSED.json')),sort_keys=True))


if __name__=='__main__':main()
