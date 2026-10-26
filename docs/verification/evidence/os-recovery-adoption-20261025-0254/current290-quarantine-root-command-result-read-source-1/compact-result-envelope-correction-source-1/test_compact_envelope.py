"""Functional result-envelope regression only; no security testing/live actions.
Reuse real retained childbytes; frame/caller metadata is mocked for runneroracle.
"""
import hashlib,importlib.util,json,unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('compact_envelope',ROOT/'exact_root_result_guard_runner.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
PROFILE=json.loads(a.PROFILE.read_text())
FIXTURE=json.loads((ROOT.parent/'COMPLETED-PROCESS-FIXTURE-RESULT.json').read_text())['results'][0]['extraction']
def bound_metadata(answer):
 result=dict(answer);result['co_filename']=PROFILE['source']['path'];result['argv']=dict(answer['argv'],code_sha256=PROFILE['proc_code']['sha256'],code_bytes=PROFILE['proc_code']['bytes'],caller_pid=1060806,caller_starttime='80309560');return result
class Checks(unittest.TestCase):
 def test_same_profile_and_helper_source_binding(self):
  self.assertEqual(hashlib.sha256(a.PROFILE.read_bytes()).hexdigest(),a.PROFILE_SHA)
  self.assertEqual(PROFILE['helper']['sha256'],'dde95e94fc4f7510f928f0d77c08d2712eb85b60878a99070bf69d413ddf180c')
  a.authenticate(PROFILE['helper'])
 def run_answer(self,answer,stdout_bytes=None,stderr=b'',guard=None):
  stdout=(json.dumps(answer)+'\n').encode() if stdout_bytes is None else stdout_bytes
  return a.perform(PROFILE,lambda _:guard or {'fixture':'unchanged'},lambda *args,**kw:SimpleNamespace(stdout=stdout,stderr=stderr,returncode=0))
 def test_retained_real_fixture_bytes_survive_summary_compaction(self):
  answer=bound_metadata(FIXTURE);result=self.run_answer(answer)
  self.assertEqual(result['status'],'PASS_EXACT_OWNED_ROOT_COMMAND_RESULT_READ')
  raw_gdb=bytes.fromhex(result['stdout']['raw_hex']);decoded=json.loads(raw_gdb)
  for stream in ('stdout','stderr'):
   self.assertEqual(set(result['extraction'][stream]),{'bytes','sha256'})
   raw=bytes.fromhex(decoded[stream]['raw_hex'])
   self.assertEqual(raw,bytes.fromhex(FIXTURE[stream]['raw_hex']))
   self.assertEqual(len(raw),result['extraction'][stream]['bytes'])
   self.assertEqual(hashlib.sha256(raw).hexdigest(),result['extraction'][stream]['sha256'])
 def test_complete_child_byte_validation_still_runs(self):
  answer=bound_metadata(FIXTURE);answer['stdout']=dict(answer['stdout'],sha256='0'*64)
  result=self.run_answer(answer);self.assertEqual(result['status'],'REFUSED');self.assertNotIn('extraction',result)
 def test_worst_envelope_and_lossless_full_copy_under_32mib(self):
  answer=bound_metadata(FIXTURE)
  for stream,raw in [('stdout',b'\0'*(3<<20)),('stderr',b'\xff'*(2<<20))]:answer[stream]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),raw_hex=raw.hex())
  line=(json.dumps(answer)+'\n').encode();cap=PROFILE['limits']['gdb_stdout_bytes'];self.assertLess(len(line),cap)
  full=b'\n'*(cap-len(line))+line
  # Worst bounded fdinfo is65536B; JSONescaping doubles this field. Two guards
  # plus fixed source/actor metadata fit well inside1MiB explicit reserve.
  guard=dict(fixture_fdinfo='\n'*65536,fixed_metadata='x'*8192)
  result=self.run_answer(answer,full,b'W'*PROFILE['limits']['gdb_stderr_bytes'],guard)
  self.assertEqual(result['status'],'PASS_EXACT_OWNED_ROOT_COMMAND_RESULT_READ')
  encoded=json.dumps(result,sort_keys=True).encode();self.assertLess(len(encoded),32<<20)
  math_bound=2*cap+2*PROFILE['limits']['gdb_stderr_bytes']+(1<<20)
  self.assertEqual(math_bound,27<<20);self.assertLess(math_bound,32<<20)
  self.assertLess(len(encoded),math_bound)
  recovered=json.loads(bytes.fromhex(result['stdout']['raw_hex']))
  for stream in ('stdout','stderr'):
   raw=bytes.fromhex(recovered[stream]['raw_hex']);self.assertEqual(len(raw),answer[stream]['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),answer[stream]['sha256']);self.assertNotIn('raw_hex',result['extraction'][stream])
  (ROOT/'WORST-ENVELOPE-MEASUREMENTS.json').write_text(json.dumps(dict(gdb_stdout_bytes=len(full),gdb_stderr_bytes=PROFILE['limits']['gdb_stderr_bytes'],child_combined_bytes=5<<20,actual_envelope_bytes=len(encoded),mathematical_bound_bytes=math_bound,file_ceiling_bytes=32<<20,raw_copy_preserved=True),indent=2)+'\n')
if __name__=='__main__':unittest.main(verbosity=2)
