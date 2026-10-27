"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-only finite ordinary staging of reviewed CURRENT110 helper/profile metadata.
No compiler/configure/Docker/guest/native/cleanup or kernel source copy occurs.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,re
D=Path(__file__).resolve().parent;P=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current113-qualified-lock4-next4-scalar4-union-source-1/corrected-scalar4-next4-accepted112-source-1/abi-private-field-correction-source-1');E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
def read(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def auth(row):assert ref(row['path'])==row;return Path(row['path'])
def write(p,value):
 raw=value if isinstance(value,bytes) else (json.dumps(value,indent=2)+'\n').encode()
 with Path(p).open('xb') as stream:stream.write(raw)
def materialize(bindings_path):
 b=read(bindings_path)
 assert b['author']=='/root' and b['decision']=='MATERIALIZE_REVIEWED_CURRENT113_ABI_CORRECTION_STATIC_INPUTS_AND_HOLDER_ONLY'
 assert b['maximum_invocations']==1 and b['root_attests_exact_UID1000_readonly_exports'] is True
 assert re.fullmatch('[0-9a-f]{32}',b['nonce']) and b['nonce']!='ea92dbc3148490a122f116a6afa7b010'
 assert b['preparation_manifest']==ref(D/'PREPARATION-MANIFEST.json')
 manifest=read(auth(b['preparation_manifest']))
 for row in manifest['files']:auth(row)
 for row in manifest['external_inputs']:auth(row)
 ledger=read(auth(b['nonce_ledger']))
 assert b['nonce_ledger']=={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER37.json', 'bytes': 4591, 'sha256': 'b6ed7c321b348e90e13a51607d88af09893ab760e3decdd4d16d000a130155e8'}
 assert b['native_custody_clearance']=={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT113-CORRECTED-SCALAR4-NEXT4-BUILD-ADMISSION-1/independent-failed-build-review-1/CURRENT-FREE.json', 'bytes': 92521, 'sha256': '070e0f2c4f367da3444f30300bfbeb193af6d1bb7cc6cda663a1cb154bfe9f13'}
 assert ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
 assert b['nonce'] not in ledger['consumed_nonces']
 for key in ['native_custody_clearance','independent_source_profile_review','source_adoption']:auth(b[key])
 adoption=read(b['source_adoption']['path'])
 assert adoption['author']=='/root' and adoption['status']=='ROOT_SOURCE_ADOPTED_CURRENT113_ABI_PRIVATE_CORRECTION_NOT_BUILT'
 for row in adoption['files']:
  assert ref(row['canonical']['path'])==row['canonical']
  assert ref(row['private_source']['path'])==row['private_source']
  assert row['canonical']['sha256']==row['private_source']['sha256']
 for row in read(Path(read(P/'PROFILE.SOURCE-ONLY.json')['inputs']['source_directory_exports'][0]['manifest']['path']))['files']:
  assert ref(row['snapshot']['path'])==row['snapshot']
  assert ref(E.parents[3]/'kernel/rust'/row['relative'])['sha256']==row['snapshot']['sha256']
 assert b['actual_origin_producer']=={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current113-qualified-lock4-next4-scalar4-union-source-1/corrected-scalar4-next4-accepted112-source-1/root-source-adoption-1/ROOT-ACTUAL-ORIGIN-PRODUCER.json', 'bytes': 3725, 'sha256': '2c419c6405deef8d6e8c2479e57f88884e34a84fec300e0aff5311ea04b944fb'}
 origin=read(auth(b['actual_origin_producer']))
 assert origin['author']=='/root' and origin['returncode']==0 and origin['direct_child_joined'] is True and origin['streams_closed'] is True
 header=b['actual_generated_header'];auth(header);assert origin['actual_header']==header
 context=read(auth(b['actual_origin_binding']));environment=read(auth(b['actual_Rust_environment']));auth(b['actual_CMake_origin'])
 template=read(P/'PROFILE.SOURCE-ONLY.json')
 assert context['command']==template['exact_commands'][2]
 assert context['source_sha256']==ref(Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current113-qualified-lock4-next4-scalar4-union-source-1/corrected-scalar4-next4-accepted112-source-1/candidate/arch/x86_64/kernel/syscall.c'))['sha256']
 assert context['profile_sha256']==ref(Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current113-qualified-lock4-next4-scalar4-union-source-1/corrected-scalar4-next4-accepted112-source-1/candidate/scripts/f06_origin_command_profile.json'))['sha256']
 assert environment=={'MCKERNEL_F06_RT_SIGRETURN_ORIGIN':'/src/arch/x86_64/kernel/syscall.c'}
 assert template['exact_commands'][0]['argv'].count('MCKERNEL_F06_RT_SIGRETURN_ORIGIN=/src/arch/x86_64/kernel/syscall.c')==1
 spec=importlib.util.spec_from_file_location('current110_materialization_v2_runner',D/'run_build_only.py')
 r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r);r.current_operation_guard()
 root=Path(b['admission']);assert root.is_absolute() and root.parent==E and re.fullmatch('ROOT-[A-Za-z0-9-]+',root.name) and not root.exists()
 profile=read(P/'PROFILE.SOURCE-ONLY.json');assert profile['request_sha256'] is None
 profile['native_custody_clearance']=b['native_custody_clearance']
 assert ref(P/'PROFILE.SOURCE-ONLY.json')['sha256']=='388c3c364f6c981a5749b058f59f94684091a12f381f785aab181508388bad05'
 assert len(profile['exact_commands'])==4 and sum(not row['replace'] for row in profile['inputs']['objects'])==8
 assert not any(row.get('source_preview_not_runtime_producer') for row in profile['inputs']['postimages'])
 assert next(row['postimage'] for row in profile['inputs']['postimages'] if row['relative']=='kernel/rust/f06-origin/f06_rt_sigreturn_origin.h')==header
 assert profile['origin_source_materialization']['actual_producer_receipt']==b['actual_origin_producer']
 profile['source_preparation_current_context']=dict(runtime_authority=None,Root37=b['nonce_ledger'],accepted_current_free=b['native_custody_clearance'],actual_admission_required=True)
 profile['actual_root_adoption']=b['source_adoption']
 profile['origin_source_materialization'].update(status='ACTUAL_CURRENT113_GENUINE_ORIGIN_BOUND_NO_BUILD_REPLAY',actual_producer_receipt=b['actual_origin_producer'],actual_generated_header=header,actual_origin_binding=b['actual_origin_binding'],actual_Rust_environment=b['actual_Rust_environment'],actual_CMake_origin=b['actual_CMake_origin'])
 root.mkdir(mode=0o700)
 tools=['run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py']
 for name in tools:write(root/name,(D/name).read_bytes())
 request=dict(scope=profile['scope'],status='ROOT_BOUND_CURRENT110_STATIC_REQUEST_NOT_EXECUTION',runtime_authority=None,
  nonce=b['nonce'],profile_template=ref(P/'PROFILE.SOURCE-ONLY.json'),source_adoption=b['source_adoption'],
  independent_source_profile_review=b['independent_source_profile_review'],current_physical_clearance=b['native_custody_clearance'],
  current_nonce_ledger=b['nonce_ledger'],preparation_manifest=b['preparation_manifest'],Root_actual_bindings=ref(bindings_path),
  actual_resource_authority=None,actual_execution_review=None,actual_execution_grant=None)
 rp=root/'STATIC-REQUEST-PAYLOAD.SOURCE-ONLY.json';write(rp,request)
 profile['request_sha256']=ref(rp)['sha256'];profile['actual_nonce']=b['nonce']
 write(root/'PROFILE.SOURCE-ONLY.json',profile)
 export=read(P/'INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json')
 assert header in export['qualified_readonly_files']
 export['actual_origin_producer_receipt']=b['actual_origin_producer']
 export.update(author='/root',decision='PASS_EXACT_UID1000_READONLY_BUILD_EXPORTS',status='ROOT_CURRENT110_ACTUAL_READONLY_EXPORT_BINDING',request_sha256=profile['request_sha256'])
 for row in export['qualified_readonly_files']:
  auth(row);assert os.access(row['path'],os.R_OK)
 for path in [export['readable_source_export'],export['readable_seed_export']]:assert os.access(path,os.R_OK|os.X_OK)
 xp=root/'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json';write(xp,export)
 adoption=dict(author='/root',decision='ADOPT_EXACT_CURRENT110_STATIC_SOURCE_REQUEST_NOT_EXECUTION',runtime_authority=None,
  nonce=b['nonce'],request=ref(rp),request_sha256=profile['request_sha256'],source_adoption=b['source_adoption'],
  independent_source_profile_review=b['independent_source_profile_review'],current_physical_clearance=b['native_custody_clearance'],
  profile=ref(root/'PROFILE.SOURCE-ONLY.json'),input_export=ref(xp),actual_resource_authority=None,actual_execution_review=None,actual_execution_grant=None)
 write(root/'ROOT-REQUEST-ADOPTION.json',adoption)
 holder=dict(author='/root',decision='GRANT_ONE_POSTCLEANUP27_4_BUILD_ONLY_HOLDER',maximum_invocations=1,nonce=b['nonce'],
  permanent_mutex_path='/run/lock/mckernel-development.lock',fresh_handshake_root=str(root/'HOLDER'),
  native_custody_clearance=b['native_custody_clearance'],source=ref(root/'hold_and_run_build_only.py'),
  runner=ref(root/'run_build_only.py'),worker=ref(root/'build_only_worker.py'),profile=ref(root/'PROFILE.SOURCE-ONLY.json'))
 write(root/'ROOT-HOLDER-BOOTSTRAP-GRANT.json',holder)
 print(json.dumps(dict(status='ROOT_CURRENT110_STATIC_INPUTS_AND_HOLDER_ONLY_PREPARATION_BOUND',admission=str(root),
  request_sha256=profile['request_sha256'],profile=ref(root/'PROFILE.SOURCE-ONLY.json'),workloads=0,
  next='Root publishes/fetch-verifies actual source metadata, then starts exact holder, captures fresh facts, obtains independent execution review and publishes one-use build grant.')))
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root-bindings',required=True);args=parser.parse_args();materialize(Path(args.root_bindings))
