"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only current source/publication join; no root, Docker or guest operations.
"""
import ast,hashlib,json,os,subprocess,time
from pathlib import Path
D=Path(__file__).resolve().parent;R=Path('/home/holden/mckernel')
assert os.sched_getaffinity(0)=={7}
B=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/native-runtime-ready-1');F=B.parent/'fork-v3-matched-process-successor-1/case-235/final-runtime-ready-1'
T=Path('/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1/actual-terminal-preparation-1')
def j(p):return json.loads(p.read_text())
def ref(p,expected=None):
    before=p.stat();raw=p.read_bytes();after=p.stat();assert (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)
    h=hashlib.sha256(raw).hexdigest()
    if expected:assert h==expected,(str(p),h,expected)
    return dict(path=str(p),bytes=len(raw),sha256=h,identity={k:getattr(after,k) for k in ('st_dev','st_ino','st_size','st_mode','st_uid','st_gid','st_nlink','st_mtime_ns','st_ctime_ns')})
def git(*a):return subprocess.check_output(['/usr/bin/git',*a],cwd=R)
a=j(B/'EXACT-PUBLICATION-AND-SOURCE-AUTHENTICATION.json');owner=B/'native_diagnostic_container_owner.py'
source_map=next(ast.literal_eval(n.value) for n in ast.parse(owner.read_text()).body if isinstance(n,ast.Assign) and any(isinstance(z,ast.Name)and z.id=='SOURCE_HASHES' for z in n.targets))
assert len(source_map)==139 and source_map==a['every_source_HASHES_entry']
# These are required runtime source/data inputs, not retention archives. The two
# >2MiB JSON inputs are hash-authoritative owner prerequisites; hash them once here.
source_rows=[ref(Path(p),h)for p,h in source_map.items()]
cohort=[ref(Path(r['path']),r['sha256'])for r in a['expected_current_cohort']]
refs={k:git('rev-parse',k).decode().strip()for k in ('HEAD','FETCH_HEAD','origin/codex/local-native-staging-repair')}
assert len(set(refs.values()))==1 and refs['HEAD'].startswith('a2d037dc')
selected=j(F/'EXACT-SOURCE-DATA-PUBLICATION-MAP.json')['selected']+j(F/'FINAL-FROZEN-PUBLICATION-SUPPLEMENT.json')['selected'];assert len(selected)==26
publication=[]
for row in selected:
    p=Path(row['private']['path']);current=ref(p,row['private']['sha256']);relative=str(Path(row['publication_path']).relative_to(R));blob_refs={}
    for name in ('HEAD','origin/codex/local-native-staging-repair'):
        raw=git('show',name+':'+relative);assert len(raw)==row['private']['bytes'] and hashlib.sha256(raw).hexdigest()==current['sha256'];blob_refs[name]=git('rev-parse',name+':'+relative).decode().strip()
    publication.append(dict(private=current,publication_path=relative,git_blob=blob_refs))
physical=ref(T/'INDEPENDENT-ACTUAL-LAUNCHER-PHYSICAL-ACCEPTANCE-1.json');assert physical['sha256'].startswith('46ed040d')
livefile=T/'ACTUAL-CURRENT-LIVE-POSTJOIN-OBSERVATION-1.json';live=j(livefile)['current_live_postjoin'];live_refs={}
for name,r in live.items():live_refs[name]=ref(Path(r['path']),r['sha256'])
assert live_refs['observer_release'] is not None
ad=D.parent/'admission';receipt=j(ad/'receipt.json');assert receipt['returncode']==0 and receipt['direct_child_joined'] and receipt['streams_closed'] and receipt['stderr_bytes']==0
fresh=j(ad/'stdout.json');assert fresh['status']=='PASS_FRESH_READ_ONLY_NATIVE235_CURRENT_LIVE_ADMISSION'
tools=[ref(Path(p).resolve())for p in ('/usr/bin/taskset','/usr/bin/prlimit','/usr/bin/sudo','/usr/bin/docker','/home/holden/anaconda3/bin/python3')]
# QEMU is deliberately an in-container executable, not a host file to invent.
image_record=ref(Path(a['image_record']['path']),a['image_record']['sha256'])
r=dict(scope=__doc__.splitlines()[0],status='PASS_CURRENT_SOURCE139_COHORT_TOOL_PUBLICATION_AND_EVIDENCE_BINDING_NO_EXECUTION_AUTHORITY',at_unix=time.time(),
current_source139=dict(owner=ref(owner,a['owner_cli_auth']['expected_owner_sha256']),inventory_authority=ref(B/'EXACT-PUBLICATION-AND-SOURCE-AUTHENTICATION.json'),count=139,rows=source_rows,semantics='All139 literal owner SOURCE_HASHES entries freshly matched; no large retention archive hashes; owner repeats its stable exact source validation in production.'),
current_private_cohort=cohort,host_tool_identities=tools,
backend=next(r for r in cohort if r['path'].endswith('native_diagnostic_backend.py')),
container_QEMU=dict(**a['QEMU'],scope='Exact pinned container-image executable; not installed at that path on HOST; runtime inside owner checks exact hash/version before guest.',image=a['Docker_image'],image_record=image_record),
git=dict(existing_local_refs=refs,network_operations=0,publication_count=26,publication=publication,prior_fetched_proof=ref(F/'ROOT-FETCHED-CASE-SOURCE-PUBLICATION-1.json'),qualification='Existing FETCH_HEAD/origin exact refs observed; no new fetch performed by worker.'),
fresh_read_only_admission=dict(receipt=ref(ad/'receipt.json'),stdout=ref(ad/'stdout.json'),returncode=0,qualification='Fresh root evidence provided by dispatcher; preparer did not execute root or Docker.'),
latest_launcher_positive_physical=physical,current_live_postjoin=dict(retained_observation=ref(livefile),exact_observer_release_and_output_captures=live_refs,qualification='Actual historical read-only observer+summary bindings, including non-null observer_release; physical_clearance remainsfalse in this record. Separate genuine46ed physical acceptance bound above. This is not invented fresh observer or new postjoin authority.'),
original_frozen_required_root_fields='Unchanged; additive binding record only.',fresh_metadata_guard='Root-owned separate capture; not claimed here.',execution_authorized=False,native_credit=0,root_Docker_guest_operations=0)
(D/'BOUND-CURRENT-IDENTITIES.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(status=r['status'],source139=len(source_rows),cohort=len(cohort),publication=len(publication),HEAD=refs['HEAD'])))
