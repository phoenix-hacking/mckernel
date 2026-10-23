"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exercise actual pure request admission. No ImageOwner.run, Docker, compiler,
heavy-operation acquisition, leases or production namespace creation.
"""
import copy, hashlib, importlib.util, json, os, time
from pathlib import Path
D=Path(__file__).resolve().parent
OLD=D.parent/'default-image-successor-1'
NAME='native_rust_exact_mckernel_image_container_owner.py'
REQUEST=OLD/'image-request.FINAL.json'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p,name):
 spec=importlib.util.spec_from_file_location(name,p)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def rejected(label,invoke,expected,error_type):
 try:invoke()
 except error_type as exc:
  assert str(exc)==expected,(label,str(exc));return {'label':label,'status':'PASS_REJECTED','reason':str(exc)}
 raise AssertionError(label+' unexpectedly accepted')

assert os.geteuid()!=0
begin=time.monotonic();request=json.loads(REQUEST.read_bytes())
manifest=Path(request['source_manifest']);document=json.loads(manifest.read_bytes())
roots=[Path(request[k]) for k in ('owner_evidence_root','work_root')]
before={str(p):sorted(q.name for q in p.iterdir()) for p in roots}
assert all(not names for names in before.values()),'preserved original roots must still be empty'
pinned={str(p):sha(p) for p in (REQUEST,manifest,OLD/NAME,D/NAME)}
original=load(OLD/NAME,'preserved_original_image_owner')
owner=load(D/NAME,'corrected_image_owner')
rows=[rejected('original_complete_request_preserved_failure',lambda:original._validate_request(request),'source manifest schema',original.OwnerError)]
# Whole production request through every real admission branch; no fixtures or stubs.
bound=owner._validate_request(request)
rows.append({'label':'corrected_actual_complete_validate_request','status':'PASS',
 'source':str(bound['source']),'manifest':str(bound['manifest']),
 'toolchain_schema':bound['toolchain_schema'],
 'measurement':bound['measurement'],
 'gitlink_root':str(bound['gitlink_root']),
 'production_namespace_creation':False,'build_execution':False})
for field in ('source_derivative_sha256','materialization_sha256','candidate_identity_scope'):
 bad=copy.deepcopy(request);bad[field]='changed-unaccepted-identity'
 rows.append(rejected('complete_request_rejects_'+field,lambda bad=bad:owner._validate_request(bad),'explicit derivative request identity differs',owner.OwnerError))
for field in ('gitlink_manifest','gitlink_root'):
 bad=dict(request);bad.pop(field)
 rows.append(rejected('actual_gitlink_admission_requires_'+field,
  lambda bad=bad:owner._admit_request_gitlink(bad,document,bound['source'],manifest,request['candidate_sha'],request['ihk_sha'],bound['allocation_roots'],bound['host_git']),
  'thin source requires supplemental libdwarf manifest and root',owner.OwnerError))
# Same authenticated provenance remains the authority for complete source bytes.
provenance=owner._authenticated_provenance(bound['provenance'])
bad=copy.deepcopy(document);bad['schema']='mckernel.unreviewed-thin-inputs.v1'
try:provenance.validate_thin_document(bad,request['candidate_sha'],request['ihk_sha'])
except Exception as exc:
 assert 'exact independently reviewed cutover authority required' in str(exc),str(exc)
 rows.append({'label':'authenticated_provenance_rejects_unknown_schema','status':'PASS_REJECTED','reason':str(exc)})
else:raise AssertionError('unknown provenance schema accepted')
after={str(p):sorted(q.name for q in p.iterdir()) for p in roots}
assert before==after and all(sha(Path(p))==s for p,s in pinned.items()),'pure admission mutated inputs/namespaces'
print(json.dumps({'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
 'schema':'mckernel.m14-actual-owner-pure-validation.v1','status':'PASS','seconds':time.monotonic()-begin,
 'request_path':str(REQUEST),'request_sha256':pinned[str(REQUEST)],
 'owner_sha256':pinned[str(D/NAME)],'source_manifest_sha256':pinned[str(manifest)],
 'cases':rows,'case_count':len(rows),'production_namespaces_unchanged':before==after,
 'limitations':['pure admission only; no ImageOwner.run, heavy acquire, Docker, compiler, build or guest',
 'original failed namespace retained; a real build needs new reviewed namespace/request binding',
 'no default-link/native/whole-file retirement credit']},sort_keys=True))
