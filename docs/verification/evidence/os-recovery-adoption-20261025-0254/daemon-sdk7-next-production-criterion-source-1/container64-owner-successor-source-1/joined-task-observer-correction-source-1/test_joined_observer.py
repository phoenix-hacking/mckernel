"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure retained-probe/source/API checks. No compiler, daemon, procfs or Root execution.
"""
from pathlib import Path
import ast,copy,hashlib,json,tempfile,unittest
from unittest.mock import patch
import joined_audit as audit
import suffix_contract as mc
import suffix_owner as owner
import prefix_evidence
S=Path(__file__).resolve().parent;D=S.parent
PROBE=D/'thread-exit-observation-repair-source-1/repro-admission-source-1/workspace/native-running-modules-candidate-7cf529a05d0430c6651f07b63168e8e1/evidence/observe/stdout'
PROBE_SHA='b6c805f7fc93035bb8d51e4662475571e6cfd7288ee5b990fe2381c1b61d0d95'
NONCE='a'*32;CLOCK=[1793057312.,839417.,854756.]
def write(p,value):p.write_bytes(mc.canonical(value));return mc.ref(p)
def two(ref):return {k:ref[k] for k in ('path','sha256')}
def encode(rows):return b''.join(mc.canonical(row) for row in rows)
def from_actual_probe():
 raw=PROBE.read_bytes();assert hashlib.sha256(raw).hexdigest()==PROBE_SHA
 old=[json.loads(line) for line in raw.splitlines()];joined=old[1];workers=joined['workers'];known={};events=[]
 # Explicit PURE regression projection of actual probe facts, never a runtime
 # observer receipt. The historical1fff extra TID remains unknown.
 for slot,worker in enumerate(workers):
  tid=worker['tid'];birth=audit.identity(worker['initial_raw_stat'],tid);known[slot]=dict(tid=tid,birth=birth,joined=True,initial_raw_stat=worker['initial_raw_stat'])
  witness=dict(slot=slot,tid=tid,birth=birth,initial_raw_stat=worker['initial_raw_stat'])
  events.extend([dict(witness,event='thread_start',result=1),dict(witness,event='create_return',result=0),dict(witness,event='join_return',result=0)])
 def snap(value,phase):
  rows=[]
  for row in value['rows']:
   slot=next((slot for slot,fact in known.items() if fact['tid']==row['tid']),-1)
   rows.append(dict(tid=row['tid'],slot=slot,stat_read=row['stat_read'],birth=audit.identity(row['raw_stat'],row['tid']) if row['stat_read'] else 0,raw_stat=row['raw_stat']))
  return dict(event='snapshot',phase=phase,literal_threads=value['literal_threads'],rows=rows,valid=True)
 events.append(snap(old[0],'initial'))
 for slot,fact in known.items():events.append(dict(event='joined_directory_ENOENT',slot=slot,tid=fact['tid'],birth=fact['birth'],initial_raw_stat=fact['initial_raw_stat'],result=2))
 events.extend([snap(old[-2],'final'),dict(event='FINAL_SINGLETON',threads=1)])
 return events,known
class Pure(unittest.TestCase):
 def tmp(self):
  temporary=tempfile.TemporaryDirectory(prefix='PURE-NO-RUNTIME-',dir=S);self.addCleanup(temporary.cleanup);return Path(temporary.name)
 def test_literal_actual_R_state_probe_and_final_singleton(self):
  rows,known=from_actual_probe();self.assertEqual(rows[-2]['literal_threads'],1)
  self.assertEqual(rows[6]['rows'][1]['raw_stat'].rsplit(')',1)[1].split()[0],'R')
  proof=audit.validate(encode(rows),13,87230860);self.assertEqual(proof['worker_count'],2)
  self.assertIsNone(proof['historical_1fff_extra_task_identity'])
 def test_unknown_unjoined_reuse_false_join_and_absence_reappearance(self):
  for mutation in ['unknown','unjoined','reuse','false-result','no-absence','reappear','wrong-main-birth']:
   rows,_=from_actual_probe()
   if mutation=='unknown':rows[6]['rows'][1]['slot']=63
   elif mutation=='unjoined':rows.pop(2)
   elif mutation=='reuse':rows[6]['rows'][1]['birth']+=1
   elif mutation=='false-result':rows[2]['result']=False
   elif mutation=='no-absence':rows.pop(7)
   elif mutation=='reappear':rows[-2]=copy.deepcopy(rows[6]);rows[-2]['phase']='final'
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):audit.validate(encode(rows),13,1 if mutation=='wrong-main-birth' else 87230860)
 def test_original_mock_oracles_leaf_deadline_and_pthread_targets_unchanged(self):
  original=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-1/m15-daemon-validation/read-errors-successor-1/fixture/mock.c').read_text()
  old='static void summary(void){int count=0;DIR *tasks=opendir("/proc/self/task");if(tasks){struct dirent *e;while((e=readdir(tasks)))if(e->d_name[0]!=\'.\')count++;closedir(tasks);}'
  new='#include "joined_task_observer.h"\nstatic void summary(void){int count=joined_task_singleton();'
  self.assertEqual((S/'mock.c').read_text().replace(new,old),original)
  a=(D/'run_fixture_precreated.py').read_text();b=(S/'run_fixture_suffix.py').read_text();start="        p,m,trace=execute(r_binary,";end='    # Direct retained C kmsg helper parity'
  self.assertEqual(a[a.index(start):a.index(end)],b[b.index(start):b.index(end)])
  closed=next(line for line in a.splitlines() if line.lstrip().startswith('def closed('));self.assertIn(closed,b)
  self.assertIn('limit(8)',b);self.assertIn('enumerate(cases[8:],8)',b);self.assertNotIn("'C-reference-build'",b);self.assertNotIn("'C-helper-build'",b)
  h=(S/'joined_task_observer.h').read_text();start=h.index('int __wrap_pthread_join(');end=h.index('static void joined_refuse',start);body=h[start:end]
  self.assertIn('int result=__real_pthread_join(handle,result_pointer);',body);self.assertIn('return result;',body)
  for forbidden in ['sched_yield','joined_stat(','fstatat(','sleep(']:self.assertNotIn(forbidden,body)
 def test_real_retained8_prefix_and_failed_old_case_preserved(self):
  count=mc.verify_retained_prefix(mc.PREP['retained_prefix_host']);self.assertGreater(count,100)
  rows=prefix_evidence.load(mc.PREP['retained_prefix_host'],mc.cases());self.assertEqual(len(rows),8)
  self.assertTrue(all(row['passed_contract'] for row in rows));self.assertTrue(all(row['Rust_resources']['threads']==1 for row in rows))
  failure=json.loads((Path(mc.PREP['retained_prefix_host'])/'first-failure.json').read_bytes());self.assertFalse(failure['passed_contract']);self.assertEqual(failure['Rust_resources']['threads'],2)
 def test_owner_lifecycle_profile_and_account_AST_unchanged(self):
  old=ast.parse((D/'mock64_owner.py').read_bytes());new=ast.parse(mc.OWNER.read_bytes())
  for name in ['run_owner','guarded_execute','ExternalDocker','BoundDocker','release_owned_records','create_args','profile','check_campaign','validate_runtime_source_bindings']:
   a=next(n for n in old.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name);b=next(n for n in new.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
   self.assertEqual(ast.dump(a,include_attributes=False),ast.dump(b,include_attributes=False),name)
  mapping={key:mc.sha(Path(owner.RUNTIME_SOURCE_PATHS[key]).read_bytes()) for key in owner.SOURCES};owner.validate_runtime_source_bindings(mapping)
  self.assertEqual(mc.PREP['profile']['pids'],64);self.assertEqual(len(mapping),28)
  self.assertEqual(next(row for row in mc.PREP['source_files'] if row['relative'].endswith('/ihkmond.rs'))['source']['sha256'],'0c0b4b6d286e9f0fdbdacf1d32c3cd33ec96d4d2420550771a0dc732dd84d86e')
 def authfixture(self):
  root=self.tmp();request=dict(nonce=NONCE,boot_id=mc.BOOT,terminal_policy='remove-owned-terminal',driver=dict(path=str(mc.DRIVER),sha256=mc.sha(mc.DRIVER.read_bytes())))
  requestpath=root/'SOURCE-ONLY-request.json';rr=write(requestpath,request)
  mapping={key:mc.sha(Path(owner.RUNTIME_SOURCE_PATHS[key]).read_bytes()) for key in owner.SOURCES}
  sr=write(root/'SOURCE-ONLY-source-review.json',dict(decision='PASS_SOURCE',implementation_ownership=False,reviewer='PURE_FIXTURE_SOURCE_ONLY',source_sha256=mapping,fixture_only=True,runtime_authority=False))
  resourcesref=write(root/'SOURCE-ONLY-resources.json',dict(observed_clocks=CLOCK,boot_id=mc.BOOT,no_existing_heavy=True));postjoin=write(root/'SOURCE-ONLY-postjoin.json',dict(fixture_only=True,runtime_authority=False));pub=write(root/'SOURCE-ONLY-publication.json',dict(fixture_only=True,runtime_authority=False))
  admission=dict(schema='mckernel.daemon-joined-suffix64-current-admission.v1',status='ROOT_RESERVED_DAEMON_JOINED_SUFFIX64_SOLE_HEAVY',author='/root',nonce=NONCE,request=two(rr),boot_id=mc.BOOT,profile=mc.PREP['profile'],one_heavy=True,observed_clocks=CLOCK,expires_wall=CLOCK[0]+120,nonce_ledger_complete=True,consumed_nonces=['b'*32],resource_physical=resourcesref,latest_postjoin_acceptance=postjoin,source_publication=pub)
  ar=write(root/'SOURCE-ONLY-admission.json',admission)
  payload=dict(schema='mckernel.daemon-joined-suffix64-release.v1',status='PASS_EXECUTION_RELEASE',execution_count=1,request=two(rr),nonce=NONCE,boot_id=mc.BOOT,fetched_source_verified=True,terminal_policy=request['terminal_policy'],historical_observer=dict(path=str(owner.HISTORICAL_OBSERVER),sha256=owner.HISTORICAL_OBSERVER_SHA,prefix=list(owner.HISTORICAL_PREFIX),timeout_seconds=30),source_sha256=mapping,source_review=two(sr),current_admission=two(ar),author='/root')
  er=write(root/'SOURCE-ONLY-execution-review.json',dict(decision='PASS_EXECUTION',implementation_ownership=False,reviewer='PURE_FIXTURE_SOURCE_ONLY',reviewed_release_payload_sha256=mc.sha(mc.canonical(payload)),fixture_only=True,runtime_authority=False));release=dict(payload,execution_review=two(er));releasepath=root/'SOURCE-ONLY-release.json';write(releasepath,release)
  return root,requestpath,rr,releasepath,release,admission

 def test_actual_new_owner_authenticate_api_refs_and_full_source_map(self):
  root,rp,rr,lp,release,admission=self.authfixture()
  with patch.object(owner,'check_campaign',return_value=CLOCK):owner.authenticate(rp,rr['sha256'],lp,mc.ref(lp)['sha256'])
  release['source_review']['bytes']=1;write(lp,release)
  with patch.object(owner,'check_campaign',return_value=CLOCK):
   with self.assertRaises(owner.Refusal):owner.authenticate(rp,rr['sha256'],lp,mc.ref(lp)['sha256'])

if __name__=='__main__':unittest.main(verbosity=2)
