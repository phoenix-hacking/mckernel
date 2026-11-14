"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One additive missing-ROOT-GRANT preflight successor only; no job or reservation.
"""
from pathlib import Path
import ast,difflib,hashlib,json
H=Path(__file__).resolve().parent;B=H.parent;SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def write(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def main():
 original=H/'run_owned_first_candidate.py';oldready=H/'EXECUTABLE-READY.NOT-GRANTED.json';rf=H/'EXACT-FUNCTIONAL-FIXTURE-AND-CONSUMER.NOT-GRANTED.json';failure=H/'FIRST-CANDIDATE-FAILURE-1.json';capture=H/'root-actual-sync-first-1/RESULT.json'
 assert pin(original)['sha256']=='b619922e059f0a685136235e2f22e4c633b9ec7a313e71fda9f0c1d55cdf4b37';assert pin(oldready)['sha256']=='9a64c27953f622dac3eac1f1d65c95b80ae8f2d558e83f951016ba1ac8aa43be';assert pin(rf)['sha256']=='1391be5c805be84a46e570d70c5e680ce26f3173c33504ad948205afffa2475d';assert pin(failure)['sha256']=='c39852dd11334fa0c393b01e9570b7c3dc4f2c6a3c7cca0d8bfe0b4e45b7a1a9'
 failed=json.loads(failure.read_text());j=json.loads(capture.read_text());assert failed['records']==[] and failed['durable_objects']=={} and failed['CPU6_released'] and 'ROOT-GRANT.json' in failed['error']
 assert j['returncode']==1 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out']
 assert not (B/'output-first-candidate-1').exists() and not (H/'actual-first-candidate-capture-1').exists() and not (H/'ROOT-GRANT.json').exists()
 histories=[pin(oldready),pin(original),pin(failure),pin(capture)]
 for row in j['captures'].values():
  actual=pin(Path(row['path']));assert actual['sha256']==row['sha256'] and actual['bytes']==row['size'];histories.append(actual)
 s=original.read_text();s=s.replace("READY=H/'EXECUTABLE-READY.NOT-GRANTED.json'","READY=H/'EXECUTABLE-READY.PREFLIGHT-SUCCESSOR.NOT-GRANTED.json'",1)
 s=s.replace("try:\n grant=", "try:\n # Refuse any previous command output/capture/result or successor failure.\n for path in (B/'output-first-candidate-1',H/'actual-first-candidate-capture-1',H/'ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json',H/'PREFLIGHT-SUCCESSOR-FAILURE-1.json'):\n  assert not path.exists(),('existing_output_or_successor_failure',str(path))\n grant=",1)
 marker=" ready=json.loads(READY.read_text());assert pin(RF)==ready['recipe'] and pin(Path(__file__))==ready['driver']\n"
 assert s.count(marker)==1;s=s.replace(marker,marker+" for row in ready['preflight_history_bindings']:assert pin(Path(row['path']))==row,row['path']\n",1)
 assert s.count("write(H/'FIRST-CANDIDATE-FAILURE-1.json'")==1;s=s.replace("write(H/'FIRST-CANDIDATE-FAILURE-1.json'","write(H/'PREFLIGHT-SUCCESSOR-FAILURE-1.json'",1)
 ast.parse(s);driver=H/'run_owned_preflight_successor_once.py';driver.write_text(s)
 delta=''.join(difflib.unified_diff(original.read_text().splitlines(True),s.splitlines(True),fromfile='preserved/run_owned_first_candidate.py',tofile='run_owned_preflight_successor_once.py'));(H/'PREFLIGHT-SUCCESSOR-ONLY.diff').write_text(delta)
 recipe=json.loads(rf.read_text());assert len(recipe['commands'])==16
 receipt=dict(scope=SCOPE,status='SOURCE_ONLY_MISSING_GRANT_SETUP_SUCCESSOR_READY_NO_EXECUTION',kind='Root setup failure before any compiler or command; no compiler/product/oracle change',original_ready=pin(oldready),original_driver=pin(original),original_failure=pin(failure),root_closed_attempt=pin(capture),driver_delta=pin(H/'PREFLIGHT-SUCCESSOR-ONLY.diff'),preserved_recipe=pin(rf),same16argv_sources_oracles=True,predecessor_compiler_commands=0,new_prepared_compiler_commands=0,CPU_reservations=0,oldfailure_never_overwritten=True,new_failure_path=str(H/'PREFLIGHT-SUCCESSOR-FAILURE-1.json'),output_reuse='Refuse output-first-candidate-1, actual-first-candidate-capture-1, successful receipt or successor failure before any grant/read/run; every evidence writer stays O_EXCL.',missing_grant_behavior='Refuse missing/incorrect ROOT-GRANT.json before any child. Root supplies exact new ready SHA, scope, CPU6 and ordinary_jobs1.',AST_dependency_checks_unchanged=True,failure_history_not_reset=True)
 write(H/'PREFLIGHT-SUCCESSOR-SETUP-QUALIFICATION.json',receipt)
 ready=json.loads(oldready.read_text());ready.update(status='F02_SYNC_ONE_PAGE_PREFLIGHT_SETUP_SUCCESSOR_READY_NO_GRANT',driver=pin(driver),recipe=pin(rf),preflight_history_bindings=histories,setup_qualification=pin(H/'PREFLIGHT-SUCCESSOR-SETUP-QUALIFICATION.json'),predecessor_missing_grant_failure=pin(failure),supersedes_execution_ready_only=pin(oldready),unchanged16argv=True,unchanged_source_and_oracles=True,successor_failure_path=str(H/'PREFLIGHT-SUCCESSOR-FAILURE-1.json'),requires='Root creates ROOT-GRANT.json with scope,CPU6,ordinary_jobs1 and this exact successor ready SHA before execution; root retains one job/slot ownership. Fresh admission and existing AST/h990 checks unchanged. No job or reservation by preparation.')
 write(H/'EXECUTABLE-READY.PREFLIGHT-SUCCESSOR.NOT-GRANTED.json',ready)
 newready=pin(H/'EXECUTABLE-READY.PREFLIGHT-SUCCESSOR.NOT-GRANTED.json')
 write(H/'ROOT-GRANT.PREFLIGHT-SUCCESSOR.EXAMPLE-NOT-AUTHORITY.json',dict(scope=SCOPE,CPU=6,ordinary_jobs=1,ready_sha256=newready['sha256']))
 for row in histories:assert pin(Path(row['path']))==row
 print(json.dumps(dict(scope=SCOPE,ready=newready,driver=ready['driver'],recipe=pin(rf),qualification=ready['setup_qualification'],example=pin(H/'ROOT-GRANT.PREFLIGHT-SUCCESSOR.EXAMPLE-NOT-AUTHORITY.json'),exact_command=['/home/holden/anaconda3/bin/python3',str(driver)],compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
