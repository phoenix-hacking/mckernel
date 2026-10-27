"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-only finite ordinary staging of reviewed CURRENT110 helper/profile metadata.
No compiler/configure/Docker/guest/native/cleanup or kernel source copy occurs.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,re
D=Path(__file__).resolve().parent;P=D.parent;E=D.parents[1]
def read(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def auth(row):assert ref(row['path'])==row;return Path(row['path'])
def write(p,value):
 raw=value if isinstance(value,bytes) else (json.dumps(value,indent=2)+'\n').encode()
 with Path(p).open('xb') as stream:stream.write(raw)
def materialize(bindings_path):
 b=read(bindings_path)
 assert b['author']=='/root' and b['decision']=='MATERIALIZE_REVIEWED_CURRENT110_STATIC_INPUTS_AND_HOLDER_ONLY'
 assert b['maximum_invocations']==1 and b['root_attests_exact_UID1000_readonly_exports'] is True
 assert re.fullmatch('[0-9a-f]{32}',b['nonce']) and b['nonce']!='ea92dbc3148490a122f116a6afa7b010'
 assert b['preparation_manifest']==ref(D/'PREPARATION-MANIFEST.json')
 manifest=read(auth(b['preparation_manifest']))
 for row in manifest['files']:auth(row)
 for row in manifest['external_inputs']:auth(row)
 ledger=read(auth(b['nonce_ledger']))
 assert ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
 assert b['nonce'] not in ledger['consumed_nonces']
 for key in ['native_custody_clearance','independent_source_profile_review','source_adoption']:auth(b[key])
 adoption=read(b['source_adoption']['path'])
 assert adoption['status']=='PASS_ROOT_EXACT_NINE_SOURCE_ADOPTION_ONLY'
 for row in adoption['files']:assert ref(row['destination'])['sha256']==row['candidate']['sha256']
 for row in read(P/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json')['files']:
  assert ref(row['original']['path'])==row['original'] and ref(row['snapshot']['path'])==row['snapshot']
 spec=importlib.util.spec_from_file_location('current110_materialization_v2_runner',D/'run_build_only.py')
 r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r);r.current_operation_guard()
 root=Path(b['admission']);assert root.is_absolute() and root.parent==E and re.fullmatch('ROOT-[A-Za-z0-9-]+',root.name) and not root.exists()
 profile=read(P/'PROFILE.SOURCE-ONLY.json');assert profile['request_sha256'] is None
 profile['native_custody_clearance']=b['native_custody_clearance']
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
