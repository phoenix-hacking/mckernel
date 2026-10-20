"""Read only completed immutable evidence; emit one private independent result review."""
import hashlib,json,os,re,stat,struct,tarfile
from pathlib import Path
P=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-repeated-cycle-20261019-1/native-packet-1/sdk-predecessor-correction-1')
R=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-repeated-cycle-independent-review-20261019-1/sdk-predecessor-correction-1')
SHA=lambda b:hashlib.sha256(b).hexdigest()
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=SHA(b),bytes=len(b))
def checked(r):
 b=Path(r['path']).read_bytes();assert SHA(b)==r['sha256'] and len(b)==r.get('bytes',r.get('size',len(b)));return b
def meta(s):return dict(device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode),size=s.st_size,nlink=s.st_nlink,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
def stable_stream(row):
 p=Path(row['path'])
 with p.open('rb') as f:
  a=os.fstat(f.fileno());b=f.read();z=os.fstat(f.fileno())
 assert meta(a)==meta(z)==meta(p.stat())==row['metadata'];assert stat.S_ISREG(a.st_mode) and SHA(b)==row['sha256'];return b
idx=json.loads(checked(dict(path=str(P/'NATIVE-MACHINE-AND-CAPTURE-INDEX.json'),sha256='826c68e8495c376b6a0e691e4ef1bf53ae6aba68184e0dc5858fe46934e936c3',bytes=20031)))
case=json.loads(checked(idx['whole_case']));whole=json.loads((P/'root-seven-whole.json').read_bytes());assert whole['status']=='PASS_WHOLE_JOINED_RELEASED_CHAIN' and whole['failed_stage'] is None and len(whole['rows'])==7
machine=ref(P/'execution-release.json');machine_obj=json.loads(checked(machine));snapshot=machine_obj['fresh_live_preflight'];checked(snapshot)
guardpath=R/'FINAL-IHK-LOGGING-NATIVE-MACHINE-REVIEW.json';guard=json.loads(guardpath.read_bytes());assert guard['status']=='PASS_EXACT_CURRENT_IHK_FP1E7_LOGGING_DIAGNOSTIC_NATIVE_RELEASE' and guard['execution_release']==machine and guard['allowed_argv']==case['launch_argv']
records=[];bodies={}
for step in idx['ordered_capture_steps']:
 name=step['name'];data=json.loads(checked(step['commands']));op=data['operations'][1];s=json.loads(Path(op['status_path']).read_bytes());outer=json.loads((P/('root-'+name+'.status.json')).read_bytes())
 for x in (s,outer):assert x['returncode']==0 and x['direct_child_joined'] is True and x['process_group_absent'] is True and x['observer_error'] is None
 expected=[machine['sha256'] if x=='ACTUAL_MACHINE_SHA256' else snapshot['sha256'] if x=='ACTUAL_SNAPSHOT_SHA256' else x for x in op['argv_template']];assert s['argv']==expected
 for role in ['stdout','stderr']:
  row=s['streams'][role];assert row['path']==op[role+'_path'];bodies[(name,role)]=stable_stream(row)
 assert bodies[(name,'stderr')]==b''
 records.append(dict(name=name,outer_status=ref(P/('root-'+name+'.status.json')),inner_status=ref(op['status_path']),pid=s['pid'],start=s['start'],elapsed_seconds=s['elapsed_seconds'],streams=s['streams']))
owner_outer=json.loads((P/'root-native-owner.status.json').read_bytes());assert owner_outer['started_at']<guard['expires_at_epoch'];assert owner_outer['argv'][-1]=='1';assert bodies[('native-owner','stdout')]==b''
raw=bodies[('readback-2','stdout')];result=json.loads(raw);assert result['status']=='PROTOCOL_PASS' and not result['application_acceptance'] and not result['mckernel_application_executed'];obs=result['observation']
archives={};archive_rows=[]
for role in ['readback-1','readback-3']:
 path=P/(role+'.stdout')
 with tarfile.open(path,'r:*') as tf:
  members=tf.getmembers();assert len({m.name for m in members})==len(members);assert all(m.name=='.' or (m.isfile() and m.name.startswith('./') and '..' not in Path(m.name).parts) for m in members)
  archives[role]={m.name:tf.extractfile(m).read() for m in members if m.isfile()}
 archive_rows.append(dict(role=role,archive=ref(path),regular_members=sum(m.isfile() for m in members),duplicate_members=0))
assert archives['readback-1']['./inner-result.json']==archives['readback-3']['./result.json']==raw
for name in ['serial.log','debugcon.log','qmp.transcript.json','qemu.stdout','qemu.stderr']:
 assert archives['readback-1']['./'+name]==archives['readback-3']['./'+name]
