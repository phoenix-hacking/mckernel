"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Existing CURRENT114 static-admission method, exact115 source/origin data successor.
Root-only ordinary metadata staging. No configure/compiler/holder/Docker/native.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,re
C=Path(__file__).resolve().parent;D=C.parent;E=D.parent
S=E/'next115-f02-local31-f06-cpuid-source-integration-preparation-1'
def read(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert isinstance(r,dict) and set(r)=={'path','bytes','sha256'} and Path(r['path']).is_absolute() and ref(r['path'])==r;return Path(r['path'])
def write(p,v):
 raw=v if isinstance(v,bytes) else (json.dumps(v,indent=2)+'\n').encode()
 with Path(p).open('xb') as f:f.write(raw)
def materialize(bindings):
 b=read(bindings);assert b['author']=='/root' and b['decision']=='MATERIALIZE_REVIEWED_CURRENT115_LOCAL31_CPUID_STATIC_INPUTS_AND_HOLDER_ONLY'
 assert b['maximum_invocations']==1 and b['root_attests_exact_UID1000_readonly_exports'] is True
 assert re.fullmatch('[0-9a-f]{32}',b['nonce']) and b['nonce']!='cf36b84313f404836ec6d80350e0e15a'
 assert b['preparation_manifest']==ref(C/'PREPARATION-MANIFEST.json')
 manifest=read(auth(b['preparation_manifest']))
 for row in manifest['files']:auth(row)
 for row in manifest['external_inputs']:auth(row)
 boundary=read(auth(b['current_boundary']))
 assert boundary['author']=='/root' and boundary['decision']=='BIND_EXISTING_REVIEWED_CURRENT_BUILD_BOUNDARY' and boundary['root_attests_exact_current_boundary'] is True
 for k in ['nonce_ledger','native_custody_clearance','observer','independent_current_boundary_review']:auth(boundary[k])
 assert b['nonce_ledger']==boundary['nonce_ledger'] and b['native_custody_clearance']==boundary['native_custody_clearance']
 ledger=read(auth(b['nonce_ledger']));assert ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True and b['nonce'] not in ledger['consumed_nonces']
 assert b['independent_source_profile_review']==ref(S/'independent-source-profile-review-1/REVIEW.json')
 for k in ['mechanical_source_profile_review','source_adoption','F02_folded_consumer_review']:auth(b[k])
 assert b['F02_folded_consumer_review']==ref(E/'m14-f02-local14-final14-qualified-preparation-source-1/independent-actual-qualification-review-1/INDEPENDENT-ACTUAL-HOST-ACCEPTANCE.json')
 recipe=read(S/'SELECTIVE-SOURCE-RECIPE.json');adoption=read(b['source_adoption']['path'])
 assert adoption['author']=='/root' and len(adoption['source_changes'])==9
 wanted={r['relative']:r['candidate']['sha256'] for r in recipe['files']}
 for r in adoption['source_changes']:
  assert r['relative'] in wanted and ref(r['after']['path'])==r['after'] and r['after']['sha256']==wanted.pop(r['relative'])
 assert not wanted
 origin=read(auth(b['actual_origin_producer']));assert origin['source_generation_only'] is True and origin['compiler_executed'] is False and origin['returncode']==0 and origin['direct_child_joined'] is True and origin['streams_closed'] is True
 for k in ['actual_generated_header','actual_generated_metadata','actual_origin_binding','actual_Rust_environment','actual_CMake_origin']:auth(b[k])
 assert origin['argv']==read(D/'ROOT-ORIGIN-PRODUCER-PROPOSAL.NOT-GRANTED.json')['argv']
 assert b['actual_generated_header'] in origin['outputs'] and b['actual_generated_metadata'] in origin['outputs']
 context=read(b['actual_origin_binding']['path']);op=read(S/'candidate/scripts/f06_origin_command_profile.json')
 profile=read(D/'PROFILE.TEMPLATE.SOURCE-ONLY.json')
 assert context['source_sha256']==recipe['files'][0]['candidate']['sha256']
 assert context['profile_sha256']==ref(S/'candidate/scripts/f06_origin_command_profile.json')['sha256']
 assert set(context['command'])=={'stage','cwd','argv','new_output'} and context['command']=={k:profile['exact_commands'][2][k] for k in ['stage','cwd','argv','new_output']} and context['origin_utf8']=='/src/arch/x86_64/kernel/syscall.c'
 assert context['clone_cpuid_debug_slots']==op['clone_cpuid_origin_reference']['retained_C_metadata']
 header=Path(b['actual_generated_header']['path']).read_text();assert '#define MCKERNEL_F06_RT_SIGRETURN_ORIGIN "/src/arch/x86_64/kernel/syscall.c"' in header
 generated=Path(b['actual_generated_metadata']['path']).read_text()
 assert 'F06_CLONE_CPU_SAMPLE_LINE_FLAGS: u32 = 898;' in generated and 'F06_CLONE_CPU_CHOICE_LINE_FLAGS: u32 = 908;' in generated
 env=read(b['actual_Rust_environment']['path']);assert env==dict(MCKERNEL_F06_RT_SIGRETURN_ORIGIN='/src/arch/x86_64/kernel/syscall.c',MCKERNEL_F06_CLONE_CPUID_METADATA_RS=b['actual_generated_metadata']['path'])
 assert 'MCKERNEL_F06_CLONE_CPUID_METADATA_RS=/work/output/build/kernel/rust/f06-origin/f06_clone_cpuid_metadata.rs' in profile['exact_commands'][0]['argv']
 assert [x for x in profile['inputs']['postimages'] if '/f06-origin/' in x['relative']]==[dict(relative='kernel/rust/f06-origin/'+name,postimage=b[key],container_destination='/work/output/build/kernel/rust/f06-origin/'+name,readonly=True) for key,name in [('actual_generated_header','f06_rt_sigreturn_origin.h'),('actual_generated_metadata','f06_clone_cpuid_metadata.rs')]]
 spec=importlib.util.spec_from_file_location('existing115_source_runner',D/'run_build_only.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
 rows=r.source_directory_postimages(profile);assert len(rows)==120
 profile['cohort_source_bindings']=[dict(relative=x['relative'],postimage=x['postimage']) for x in profile['inputs']['postimages']]+rows
 profile.update(native_custody_clearance=b['native_custody_clearance'],actual_root_adoption=b['source_adoption'],actual_nonce=b['nonce'],source_preparation_current_context=dict(runtime_authority=None,nonce_ledger=b['nonce_ledger'],accepted_current_free=b['native_custody_clearance'],current_boundary=b['current_boundary']),origin_source_materialization={k:b[k] for k in ['actual_origin_producer','actual_generated_header','actual_generated_metadata','actual_origin_binding','actual_Rust_environment','actual_CMake_origin']})
 root=Path(b['admission']);assert root.parent==E and re.fullmatch(r'ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-(?:[2-9]|[1-9][0-9]+)',root.name) and not root.exists()
 r.current_operation_guard() # Original mandatory actual account/window check, only Root executes.
 root.mkdir(mode=0o700)
 for name in ['run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py']:write(root/name,(D/name).read_bytes())
 request=dict(scope=profile['scope'],status='ROOT_BOUND_CURRENT115_STATIC_REQUEST_NOT_EXECUTION',runtime_authority=None,nonce=b['nonce'],profile_template=ref(D/'PROFILE.TEMPLATE.SOURCE-ONLY.json'),source_adoption=b['source_adoption'],independent_source_profile_review=b['independent_source_profile_review'],current_physical_clearance=b['native_custody_clearance'],current_nonce_ledger=b['nonce_ledger'],preparation_manifest=b['preparation_manifest'],Root_actual_bindings=ref(bindings),actual_resource_authority=None,actual_execution_review=None,actual_execution_grant=None)
 rp=root/'STATIC-REQUEST-PAYLOAD.SOURCE-ONLY.json';write(rp,request);profile['request_sha256']=ref(rp)['sha256'];r.commands_for_plan(profile);write(root/'PROFILE.SOURCE-ONLY.json',profile)
 export=read(D/'INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json');export.update(author='/root',decision='PASS_EXACT_UID1000_READONLY_BUILD_EXPORTS',status='ROOT_CURRENT115_ACTUAL_READONLY_EXPORT_BINDING',request_sha256=profile['request_sha256'],actual_origin_producer_receipt=b['actual_origin_producer'])
 export['qualified_readonly_files']=[x['source'] for x in profile['inputs']['configuration']]+[x['source'] for x in profile['inputs']['objects'] if not x['replace']]+[x['postimage'] for x in profile['inputs']['postimages']]+[x['postimage'] for x in rows]
 for x in export['qualified_readonly_files']:auth(x);assert os.access(x['path'],os.R_OK)
 for x in [export['readable_source_export'],export['readable_seed_export']]:assert os.access(x,os.R_OK|os.X_OK)
 xp=root/'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json';write(xp,export)
 write(root/'ROOT-REQUEST-ADOPTION.json',dict(author='/root',decision='ADOPT_EXACT_CURRENT115_STATIC_SOURCE_REQUEST_NOT_EXECUTION',runtime_authority=None,nonce=b['nonce'],request=ref(rp),request_sha256=profile['request_sha256'],source_adoption=b['source_adoption'],independent_source_profile_review=b['independent_source_profile_review'],current_physical_clearance=b['native_custody_clearance'],profile=ref(root/'PROFILE.SOURCE-ONLY.json'),input_export=ref(xp),actual_resource_authority=None,actual_execution_review=None,actual_execution_grant=None))
 write(root/'ROOT-HOLDER-BOOTSTRAP-GRANT.json',dict(author='/root',decision='GRANT_ONE_POSTCLEANUP27_4_BUILD_ONLY_HOLDER',maximum_invocations=1,nonce=b['nonce'],permanent_mutex_path='/run/lock/mckernel-development.lock',fresh_handshake_root=str(root/'HOLDER'),native_custody_clearance=b['native_custody_clearance'],source=ref(root/'hold_and_run_build_only.py'),runner=ref(root/'run_build_only.py'),worker=ref(root/'build_only_worker.py'),profile=ref(root/'PROFILE.SOURCE-ONLY.json')))
 print(json.dumps(dict(status='ROOT_CURRENT115_STATIC_AND_HOLDER_METADATA_ONLY',admission=str(root),profile=ref(root/'PROFILE.SOURCE-ONLY.json'),workloads=0)))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root-bindings',required=True);a=p.parse_args();materialize(Path(a.root_bindings))
