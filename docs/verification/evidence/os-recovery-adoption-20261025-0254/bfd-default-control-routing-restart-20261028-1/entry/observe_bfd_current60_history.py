"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Typed ordinary-build postjoin extension of genuine Root59 native lifecycle history.
No guard/physical observation on import or validate_current; separate readonly release required.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import re
import stat
import subprocess

HERE=Path(__file__).resolve().parent
PINS=json.loads((HERE/'ACTUAL-PINS.json').read_bytes())
NONCE='ff79f7711b2ba35b039f3a191ab09663'
CID='57a5fb1f62bc707ee90412fe9585718cdaa39e4110854f91bf4cb6df4380fda3'
NAME='current116-build-only-'+NONCE
STATUS='PASS_ROOT60_CURRENT116_BUILD_POSTJOIN_OBSERVATION_PENDING_INDEPENDENT_ACCEPTANCE'
PREFIX=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock']


def need(ok,why):
 if not ok:raise ValueError(why)
def ref(path):
 path=Path(path);raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def auth(row):
 need(type(row)is dict and set(row)=={'path','bytes','sha256'} and ref(row['path'])==row,'exact BYTE subject');return Path(row['path'])
def checked(row):return json.loads(auth(row).read_bytes())
def load(row,name):
 spec=importlib.util.spec_from_file_location(name,auth(row));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def validate_bundle(ledger,prior,profile,grant,once,claim,result,terminal,started,joined,ready,local,plan):
 need(ledger['author']=='/root' and ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True,'Root60 complete attestation')
 need(ledger['prior_ledger_retained']==PINS['ledger59'] and ledger['consumed_nonces']==prior['consumed_nonces']+[NONCE] and len(set(ledger['consumed_nonces']))==70,'one genuine ordinary build after Root59')
 need(ledger['current_physical_clearance_pending'] is True and ledger['latest_accepted_free_boundary']==prior['latest_accepted_free_boundary'],'f76 historical previous clearance; fresh postjoin pending')
 need(ledger['current_native_operation']==prior['current_native_operation'] and ledger['current_native_operation']['nonce']=='4d1c28c2d9caa913e4ab1e8a504ac5ea','native branch retained without ordinary relabel')
 need(ledger['ordinary_operations_since_prior_heavy_boundary']==prior['ordinary_operations_since_prior_heavy_boundary'],'ordinary build separate typed extension')
 build=ledger['current116_build'];need(build['operation']=='CURRENT116_BUILD_ONLY_NOT_NATIVE' and build['nonce']==NONCE and build['holder_tool_session']==54937 and build['holder_tool_joined_returncode']==0,'actual tool54937 positive join')
 need(build['current_physical_clearance_pending'] is True and build['current_native_acceptance'] is None and build['current_default_artifact_acceptance'] is None,'no invented physical/native/artifact acceptance')
 for key in ['profile','actual_grant','once_entry','container_claim','worker_result','terminal','runner_started','runner_join','holder_ready','holder_local_terminal']:need(build[key]==PINS[key],'exact build reference '+key)
 need(grant['author']=='/root' and grant['nonce']==NONCE and grant['maximum_invocations']==1 and grant['profile']==PINS['profile'],'actual bounded build grant')
 need(once['author']=='/root' and once['nonce']==NONCE and claim['grant']==PINS['actual_grant'] and claim['pid']==1901981 and claim['native_authority'] is False,'consumed once publication/container claims')
 argv=claim['argv'];need(argv[:4]==PREFIX and argv[4]=='run' and argv[argv.index('--name')+1]==NAME,'exact build container name/client')
 need(profile['actual_nonce']==NONCE and len(profile['exact_commands'])==4 and plan['commands']==profile['exact_commands'],'original exact four-command profile/plan')
 need(result['status']=='PASS_BUILD_ONLY_PENDING_CURRENT_DEFAULT_AND_NATIVE_VALIDATORS' and result['default_native_retirement_acceptance'] is False and len(result['commands'])==4,'four real compiler/link results only')
 for index,(actual,expected) in enumerate(zip(result['commands'],profile['exact_commands'])):
  need(actual['index']==index and actual['argv']==expected['argv'] and actual['cwd']==expected['cwd'] and actual['returncode']==0,'exact command '+str(index))
  need(actual['output']['path']==expected['new_output'] and actual['finished_at_epoch']>=actual['started_at_epoch'],'command output/timing evidence')
 need(terminal['returncode']==0 and terminal['container']==CID and terminal['default_native_retirement_acceptance'] is False,'actual stopped build container')
 state=terminal['state'];need(state['Status']=='exited' and state['Running'] is False and state['Pid']==0 and state['ExitCode']==0 and state['OOMKilled'] is False and state['Error']=='' and not any(state[x] for x in ['Paused','Restarting','Dead']),'stopped exit0/noOOM state')
 need(started['pid']==joined['pid']==1901981 and started['starttime']==joined['starttime']==96608898 and joined['joined'] is True and joined['returncode']==0,'exact runner positive join')
 need(started['argv']==['/home/holden/anaconda3/bin/python3','-I','-B',grant['runner']['path'],'--execute',PINS['actual_grant']['path']],'literal runner grant argv')
 holder=dict(path='/run/lock/mckernel-development.lock',pid=1901931,starttime=96606231,device=27,inode=4,fd=3)
 need(ready['nonce']==NONCE and ready['holder']==local['holder']==holder and local['joined'] is True and local['returncode']==0 and local['container_terminal_or_no_launch'] is True,'exact holder positive retirement/permanent custody')
 return [dict(pid=holder['pid'],start=holder['starttime'],role='CURRENT116_holder'),dict(pid=started['pid'],start=started['starttime'],role='CURRENT116_runner')]


