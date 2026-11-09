"""Three once-only partial-link/read commands after called exact-owner gate."""
from pathlib import Path
import hashlib,json,subprocess,sys,traceback
import join_checks

def main():
 path=Path(sys.argv[1]);q=json.loads(path.read_text());p=path.parent;rows=[];phase='input-bindings'
 try:
  for name,digest in q['inputs'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
  Path(q['output_directory']).mkdir(exist_ok=False);phase='called-prejoin';decision=join_checks.prejoin(q);(p/'PREJOIN-CHECK.json').write_text(json.dumps(decision,indent=2)+'\n');gate_passed=True
  assert [x['label'] for x in q['commands']]==['partial-join','joined-symbols','joined-elf']
  for command in q['commands']:
   assert gate_passed;phase=command['label'];row={'label':phase,'argv':command['argv'],'pid':None,'proc_start_ticks':None,'returncode':None,'direct_wait_joined':False};rows.append(row)
   with Path(command['stdout_path']).open('xb') as stdout,Path(command['stderr_path']).open('xb') as stderr:
    child=subprocess.Popen(command['argv'],cwd=q['cwd'],env=q['environment_replace'],stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr);row['pid']=child.pid
    try:
     try:row['proc_start_ticks']=Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
     except OSError as error:row['birth_observation_error']=type(error).__name__
     (p/'COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n')
    finally:status=child.wait()
   row.update({'returncode':status,'direct_wait_joined':True});(p/'COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n');assert status==0,phase;assert Path(command['stderr_path']).read_bytes()==b'',phase+' unexpecteddiagnostics'
  phase='called-postjoin';post=join_checks.postjoin(q);(p/'POSTJOIN-CHECK.json').write_text(json.dumps(post,indent=2)+'\n');result={'status':'PASS_ACTUAL_NONEXECUTED_TWO_ROOT_STRING_PROVIDER_PARTIAL_JOIN','request_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'actual_prejoin_called_before_any_Popen':True,'actual_postjoin_called_and_passed':True,'all3_direct_waits_joined':True,'commands':rows,'joined_object':q['joined_object'],'joined_sha256':hashlib.sha256(Path(q['joined_object']).read_bytes()).hexdigest(),'strong':44,'global_T':35,'global_data':9,'genuine_U':post['genuine_U'],'no_compile_function_or_native_init_runtime':True};(p/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0
 except BaseException as error:
  failure={'status':'FIRST_FAILURE_STOP_NO_AUTOMATIC_RETRY','phase':phase,'error_type':type(error).__name__,'error':str(error),'traceback':traceback.format_exc(),'commands':rows,'all_started_children_joined':all(r['pid'] is None or r['direct_wait_joined'] for r in rows)};(p/'FIRST-FAILURE.json').write_text(json.dumps(failure,indent=2)+'\n');print(json.dumps(failure,indent=2));return 1
if __name__=='__main__':raise SystemExit(main())
