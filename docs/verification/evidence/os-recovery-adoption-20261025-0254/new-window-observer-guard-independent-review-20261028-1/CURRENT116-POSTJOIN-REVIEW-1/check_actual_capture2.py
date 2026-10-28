"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Independent actual capture2 retained-data acceptance checks. No live effects.
"""
from pathlib import Path
import hashlib,importlib.util,json,math
B=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
D=B/'current116-actual-postjoin-current60-source-20261028-1'; C=D/'profile-caller-correction-source-1'; O=Path(__file__).parent

def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(p):return json.loads(Path(p).read_bytes())
def load(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

m=load(D/'observe_current60_postjoin.py','actual_capture2_typed_observer')
assert ref(D/'observe_current60_postjoin.py')['sha256']=='de9f6a1b76faded7a31227d13fe30cab33867ba769eb0a0b7234ea564946f048'
rows,common,actors=m.validate_current()
observation_path=D/'ACTUAL-POSTJOIN-OBSERVATION-2-CPU0.json'; observation=read(observation_path)
assert ref(observation_path)['sha256']=='ebbd745f00e17f52fb2e4f589633ca74c9e64e44a643f875c6d9697dc7c9a270'
request=read(C/'REVIEW-REQUEST.json'); caller=read(C/'ROOT-ACTUAL-CPU0-CAPTURE-CALLER.json'); started=read(C/'ACTUAL-CPU0-POSTJOIN-2.STARTED.json'); joined=read(C/'ACTUAL-CPU0-POSTJOIN-2.RESULT.json'); claim=read(C/'ACTUAL-CPU0-POSTJOIN-2.ONCE-CLAIM.json'); manifest=read(C/'ROOT-COMMAND-MANIFEST.PROPOSED.json')
assert ref(C/'owned_capture.py')==request['source'] and caller['argv']==request['root_argv'] and caller['returncode']==0 and caller['stderr']==''
assert json.loads(caller['stdout'])==joined
assert started['pid']==joined['pid']==1907223 and started['birth']==joined['birth']=='96691234'
assert started['actual_affinity']==joined['actual_affinity']==claim['CPU']==[0]
assert started['argv']==joined['argv']==claim['argv']==manifest['argv']
for key,value in started.items():assert joined[key]==value
assert joined['positive_direct_wait4_join'] is joined['streams_closed'] is joined['process_group_absent'] is True
assert joined['returncode']==0 and joined['remaining_group_members']==joined['group_observation_errors']==[]
assert joined['wall_seconds']<120 and joined['CPU_seconds']<60 and joined['maximum_RSS_KiB']*1024<2<<30
assert (C/'ACTUAL-CPU0-POSTJOIN-2.stderr').read_bytes()==b''
assert not (C/'ACTUAL-CPU0-POSTJOIN-2.TIMEOUT-OWNERSHIP-RETAINED.json').exists()
stdout=read(C/'ACTUAL-CPU0-POSTJOIN-2.stdout'); assert stdout['status']==m.STATUS and stdout['output']==ref(observation_path)
assert ref(D/'ROOT-ACTUAL-READONLY-RELEASE-2.json')['sha256']=='1ee8420fba1928b9661dca006e23b647b1487cbc62de88974ee8405f0ff5ee6f'
assert observation['status']==m.STATUS and observation['Root60']==observation['current_boundary']==m.PINS['ledger60']
assert observation['ordinary_build_nonce']==m.NONCE and observation['retained_stopped_container']==m.CID
assert observation['previous_accepted_free_boundary']==rows['ledger60']['latest_accepted_free_boundary']
assert observation['actual_current60_postjoin_acceptance'] is None and observation['current_free_candidate'] is True
assert observation['independent_acceptance'] is observation['native_acceptance'] is observation['artifact_acceptance'] is False
assert observation['runtime_authority'] is None and observation['signals_cleanup_workloads']==0
assert observation['all53_prior_and_new_actors_absent']==actors and len(actors)==53 and len({a['pid'] for a in actors})==48
history=observation['historical_Root59_native_and_physical']
queries=observation['queries']; assert len(queries)==4
for row in queries:assert type(row['returncode']) is int and row['returncode']==0 and row['stderr']=='' and row['positive_wait'] is row['streams_closed'] is True
expected=[(m.PREFIX+['ps','-q','--no-trunc'],''),(m.PREFIX+['ps','-aq','--no-trunc','--filter','name=^/'+m.NAME+'$'],m.CID+'\n'),(m.PREFIX+['ps','-aq','--no-trunc','--filter','id='+m.CID],m.CID+'\n')]
for row,(argv,out) in zip(queries,expected):assert row['argv']==argv and row['stdout']==out
assert queries[3]['argv']==m.PREFIX+['inspect',m.CID]
inspected=json.loads(queries[3]['stdout']); assert m.validate_physical(history,actors,inspected,rows['terminal'])
record=inspected[0];hc=record['HostConfig'];assert record['Image']==rows['profile']['inputs']['image'] and record['Config']['User']=='1000:1000'
assert hc['CpusetCpus']=='2-5' and hc['Memory']==hc['MemorySwap']==12<<30 and hc['PidsLimit']==512 and hc['NetworkMode']=='none' and hc['ReadonlyRootfs'] is True
assert observation['group_membership_observation']==history['group_membership_observation'] and observation['closed_exclusive_probes']==history['closed_exclusive_probes']
census=history['group_membership_observation'];assert not census['errors']
for actor in actors:assert not any(r['pid']==actor['pid'] or r['pgrp']==actor.get('group',actor['pid']) for r in census['rows'])
assert observation['permanent_mutex']==dict(device=27,inode=4,regular=True,no_kernel_lock_row=True)
assert len(observation['closed_exclusive_probes'])==2 and all('FLOCK  ADVISORY  WRITE' in row and '00:1b:4 0 EOF' in row for row in observation['closed_exclusive_probes'])
assert observation['pids_current']==0 and observation['no_existing_heavy'] is observation['active_shared_records_absent'] is True
assert history['capacity']['/home/holden/mckernel']>=16<<30 and history['capacity']['/home/holden/mckernel-work/scratch']>=12<<30 and history['memory']['MemAvailable']>=16<<30
assert history['cgroup']=={'/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_period_us':'100000','/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_quota_us':'400000','/sys/fs/cgroup/memory/mckernel-dev/memory.limit_in_bytes':'12884901888','/sys/fs/cgroup/memory/mckernel-dev/memory.use_hierarchy':'1','/sys/fs/cgroup/pids/mckernel-dev/pids.max':'512'}
# Recheck actual current old-CID full-record comparator and genuine native absence queries.
prior,free,ext,_=common.validate_current(); compare=common.load(common.PINS['mount_compare'],'actual_capture2_mount_multiset_comparator')
assert len(history['current115_exact_CID_queries'])==len(ext['exact_CID_queries'])
for expected,actual in zip(ext['exact_CID_queries'],history['current115_exact_CID_queries']):
 assert actual['argv']==expected['argv'] and actual['positive_wait'] is actual['streams_closed'] is True
 compare.compare(expected,actual['returncode'],actual['stdout'],actual['stderr'])
common.validate_queries(history['native_exact_CID_queries'])
assert history['native_lifecycle']['nonce']=='4d1c28c2d9caa913e4ab1e8a504ac5ea' and history['native_lifecycle']['clients_reaped']==30 and history['native_lifecycle']['host_controls_absent']==35
limits=[1793253600,1035705.5689454618,1051043.6959931096]
assert observation['fixed_cutoffs']==history['fixed_cutoffs']==limits and observation['boot_id']=='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
clocks=[observation['observed_clocks'],history['observed_clocks'],history['last_observed_clocks'],observation['last_observed_clocks']]
for values in clocks:assert len(values)==3 and all(type(v) in (int,float) and math.isfinite(v) and 0<=v<limit for v,limit in zip(values,limits))
assert all(a<=b for before,after in zip(clocks,clocks[1:]) for a,b in zip(before,after))
assert started['started_epoch']<=clocks[0][0]<=clocks[-1][0]<=started['started_epoch']+joined['wall_seconds']+.1
# New HOST source qualifications are disclosed separately, actually joined and absent in this capture census.
supplement_path=B/'new-window-resume-20261028-1/ACTUAL-BODY2-HOST-QUALIFICATION-SUPPLEMENT.json';supplement=read(supplement_path)
assert supplement['author']=='/root' and supplement['consumed_runtime_nonce_delta']==0 and supplement['source_qualification_outside_declared_runtime_nonce_ledger'] is True and len(supplement['actors'])==7
for actor in supplement['actors']:
 assert ref(Path(actor['evidence']['path']))==actor['evidence']
 actual=read(actor['evidence']['path']); commands=actual.get('records',actual.get('commands'))
 records=[r.get('join',r) for r in commands]
 matches=[r for r in records if r['pid']==actor['pid'] and str(r.get('start',r.get('birth')))==actor['birth']]
 assert len(matches)==1; row=matches[0]
 assert row['returncode']==actor['returncode']==0 and row.get('direct_child_joined',row.get('positive_direct_wait4_join')) is True and row.get('group_absent',row.get('process_group_absent')) is True and row.get('closed_streams',row.get('streams_closed')) is True
 assert actor['positive_join'] is actor['group_absent'] is actor['streams_closed'] is True
 assert not any(r['pid']==actor['pid'] or r['pgrp']==actor['pid'] for r in census['rows'])
print(json.dumps(dict(status='PASS_ACTUAL_CAPTURE2_ONLY_FULL_RETAINED_DATA_ACCEPTANCE_CHECKS',observation=ref(observation_path),profile_child=joined,Root60=m.PINS['ledger60'],rows=len(actors),distinct_PIDs=len({a['pid'] for a in actors}),capacity=history['capacity'],memory=history['memory'],clocks=clocks,fixed_cutoffs=limits,HOST_qualification_supplement=ref(supplement_path),live_calls=0),indent=2))
