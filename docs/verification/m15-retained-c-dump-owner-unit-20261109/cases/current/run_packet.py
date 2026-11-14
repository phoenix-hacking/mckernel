"""Five literal C-only payloads; actual typed-hook gate MUST pass before link/run."""
from pathlib import Path
import hashlib,json,subprocess,sys,traceback
import validate_hooks

def main():
 request=Path(sys.argv[1]);q=json.loads(request.read_text());p=request.parent;rows=[];phase='bindings';hook_passed=False
 try:
  for name,digest in q['inputs'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
  Path(q['output_directory']).mkdir(exist_ok=False)
  assert [c['label'] for c in q['commands']]==['observer-compile','candidate-compile','candidate-symbols','candidate-link','candidate-run']
  for command in q['commands']:
   phase=command['label']
   if phase in ('candidate-link','candidate-run'):assert hook_passed,'Actual hook gate must pass before link/runtime'
   row={'label':phase,'argv':command['argv'],'pid':None,'proc_start_ticks':None,'returncode':None,'direct_wait_joined':False};rows.append(row)
   with Path(command['stdout_path']).open('xb') as stdout,Path(command['stderr_path']).open('xb') as stderr:
    child=subprocess.Popen(command['argv'],cwd=q['cwd'],env=q['environment_replace'],stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr);row['pid']=child.pid
    try:
     try:row['proc_start_ticks']=Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
     except OSError as error:row['birth_observation_error']=type(error).__name__
     (p/'COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n')
    finally:status=child.wait()
   row.update({'returncode':status,'direct_wait_joined':True});(p/'COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n')
   assert status==0,phase;assert Path(command['stderr_path']).read_bytes()==b'',phase+' unexpected diagnostics'
   if phase=='candidate-symbols':
    phase='called-actual-object-hook-gate';decision=validate_hooks.validate(Path(command['stdout_path']).read_text(),q['candidate_object']);(p/'HOOK-GATE.json').write_text(json.dumps(decision,indent=2)+'\n');hook_passed=True
   elif phase=='candidate-run':assert Path(command['stdout_path']).read_text()==q['expected_stdout'],'Unexpected ownership/order/result output'
  artifacts={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.iterdir() if f.is_file() and f.suffix in ('.stdout','.stderr','.metrics')};artifacts.update({str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in Path(q['output_directory']).iterdir() if f.is_file()});(p/'ARTIFACTS.json').write_text(json.dumps(artifacts,indent=2)+'\n')
  result={'status':'PASS_THREE_DEFINED_C_DUMP_BUFFER_OWNERSHIP_EXITS','request_sha256':hashlib.sha256(request.read_bytes()).hexdigest(),'new_candidate_cases':3,'owners_freed_once_per_case':[0,1,2],'survivors_per_case':[0,0,0],'actual_object_hook_gate_called_before_link_runtime':hook_passed,'all5_direct_waits_joined':True,'commands':rows,'scope':q['scope'],'retained_baseline_proof_reused_without_runtime':True,'no_Rust_or_old_parent_cases_replayed':True,'no_actual_device_NMI_dump_BFD_object_file_native_or_default_acceptance':True};(p/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0
 except BaseException as error:
  failure={'status':'FIRST_FAILURE_STOP_FOCUSED_REVIEW_NO_AUTOMATIC_RETRY','phase':phase,'error_type':type(error).__name__,'error':str(error),'traceback':traceback.format_exc(),'commands':rows,'all_started_children_joined':all(row['pid'] is None or row['direct_wait_joined'] for row in rows)};(p/'FIRST-FAILURE.json').write_text(json.dumps(failure,indent=2)+'\n');print(json.dumps(failure,indent=2));return 1
if __name__=='__main__':raise SystemExit(main())
