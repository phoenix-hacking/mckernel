"""One current metadata path: fresh parent, actual verify, existing nineteen roles.
External ordinary grant required. This emits metadata, never a native release.
"""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import os
import runpy
import subprocess
import sys
sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parent
P = SOURCE.parent

def need(ok, why):
    if not ok: raise ValueError(why)

def ref(path):
    p=Path(path); raw=p.read_bytes()
    return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def write(path, value):
    with path.open('x') as f:
        os.fchmod(f.fileno(),0o600);json.dump(value,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())

def materialize(context,static,proof,fixture_only=False):
    spec=importlib.util.spec_from_file_location('current_m02_contract_materializer',SOURCE/'current_m02_contract.py')
    contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)
    data=contract.checked(context['case_data'])
    need(bool(context.get('fixture_only',False))==fixture_only and bool(data.get('fixture_only',False))==fixture_only,'fixed production/fixture role')
    contract.read_source(data,context['stage_acceptance'],context['normalization_acceptance'])
    outputs=[Path(x) for x in data['final19_outputs']]
    need(len(outputs)==19 and len(set(outputs))==19,'exact19')
    for path in outputs+[Path(x) for x in data['capture_paths']]:need(not os.path.lexists(path),'all current nineteen/capture paths absent')
    # Exact earlier fixed parent entry now consumed by this complete path, not a stopping point.
    parent_script=P/'prepare_current_parent_once.py'
    need(ref(parent_script)=={k:context['parent_metadata_entry'][k] for k in ('path','bytes','sha256')},'fixed current parent metadata entry')
    pspec=importlib.util.spec_from_file_location('current_m02_real_parent_implementation',parent_script)
    parent_impl=importlib.util.module_from_spec(pspec);pspec.loader.exec_module(parent_impl)
    parent_impl.prepare(context['case_data']['path'],context['case_data']['sha256'],context['fresh_metadata_result'],Path(data['prospective_parent']),fixture_only)
    freshref=ref(context['fresh_metadata_result'])
    bundle=contract.read(context['case_data'],freshref,context['stage_acceptance'],context['normalization_acceptance'],proof,require_publication=not fixture_only,allow_fixture=fixture_only)
    fresh=bundle['fresh'];pre=bundle['preflight'];binding=bundle['binding']
    seed=contract.checked(context['seed_static_inputs'])
    c=dict(seed)
    owner=Path(data['current_owner']['path']);tree=ast.parse(owner.read_bytes())
    authority=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCE_HASHES' for t in n.targets)))
    sourcepaths=list(dict.fromkeys([x['path'] for x in seed['runtime_source_refs']]+[str(p) for p in SOURCE.iterdir() if p.is_file()]+[str(P/'CURRENT-CASE-DATA.reader-bound.json'),freshref['path']]))
    sourcerefs=[ref(p) for p in sourcepaths]
    need(not set(sourcepaths)&set(data['final19_outputs']),'source/output disjoint')
    ro=[]
    for i,arg in enumerate(pre['container_create_argv'][:-1]):
        if arg=='--mount':
            fields=pre['container_create_argv'][i+1].split(',')
            if fields[0]=='type=bind' and 'readonly' in fields:ro.append(next(x[4:] for x in fields if x.startswith('src=')))
    c.update(current_case_data=context['case_data'],actual_fresh_parent_result=freshref,current_profile=data['profile'],
        actual_preparation_acceptance=ref(data['actual_source_closure_acceptance']['path']),actual_binding_result=freshref,
        actual_full_preflight=freshref,binding=binding,whole_manifest=binding['manifest'],normalized_manifest=binding['manifest'],
        accepted_owner_argv=pre['owner_argv'],root_owner_argv=data['prospective_root_owner_argv'],inside_argv=pre['inside_owner_argv'],
        container_create_argv=pre['container_create_argv'],qemu_argv=pre['qemu_argv'],AF_UNIX=[dict(option='-qmp',path=pre['paths']['qmp_socket'],encoded_bytes=99)],
        parent_identity=bundle['parent_legacy'],parent_nine_field_identity=bundle['parent_stat_fields'],runtime_owner=ref(owner),runtime_source_hashes=authority,
        runtime_runner=ref(data['unchanged_absolute_RUNNER']['path']),runtime_observer=ref(data['unchanged_absolute_bound_manifest_diagnostic']['path']),
        runtime_source_refs=sourcerefs,consumed_paths=sourcepaths,readonly_roots=ro,fetched_runtime_proof=proof,
        whole_boundary_freeze=ref(SOURCE/'CURRENT-SOURCE-CONTEXT.json'),actual_stage_acceptance=context['stage_acceptance'],
        latest_physical=ref(data['latest_exclusive_physical']['path']),latest_exclusive_physical=ref(data['latest_exclusive_physical']['path']),
        physical_reader_kind=data.get('physical_reader_kind','NATIVE_POSITIVE'),physical_projection_source=ref(bundle['physical_reader_source']['path']),physical_consumer_context=ref(bundle['physical_reader_context']['path']),
        physical_consumer_actual_acceptance=ref((data['failed_native_reader_actual_acceptance'] if data.get('physical_reader_kind')=='CURRENT_CHILD_FAILED_NATIVE' else data['positive_reader_actual_acceptance'])['path']),root_caller=data['existing_exact_root_decoder'],
        source_only_adapter=ref(SOURCE/'root_manual_snapshot_m03.py'),final_guard=ref(SOURCE/'review_final_205_release.py'),
        status='ACTUAL_CURRENT_M02_METADATA_PENDING_INDEPENDENT_WHOLE_RESULT_REVIEW',runtime_release=None)
    I=Path(context['input_namespace']);Q=Path(data['output_namespace'])
    need(not I.exists() and not Q.exists(),'fresh current metadata namespaces')
    I.mkdir(mode=0o700);Q.mkdir(mode=0o700)
    write(I/'STATIC-M03-NONTEMPORAL-INPUTS.SCHEMA-CORRECTED.json',c)
    # Existing binder consumes the same exact seven-row seed, relocated once.
    write(Q/'MANUAL-READBACK-CONTRACT.json',contract.checked(context['manual_failure_readbacks']))
    A=c['actual_preparation_acceptance'];physical=c['latest_physical']
    binder_argv=['/usr/bin/python3','-I','-B',str(SOURCE/'bind_m03_handshake_native_packet.py'),A['path'],A['sha256'],physical['path'],physical['sha256']]
    if not fixture_only:binder_argv += [static['path'],static['sha256']]
    nested_binder=subprocess.run(binder_argv,check=True,timeout=20)  # Inherited owned process group/limits; no setsid.
    need(all(path.is_file() for path in outputs),'all exact current19 outputs materialized')
    seven=json.loads((Q/'FINAL-SEVEN-ROOT-CALL-DATA.json').read_bytes())
    need(seven['fresh_capture_and_actual_command_paths']==data['capture_paths'],'whole current49 capture namespace')
    for path in data['capture_paths']:need(not os.path.lexists(path),'root captures remain unrun')
    for name in ('root-live-preflight-1.json','execution-release.json','FINAL-205-MATCHED-SDK-NATIVE-MACHINE-REVIEW.json'):
        need(not os.path.lexists(Q/name),'no future snapshot/machine/guard minted')
    # Exercise real generated bindings through actual LAST static_joins before privilege.
    rootspec=importlib.util.spec_from_file_location('current_m02_LAST_actual_generated_joins',SOURCE/'root_manual_snapshot_m03.py')
    last=importlib.util.module_from_spec(rootspec);rootspec.loader.exec_module(last)
    bindings=json.loads((Q/'ROOT-SNAPSHOT-BINDINGS.json').read_bytes())
    if fixture_only:last.fixture_static_joins(bindings)
    else:last.static_joins(bindings)
    write(P/'ACTUAL-CURRENT-M02-NINETEEN-WHOLE-RESULT.json',dict(status=('PASS_FIXTURE_NINETEEN_AND_ACTUAL_JOIN_BODIES_ONLY' if fixture_only else 'PASS_CURRENT_METADATA_NINETEEN_AND_GENERATED_LAST_STATIC_JOINS_ONLY'),fixture_only=fixture_only,
        nested_binder=dict(argv=binder_argv,returncode=nested_binder.returncode,direct_joined=True,process_group_inherited=True),actual_fresh_parent=freshref,final19=[ref(x) for x in outputs],capture_paths=data['capture_paths'],
        generated_LAST_static_joins=True,source_review=static,fetched_proof=proof,LAST_snapshot=None,runtime_release=None,root_operations=0,guest_runs=0))
    print(json.dumps(dict(status=('PASS_FIXTURE_NINETEEN_AND_ACTUAL_JOIN_BODIES_ONLY' if fixture_only else 'PASS_CURRENT_METADATA_NINETEEN_AND_GENERATED_LAST_STATIC_JOINS_ONLY'),fixture_only=fixture_only,final19=19,captures=49,LAST_snapshot=None,runtime_release=None)))

def main():
    need(len(sys.argv)==5,'STATIC_REVIEW SHA256 FETCHED_SOURCE_PROOF SHA256')
    static=ref(sys.argv[1]);need(static['sha256']==sys.argv[2],'exact independent source decision')
    decision=json.loads(Path(static['path']).read_bytes())
    need(decision['status']=='PASS' and decision['implementation_ownership'] is False,'independent source/data review')
    proof=ref(sys.argv[3]);need(proof['sha256']==sys.argv[4],'exact actual fetched proof')
    proofbody=json.loads(Path(proof['path']).read_bytes())
    need(proofbody.get('verified') is True and proofbody.get('commit')==proofbody.get('fetched_commit'),'genuine fetched source proof')
    context=json.loads((SOURCE/'CURRENT-SOURCE-CONTEXT.json').read_bytes())
    need(not context.get('fixture_only',False),'fixture context cannot enter production wrapper')
    materialize(context,static,proof,False)

if __name__=='__main__':main()
