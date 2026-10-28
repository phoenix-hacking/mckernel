"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure validation of retained source/command/terminal facts; no live process/guard/Docker I/O.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,unittest
D=Path(__file__).resolve().parent

def read(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def validate(p):
 assert p['nonce']=='faac1b4804174de5800c58d61ba98004' and p['nonce_consumed_once'] is True
 assert p['container_id']=='2460c49fbbbf8be6ee5ae931e7e769eec2f26e352937e7f4a4dcf5d2ebec8008'
 assert p['container_name']=='bfd-current-two-target-'+p['nonce']
 assert p['proposed_mutation_argv']==['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock','rm','--',p['container_id']]
 assert p['shared_custody']['lease_records_created']==p['shared_custody']['shared_records_created']==p['shared_custody']['owner_records_created']==p['shared_custody']['records_authorized_for_release']==[]
 assert p['shared_custody']['container_owner_label_added'] is False
 refs=p['source_refs']
 for r in refs.values():assert ref(r['path'])==r
 profile=read(refs['PROFILE.SOURCE-ONLY.json']['path']);claim=read(refs['output:claim.json']['path']);grant=read(refs['ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json']['path']);terminal=read(refs['output:terminal.json']['path']);plan=read(refs['output:plan.json']['path']);result=read(refs['worker_result']['path'])
 assert claim['grant']==refs['ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json'] and claim['pid']==2124454 and claim['native_authority'] is False
 assert terminal['state']==p['terminal_state'] and terminal['container']==p['container_id'] and terminal['returncode']==0
 assert terminal['default_native_retirement_acceptance'] is False
 st=terminal['state'];assert st=={'Status':'exited','Running':False,'Paused':False,'Restarting':False,'OOMKilled':False,'Dead':False,'Pid':0,'ExitCode':0,'Error':'','StartedAt':'2026-10-28T19:48:02.919084286Z','FinishedAt':'2026-10-28T19:48:11.197900655Z'}
 assert grant['nonce']==p['nonce'] and grant['fresh_output_root']==p['output_root']
 runner=load('BFD_RETAINED_PURE_RUNNER',refs['run_build_only.py']['path'])
 # Reuse the real pure argv builder, supplying the actual retained mount contract.
 O=Path(p['output_root']);C=Path(p['cohort']);inp=profile['inputs'];export=read(refs['ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json']['path'])
 rows=[dict(host=export['readable_source_export'],target='/src',readonly=True),dict(host=inp['assets_root'],target='/candidate',readonly=True)]
 rows.extend(dict(host=x['host_path'],target=x['container_path'],readonly=True) for x in inp['toolchain_mounts'])
 rows.extend([dict(host=str(C/'build_only_worker.py'),target='/build-only-worker.py',readonly=True),dict(host=str(O/'plan.json'),target='/build-only-plan.json',readonly=True)])
 assert runner.docker_argv(profile,p['container_name'],rows,O)==claim['argv']
 assert not any(x.startswith('--label') for x in claim['argv'])
 assert plan['commands']==profile['exact_commands']==runner.commands_for_plan(profile)
 assert len(result['commands'])==len(p['actual_commands'])==3
 for observed,expected in zip(result['commands'],profile['exact_commands']):assert observed['returncode']==0 and observed['argv']==expected['argv'] and observed['cwd']==expected['cwd']
 ready=read(refs['holder:HOLDER.READY.json']['path']);joined=read(refs['holder:RUNNER.JOINED.json']['path']);local=read(refs['holder:BUILD-LOCAL-TERMINAL.json']['path'])
 assert ready['holder']==local['holder']==dict(path='/run/lock/mckernel-development.lock',pid=2124365,starttime=101427979,device=27,inode=4,fd=3)
 assert joined==dict(pid=2124454,starttime=101432667,returncode=0,joined=True)
 assert local['joined'] is True and local['returncode']==0 and local['container_terminal_or_no_launch'] is True
 holder=load('BFD_RETAINED_PURE_HOLDER',refs['hold_and_run_build_only.py']['path'])
 assert holder.releasable(O,True) is True and holder.releasable(O,False) is False
 # Source calls identify ordinary FD custody; there is no lease/shared release API.
 for source in [refs['run_build_only.py'],refs['hold_and_run_build_only.py']]:
  tree=ast.parse(Path(source['path']).read_bytes());calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
  assert not any(isinstance(n.func,ast.Attribute) and n.func.attr in ('unlink','rmdir','remove','kill','killpg') for n in calls)
 ledger=read(D/'ROOT-NEXT-LEDGER-EXTENSION.TEMPLATE.NOT-AUTHORITY.json');prior=read(profile['actual_root_ledger']['path'])
 assert ledger['consumed_nonces']==prior['consumed_nonces']+[p['nonce']] and len(ledger['consumed_nonces'])==71
 assert ledger['current_native_operation']==prior['current_native_operation']
 assert ledger['current_physical_clearance_pending'] is True and ledger['latest_accepted_free_boundary']==profile['native_custody_clearance']
 assert ledger['author'] is None and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is None
 return dict(retained_three_commands=3,commands_all_zero=True,shared_records_created=0,signals=0,actual_queries=0,actual_cleanup=0)

class RetainedPacket(unittest.TestCase):
 def setUp(self):self.p=read(D/'RETIREMENT-PACKET.NOT-AUTHORITY.json')
 def test_actual_source_records_commands_and_typed_boundary(self):self.assertEqual(validate(self.p)['retained_three_commands'],3)
 def test_no_force_or_different_container_removal(self):
  for argv in [self.p['proposed_mutation_argv']+['--force'],self.p['proposed_mutation_argv'][:-1]+['0'*64]]:
   candidate=copy.deepcopy(self.p);candidate['proposed_mutation_argv']=argv
   with self.assertRaises(AssertionError):validate(candidate)
 def test_no_fabricated_sdk_record_release(self):
  candidate=copy.deepcopy(self.p);candidate['shared_custody']['records_authorized_for_release']=['/old/sdk/shared']
  with self.assertRaises(AssertionError):validate(candidate)
 def test_no_relabeling_normal_owner_label(self):
  candidate=copy.deepcopy(self.p);candidate['shared_custody']['container_owner_label_added']=True
  with self.assertRaises(AssertionError):validate(candidate)
 def test_changed_terminal_state_rejected(self):
  candidate=copy.deepcopy(self.p);candidate['terminal_state']['ExitCode']=1
  with self.assertRaises(AssertionError):validate(candidate)

if __name__=='__main__':unittest.main(verbosity=2)
