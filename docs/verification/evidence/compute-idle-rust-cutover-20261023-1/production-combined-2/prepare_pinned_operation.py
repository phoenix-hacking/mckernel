#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Reuse the accepted production chain with exact manifest/pin/namespace successors.
Source and data preparation only; no compiler, build, Docker, root, guest or Git.
"""
from pathlib import Path
import ast
import copy
import difflib
import hashlib
import json

D=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-2')
S=H/'source-materialization-attempt-2'
B=Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1')
OLD_MANIFEST='28a6c1dededda19d2da07279f9a59d542996ae77bd96d176567cc86f0c5a8459'
PINS={'native_rust_exact_build_offline.py':'4865b6c91aae8e9f0b30027c9e63c1551ea37ad23ae13cff952eaf2f5ca541f9',
      'native_rust_exact_mckernel_image_offline.py':'801ced380bad545215ec42ad5a07d4180df923c9888a3b75adee3a16070217ae',
      'native_rust_exact_mckernel_image_container_owner.py':'3c6f79631ad7de19ed15e40eb87c4426150bc904b4b9379fa3fadba10c7edf28'}
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'

def canonical(x):return (json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def checksum(x):return hashlib.sha256(x).hexdigest()
def ref(path):
    b=path.read_bytes();return dict(path=str(path),bytes=len(b),sha256=checksum(b))
def write(path,value):
    with path.open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def replace_exact(text,before,after,count=1):
    assert text.count(before)==count,(before,text.count(before),count)
    return text.replace(before,after)
def source(name,before,after):
    ast.parse(after,str(H/name))
    with (H/name).open('x') as f:f.write(after)
    with (D/(name+'.diff')).open('x') as f:
        f.write(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile=str(B/name),tofile=str(H/name))))
    return ref(H/name)


def main():
    materialization=json.loads((S/'MATERIALIZATION-RESULT.json').read_text())
    assert materialization['status']=='PASS_COHERENT_LATEST_FIVE_POSTIMAGE_SOURCE_MATERIALIZATION_ONLY'
    manifest=json.loads((S/'source-inputs.json').read_text())
    mh=checksum((S/'source-inputs.json').read_bytes())
    assert mh==materialization['source_manifest_canonical_sha256']==checksum(canonical(manifest))
    for name,pin in PINS.items():assert ref(B/name)['sha256']==pin
    old_prov=(B/'native_rust_exact_build_offline.py').read_text()
    prov=replace_exact(old_prov,"THIN_SCHEMA = 'mckernel.rust-fpu-sched-cutover-thin-inputs.v1'","THIN_SCHEMA = 'mckernel.m14-combined-production-thin-inputs.v1'")
    prov=replace_exact(prov,OLD_MANIFEST,mh)
    pr=source('native_rust_exact_build_offline.py',old_prov,prov)
    old_driver=(B/'native_rust_exact_mckernel_image_offline.py').read_text()
    driver=replace_exact(old_driver,PINS['native_rust_exact_build_offline.py'],pr['sha256'])
    driver=replace_exact(driver,'a400590c51d4badeca9af7f75fa2aaca2c15a7182020380fed79bdf9d007ac33','7203019d2ba8143f9240a03d11bc8c5cfcd495d89183aa7ab643c6159a6bd02d')
    driver=replace_exact(driver,'a5b8ed0f048adcfa6908094f7b8b5d459b9b14aa0ed4b75e5250abe6f8387c57','449df570965855f992a0fe024fca7cd6527b20622b4b8e3b33af04900b02e923',2)
    extension=(D/'m14_production_checks.inc.py').read_text()
    anchor='def _validate_owned_fork_current_sources(source_root):'
    driver=replace_exact(driver,anchor,extension+'\n\n'+anchor)
    anchor='    source_root = _canonical(source_root, "source root")\n    if native_fork_owned_transaction:'
    driver=replace_exact(driver,anchor,'    source_root = _canonical(source_root, "source root")\n    _validate_m14_source_pins(source_root)\n    if native_fork_owned_transaction:')
    anchor='                _validate_clone_affinity_production(source_root, build, tools, evidence, env, stdout, stderr, timeout, command_rows)'
    driver=replace_exact(driver,anchor,anchor+'\n                _validate_m14_selected_memory_TU(source_root, build, tools, evidence, env, stdout, stderr, timeout, command_rows)')
    anchor='        source_after = _validate_source(source_root, candidate_sha, ihk_sha, manifest,'
    driver=replace_exact(driver,anchor,'        m14_proof = _validate_m14_default_link(source_root, build, tools, evidence, env, timeout, command_rows)\n'+anchor)
    anchor='        result = {"production_rust_core_panic_reference_proof":production_rust_proof,'
    driver=replace_exact(driver,anchor,'        result = {"m14_combined_production_linkage":m14_proof, "production_rust_core_panic_reference_proof":production_rust_proof,')
    anchor='            _revalidate_link_contract_snapshots(build, evidence, link_snapshot)\n        _atomic_json(evidence / "receipt.json", result)'
    driver=replace_exact(driver,anchor,'            _revalidate_link_contract_snapshots(build, evidence, link_snapshot)\n            _revalidate_m14_objects(m14_proof)\n        _atomic_json(evidence / "receipt.json", result)')
    dr=source('native_rust_exact_mckernel_image_offline.py',old_driver,driver)
    old_owner=(B/'native_rust_exact_mckernel_image_container_owner.py').read_text()
    owner=replace_exact(old_owner,PINS['native_rust_exact_build_offline.py'],pr['sha256'])
    owner=replace_exact(owner,PINS['native_rust_exact_mckernel_image_offline.py'],dr['sha256'])
    owner=replace_exact(owner,str(B/'native_rust_exact_build_offline.py'),str(H/'native_rust_exact_build_offline.py'))
    old_attempt=B/'full-image-attempt-1'
    new_attempt=H/'pinned-full-image-attempt-1'
    owner=replace_exact(owner,str(old_attempt/'common-exclusion.json'),str(new_attempt/'common-exclusion.json'))
    owner=replace_exact(owner,'LIMITS = {',"RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(("+repr(str(old_attempt/'common-exclusion.json'))+",))\n\nLIMITS = {")
    ow=source('native_rust_exact_mckernel_image_container_owner.py',old_owner,owner)
    supplement=json.loads((B/'gitlink-inputs.json').read_text())
    assert supplement['base_manifest_sha256']==OLD_MANIFEST
    supplement['base_manifest_sha256']=mh
    write(H/'gitlink-inputs.json',supplement)
    # Preserve the existing exact toolchain/backup inventories without another
    # audit or rehash. Only named request fields/path prefixes advance.
    static=json.loads((B/'image-request.STATIC-DATA.json').read_text())
    before_fields={k:static[k] for k in ('source_root','source_manifest','source_manifest_sha256','source_derivative_sha256','materialization_sha256','driver_path','driver_sha256','provenance_path','provenance_sha256','gitlink_manifest','gitlink_manifest_sha256','work_root','output_root','evidence_root','owner_evidence_root','attempt_root','lease_path','common_exclusion_path','memory_allocation_roots')}
    for k in ('work_root','output_root','evidence_root','owner_evidence_root','attempt_root','lease_path','common_exclusion_path'):
        assert static[k].startswith(str(old_attempt)+'/')
        static[k]=str(new_attempt)+static[k][len(str(old_attempt)):]
    static.update(source_root=str(S/'materialized-source'),source_manifest=str(S/'source-inputs.json'),
        source_manifest_sha256=mh,source_derivative_sha256=manifest['source_derivative_sha256'],
        materialization_sha256=manifest['materialization_sha256'],driver_path=dr['path'],driver_sha256=dr['sha256'],
        provenance_path=pr['path'],provenance_sha256=pr['sha256'],gitlink_manifest=str(H/'gitlink-inputs.json'),
        gitlink_manifest_sha256=ref(H/'gitlink-inputs.json')['sha256'])
    static['memory_allocation_roots']=[str(S/'materialized-source'),str(new_attempt/'owner-work'),str(new_attempt/'owner-evidence'),static['gitlink_root']]
    # Actual per-directory identities and capacity remain typed-null, as in the
    # accepted static preparation. This JSON is not a live admission/release.
    for k in ('source_identity','disk_identity','backup_identity'):assert static[k] is None
    assert static['disk_admission']['host_device'] is None and static['disk_admission']['scratch_device'] is None
    write(H/'image-request.STATIC-DATA.json',static)
    write(D/'REQUEST-FIELD-DELTA.json',dict(scope=SCOPE,before=before_fields,after={k:static[k] for k in before_fields},
        inventories_and_toolchain_unchanged=True,current_geometry='110GiB, no142 prerequisite',
        still_unreleased_fields=['source_identity','disk_identity','backup_identity','disk_admission.host_device','disk_admission.scratch_device','fresh aggregate allocation/capacity and independent one-shot root release']))
    tools=json.loads(Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/image-toolchain.json').read_text())
    rustroot=next(Path(row['host_path']) for row in static['toolchain_roots'] if row['container_path']=='/nightly')
    rustc=rustroot/'bin/rustc'
    rust=ref(rustc)
    assert rust['sha256']==tools['mounted_tools']['rustc']['sha256']
    make=B/'full-image-attempt-1/owner-work/output/build/kernel/CMakeFiles/mckernel_rust_obj.dir/build.make'
    commands=[line.strip() for line in make.read_text().splitlines() if '/nightly/bin/rustc --crate-name mckernel_rust ' in line]
    assert len(commands)==1
    write(D/'EXACT-PINNED-RUST-HOST-AVAILABILITY.json',dict(scope=SCOPE,
        pinned_compiler=rust,pinned_container_descriptor=tools['mounted_tools']['rustc'],
        same_sysroot_host_root=str(rustroot),same_sysroot_is_existing_readonly_nightly_mount=True,
        exact_generated_container_command=commands[0],
        host_only_substitutions={'/nightly':str(rustroot),'/src':str(S/'materialized-source'),'/work/output':str(new_attempt/'owner-work/output')},
        original_cfg_and_target_flags_must_remain_identical=True,
        ordinary_2GiB_AS_CPU60_fit='NOT MEASURED. Fullcrate generated command has no CGU1 override; adding it would change the pinned flags. No ordinary compiler invocation made. Retained exact compiler/sysroot exist, but this is not an admitted resource-fit proof.',
        selected_route='One existing reviewed4CPU/12GiB pinned container operation, preserving all mandatory production gates. No alternate host compiler/target/sysroot.',
        cheaper_host_fullcrate_candidate_identified=True,cheap_host_route_released=False))
    binding=json.loads((B/'BUILD-BINDING.json').read_text())
    operation=dict(scope=SCOPE,status='EXACT_CURRENT110_PINNED_OPERATION_PREPARED_SOURCE_AND_DATA_ONLY',
        geometry='CURRENT110GiB; user142growth remains pending and is not a prerequisite',
        execution_released=False,one_heavy_operation=True,
        outer_argv=['/home/holden/anaconda3/bin/python3','-I','-B',ow['path'],str(H/'image-request.FINAL.json')],
        final_request_rule='Start the exact static request, fill only the typed-null current directory/device identities and fresh physical/capacity/release data required by the existing owner; preserve all frozen source/toolchain/cohort hashes and current110 UUID/loop/backing. Publish exact final request/source-independent one-shot release through existing dispatcher protocol before invocation.',
        static_request=ref(H/'image-request.STATIC-DATA.json'),source_manifest=ref(S/'source-inputs.json'),
        source_derivative_sha256=manifest['source_derivative_sha256'],materialization_sha256=manifest['materialization_sha256'],
        three_production_source_successors=[pr,dr,ow],unchanged_host_owner=binding['production_four_source_cohort']['fixed_host_owner'],
        gitlink_supplement=ref(H/'gitlink-inputs.json'),toolchain=binding['actual_toolchain'],profile=binding['reviewed_heavy_profile'],
        pinned_inner_commands=binding['exact_inner_commands'],
        new_observations='One additional actual selected GCC14 memory TU with paired C ABI/flag assertions and selected PP exclusion, existing actual process TU and full native/legacy Rust gates reused; actual DEFAULT process/memory object imports+relocations; unique Rust/final idle+two memory callback providers, no final undefineds, stable objects until receipt. No new helper-vector suite.',
        source_oracle_history='SourceFSIZE8MiB EFBIG before copying retained at materialization.stderr and truncated source-inputs.json. One correction uses fresh attempt2 with32MiB FSIZE. No production compiler attempt exists.',
        fresh_output=str(new_attempt),frozen10972_modified=False,canonical_sources_modified=False,
        no_native_or_whole_M14_retirement_credit=True)
    write(D/'EXACT-PRODUCTION-OPERATION.PROPOSED.json',operation)
    write(D/'PREPARATION-RESULT.json',dict(scope=SCOPE,status='PASS_SOURCE_MATERIALIZATION_AND_EXACT_PINNED_CHAIN_PREPARATION_ONLY',
        source_manifest_sha256=mh,source_derivative_sha256=manifest['source_derivative_sha256'],materialization_sha256=manifest['materialization_sha256'],
        source_entries=6959,exact_postimages_vs_frozen10972=5,AST_source_parse_only=True,compiler_runs=0,builds=0,root_Docker_guest=0,
        production_default_link_and_native='OPEN',bindings=[ref(D/'EXACT-PRODUCTION-OPERATION.PROPOSED.json'),ref(D/'EXACT-PINNED-RUST-HOST-AVAILABILITY.json'),ref(Path(__file__))]))
    print(json.dumps(dict(status='PASS_PREPARED_ONLY',source_manifest_sha256=mh,operation=ref(D/'EXACT-PRODUCTION-OPERATION.PROPOSED.json')),sort_keys=True))


if __name__=='__main__':main()
