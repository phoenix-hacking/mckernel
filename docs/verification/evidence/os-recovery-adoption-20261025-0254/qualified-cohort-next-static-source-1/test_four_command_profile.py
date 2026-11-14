"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Focused pure actual source/map and mocked four-command prefix-reuse regressions.
"""
from pathlib import Path
import copy,hashlib,json,tempfile,types,unittest
from unittest.mock import patch
D=Path(__file__).resolve().parent

def load(name):
 x=json.loads((D/(name+'.edits.json')).read_text());raw=Path(x['baseline']['path']).read_bytes();assert len(raw)==x['baseline']['bytes'] and hashlib.sha256(raw).hexdigest()==x['baseline']['sha256'];s=raw.decode()
 for edit in x['edits']:
  assert s.count(edit['before'])==1;s=s.replace(edit['before'],edit['after'])
 m=types.ModuleType(name);m.__file__=x['baseline']['path'];exec(compile(s,m.__file__+'[fixed-four exact adapter]','exec'),m.__dict__);return m
runner=load('run_build_only_four.py');worker=load('build_only_worker_four.py');P=json.loads((D/'PROFILE.SOURCE-ONLY.json').read_text());X=json.loads((D/'INPUT-EXPORT.DRAFT.NOT-AUTHORITY.json').read_text())
class FourCommandProfileTests(unittest.TestCase):
 def bound(self):p=copy.deepcopy(P);p['request_sha256']='a'*64;return p
 def test_exact_four_plan_reuses_matching_process(self):
  p=self.bound();c=runner.commands_for_plan(p);self.assertEqual(len(c),4)
  self.assertTrue(all('/src/kernel/process.c' not in r['argv'] for r in c))
  self.assertEqual(sum(not r['replace'] for r in p['inputs']['objects']),8);self.assertEqual(sum(r['replace'] for r in p['inputs']['objects']),3)
  r=next(r for r in p['inputs']['objects'] if r['link_token']=='CMakeFiles/mckernel.img.dir/process.c.o');runner.auth(r['source']);self.assertEqual(r['source']['sha256'],'b8168c1f52369f7909bf174fe1c926a4a4a3be4a63cd0667741841680b0ca289')
 def test_unbound_actual_request_refused(self):
  with self.assertRaisesRegex(RuntimeError,'Root must bind'):runner.commands_for_plan(P)
 def test_process_recompile_or_wrong_reuse_refused(self):
  for mode in ['recompile','reference','decision']:
   p=self.bound();r=next(r for r in p['inputs']['objects'] if r['link_token']=='CMakeFiles/mckernel.img.dir/process.c.o')
   if mode=='recompile':r['replace']=True
   elif mode=='reference':r['source']=dict(r['source'],sha256='0'*64)
   else:p['unchanged_completed_process_prefix']['Root_decision']='RECOMPILE'
   with self.subTest(mode=mode),self.assertRaises(RuntimeError):runner.commands_for_plan(p)
 def test_directory_mount_map_and_exact_export_closure(self):
  rows=runner.source_directory_postimages(P);self.assertEqual(len(rows),101)
  expected=[r['source'] for r in P['inputs']['configuration']]+[r['source'] for r in P['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in P['inputs']['postimages']]+[r['postimage'] for r in rows]
  self.assertEqual(X['qualified_readonly_files'],expected)
  for ref in expected:runner.auth(ref)
  mounts=runner.mounts(P,X,Path('/pure-not-created'));self.assertEqual(len({r['target'] for r in mounts}),len(mounts));self.assertEqual([r for r in mounts if r['target'].startswith('/src/kernel/rust')],[dict(host=str(D/'rust-subtree'),target='/src/kernel/rust',readonly=True)])
 def test_no_new_flags_for_process_no_NOCACHE_and_same11_link(self):
  prior=json.loads((D.parent/'qualified-cohort-default-profile-source-1/LITERAL-COMMAND-BASELINES.NOT-NEW-COHORT.json').read_text())['commands'];self.assertEqual(P['exact_commands'][-1],prior[-1]);self.assertNotIn('f06_use_nocache_mmap',P['exact_commands'][0]['argv'])
 def exercise(self,fail=None,collision=False):
  with tempfile.TemporaryDirectory(dir=D,prefix='pure-four-') as temp:
   root=Path(temp);out=root/'evidence';out.mkdir();targets=[root/(str(i)+'.o') for i in range(4)];calls=[]
   if collision:targets[0].write_bytes(b'retained')
   plan=dict(runtime_authority=None,deadline_epoch=1793100290,tool_files=[],commands=[dict(argv=['mock',str(i)],cwd=str(root),new_output=str(p)) for i,p in enumerate(targets)],source_profile=dict(synthetic=True),producer_contract=dict(synthetic=True));pp=root/'plan.json';pp.write_text(json.dumps(plan))
   class Child:
    def __init__(self,argv,**kw):
     i=int(argv[1]);calls.append(i);self.code=7 if i==fail else 0
     if self.code==0:targets[i].write_bytes(b'new')
    def wait(self):return self.code
   def path(value):return out if value=='/work/evidence' else Path(value)
   with patch.object(worker,'Path',path),patch.object(worker.os,'getuid',return_value=1000),patch.object(worker.os,'geteuid',return_value=1000),patch.object(worker.os,'sched_getaffinity',return_value={2,3,4,5}),patch.object(worker.subprocess,'Popen',Child),patch.object(worker.signal,'signal'),patch.object(worker.signal,'alarm'),patch.object(worker.time,'time',return_value=1793060000):
    if fail is not None or collision:
     with self.assertRaises(RuntimeError):worker.execute(pp)
    else:worker.execute(pp)
   if collision:self.assertEqual(calls,[]);self.assertEqual(targets[0].read_bytes(),b'retained')
   elif fail is not None:self.assertEqual(calls,list(range(fail+1)));self.assertFalse((out/'producer-contract.json').exists())
   else:self.assertEqual(calls,[0,1,2,3]);self.assertEqual(json.loads((out/'producer-contract.json').read_text())['status'],'ACTUAL_BUILD_ONLY_FOUR_COMMAND_PRODUCER')
 def test_four_worker_success(self):self.exercise()
 def test_each_failure_stops_four_suffix(self):
  for i in range(4):
   with self.subTest(i=i):self.exercise(fail=i)
 def test_no_stale_output_replay(self):self.exercise(collision=True)
if __name__=='__main__':unittest.main(verbosity=2)
