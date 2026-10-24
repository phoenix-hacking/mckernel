"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only successor of the retained finite root publisher; DO NOT EXECUTE without root release.
"""
import hashlib,importlib.util,json,os,pathlib,sys
D=pathlib.Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-8/m15-bfd-owner-successor')
p=D/'compile_image_owner.py'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='71381de806c21b7487e1515927543b376199a021a08b965a60d68063241bc794'
s=importlib.util.spec_from_file_location('bfd_compile_owner_finalization',p)
o=importlib.util.module_from_spec(s);sys.modules[s.name]=o;s.loader.exec_module(o)
assert os.getuid()==os.geteuid()==0 and os.sched_getaffinity(0)=={7}
assert len(sys.argv)==9
query=D/'admission-preparation-1/actual-readonly-query-1/ROOT-ADMISSION.CANDIDATE.json'
request=D/'admission-preparation-1/actual-readonly-query-1/REQUEST.FINALIZED.UNRELEASED.CANDIDATE.json'
query_sha,request_sha=sys.argv[1:3]
review=pathlib.Path(sys.argv[3]);review_sha=sys.argv[4]
source_review=pathlib.Path(sys.argv[5]);source_review_sha=sys.argv[6]
joined=pathlib.Path(sys.argv[7]);joined_sha=sys.argv[8]
for path,expected in ((query,query_sha),(request,request_sha),(review,review_sha),(source_review,source_review_sha),(joined,joined_sha)):
 assert len(expected)==64 and hashlib.sha256(path.read_bytes()).hexdigest()==expected
whole=json.loads(joined.read_bytes())
assert whole['returncode']==0 and whole['direct_child_joined'] and whole['group_absent'] and whole['closed_streams']
assert whole['error'] is None and whole['retirement_error'] is None
facts=json.loads(query.read_bytes());q=json.loads(request.read_bytes())
o._validate_compile_domain(q)
assert q['compile_only_release'] is None
assert facts['request_core_sha256']==o._request_core_hash(q)
assert facts['profile_sha256']==o.COMPILE_PROFILE_SHA256 and facts['operation']==o.COMPILE_PROFILE['operation']
assert facts['schema']=='mckernel.m15-bfd-dual-container-admission.v1'
assert facts['capacity_verdict']=='PASS_DUAL_CONTAINER_COMPILE_CPU6_2G'
assert '_template_only_no_authority' not in facts
# Preserve the actual query timestamp. No new observation time is minted.
o._fresh_compile_resources(facts)
a=D/'ROOT-ADMISSION.json';r=D/'ROOT-RELEASE.json';released_request=D/'compile-request.RELEASED.json'
assert not any(os.path.lexists(path) for path in (a,r,released_request))
release=json.loads((D/'ROOT-RELEASE.TEMPLATE.json').read_text());release.pop('_template_only_no_authority')
release['request_core_sha256']=o._request_core_hash(q)
release['independent_source_review_sha256']=source_review_sha
def publish(path,document):
 o._exclusive_json(path,document);os.chmod(path,0o644)
 fd=os.open(path,os.O_RDONLY);os.fsync(fd);os.close(fd);o._fsync_dir(D)
 return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
aref=publish(a,facts);o._read_root_document(aref,a,'published BFD root admission')
release['root_admission']=aref
rref=publish(r,release);q['compile_only_release']=rref
o._validate_launch_admission(q)
qref=publish(released_request,q)
assert o._request_core_hash(q)==facts['request_core_sha256']
print(json.dumps({'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PUBLISHED_BFD_ROOT_DOCUMENTS_NOT_EXECUTION_ACCEPTANCE','root_admission':aref,'root_release':rref,'released_request':qref,'actual_query':{'path':str(query),'sha256':query_sha},'independent_execution_review':{'path':str(review),'sha256':review_sha},'independent_owner_source_review':{'path':str(source_review),'sha256':source_review_sha},'actual_query_outer_wholejoin':{'path':str(joined),'sha256':joined_sha}},sort_keys=True))