def validate_current():
 need(ref(PINS['ledger60']['path'])['sha256']=='bd4b75db9c1c7cdb2993aa957c0c9a690eed39210d751ba89319c29ef4fc28d4','exact Root60 byte identity')
 rows={k:checked(PINS[k]) for k in ['ledger60','ledger59','profile','actual_grant','once_entry','container_claim','worker_result','terminal','runner_started','runner_join','holder_ready','holder_local_terminal','plan']}
 common=load(PINS['common'],'retained_real_Root59_native_data');prior,free,ext,actors=common.validate_current(common.CURRENT)
 need(prior==rows['ledger59'] and len(actors)==51,'all51 prior ordinary/native actors retained')
 for key in ['actual_independent_PASS','publisher']:auth(rows['once_entry'][key])
 for key in ['runner','worker','review','resource_authority','input_export_authority']:auth(rows['actual_grant'][key])
 need(auth(PINS['container_id']).read_text().strip()==CID,'retained CID file')
 auth(PINS['container_stdout']);auth(PINS['container_stderr']);checked(PINS['operation_binding']);checked(PINS['common_dependencies'])
 new=validate_bundle(rows['ledger60'],rows['ledger59'],*[rows[k] for k in ['profile','actual_grant','once_entry','container_claim','worker_result','terminal','runner_started','runner_join','holder_ready','holder_local_terminal','plan']])
 return rows,common,actors+new


def validate_physical(history,actors,inspect_row,terminal):
 need(history['Root59']==PINS['ledger59'] and history['actual_latest_operation_postjoin_acceptance']==checked(PINS['ledger59'])['latest_accepted_free_boundary'],'genuine historical native branch retained')
 need(history['pids_current']==0 and history['no_existing_heavy'] is True and history['active_shared_records_absent'] is True and len(history['closed_exclusive_probes'])==2,'physical/cgroup/shared custody free')
 census=history['group_membership_observation'];need(not census['errors'],'complete process census')
 for actor in actors:need(not any(row['pid']==actor['pid'] or row['pgrp']==actor['pid'] for row in census['rows']),'all53 actor PID/groups absent')
 need(type(inspect_row)is list and len(inspect_row)==1,'one exact stopped CID record')
 record=inspect_row[0];need(record['Id']==CID and record['Name']=='/'+NAME and record['State']==terminal['state'],'live exact retained CID/name/allstatefields')
 need(history['capacity']['/home/holden/mckernel']>=16*2**30 and history['capacity']['/home/holden/mckernel-work/scratch']>=12*2**30,'original storage floors')
 return True