for file,key in [('serial.log','serial'),('debugcon.log','debugcon')]:assert archives['readback-1']['./'+file].decode()==obs[key]
assert archives['readback-1']['./qemu.stderr']==b''
receipt=json.loads(archives['readback-1']['./result.json']);assert receipt['status']=='PROTOCOL_PASS' and receipt['failure'] is None and receipt['absence_verified'] is True and receipt['lease_retained'] is False
for role,row in case['source_refs'].items():checked(row)
assert case['runtime_source_hashes'][case['source_refs']['runtime_observer']['path']]=='622a8df5f3831fa24f4469bf6fda0b64d06f9c1a4742a988867277cbc12ccd5d'
assert case['source_refs']['mandatory_cycle_oracle']['sha256']=='05bba58841990cf01907a2b9dbc38cc95822dfb18cef1ee0e53906b4165c112e'
checked(case['manifest']);checked(case['stage_review']);checked(case['typed_composition_review'])
assessment=json.loads((R/'ACTUAL-CLOSED-TWO-CYCLE-ORACLE-ASSESSMENT.json').read_bytes());assert assessment['result_sha256']==SHA(raw) and assessment['full_host_evaluate'] and assessment['exact_guest_report_equality'] and assessment['archive_result_serial_debugcon_qmp_equal']
assert result['pair_metrics']==dict(completed_apps=4,completed_cycles=2,full_restoration_verified=False)
frames=[];streams={};controls={};ident={}
for line in obs['serial'].splitlines():
 if not line.startswith('ND_CYCLE'):continue
 prefix,body=line.split(' ',1);value=json.loads(body);frames.append(prefix)
 if prefix=='ND_CYCLE_CHUNK':
  key=(value['cycle'],value['kind'],value['name']);out=streams.setdefault(key,bytearray());assert value['offset']==len(out);out.extend(bytes.fromhex(value['hex']))
 elif prefix=='ND_CYCLE_CONTROL':controls[(value['cycle'],value['kind'])]=value
 elif prefix=='ND_CYCLE_IDENTITY':ident[value['cycle']]=value
summaries=[]
for i,c in enumerate(result['guest_report']['cycles']):
 identity=ident[i];g=identity['generation'];assert g==c['generation_observed'];proof=bytes(streams[(i,'pair','assignment')]);magic,n0,n1,osid,count,actualg,cpu0,cpu1=struct.unpack('<QQQIIQii',proof);assert len(proof)==48 and (magic,osid,count,actualg,cpu0,cpu1)==(0x3155504344524150,0,2,g,1,2) and ('%016x%016x'%(n0,n1))==identity['challenge']
 trace=bytes(streams[(i,'pair','kernel_log')]).decode();apps=[]
 for a in c['pair']['apps']:
  pid=a['pid'];prefix='os=0 generation='+str(g)+' pid='+str(pid);delivered=re.findall('application_syscall=delivered '+re.escape(prefix)+r' worker=(\d+) delivery=(\d+) cpu=(\d+) number=(\d+)',trace);retire=re.findall('application retirement '+re.escape(prefix)+r' token=(\d+) errno=(-?\d+)',trace)
  assert len([r for r in delivered if r[3]=='231'])==1 and not any(r[3]=='60' for r in delivered)
  apps.append(dict(id=a['id'],pid=pid,cpu=a['cpu'],argv=a['argv'],cwd=a['cwd'],raw_wait_status=a['raw_wait_status'],started_ns=a['started_ns'],reaped_ns=a['reaped_ns'],finished_ns=a['finished_ns'],stdout=dict(bytes=a['streams']['stdout']['observed'],sha256=SHA(bytes.fromhex(a['streams']['stdout']['hex']))),stderr_bytes=a['streams']['stderr']['observed'],syscalls_delivered=len(delivered),retirement_attempts=len(retire),successful_retirement_tokens=[int(t) for t,e in retire if e=='0'],strict_startup_schedule_cpu=True,syscall_cpu_routes_order_and_procfs_verified=True))
 stop=[json.loads(l) for l in streams[(i,'stop','stdout')].decode().splitlines()];release=[json.loads(l) for l in streams[(i,'release','stdout')].decode().splitlines()];memory=[r for r in release if r.get('stage')=='memory_inventory'];cpu=[r for r in release if r.get('stage')=='cpu_inventory'];assert [m['bytes'] for m in memory]==[134217728,134217728,0] and len(cpu)==3 and all(r['cpus']==[] and r['count']==0 for r in cpu)
 summaries.append(dict(cycle=i,os=0,generation_observed=g,challenge=identity['challenge'],assignment48_sha256=SHA(proof),prior_log_bytes=identity['prior_log_bytes'],fresh_log_bytes=identity['fresh_log_bytes'],trace_sha256=SHA(trace.encode()),trace_lines=len(trace.splitlines()),apps=apps,controls={k:controls[(i,k)] for k in ['boot','stop','release']},strict_stop=stop,public_inventory=dict(memory=memory,cpu=cpu,cpu1_online_before_after=True,cpu2_online_before_after=True,destroy_os_return=0,release_device_mem_return=0),protocol_public_release=c['public_release']))
