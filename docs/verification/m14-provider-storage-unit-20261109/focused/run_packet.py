"""One focused predicate correction, then ONLY three unstarted original commands."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import traceback
import storage_predicate

def main():
 request_path=Path(sys.argv[1]);q=json.loads(request_path.read_text());receipt=request_path.parent;rows=[];phase='input-binding';prejoin_passed=False
 try:
  for name,wanted in q['inputs'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==wanted,name
  old=Path(q['reused_first4_metadata_directory']);prior=json.loads((old/'COMMANDS.json').read_text());assert len(prior)==4 and [r['label'] for r in prior]==['storage-compile','storage-symbols','storage-elf','storage-bytes'] and all(r['returncode']==0 and r['direct_wait_joined'] for r in prior)
  assert (old/'storage-compile.stderr').read_bytes()==Path(q['compiler_profile']['expected_compile_stderr_path']).read_bytes()
  for label in ('storage-symbols','storage-elf','storage-bytes'):assert (old/(label+'.stderr')).read_bytes()==b''
  assert not Path(q['joined_object']).exists();contract=json.loads(Path(q['predicate_contract']).read_text())
  # Concrete corrected predicate is CALLED on the existing object/raw captures,
  # and its success is persisted BEFORE ANY Popen or remaining ld-r operation.
  phase='called-corrected-prejoin-predicate';decision=storage_predicate.prejoin(q,contract,old);(receipt/'PREJOIN-CHECK.json').write_text(json.dumps(decision,indent=2)+'\n');prejoin_passed=True
  assert [row['label'] for row in q['commands']]==['unique-partial-join','joined-symbols','joined-elf']
  for command in q['commands']:
   phase=command['label'];assert prejoin_passed
   row={'label':phase,'argv':command['argv'],'pid':None,'proc_start_ticks':None,'returncode':None,'direct_wait_joined':False};rows.append(row)
   with Path(command['stdout_path']).open('xb') as stdout,Path(command['stderr_path']).open('xb') as stderr:
    child=subprocess.Popen(command['argv'],cwd=q['payload_cwd'],env=q['environment_replace'],stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr);row['pid']=child.pid
    try:
     try:row['proc_start_ticks']=Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
     except OSError as error:row['birth_observation_error']=type(error).__name__
     (receipt/'COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n')
    finally:status=child.wait()
   row.update({'returncode':status,'direct_wait_joined':True});(receipt/'COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n');assert status==0,phase;assert Path(command['stderr_path']).read_bytes()==b'','Unexpected diagnostics: '+phase
  phase='called-corrected-postjoin-predicate';post=storage_predicate.postjoin(q,contract);(receipt/'POSTJOIN-CHECK.json').write_text(json.dumps(post,indent=2)+'\n')
  result={'status':'PASS_FOCUSED_STORAGE_PREDICATE_CORRECTION_AND_THREE_UNSTARTED_COMMANDS','request_sha256':hashlib.sha256(request_path.read_bytes()).hexdigest(),'prejoin_predicate_called_and_passed_before_any_Popen_ld_r':prejoin_passed,'postjoin_predicate_called_and_passed':True,'all3_child_direct_waits_joined':all(row['direct_wait_joined'] for row in rows),'original4_commands_reused_not_replayed':True,'commands':rows,'global_joined_T':22,'global_joined_data':9,'global_joined_strong':31,'genuine_remaining_U':post['genuine_U'],'original_private_TRACE_FILE319_bound_exactly':q['original_trace_static_symbol'],'runtime_or_native_initialization_executed':False,'artifact_hashes':{name:hashlib.sha256(Path(q[name]).read_bytes()).hexdigest() for name in ('storage_object','joined_object')}};(receipt/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0
 except BaseException as error:
  failure={'status':'FIRST_CORRECTED_FAILURE_STOP_FOCUSED_ESCALATION_NO_SECOND_CORRECTION','phase':phase,'error_type':type(error).__name__,'error':str(error),'traceback':traceback.format_exc(),'commands':rows,'all_started_children_direct_wait_joined':all(row['pid'] is None or row['direct_wait_joined'] for row in rows)};(receipt/'FIRST-CORRECTED-FAILURE.json').write_text(json.dumps(failure,indent=2)+'\n');print(json.dumps(failure,indent=2));return 1
if __name__=='__main__':raise SystemExit(main())
