"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Metadata only; no queries executed."""
from pathlib import Path
import json,hashlib,shutil,difflib
HP=Path('/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1');RE=Path('/home/holden/mckernel/docs/verification/evidence/p12-long-first-round-progress-expert-20261023-1');B=HP/'failed91c-physical-preparation-1';P=Path(__file__).resolve().parent;R=RE/'next-live-observation-5603-1/physical-preparation-1';O=R/'authenticated-retired-owner-commands-1'
def desc(p):b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(p,x):
 with p.open('x') as f:f.write(json.dumps(x,sort_keys=True,indent=2)+'\n')
write(P/'PRESERVED-METADATA-PARSER-ASSERTION-1.json',dict(scope=__doc__,status='PRESERVED_METADATA_PREPARATION_FAILURE_NO_QUERY',error='AssertionError requiring command.returncode == nullable outer record.returncode for009-start; outer returncodeNone is retained exception result, real child returncode-9/reapedtrue in command record.',correction='Use actual command record child returncode; retain outer recordreturncodeNone separately; compare only if nonNone.',source_row=desc(O/'009-start.json'),root_queries=0))
owner=json.loads((O/'owner.json').read_bytes());result=json.loads((O/'result.json').read_bytes());bind=json.loads((O/'EXPORT-BINDING.json').read_bytes());nonce=owner['nonce'];cid=result['container'];assert nonce=='5603c55a294240fdb86c3613ec42e293' and result['absence_verified'] is True and result['lease_retained'] is False
clients=[]
for path in sorted(O.glob('*.json')):
 if not path.name.partition('-')[0].isdigit():continue
 row=json.loads(path.read_bytes());c=row['command'];assert c['reaped'] is True and c['pid']==c['pgid'] and c['sid']==3857698
 if row['returncode'] is not None:assert c['returncode']==row['returncode']
 clients.append(dict(name=path.name,argv=row['argv'],source=desc(path),record_returncode=row['returncode'],**c))
assert len(clients)==23 and len({(x['pid'],x['proc_starttime']) for x in clients})==23
for name in ['004-create.stdout','020-rm.stdout']:assert (O/name).read_bytes()==(cid+'\n').encode()
for n in range(21,24):
 assert json.loads((O/('%03d-ps.json'%n)).read_bytes())['returncode']==0
 for ext in ['stdout','stderr']:assert (O/('%03d-ps.%s'%(n,ext))).read_bytes()==b''