def observe():
 need(os.getuid()==os.geteuid()==1000,'ordinary readonly observer profile')
 rows,common,actors=validate_current()
 dependencies=json.loads((HERE/'ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json').read_bytes());guard,_physical=common.configured_dependencies(dependencies)
 first=guard.guard();history=common.observe()
 for actor in actors:need(not Path('/proc',str(actor['pid'])).exists(),'all53 prior/new host PIDs absent')
 need(not Path('/proc/1901931/fd/3').exists(),'retired holder descriptor absent')
 for actor in actors[-2:]:need(not Path('/proc',str(actor['pid']),'task').exists(),'new holder/runner threads absent')
 lock=Path('/run/lock/mckernel-development.lock');st=lock.stat();need(stat.S_ISREG(st.st_mode) and st.st_dev==27 and st.st_ino==4,'permanent lock identity retained')
 lock_rows=Path('/proc/locks').read_text().splitlines();need(not any(re.search(r'\b00:1b:4\b',line) for line in lock_rows),'no current kernel owner of permanent27:4')
 queries=[]
 for argv,expected in [(PREFIX+['ps','-q','--no-trunc'],''),(PREFIX+['ps','-aq','--no-trunc','--filter','name=^/'+NAME+'$'],CID+'\n'),(PREFIX+['ps','-aq','--no-trunc','--filter','id='+CID],CID+'\n')]:
  child=subprocess.run(argv,capture_output=True,text=True,timeout=15);need(child.returncode==0 and child.stdout==expected and child.stderr=='','exact current stopped/running census');queries.append(dict(argv=argv,returncode=child.returncode,stdout=child.stdout,stderr=child.stderr,positive_wait=True,streams_closed=True))
 argv=PREFIX+['inspect',CID];child=subprocess.run(argv,capture_output=True,text=True,timeout=15);need(child.returncode==0 and child.stderr=='','exact stopped CID inspect')
 inspected=json.loads(child.stdout);queries.append(dict(argv=argv,returncode=child.returncode,stdout=child.stdout,stderr=child.stderr,positive_wait=True,streams_closed=True))
 validate_physical(history,actors,inspected,rows['terminal'])
 last=guard.guard();cutoffs=guard.current_cutoffs();need(all(a<b for a,b in zip(last,cutoffs)),'unchanged O2 actual account/window cutoffs')
 return dict(scope=__doc__.splitlines()[0],status=STATUS,runtime_authority=None,Root60=PINS['ledger60'],current_boundary=PINS['ledger60'],previous_accepted_free_boundary=rows['ledger60']['latest_accepted_free_boundary'],actual_current60_postjoin_acceptance=None,current_free_candidate=True,independent_acceptance=False,native_acceptance=False,artifact_acceptance=False,ordinary_build_nonce=NONCE,retained_stopped_container=CID,terminal=PINS['terminal'],all53_prior_and_new_actors_absent=actors,holder=PINS['holder_ready'],runner_join=PINS['runner_join'],holder_join=PINS['holder_local_terminal'],worker_result=PINS['worker_result'],queries=queries,historical_Root59_native_and_physical=history,group_membership_observation=history['group_membership_observation'],closed_exclusive_probes=history['closed_exclusive_probes'],permanent_mutex=dict(device=27,inode=4,regular=True,no_kernel_lock_row=True),pids_current=0,no_existing_heavy=True,active_shared_records_absent=True,observed_clocks=first,last_observed_clocks=last,fixed_cutoffs=list(cutoffs),boot_id=guard.BOOT,signals_cleanup_workloads=0)


def main():
 parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False);parser.add_argument('--validate-retained-only',action='store_true');parser.add_argument('--release',type=Path);parser.add_argument('--release-sha256');parser.add_argument('--output',type=Path);args=parser.parse_args()
 if args.validate_retained_only:
  rows,_common,actors=validate_current();print(json.dumps(dict(status='PASS_ACTUAL_ROOT60_BUILD_RETAINED_DATA_ONLY',actors=len(actors),commands=len(rows['worker_result']['commands']),Root60=PINS['ledger60'],previous_free_only=rows['ledger60']['latest_accepted_free_boundary'],guard_calls=0,observations=0,runtime_authority=None)));return
 need(args.release and args.output and ref(args.release)['sha256']==args.release_sha256,'Root separate bounded readonly release required')
 release=json.loads(args.release.read_bytes());need(release['author']=='/root' and release['decision']=='AUTHORIZE_ONE_EXACT_ROOT60_POSTJOIN_READONLY_OBSERVATION' and release['maximum_invocations']==1 and release['source']==ref(__file__) and release['pins']==ref(HERE/'ACTUAL-PINS.json') and release['ledger']==PINS['ledger60'] and release['output']==str(args.output),'exact one readonly release')
 review=checked(release['independent_review']);need(review['independent'] is True and review['implementation_ownership'] is False and review['decision']=='PASS_EXACT_ROOT60_POSTJOIN_READONLY_SOURCE' and review['source']==ref(__file__) and review['pins']==ref(HERE/'ACTUAL-PINS.json'),'independent exact readonly source review')
 with args.output.open('x') as out:
  try: result=observe()
  except BaseException as error:
   out.write(json.dumps(dict(status='READONLY_OBSERVATION_FAILED_NO_RETRY',error=repr(error),runtime_authority=None))+'\n');raise
  out.write(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(status=STATUS,output=ref(args.output),runtime_authority=None)))

if __name__=='__main__':main()
