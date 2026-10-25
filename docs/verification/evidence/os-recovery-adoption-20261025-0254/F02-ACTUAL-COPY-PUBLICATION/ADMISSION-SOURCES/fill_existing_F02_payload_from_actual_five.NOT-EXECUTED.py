"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Fill existing normal-image payload from authentic closed five outputs and ROOT declarations only.
No root/query/build/owner or independent release effects.
"""
from pathlib import Path
import hashlib,json,re,sys,time
D=Path(__file__).resolve().parent
T=D/'ROOT-EXACT-F02-RETAINED-VALIDATION-PAYLOAD.PENDING-FETCH-FIVE-AND-ROOT.json'
assert hashlib.sha256(T.read_bytes()).hexdigest()=='50167eda9251fb96456a367b28ddb9326c8db89eae5ab6d6121400cc664fe8bc'
p=json.loads(T.read_bytes());context_path=Path(sys.argv[3]);context=json.loads(context_path.read_bytes())
def ref(q):
 b=q.read_bytes();return {'path':str(q),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
# ROOT binds the actual fetched-proof SHA in its exact metadata invocation after publication.
proof=Path(sys.argv[1]);proof_ref=ref(proof);assert proof_ref['sha256']==sys.argv[2]
pub=json.loads(proof.read_bytes());assert pub['status']=='PASS_ACTUAL_FETCHED_SOURCE_BLOBS' and pub['archive_exact_members']==28 and pub['original_request_sha256']==p['source']['request']['sha256']
assert len(pub['commit'])==40 and all(c in '0123456789abcdef' for c in pub['commit'])
query=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/actual-copy-bound-source-1/READONLY-ADMISSION-ARGV.EXACT-F02-COPY-NAMESPACE.NOT-EXECUTED.json')
runner=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/actual-copy-bound-source-1/capture_readonly_admission.EXACT-F02-COPY-NAMESPACE.NOT-EXECUTED.py')
assert {ref(query)['sha256'],ref(runner)['sha256'],ref(Path(__file__))['sha256']} <= {f['sha256'] for f in pub['files']}

# Bind the exact existing fetched-proof repository field to the five sources;
# the root's fresh runtime continuity declaration is separate from its template.
expected_publication_sources = {'/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/actual-copy-bound-source-1/READONLY-ADMISSION-ARGV.EXACT-F02-COPY-NAMESPACE.NOT-EXECUTED.json': 'docs/verification/evidence/os-recovery-adoption-20261025-0254/F02-ACTUAL-COPY-PUBLICATION/ADMISSION-SOURCES/READONLY-ADMISSION-ARGV.EXACT-F02-COPY-NAMESPACE.NOT-EXECUTED.json', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/actual-copy-bound-source-1/capture_readonly_admission.EXACT-F02-COPY-NAMESPACE.NOT-EXECUTED.py': 'docs/verification/evidence/os-recovery-adoption-20261025-0254/F02-ACTUAL-COPY-PUBLICATION/ADMISSION-SOURCES/capture_readonly_admission.EXACT-F02-COPY-NAMESPACE.NOT-EXECUTED.py', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/actual-copy-bound-source-1/admission-source-preparation-1/fill_existing_F02_payload_from_actual_five.NOT-EXECUTED.py': 'docs/verification/evidence/os-recovery-adoption-20261025-0254/F02-ACTUAL-COPY-PUBLICATION/ADMISSION-SOURCES/fill_existing_F02_payload_from_actual_five.NOT-EXECUTED.py', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/actual-copy-bound-source-1/admission-source-preparation-1/ROOT-CONTINUITY-AND-AGGREGATE.F02-ACTUAL-COPY.TEMPLATE.json': 'docs/verification/evidence/os-recovery-adoption-20261025-0254/F02-ACTUAL-COPY-PUBLICATION/ADMISSION-SOURCES/ROOT-CONTINUITY-AND-AGGREGATE.F02-ACTUAL-COPY.TEMPLATE.json', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/actual-copy-bound-source-1/admission-source-preparation-1/ROOT-EXACT-F02-RETAINED-VALIDATION-PAYLOAD.PENDING-FETCH-FIVE-AND-ROOT.json': 'docs/verification/evidence/os-recovery-adoption-20261025-0254/F02-ACTUAL-COPY-PUBLICATION/ADMISSION-SOURCES/ROOT-EXACT-F02-RETAINED-VALIDATION-PAYLOAD.PENDING-FETCH-FIVE-AND-ROOT.json'}
published_files = {f['repository']: f for f in pub['files']}
assert len(published_files) == len(pub['files'])
for source, repository in expected_publication_sources.items():
    assert published_files[repository]['sha256'] == ref(Path(source))['sha256']

repo=Path('/home/holden/mckernel');head=(repo/'.git/HEAD').read_text().strip();assert head.startswith('ref: ')
assert (repo/'.git'/head[5:]).read_text().strip()==pub['commit']
p['fetched_publication']=proof_ref
pure=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/actual-copy-bound-source-1/ACTUAL-F02-TYPEALIGN-PURE-CONSUMER-RESULT.json');pure_data=json.loads(pure.read_bytes());assert pure_data['status']=='PASS_ACTUAL_COMPLETE_PURE_F02_TYPEALIGN_RETAINED_VALIDATION_REQUEST' and pure_data['request']['sha256']==p['source']['request']['sha256']
p['actual_complete_pure_consumer']=ref(pure)
p['actual_request_validation']=ref(Path(context['actual_request_validation_whole_join_path']))
cap=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/actual-copy-bound-source-1/actual-readonly-admission-capture-1');actual=cap/'ACTUAL-READONLY-RESULT.json';a=json.loads(actual.read_bytes());assert len(a['results'])==5
for x in a['results']:assert x['returncode']==0 and x['direct_child_joined'] and x['group_absent'] and x['closed_streams'] and x['error'] is None and x['retirement_error'] is None
observed=[(cap/str(i)/'stdout').read_text() for i in range(1,6)]
ident=json.loads(observed[0]);mount=json.loads(observed[1]);loops=json.loads(observed[3]);namespace=json.loads(observed[4])
expected_namespace_paths=['/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-work', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-evidence', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-evidence/attempt', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/common-exclusion.json', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/lease.json', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-work/output', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/owner-work/evidence', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/actual-copy-bound-source-1/actual-build-owner-capture-1', '/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock']
assert [x['path'] for x in namespace['rows']]==expected_namespace_paths
back=next(l for l in observed[2].splitlines() if l.startswith('/home/holden/mckernel-work/scratch.ext4 '));size=int(re.search(r' size=(\d+)',back)[1]);blocks=int(re.search(r' blocks=(\d+)',back)[1]);gap=max(0,size-512*blocks);assert size==118111600640
assert any('2a5768c8-718d-4914-bdc0-6b32c5a92a52' in str(x) for x in mount['filesystems'])
mem=int(next(l.split()[1] for l in ident['memory'] if l.startswith('MemAvailable:')))*1024
HOST=ident['space']['/home/holden']['free'];scratch=ident['space']['/home/holden/mckernel-work/scratch']['free']
HOST_required=max(50248630272,17179869184+gap+16106090496+377487360+679477248);scratch_required=14092861440
assert mem>=25501368320 and HOST>=HOST_required and scratch>=scratch_required
assert context['author']=='/root' and context['continuity']['no_heavy_since_latest_physical'] is True and context['aggregate']['actual_no_other_heavy'] is True
assert context['aggregate']['committed_memory_bytes']==21206401024 and context['aggregate']['host_reserve_bytes']==4294967296 and context['aggregate']['minimum']==25501368320 and context['aggregate']['durable_memory_lease'] is False
p.update(status='ROOT_EXACT_PAYLOAD_AWAITING_INDEPENDENT_EXECUTION_REVIEW',author='/root',actual_five_query=ref(actual),aggregate=dict(context['aggregate'],MemAvailable=mem),continuity=context['continuity'],namespace=namespace,disk={'HOST_available':HOST,'HOST_required':HOST_required,'scratch_available':scratch,'scratch_required':scratch_required,'full_sparse_gap':gap,'preserve_uuid':'2a5768c8-718d-4914-bdc0-6b32c5a92a52'},issued_at_epoch=time.time(),observations_finished_at_epoch=actual.stat().st_mtime,root_fill_context=ref(context_path),fresh_raw_five=[ref(cap/str(i)/'stdout') for i in range(1,6)],actual_loop_association=loops,actual_mount=mount)
out=D/'ROOT-EXACT-F02-RETAINED-VALIDATION-PAYLOAD.NOT-RELEASED.json'
with out.open('x') as f:json.dump(p,f,indent=2);f.write('\n')
print(json.dumps(ref(out),sort_keys=True))