first=json.loads((O/'015-inspect.stdout').read_bytes())[0];last=json.loads((O/'019-inspect.stdout').read_bytes())[0];assert first['Id']==last['Id']==cid and last['State']['Pid']==0 and last['State']['Running'] is False and last['State']['ExitCode']==143 and last['State']['OOMKilled'] is False
init=first['State']['Pid'];assert init==3857780
initfact=dict(actual_inspect_refs={n:desc(O/n) for n in ['015-inspect.stdout','019-inspect.stdout']},observed_PID_015=init,observed_PID_019=0,positive_retained_pids=[init],birth=None,qualification='Positive initPID3857780 retained015; birth not captured. Require numericPID absence BOTH fresh complete snapshots; no PID0 identity or invented birth.')
facts=dict(scope=__doc__,boot_id='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb',nonce=nonce,outer_anchor=dict(pid=3857691,proc_starttime=57872086),inner_owner=dict(pid=3857698,proc_starttime=57872098),owner_identity=owner['outer'],owner_result=desc(O/'result.json'),authenticated_export_binding=desc(O/'EXPORT-BINDING.json'),authenticated_directory_listing=None,listing_completeness='Pending same finalPROC operation: bounded stable retainedowner listing requires commandJSON names exactly exported23.',owner_evidence_root=bind['root'],owner_evidence_root_identity=bind['root_identity'],clients=clients,container_init_observation=initfact,physical_clearance=False)
write(P/'ACTUAL-23-CLIENT-IDENTITIES.json',facts);factsha=desc(P/'ACTUAL-23-CLIENT-IDENTITIES.json')['sha256']
old=(B/'readonly_exact_retired_LONG_proc.py').read_text();source=old.replace('import fcntl','import fcntl,stat',1).replace('retired-LONG-91c-final-physical-20261023-1','retired-LONG-5603-final-physical-20261023-1').replace(str(B/'ACTUAL-23-CLIENT-IDENTITIES.json'),str(P/'ACTUAL-23-CLIENT-IDENTITIES.json')).replace('0cded10600273c6cd2d2bdebfaf65e3677486d3055f16fb64c34ba51c7f55798',factsha)
needle="identities=[facts['outer_anchor'],facts['inner_owner']]+facts['clients']"
listing="""# One bounded retained directory listing supplies exact command-ledger completeness.
root=Path(facts['owner_evidence_root']);root_fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
try:
 before=os.fstat(root_fd);directory_names=sorted(os.listdir(root_fd));after=os.fstat(root_fd);named=root.lstat()
 fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_mtime_ns','st_ctime_ns')
 need(stat.S_ISDIR(before.st_mode) and before.st_uid==before.st_gid==0 and stat.S_IMODE(before.st_mode)==0o700 and len(directory_names)<=4096 and all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in fields),'bounded stable retained owner directory')
 need(before.st_dev==facts['owner_evidence_root_identity']['dev'] and before.st_ino==facts['owner_evidence_root_identity']['inode'],'exact authenticated retained owner directory identity')
 command_names=sorted(name for name in directory_names if name.endswith('.json') and name.partition('-')[0].isdigit())
 need(command_names==sorted(row['name'] for row in facts['clients']),'complete exact23command client ledger; additional or missing command identity')
finally:os.close(root_fd)
"""
assert needle in source;source=source.replace(needle,listing+needle,1).replace("container_init_birth=None,physical_clearance=False", "container_init_birth=None,retained_owner_directory_listing=directory_names,exact_command_names=command_names,retained_owner_directory_identity={'dev':before.st_dev,'inode':before.st_ino},physical_clearance=False")
(P/'readonly_exact_retired_LONG_proc.py').write_text(source);(P/'proc.successor.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),source.splitlines(True),fromfile='accepted91c59ef2COMPLETE',tofile='5603actualidentities-plus-one-bounded-retained-listing')))
argv=json.loads((B/'ROOT-FINAL-PROC-ARGV.NOT-RELEASED.json').read_bytes());argv[-1]=str(P/'readonly_exact_retired_LONG_proc.py');write(P/'ROOT-FINAL-PROC-ARGV.NOT-RELEASED.json',argv)
packet=json.loads((B/'EXACT-FINAL-PHYSICAL-OPERATIONS.NOT-RELEASED.json').read_bytes());packet.update(status='EXACT5603_SDK6_RETIRED_OWNER_FINAL_PROC_MUTEX_READY_FOR_REVIEW',actual_client_binding=desc(P/'ACTUAL-23-CLIENT-IDENTITIES.json'),actual_export_owner_result=desc(O/'result.json'),actual_final_mutex=None,actual_final_proc=None,independent_release=None,independent_physical_acceptance=None,physical_clearance=False,current_live_postjoin='CLOSED_FAILED_SDK6_PENDING_PHYSICAL',container_init_observation=initfact,source_delta='ENGINE59ef/twoCOMPLETE/run/need unchanged. Actual5603clientfacts path/SHA/challenge literals. One bounded stable retainedowner listing asserts no commandJSON clients beyond23; numericinit3857780 absent BOTH snapshots/birthNULL. Mutex byteidenticalca4485.',predecessors=[desc(B/'readonly_exact_retired_LONG_proc.py'),desc(B/'readonly_current_mutex_paths_positive.py')])
packet['captured_container_absence_evidence']={n:desc(O/n) for n in packet['captured_container_absence_evidence']}
for op,name in zip(packet['operations'],['readonly_exact_retired_LONG_proc.py','readonly_current_mutex_paths_positive.py']):
 op['source']=desc(P/name);op['argv'][-1]=str(P/name);op['capture_namespace']=str(P/('actual-final-proc-1' if op['name']=='final-proc' else 'actual-final-mutex-1'))
write(P/'EXACT-FINAL-PHYSICAL-OPERATIONS.NOT-RELEASED.json',packet)
for name in ['PRESERVED-METADATA-PARSER-ASSERTION-1.json','ACTUAL-23-CLIENT-IDENTITIES.json','readonly_exact_retired_LONG_proc.py','proc.successor.diff','ROOT-FINAL-PROC-ARGV.NOT-RELEASED.json','EXACT-FINAL-PHYSICAL-OPERATIONS.NOT-RELEASED.json',Path(__file__).name]:shutil.copy2(P/name,R/name)
for name in ['EXACT-FINAL-PHYSICAL-OPERATIONS.NOT-RELEASED.json','readonly_exact_retired_LONG_proc.py','ACTUAL-23-CLIENT-IDENTITIES.json']:print(json.dumps(desc(P/name),sort_keys=True))
