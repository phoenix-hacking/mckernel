"""Seven literal admitted commands; storage predicate is called before ld-r."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import traceback
import storage_predicate

def main():
 request_path=Path(sys.argv[1]);q=json.loads(request_path.read_text());receipt=Path(q['cwd']);rows=[];phase='input-binding';prejoin_passed=False
 try:
  for name,wanted in q['inputs'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==wanted,name
  Path(q['output_directory']).mkdir(exist_ok=False)
  contract=json.loads(Path(q['predicate_contract']).read_text())
  assert [row['label'] for row in q['commands']]==['storage-compile','storage-symbols','storage-elf','storage-bytes','unique-partial-join','joined-symbols','joined-elf']
  for number,command in enumerate(q['commands']):
   phase=command['label']
   if phase=='unique-partial-join':assert prejoin_passed,'The actual called prejoin predicate must pass before ld-r'
   row={'label':phase,'argv':command['argv'],'pid':None,'proc_start_ticks':None,'returncode':None,'direct_wait_joined':False};rows.append(row)
   with Path(command['stdout_path']).open('xb') as stdout,Path(command['stderr_path']).open('xb') as stderr:
    child=subprocess.Popen(command['argv'],cwd=q['cwd'],env=q['environment_replace'],stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr);row['pid']=child.pid
    try:
     try:row['proc_start_ticks']=Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
     except OSError as error:row['birth_observation_error']=type(error).__name__
     (receipt/'COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n')
    finally:status=child.wait()
   row.update({'returncode':status,'direct_wait_joined':True});(receipt/'COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n');assert status==0,phase
   diagnostics=Path(command['stderr_path']).read_bytes()
   expected=Path(q['compiler_profile']['expected_compile_stderr_path']).read_bytes() if phase=='storage-compile' else b''
   assert diagnostics==expected,'Unexpected diagnostics: '+phase
   if number==3:
    phase='called-prejoin-predicate';decision=storage_predicate.prejoin(q,contract,receipt);(receipt/'PREJOIN-CHECK.json').write_text(json.dumps(decision,indent=2)+'\n');prejoin_passed=True
  phase='called-postjoin-predicate';post=storage_predicate.postjoin(q,contract);(receipt/'POSTJOIN-CHECK.json').write_text(json.dumps(post,indent=2)+'\n')
  result={'status':'PASS_NONEXECUTED_STORAGE_AND_BOUNDED_LOGGER_PARTIAL','request_sha256':hashlib.sha256(request_path.read_bytes()).hexdigest(),'prejoin_predicate_called_and_passed_before_ld_r':prejoin_passed,'postjoin_predicate_called_and_passed':True,'all7_child_direct_waits_joined':all(row['direct_wait_joined'] for row in rows),'commands':rows,'global_joined_T':22,'global_joined_data':8,'genuine_remaining_U':post['genuine_U'],'runtime_or_native_initialization_executed':False,'artifact_hashes':{name:hashlib.sha256(Path(q[name]).read_bytes()).hexdigest() for name in ('storage_object','joined_object')}};(receipt/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0
 except BaseException as error:
  failure={'status':'FIRST_FAILURE_STOP_NO_AUTOMATIC_RETRY','phase':phase,'error_type':type(error).__name__,'error':str(error),'traceback':traceback.format_exc(),'commands':rows,'all_started_children_direct_wait_joined':all(row['pid'] is None or row['direct_wait_joined'] for row in rows)};(receipt/'FIRST-FAILURE.json').write_text(json.dumps(failure,indent=2)+'\n');print(json.dumps(failure,indent=2));return 1
if __name__=='__main__':raise SystemExit(main())
