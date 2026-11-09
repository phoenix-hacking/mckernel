"""Four exact source/object qualification commands; no link or function execution."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import traceback
import string_predicate

def main():
 path=Path(sys.argv[1]);q=json.loads(path.read_text());receipt=path.parent;rows=[];phase='input-binding'
 try:
  for name,digest in q['inputs'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
  Path(q['output_directory']).mkdir(exist_ok=False);assert [r['label'] for r in q['commands']]==['provider-compile','provider-symbols','provider-elf','provider-disassembly']
  for command in q['commands']:
   phase=command['label'];row={'label':phase,'argv':command['argv'],'pid':None,'proc_start_ticks':None,'returncode':None,'direct_wait_joined':False};rows.append(row)
   with Path(command['stdout_path']).open('xb') as stdout,Path(command['stderr_path']).open('xb') as stderr:
    child=subprocess.Popen(command['argv'],cwd=q['cwd'],env=q['environment_replace'],stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr);row['pid']=child.pid
    try:
     try:row['proc_start_ticks']=Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
     except OSError as error:row['birth_observation_error']=type(error).__name__
     (receipt/'COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n')
    finally:status=child.wait()
   row.update({'returncode':status,'direct_wait_joined':True});(receipt/'COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n');assert status==0,phase
   expected=Path(q['compiler_profile']['expected_compile_stderr_path']).read_bytes() if phase=='provider-compile' else b'';assert Path(command['stderr_path']).read_bytes()==expected,'Unexpected diagnostics: '+phase
  phase='actual-called-two-root-object-disassembly-predicate';decision=string_predicate.qualify(q,receipt);(receipt/'PROVIDER-CHECK.json').write_text(json.dumps(decision,indent=2)+'\n')
  result={'status':'PASS_SCOPED_TWO_ROOT_KERNEL_STRING_PROVIDER_OBJECT','request_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'all4_direct_waits_joined':True,'commands':rows,'actual_predicate_called_and_passed':True,'provider_object':q['provider_object'],'provider_sha256':decision['object_sha256'],'global_T':decision['global_T'],'genuine_U':[],'global_data':[],'generated_self_cross_helper_calls':0,'link_or_function_native_runtime_executed':False};(receipt/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0
 except BaseException as error:
  failure={'status':'FIRST_FAILURE_STOP_NO_AUTOMATIC_RETRY','phase':phase,'error_type':type(error).__name__,'error':str(error),'traceback':traceback.format_exc(),'commands':rows,'all_started_children_joined':all(r['pid'] is None or r['direct_wait_joined'] for r in rows)};(receipt/'FIRST-FAILURE.json').write_text(json.dumps(failure,indent=2)+'\n');print(json.dumps(failure,indent=2));return 1
if __name__=='__main__':raise SystemExit(main())
