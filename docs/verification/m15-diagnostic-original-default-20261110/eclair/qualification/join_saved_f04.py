#!/usr/bin/python3
"""Saved-data F04 join only. Run after Root confirms actual915 PASS/retirement."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

D = Path('/home/holden/mckernel-work/m15-original-integration-20261110T0708Z/eclair-matching-provider-build-1/original-default-qualification-sdk-max-1')
P = D / 'shared-provider-read-1'

def ref(path):
    blob = path.read_bytes()
    return {'path':str(path),'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest()}

def read_pinned(path, expected):
    identity = ref(path)
    if identity['sha256'] != expected:
        raise ValueError('frozen source input differs: '+str(path))
    return json.loads(path.read_text()), identity

def main():
    args = argparse.ArgumentParser()
    args.add_argument('--actual-root-result',type=Path,required=True)
    args.add_argument('--actual-root-result-sha256',required=True)
    args.add_argument('--output',type=Path,required=True)
    parsed = args.parse_args()
    # Root supplies the genuine terminal PASS receipt after direct/whole-family
    # and stream joins and exact owned removal. This script does not replace
    # the independent review of those outer lifecycle facts or release leases.
    outer, outer_ref = read_pinned(parsed.actual_root_result,parsed.actual_root_result_sha256)
    if not isinstance(outer.get('status'),str) or not outer['status'].startswith('PASS'):
        raise ValueError('no actual Root PASS receipt')
    if parsed.output.exists():
        raise ValueError('preserve any prior qualification output')
    assessment, assessment_ref = read_pinned(D/'ASSESSMENT.json','f3179f7529e923d48d347661bc2a565730e9b4248c03110d5f071519a61b5c36')
    request, request_ref = read_pinned(P/'REQUEST.json','915b7645297beab2acef5d07e5a808a104db51b817435dd29458feff8cfba9fd')
    spec, spec_ref = read_pinned(P/'INPUTS.json','8a74adb1b517006cd2305c1e154a0db04ff51af4f49d4ab4cb1fbb64df5fad49')
    report_path = P/'output-1/REPORT.json'
    report = json.loads(report_path.read_text())
    if report.get('status') != request['expected_status']:
        raise ValueError('actual provider receipt is incomplete/failed')
    provider_list = report['providers']
    if [x['id'] for x in provider_list] != ['zlib','libelf']:
        raise ValueError('actual exact provider envelope differs')
    zlib = provider_list[0]
    expected = spec['providers'][0]
    if zlib['caller_rows'] != expected['caller_rows']:
        raise ValueError('saved actual caller provenance differs')
    if not all(zlib.get(x) is True for x in ['runtime_link_same_file','same_runtime_devel_EVR_arch_source','identity_stable_after_metadata']):
        raise ValueError('actual file/package identity closure missing')
    runtime = zlib['runtime']
    if runtime['ELF'] != {'class':64,'little_endian':True,'type':3,'machine':62} or not re.fullmatch('[0-9a-f]{64}',runtime['sha256']):
        raise ValueError('actual provider ELF type/file digest differs')
    if not 0 < runtime['bytes'] <= spec['file_size_limit_bytes']:
        raise ValueError('actual provider file bounds differ')
    packages = zlib['package_headers']
    if [x['role'] for x in packages] != ['runtime','devel']:
        raise ValueError('actual RPM source relation missing')
    if packages[0]['fields'][:5] != expected['prior_runtime_package'] or packages[1]['fields'][:5] != expected['prior_devel_package'] or packages[0]['fields'][1:] != packages[1]['fields'][1:]:
        raise ValueError('actual matching RPM identity/source differs')
    if zlib['ELF_join']['SONAME'] != 'libz.so.1':
        raise ValueError('actual runtime SONAME differs')
    raw_path = P/'output-1/zlib-ELF.stdout'
    raw_lines = raw_path.read_text().splitlines()
    rows = []
    for caller in [x for x in expected['caller_rows'] if x['original_check']=='M15-F04-original-default']:
        matching = [x for x in zlib['ELF_join']['selected_definitions'] if x['required']=={'name':caller['name'],'required_version':caller['required_version']}]
        if len(matching) != 1:
            raise ValueError('missing exact actual F04 provider row')
        provider = matching[0]
        definition = provider['definition']
        version = provider['versym']
        if raw_lines.count(definition['raw']) != 1 or definition['section']=='UND' or definition['kind'] not in ['FUNC','IFUNC'] or definition['binding'] not in ['GLOBAL','WEAK'] or definition['visibility']!='DEFAULT':
            raise ValueError('raw actual callable definition not unique')
        required_version = caller['required_version']
        if required_version is not None:
            if version['name'] != required_version or provider['verdef'] != required_version:
                raise ValueError('exact caller/provider version differs')
        elif version['hidden'] or ('@' in definition['name'] and '@@' not in definition['name']):
            raise ValueError('unversioned caller lacks default provider')
        rows.append({'caller':caller,'actual_provider_definition':provider,'runtime':runtime,'package_headers':packages})
    if len(rows) != 6 or {x['caller']['name'] for x in rows} != {'compress','compressBound','inflate','inflateEnd','inflateInit_','inflateReset'}:
        raise ValueError('F04 source-selected closure differs')
    inner = report['owned_records']
    if [x['label'] for x in inner] != request['expected_six_owned_command_labels']:
        raise ValueError('six actual positive child records missing')
    for item in inner:
        if not (int(item['leader_birth'])>0 and item['status']==0 and item['leader_parent_joined'] and item['whole_descendants_joined'] and item['streams_closed']):
            raise ValueError('actual child lifecycle incomplete')
        if any(item.get(x) for x in ['adopted_reaps','adopted_kills','remaining_direct_children','error','timed_out','leader_group_signalled']):
            raise ValueError('actual child cleanup unresolved')
    new_needed = [x for x in zlib['ELF_join']['DT_NEEDED'] if x != 'libc.so.6']
    result = {'schema':'mckernel.M15-F04-original-default-post-provider-join.v1',
              'at_utc':datetime.now(timezone.utc).isoformat(),
              'original_check':'M15-F04-original-default',
              'whole_condition_decision':'DEMONSTRATED_AT_SUPPORTED_HOST_ARTIFACT_SCOPE_READY_FOR_INDEPENDENT_ORIGINAL_CONDITION_REVIEW' if not new_needed else 'NOT_YET_DEMONSTRATED_EXACT_ADDITIONAL_RUNTIME_DEPENDENCY_REVIEW_REQUIRED',
              'original_done_when':assessment['original_ledger']['done_when'],
              'whole_preassessment':assessment_ref,'request':request_ref,'inputs':spec_ref,
              'actual_Root_PASS_result':outer_ref,'actual_Root_status':outer['status'],
              'actual_provider_report':ref(report_path),'actual_zlib_raw_ELF':ref(raw_path),
              'all_six_current_F04_caller_provider_joins':rows,
              'source_profile_whole_tool_install_join':assessment['whole_condition_join'],
              'unchanged_complete_tool_and_independent_GO':assessment['evidence_reused'],
              'actual_inner_ownership':inner,
              'new_exact_DT_NEEDED_not_covered_by_existing_libc_proof':new_needed,
              'F03_handoff':{'report':ref(report_path),'JSON_pointer':'/providers/1','zlib_shared_rows_pointer':'/providers/0/ELF_join/selected_definitions','libelf_raw_ELF':ref(P/'output-1/libelf-ELF.stdout'),'libelf_audit_by_this_qualifier':False},
              'outer_lifecycle_gate':'Root actual terminal/positive direct+wholefamily/stream/owned-removal facts must be independently joined from the bound PASS receipt; no resource release is performed by this saved-data join.',
              'limits':assessment['source_backed_runtime_boundaries'],
              'ledger_acceptance_changed':False,'native_or_deployed_accepted':False,
              'old_UNKNOWN_owners_released':False,
              'operations':'Saved JSON/raw metadata only; no consumer/source/compiler/provider/tool/API/main/native replay.'}
    parsed.output.parent.mkdir(parents=True,exist_ok=True)
    with parsed.output.open('x') as target:
        json.dump(result,target,indent=2,sort_keys=True)
        target.write('\n')
    print(json.dumps(ref(parsed.output),sort_keys=True))

if __name__ == '__main__':
    main()
