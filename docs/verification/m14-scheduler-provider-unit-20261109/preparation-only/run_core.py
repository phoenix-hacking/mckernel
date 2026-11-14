"""Only the three source-qualified scheduler codegen/readback payloads; NO linker."""
from pathlib import Path
import hashlib,json,subprocess,sys,traceback
import scheduler_checks

def main():
 request=Path(sys.argv[1]);q=json.loads(request.read_text());p=request.parent;rows=[];phase='bindings'
 try:
  for name,digest in q['inputs'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
  Path(q['output_directory']).mkdir(exist_ok=False)
  assert [row['label'] for row in q['commands']]==['provider-compile','provider-symbols','provider-elf']
  for command in q['commands']:
   phase=command['label'];row={'label':phase,'argv':command['argv'],'pid':None,'proc_start_ticks':None,'returncode':None,'direct_wait_joined':False};rows.append(row)
   with Path(command['stdout_path']).open('xb') as stdout,Path(command['stderr_path']).open('xb') as stderr:
    child=subprocess.Popen(command['argv'],cwd=q['cwd'],env=q['environment_replace'],stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr);row['pid']=child.pid
    try:
     try:row['proc_start_ticks']=Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
     except OSError as error:row['birth_observation_error']=type(error).__name__
     (p/'CORE-COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n')
    finally:status=child.wait()
   row.update({'returncode':status,'direct_wait_joined':True});(p/'CORE-COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n');assert status==0,phase
   expected=Path(q['retained_exact_compile_diagnostics']).read_bytes() if phase=='provider-compile' else b''
   assert Path(command['stderr_path']).read_bytes()==expected,phase+' diagnostics differ from retained profile'
  phase='called-actual-source-object-gate';decision=scheduler_checks.object_gate(q);(p/'OBJECT-CHECK.json').write_text(json.dumps(decision,indent=2)+'\n')
  result={'status':'PASS_ACTUAL_FINITE_SCHEDULER_CORE_OBJECT_NO_LINK_OR_RUNTIME','request_sha256':hashlib.sha256(request.read_bytes()).hexdigest(),'object_sha256':hashlib.sha256(Path(q['new_object']).read_bytes()).hexdigest(),'actual_object_gate_called':True,'all3_direct_waits_joined':True,'commands':rows,'no_link_or_kernel_function_execution':True};(p/'CORE-RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0
 except BaseException as error:
  failure={'status':'FIRST_ACTUAL_FAILURE_STOP_BEFORE_LINK_NO_AUTOMATIC_RETRY','phase':phase,'error_type':type(error).__name__,'error':str(error),'traceback':traceback.format_exc(),'commands':rows,'all_started_children_joined':all(row['pid'] is None or row['direct_wait_joined'] for row in rows)};(p/'CORE-FIRST-FAILURE.json').write_text(json.dumps(failure,indent=2)+'\n');print(json.dumps(failure,indent=2));return 1
if __name__=='__main__':raise SystemExit(main())
