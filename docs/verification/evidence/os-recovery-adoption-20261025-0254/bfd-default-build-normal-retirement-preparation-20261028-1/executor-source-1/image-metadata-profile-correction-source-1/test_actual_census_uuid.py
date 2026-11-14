"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Run the real Actual.census and Actual.call bodies, real uuid.UUID, and real pure
process/OCI validators. Substitute only machine-admission/proc-stat/command effects.
"""
from pathlib import Path
import copy,importlib.util,json,os,subprocess,tempfile,types,unittest,uuid
D=Path(__file__).resolve().parent

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
m=load('corrected_BFD_uuid_executor',D/'retire_exact_bfd_stopped_container.py');oracle=load('retained_BFD_OCI_oracle',D/'test_retirement_executor.py')
B=m.bindings();P,PROTECTED,PROFILE,CLAIM,PLAN,TERMINAL=m.validate_retained(B)

class ActualCensusUUID(unittest.TestCase):
 def ops(self,T,present=True,bad_profile=False):
  ops=m.Actual.__new__(m.Actual);ops.b=B;ops.p=P;ops.profile=PROFILE;ops.claim=CLAIM;ops.terminal=TERMINAL;ops.normal=oracle.NORMAL;ops.out=T;ops.proofs=[]
  ops.safe=lambda:dict(clocks=[1793218000.,1000000.,1015000.],TEST_ONLY=True)
  ops.m=types.SimpleNamespace(proc_stat=lambda pid:['0']*19+['100'])
  ops.commands=types.SimpleNamespace(children=[],receipts=[],client_retirement_unproven=False);ops.seen=[]
  item,image=oracle.fixture()
  if bad_profile:item['HostConfig']['MemorySwap']=-1
  def effect(argv,timeout,check):
   # The real Actual.call has already checked exact source/caller/challenge argv.
   self.assertEqual(timeout,30);ops.seen.append(argv)
   if argv[:5]==['/usr/bin/sudo','-A','/usr/bin/python3','-I','-B']:
    challenge=argv[7];self.assertIsInstance(challenge,str);self.assertEqual(uuid.UUID(hex=challenge).hex,challenge)
    caller=[os.getpid(),'100'];rows=[[1,0,'1'],[caller[0],1,caller[1]]];groups=[[1,0,'1',1,1],[caller[0],1,caller[1],caller[0],caller[0]]]
    response=dict(schema='fp-save-image.proc.v1',uid=0,boot_id=B['boot'],challenge=challenge,caller=caller,publishers=[],snapshots=[rows,copy.deepcopy(rows)],groups=[groups,copy.deepcopy(groups)])
    stdout=json.dumps(response)
   else:
    args=argv[4:]
    if args==['ps','-a','--no-trunc','--format','{{json .}}']:stdout=json.dumps(dict(ID=B['cid'],Names=B['name'],Labels='name=rockylinux',State='exited')) if present else ''
    elif args==['inspect','--type','container',B['cid']]:stdout=json.dumps([item])
    elif args==['image','inspect',PROFILE['inputs']['image']]:stdout=json.dumps([image])
    else:raise AssertionError('Unexpected effect leaf: '+str(args))
   pid=990000+len(ops.seen);ops.commands.children.append(types.SimpleNamespace(pid=pid))
   receipt=m.write_new(T/('TEST_ONLY_EFFECT_%d.json'%len(ops.seen)),dict(TEST_ONLY=True,argv=argv,returncode=0,actual_spawn=False))
   ops.commands.receipts.append(receipt);return subprocess.CompletedProcess(argv,0,stdout,'')
  ops.commands.exact=effect
  return ops
 def test_original_real_census_reproduces_uuid_hex_failure_before_first_command(self):
  old=load('original_BFD_uuid_failure',D.parent/'retire_exact_bfd_stopped_container.py')
  self.assertEqual(m.reference(D.parent/'retire_exact_bfd_stopped_container.py')['sha256'],'0a262aa55a6da2165d98093b9c3583f2fa1efa77799cd4bb20a627e0da9b193c')
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY_original_uuid_') as tmp:
   ops=self.ops(Path(tmp))
   with self.assertRaisesRegex(TypeError,'str.*not callable'):old.Actual.census(ops,'TEST_ONLY_EXPECTED_FAILURE',True)
   self.assertEqual(ops.seen,[]);self.assertEqual(ops.proofs,[])
 def test_real_actual_census_present_path_with_real_UUID(self):
  self.assertIsInstance(uuid.uuid4(),uuid.UUID)
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY_actual_census_') as tmp:
   ops=self.ops(Path(tmp));proof,r=ops.census('TEST_ONLY_PRESENT',True)
   self.assertEqual(len(ops.seen),4);self.assertTrue(proof['present']);self.assertEqual(proof['container'][0]['Id'],B['cid']);self.assertEqual(m.authenticated(r,True),proof);self.assertEqual(ops.proofs,[r])
 def test_real_actual_census_absence_path_with_real_UUID(self):
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY_actual_census_absent_') as tmp:
   ops=self.ops(Path(tmp),present=False);proof,r=ops.census('TEST_ONLY_ABSENT',False)
   self.assertEqual(len(ops.seen),2);self.assertFalse(proof['present']);self.assertEqual(proof['inventory'],[]);self.assertIsNone(proof['container']);self.assertIsNone(proof['image'])
 def test_real_census_retains_original_OCI_rejection_before_proof_publication(self):
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY_actual_census_badprofile_') as tmp:
   ops=self.ops(Path(tmp),bad_profile=True)
   with self.assertRaisesRegex(m.Refusal,'MemorySwap'):ops.census('TEST_ONLY_BAD_PROFILE',True)
   self.assertEqual(len(ops.seen),4);self.assertEqual(ops.proofs,[]);self.assertFalse((Path(tmp)/'TEST_ONLY_BAD_PROFILE.json').exists())

if __name__=='__main__':unittest.main(verbosity=2)
