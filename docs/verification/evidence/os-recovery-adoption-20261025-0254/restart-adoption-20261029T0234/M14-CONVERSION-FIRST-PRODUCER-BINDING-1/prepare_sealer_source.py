#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private sealer adaptation; not an invocation or execution authority.
"""
from pathlib import Path
import ast,difflib,json,hashlib
D=Path(__file__).resolve().parent;A=D.parent
P=A/'M14-WEEKLY-OPERATION-CONSUMER-SOURCE-1/actual-weekly-binding-source-1/LIVE-REVALIDATION-CAP-CORRECTION-1/current119'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
old=(P/'seal_root_current119_inputs.py').read_text();s=old
s=s.replace('BIND_CURRENT119_PRODUCER_SOURCE_INPUTS_ONLY','BIND_CONVERSION_FIRST_PRODUCER_SOURCE_INPUTS_ONLY')
s=s.replace("'control_bundle','cutoffs'}", "'control_bundle','cutoffs','candidate_snapshot_manifest','reuse_descriptor'}")
s=s.replace("'origin_receipt','armed_controls','control_bundle']:auth(q[key])", "'origin_receipt','armed_controls','control_bundle','candidate_snapshot_manifest','reuse_descriptor']:auth(q[key])")
a=s.index(' accepted.accepted_metadata(q,free,ledger)');b=s.index(" assert re.fullmatch('[0-9a-f]{32}'",a)
s=s[:a]+''' # Preserve the previously accepted full Root65 chain, then authenticate the
 # separately independently reviewed Root68 successor boundary and full ledger.
 oldq=read(auth(OLD_ROOT_INPUT)); oldfree=read(auth(oldq['current_free'])); oldledger=read(auth(oldq['current_ledger']))
 accepted.accepted_metadata(oldq,oldfree,oldledger); accepted.accepted_chain(oldq)
 assert q['current_free']==ROOT68_FREE and q['current_ledger']==ROOT68_LEDGER and q['current_bindings']==ROOT68_BOUNDARY
 boundary=read(auth(q['current_bindings'])); review=read(auth(ROOT68_REVIEW))
 assert boundary['nonce_ledger']==q['current_ledger'] and boundary['native_custody_clearance']==q['current_free'] and boundary['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
 assert review['decision']=='PASS_EXACT_ROOT68_CURRENT119_CURRENT_BOUNDARY_ADOPTION' and review['independent'] is True and review['implementation_ownership'] is False
 assert review['nonce_ledger']==q['current_ledger'] and review['current_boundary']==q['current_bindings'] and review['independent_current_free']==q['current_free']
 assert all(review['checks'].values()) and len(ledger['consumed_nonces'])==73 and ledger['latest_accepted_free_boundary']==q['current_free'] and ledger['current_physical_clearance_pending'] is False
''' +s[b:]
a=s.index('def render_sources(')
s=s[:a]+'''def render_sources(limits,guard_ref):
 accepted.CUTOFF.positive_triplet(limits)
 runner=(HERE/'run_build_only.template.py').read_text(); worker=(HERE/'build_only_worker.template.py').read_text()
 start=runner.index('RUNTIME_GUARD_REF=');end=runner.index('\\n',start);runner=runner[:start]+'RUNTIME_GUARD_REF='+repr(guard_ref)+runner[end:]
 start=runner.index('CUTOFFS=');end=runner.index('\\n',start);runner=runner[:start]+'CUTOFFS='+repr(limits)+runner[end:]
 start=worker.index('CUTOFFS=');end=worker.index('\\n',start);worker=worker[:start]+'CUTOFFS='+repr(limits)+worker[end:]
 return runner,worker

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root-input',type=Path,required=True);parser.add_argument('--root-input-sha256',required=True);args=parser.parse_args()
 assert ref(args.root_input)['sha256']==args.root_input_sha256
 q=read(args.root_input);limits,generated=validate_root(q)
 request=read(auth(q['request']));assert request['author']=='/root' and request['runtime_authority'] is None and request['candidate']==CANDIDATE and request['recipe']==RECIPE and request['snapshot_map']==SNAPSHOT_MAP
 profile=read(auth(PROFILE119));affected=read(auth(AFFECTED)); recipe=read(auth(RECIPE));mapping=read(auth(SNAPSHOT_MAP))
 manifest=read(auth(q['candidate_snapshot_manifest']));root=Path(manifest['export_root'])
 assert manifest['schema']=='mckernel.exact-kernel-rust-subtree-readonly.v1' and manifest['runtime_authority'] is None and manifest['container_destination']=='/src/kernel/rust'
 assert manifest['base_source_root']==profile['inputs']['source6153']+'/kernel/rust' and root.is_absolute() and root.is_dir() and not root.is_symlink()
 assert manifest['external_inputs']==profile['inputs']['external_relative_modules'] and len(manifest['files'])==149
 expected={r['relative']:r['source'] for r in mapping['entries']};actual={}
 for row in manifest['files']:
  relative=Path(row['relative']);assert not relative.is_absolute() and '..' not in relative.parts and str(relative)==row['relative'] and row['relative'] not in actual
  assert row['snapshot']['path']==str(root/relative);auth(row['snapshot'])
  source=expected[row['relative']];assert row['snapshot']['sha256']==source['sha256'] and row['snapshot']['bytes']==source['bytes'];actual[row['relative']]=row['snapshot']
 assert set(actual)==set(expected) and all(not p.is_symlink() for p in root.rglob('*'))
 assert {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}==set(expected)
 profile.update(request_sha256=q['request']['sha256'],actual_nonce=q['nonce'],native_custody_clearance=q['current_free'],fixed_three_clock_cutoffs=limits,deadline_epoch=limits[0],origin_source_materialization=generated,source_preparation_current_context=dict(current_ledger=q['current_ledger'],current_free=q['current_free'],armed_controls=q['armed_controls'],runtime_guard=q['runtime_guard'],runtime_guard_source_review=q['runtime_guard_source_review'],current_bindings=q['current_bindings'],control_bundle=q['control_bundle'],cutoffs=limits))
 profile['status']='CONVERSION_FIRST_INPUTS_BOUND_NOT_EXECUTION_RELEASE';profile['runtime_authority']=None
 profile['exact_commands']=recipe['ordered_commands'];profile['reuse_descriptor']=q['reuse_descriptor']['path']
 profile['inputs']['source_directory_exports']=[dict(host_path=str(root),container_destination='/src/kernel/rust',readonly=True,manifest=q['candidate_snapshot_manifest'])]
 overlay={r['target']:r['source'] for r in affected['file_overlay']}
 for row in profile['inputs']['postimages']:
  if row['relative'] in ('kernel/syscall.c','kernel/CMakeLists.txt'):row['postimage']=overlay[row['relative']]
  elif row['relative'].endswith('/f06_rt_sigreturn_origin.h'):row['postimage']=generated['actual_generated_header']
  elif row['relative'].endswith('/f06_clone_cpuid_metadata.rs'):row['postimage']=generated['actual_generated_metadata']
 retained={r['link_token']:r['source'] for r in recipe['retained_inputs']}
 for row in profile['inputs']['objects']:
  if row['link_token'] in retained:row['replace']=False;row['source']=retained[row['link_token']]
  else:row['replace']=True
 profile['inputs']['retained_count']=9;profile['inputs']['replaced_count']=2
 profile['producer_contract']['new_objects']=['rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/syscall.c.o'];profile['producer_contract']['reused_objects']=9
 profile['producer_contract']['process_delta']='Accepted CURRENT119 process and arch objects retained; new Rust crate and generic syscall C only.'
 profile['cohort_source_bindings']=[dict(relative=r['relative'],postimage=r['postimage']) for r in profile['inputs']['postimages']]+[dict(relative='kernel/rust/'+r['relative'],postimage=r['snapshot']) for r in manifest['files']]
 runner,worker=render_sources(limits,q['runtime_guard']);assert not any((HERE/name).exists() for name in ['run_build_only.py','build_only_worker.py','PROFILE.SOURCE-ONLY.json','ROOT-SOURCE-BINDING.ACTUAL.json'])
 ast.parse(runner);ast.parse(worker)
 write('run_build_only.py',runner);write('build_only_worker.py',worker);write('PROFILE.SOURCE-ONLY.json',profile)
 write('ROOT-SOURCE-BINDING.ACTUAL.json',dict(scope=SCOPE,status='ROOT_EXACT_CONVERSION_FIRST_SOURCE_DATA_SEALED_NOT_EXECUTION_AUTHORITY',root_input=ref(args.root_input),runner=ref(HERE/'run_build_only.py'),worker=ref(HERE/'build_only_worker.py'),profile=ref(HERE/'PROFILE.SOURCE-ONLY.json'),runtime_guard=q['runtime_guard'],cutoffs=limits,runtime_authority=None))
 print(json.dumps(read(HERE/'ROOT-SOURCE-BINDING.ACTUAL.json')))
if __name__=='__main__':main()
'''
# Fully-bound fixed predecessor evidence; freshness and active ownership are
# independently required at execution, never inferred from this history.
def rr(rel):return ref(A/rel)
constants={
 'OLD_ROOT_INPUT':ref(P/'ROOT-CURRENT119-INPUT.ACTUAL.json'),
 'ROOT68_FREE':rr('CURRENT119-POSTJOIN-CURRENTFREE-PREPARATION-1/actual-acceptance-1/CURRENT-FREE.ACTUAL.json'),
 'ROOT68_LEDGER':rr('ROOT68-CURRENT119-ADOPTION-1/ROOT68-NONCE-LEDGER.ACTUAL.json'),
 'ROOT68_BOUNDARY':rr('ROOT68-CURRENT119-ADOPTION-1/ROOT68-CURRENT-BOUNDARY.ACTUAL.json'),
 'ROOT68_REVIEW':rr('ROOT68-CURRENT119-ADOPTION-1/independent-review-1/ADOPTION-REVIEW.ACTUAL.json'),
 'CANDIDATE':rr('M14-CONVERSION-FIRST-COMPOSITION-1/SOURCE-READY.json'),
 'AFFECTED':rr('M14-CONVERSION-FIRST-COMPOSITION-1/AFFECTED-UNIT-CANDIDATE-INPUTS.json'),
 'RECIPE':ref(D/'THREE-COMMANDS.SOURCE-ONLY.json'),
 'SNAPSHOT_MAP':ref(D/'SNAPSHOT-INPUT-MAP.SOURCE-ONLY.json'),
 'PROFILE119':ref(P/'PROFILE.SOURCE-ONLY.json')}
insert='\n'.join(k+'='+repr(v) for k,v in constants.items())+'\n'
s=s.replace("INITIAL=NEWSC/'EARLIEST-CONTROL-CAPS.json'", "INITIAL=NEWSC/'EARLIEST-CONTROL-CAPS.json'\n"+insert)
ast.parse(s)
(D/'seal_root_conversion_inputs.py').write_text(s)
(D/'seal_root_conversion_inputs.py.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='a/seal_root_current119_inputs.py',tofile='b/seal_root_conversion_inputs.py')))
(D/'accepted_bindings.py').write_bytes((P/'accepted_bindings.py').read_bytes())
print('PASS_STATIC_SEALER_SOURCE_GENERATION')
