"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root117 static materializer, retaining accepted116 holder/build/publication contracts.
No compiler/guest/controller. Actual guard is called only during Root materialization.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,re
D=Path(__file__).resolve().parent
P=D.parent
E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
ADMISSION_PARENT=E
CHECKOUT_ROOT=Path('/home/holden/mckernel')
S=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-next118-composition-restart-20261028-1')
def read(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):
 assert isinstance(r,dict) and set(r)=={'path','bytes','sha256'} and Path(r['path']).is_absolute() and ref(r['path'])==r
 return Path(r['path'])
def write(p,v):
 with Path(p).open('xb') as f:f.write(v if isinstance(v,bytes) else (json.dumps(v,indent=2)+'\n').encode())
def load_runner():
 spec=importlib.util.spec_from_file_location('current118_source_runner',D/'run_build_only.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def typed_boundary():
 row={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-next118-recursive-fixture-expert-20261028-1/next-current-boundary-successor-1/prepared118-current63-1/typed_current_boundary.py', 'bytes': 12354, 'sha256': '00483f2b97dbd03d76ee397ab9c80c050821ba1f705168d3606822b796e87514'}
 assert ref(row['path'])==row
 spec=importlib.util.spec_from_file_location('exact118_typed_boundary_core',row['path']);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def validate118(b):
 """Pure bindings/profile validation; no guard or writes. Used by TEST_ONLY too."""
 assert b['author']=='/root' and b['decision']=='MATERIALIZE_REVIEWED_CURRENT118_STATIC_INPUTS_AND_HOLDER_ONLY'
 assert b['maximum_invocations']==1 and b['root_attests_exact_UID1000_readonly_exports'] is True
 assert re.fullmatch('[0-9a-f]{32}',b['nonce'])
 manifest=read(auth(b['preparation_manifest']))
 for row in manifest['files']+manifest['external_inputs']:auth(row)
 boundary=read(auth(b['current_boundary']))
 assert boundary['author']=='/root' and boundary['decision']=='BIND_EXISTING_REVIEWED_CURRENT_BUILD_BOUNDARY' and boundary['root_attests_exact_current_boundary'] is True
 for key in ['nonce_ledger','native_custody_clearance','observer','independent_current_boundary_review','observer_schema','observer_schema_review']:auth(boundary[key])
 assert boundary['nonce_ledger']==b['nonce_ledger'] and boundary['native_custody_clearance']==b['native_custody_clearance']
 ledger=read(auth(b['nonce_ledger']));assert ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True and b['nonce'] not in ledger['consumed_nonces']
 baseline=read(E/'CURRENT116-ACCEPTED-ARTIFACT-AND-CURRENTFREE.json')
 assert baseline['actual_new_default_artifact']['image']['sha256']=='42473e03dae2310cb444008f4a46e84b3da87b00e4b2e2ab008f2637abbdc2c4'
 typed_boundary().validate_root_context(b,{'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-next118-recursive-fixture-expert-20261028-1/next-current-boundary-successor-1/prepared118-current63-1/UPSTREAM-SELECTION.SOURCE-ONLY.json', 'bytes': 2114, 'sha256': '596600fab7c3e8551c564187cce52e8207ecf088fe4ac618cf74028eeaee5312'},{'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-next118-recursive-fixture-expert-20261028-1/next-current-boundary-successor-1/prepared118-current63-1/observe_current63_current118.py', 'bytes': 1614, 'sha256': 'e6b734f0683b72c329f7fee69532e6e6fe9556b294a3b8e3bfbc646f6a044876'},{'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-next118-recursive-fixture-expert-20261028-1/next-current-boundary-successor-1/prepared118-current63-1/typed_current_boundary.py', 'bytes': 12354, 'sha256': '00483f2b97dbd03d76ee397ab9c80c050821ba1f705168d3606822b796e87514'})
 for key in ['independent_source_profile_review','mechanical_source_profile_review']:auth(b[key])
 review=read(b['independent_source_profile_review']['path'])
 assert review['independent'] is True and review['implementation_ownership'] is False and review['runtime_authority'] is None and review['decision'].startswith('PASS_')
 assert review['source_maps']['116']==ref(S/'SOURCE-MAP-FROM116.json') and review['recipe']==ref(S/'MINIMAL-FOUR-COMMAND-CONTINUATION.NOT-GRANTED.json')
 recipe=read(S/'SOURCE-MAP-FROM116.json');adoption=read(auth(b['source_adoption']))
 assert ref(P/'materialize_source_export.py') in manifest['external_inputs']
 spec=importlib.util.spec_from_file_location('exact118_genuine_adoption_validator',P/'materialize_source_export.py');exporter=importlib.util.module_from_spec(spec);spec.loader.exec_module(exporter)
 exporter.validate_adoption(b['source_adoption'])
 assert adoption['review']==b['independent_source_profile_review']
 profile=read(D/'PROFILE.TEMPLATE.SOURCE-ONLY.json')
 command_recipe=read(S/'MINIMAL-FOUR-COMMAND-CONTINUATION.NOT-GRANTED.json')
 assert profile['exact_commands']==command_recipe['ordered_commands']
 assert sorted((x['link_token'],x['source']['sha256']) for x in profile['inputs']['objects'] if not x['replace'])==sorted((x['link_token'],x['source']['sha256']) for x in command_recipe['retained_inputs'])
 origin=read(auth(b['actual_origin_producer']))
 assert origin['source_generation_only'] is True and origin['compiler'] is False and origin['returncode']==0 and origin['child_positive_join'] is True and origin['closed_streams'] is True
 assert origin['argv']==read(D/'ROOT-ORIGIN-PRODUCER-PROPOSAL.NOT-GRANTED.json')['argv']
 for key in ['actual_generated_header','actual_generated_metadata','actual_origin_binding','actual_Rust_environment','actual_CMake_origin']:auth(b[key])
 assert all(b[key] in origin['outputs'] for key in ['actual_generated_header','actual_generated_metadata','actual_origin_binding','actual_Rust_environment','actual_CMake_origin'])
 context=read(b['actual_origin_binding']['path'])
 assert context['source_sha256']==next(x['postimage']['sha256'] for x in recipe['writes'] if x['relative']=='arch/x86_64/kernel/syscall.c')
 assert context['profile_sha256']==ref(S/'candidate/scripts/f06_origin_command_profile.json')['sha256']
 assert context['command']=={k:profile['exact_commands'][2][k] for k in ['stage','cwd','argv','new_output']} and context['origin_utf8']=='/src/arch/x86_64/kernel/syscall.c'
 assert '#define MCKERNEL_F06_RT_SIGRETURN_ORIGIN "/src/arch/x86_64/kernel/syscall.c"' in Path(b['actual_generated_header']['path']).read_text()
 env=read(b['actual_Rust_environment']['path']);assert env==dict(MCKERNEL_F06_RT_SIGRETURN_ORIGIN='/src/arch/x86_64/kernel/syscall.c',MCKERNEL_F06_CLONE_CPUID_METADATA_RS=b['actual_generated_metadata']['path'])
 for row in profile['inputs']['postimages']:
  if row['relative'].endswith('/f06_rt_sigreturn_origin.h'):row['postimage']=b['actual_generated_header']
  elif row['relative'].endswith('/f06_clone_cpuid_metadata.rs'):row['postimage']=b['actual_generated_metadata']
 closed=read(auth(b['rust_export_manifest']));overlay=read(S/'RUST-CLOSED-SOURCE-OVERLAY.NOT-MATERIALIZED.json')
 expected={x['relative']:x['source']['sha256'] for x in overlay['files']}
 assert len(expected)==123 and sum(x.endswith('.rs') for x in expected)==112
 assert closed['export_root']==b['rust_export_root'] and len(closed['files'])==123
 external=read(P/'EXTERNAL-THREE-MODULE-INPUTS.json')['external_inputs']
 assert len(external)==3 and closed['external_inputs']==profile['inputs']['external_relative_modules']==external
 for row in external:auth(row['source']);assert row['source']['path']==str(Path(profile['inputs']['source6153'])/row['relative']) and row['container_path']=='/src/'+row['relative']
 actual={x['relative']:x['snapshot']['sha256'] for x in closed['files']}
 assert actual==expected
 profile['inputs']['source_directory_exports']=[dict(host_path=b['rust_export_root'],container_destination='/src/kernel/rust',readonly=True,manifest=b['rust_export_manifest'])]
 r=load_runner();rows=r.source_directory_postimages(profile);assert len(rows)==123
 profile['cohort_source_bindings']=[dict(relative=x['relative'],postimage=x['postimage']) for x in profile['inputs']['postimages']]+rows
 profile.update(native_custody_clearance=b['native_custody_clearance'],actual_root_adoption=b['source_adoption'],actual_nonce=b['nonce'],source_preparation_current_context=dict(runtime_authority=None,nonce_ledger=b['nonce_ledger'],accepted_current_free=b['native_custody_clearance'],current_boundary=b['current_boundary']),origin_source_materialization={k:b[k] for k in ['actual_origin_producer','actual_generated_header','actual_generated_metadata','actual_origin_binding','actual_Rust_environment','actual_CMake_origin']})
 return profile,r,rows

def materialize(bindings):
 b=read(bindings);profile,r,rows=validate118(b)
 root=Path(b['admission']);assert root.parent==ADMISSION_PARENT and re.fullmatch(r'ROOT-CURRENT118-CLEARPTE-SIGNALFP-BUILD-ADMISSION-[1-9][0-9]*',root.name) and not root.exists()
 r.current_operation_guard()
 root.mkdir(mode=0o700)
 for name in ['run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py']:write(root/name,(D/name).read_bytes())
 request=dict(scope=profile['scope'],status='ROOT_BOUND_CURRENT118_STATIC_REQUEST_NOT_EXECUTION',runtime_authority=None,nonce=b['nonce'],profile_template=ref(D/'PROFILE.TEMPLATE.SOURCE-ONLY.json'),source_adoption=b['source_adoption'],independent_source_profile_review=b['independent_source_profile_review'],current_physical_clearance=b['native_custody_clearance'],current_nonce_ledger=b['nonce_ledger'],preparation_manifest=b['preparation_manifest'],Root_actual_bindings=ref(bindings),actual_resource_authority=None,actual_execution_review=None,actual_execution_grant=None)
 rp=root/'STATIC-REQUEST-PAYLOAD.SOURCE-ONLY.json';write(rp,request);profile['request_sha256']=ref(rp)['sha256'];r.commands_for_plan(profile);write(root/'PROFILE.SOURCE-ONLY.json',profile)
 export=read(D/'INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json');export.update(author='/root',decision='PASS_EXACT_UID1000_READONLY_BUILD_EXPORTS',status='ROOT_CURRENT118_ACTUAL_READONLY_EXPORT_BINDING',request_sha256=profile['request_sha256'],actual_origin_producer_receipt=b['actual_origin_producer'])
 export['qualified_readonly_files']=[x['source'] for x in profile['inputs']['configuration']]+[x['source'] for x in profile['inputs']['objects'] if not x['replace']]+[x['postimage'] for x in profile['inputs']['postimages']]+[x['postimage'] for x in rows]+[x['source'] for x in profile['inputs']['external_relative_modules']]
 for x in export['qualified_readonly_files']:auth(x);assert os.access(x['path'],os.R_OK)
 for x in [export['readable_source_export'],export['readable_seed_export']]:assert os.access(x,os.R_OK|os.X_OK)
 xp=root/'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json';write(xp,export)
 write(root/'ROOT-REQUEST-ADOPTION.json',dict(author='/root',decision='ADOPT_EXACT_CURRENT118_STATIC_SOURCE_REQUEST_NOT_EXECUTION',runtime_authority=None,nonce=b['nonce'],request=ref(rp),request_sha256=profile['request_sha256'],source_adoption=b['source_adoption'],independent_source_profile_review=b['independent_source_profile_review'],current_physical_clearance=b['native_custody_clearance'],profile=ref(root/'PROFILE.SOURCE-ONLY.json'),input_export=ref(xp),actual_resource_authority=None,actual_execution_review=None,actual_execution_grant=None))
 write(root/'ROOT-HOLDER-BOOTSTRAP-GRANT.json',dict(author='/root',decision='GRANT_ONE_POSTCLEANUP27_4_BUILD_ONLY_HOLDER',maximum_invocations=1,nonce=b['nonce'],permanent_mutex_path='/run/lock/mckernel-development.lock',fresh_handshake_root=str(root/'HOLDER'),native_custody_clearance=b['native_custody_clearance'],source=ref(root/'hold_and_run_build_only.py'),runner=ref(root/'run_build_only.py'),worker=ref(root/'build_only_worker.py'),profile=ref(root/'PROFILE.SOURCE-ONLY.json')))
 print(json.dumps(dict(status='ROOT_CURRENT118_STATIC_AND_HOLDER_METADATA_ONLY',admission=str(root),profile=ref(root/'PROFILE.SOURCE-ONLY.json'),workloads=0)))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root-bindings',required=True);a=p.parse_args();materialize(Path(a.root_bindings))