assert [s['generation_observed'] for s in summaries]==[1,2] and summaries[0]['challenge']!=summaries[1]['challenge']
report=dict(schema='mckernel.independent-selected205-two-complete-cycle-actual-native-semantic-review.v1',status='PASS',decision='PASS_ACTUAL_TWO_COMPLETE_SELECTED205_LIFECYCLE_CYCLES_AND_FOUR_PAYLOAD_LAUNCHES_ONLY',implementation_ownership=False,reviewer='/root/resume_git_owner_review',scope='Functional OS/apps and Rust plus reviewed assembly: actual selected205 same-Linux-guest two complete McKernel incarnations, unchanged two payloads per incarnation; semantic result only.',whole_join=ref(P/'root-seven-whole.json'),source_and_capture_review=ref(R/'FINAL-SEVEN-ROW-CAPTURE-AND-LAST-SNAPSHOT-REVIEW.json'),whole_case=idx['whole_case'],actual_final_guard=ref(guardpath),machine_release=machine,actual_snapshot=snapshot,stage_review=case['stage_review'],mandatory_consumer_review=case['typed_composition_review'],manifest=case['manifest'],selected_tuple=case['selected_tuple_manifest'],image=case['image'],modules=case['modules'],source_refs=case['source_refs'],runtime_source_count=45,unchanged_full_owner_source_authority_reused=True,completed_capture_records=records,archive_joins=archive_rows,actual_result=ref(P/'readback-2.stdout'),oracle_assessment=ref(R/'ACTUAL-CLOSED-TWO-CYCLE-ORACLE-ASSESSMENT.json'),raw_protocol_status=result['status'],raw_protocol_acceptance_flags_unchanged=dict(application_acceptance=result['application_acceptance'],mckernel_application_executed=result['mckernel_application_executed'],guest_report={k:v for k,v in result['guest_report'].items() if k!='cycles'}),actual_native_diagnostic_execution_observed=True,bounded_two_complete_cycle_semantic_acceptance=True,first_semantic_failure=None,cycles=summaries,counts=dict(native_owner_invocations=1,linux_qemu_guests=1,complete_mckernel_boot_pair_stop_public_release_cycles=2,payload_launches=4,distinct_existing_payloads=2,new_logical_application_cases=0,strict_stops=2,public_releases=2,fresh_generation_assignments=2),host_observation=dict(started_at=obs['started_at'],finished_at=obs['finished_at'],deadline=obs['deadline'],elapsed_seconds=obs['finished_at']-obs['started_at'],qmp=obs['qmp'],teardown=obs['teardown'],qemu_evidence=obs['qemu_evidence'],qemu_minus9_after_shutdown_is_existing_host_transport=True),physical_retirement=dict(independent_separate_reviewer=True,not_issued_by_this_report=True,root_receipt_sha256=SHA(archives['readback-1']['./result.json']),container=receipt['container']),practical_credit=dict(M12='Two complete native diagnostic cycles are observed; this is bounded repeatability evidence, not the deferred duration/launch quotas or full milestone acceptance.',P_M00_02='Functional boot, application execution, strict stop and public pool release are observed twice for the exact tuple; whole-OS/full restoration acceptance remains open.',logical_case_dedup='The same two existing payloads ran twice. Four actual launches and two complete cycles; zero new logical application cases.'),limitations=dict(full_restoration_verified=False,physical_frame_identity_verified=False,full_generation_restoration_verified=False,reference_callback_restoration_verified=False,held_tasks_restoration_verified=False,nonnull_FP_acceptance=False,UTI_refill_or_replaceTID_verified=False,failed_MM_error_path_verified=False,ten_cycle_credit=False,hundred_launch_credit=False,sixty_minute_credit=False,repeat_quota_credit=False,whole_OS_acceptance=False,whole_Rust_retirement=False,original_case_ids_and_failed_attempts_preserved=True))
out=R/'ACTUAL-TWO-COMPLETE-CYCLE-NATIVE-SEMANTIC-REVIEW.json';b=(json.dumps(report,sort_keys=True,indent=2)+'\n').encode();out.open('xb').write(b);print(json.dumps(ref(out)));print('PASS: two complete cycles; four payload launches; generations1,2; zero new logical cases; physical acceptance separate.')
