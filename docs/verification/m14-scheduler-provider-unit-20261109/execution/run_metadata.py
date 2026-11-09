"""Only two actual scheduler metadata reads; consume Root compile, NO linker."""
from pathlib import Path
import hashlib,json,subprocess,sys,traceback
import scheduler_checks

def main():
 request=Path(sys.argv[1]);q=json.loads(request.read_text());p=request.parent;rows=[];phase='bindings';prejoin_passed=False
 try:
  for name,digest in q['inputs'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
  assert Path(q['output_directory']).is_dir()
  assert hashlib.sha256(Path(q['new_object']).read_bytes()).hexdigest()==q['compiled_input']['sha256']
  assert [row['label'] for row in q['commands']]==['provider-symbols','provider-elf']
  for command in q['commands']:
   phase=command['label']
   row={'label':phase,'argv':command['argv'],'pid':None,'proc_start_ticks':None,'returncode':None,'direct_wait_joined':False};rows.append(row)
   with Path(command['stdout_path']).open('xb') as stdout,Path(command['stderr_path']).open('xb') as stderr:
    child=subprocess.Popen(command['argv'],cwd=q['cwd'],env=q['environment_replace'],stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr);row['pid']=child.pid
    try:
     try:row['proc_start_ticks']=Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
     except OSError as error:row['birth_observation_error']=type(error).__name__
     (p/'METADATA-COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n')
    finally:status=child.wait()
   row.update({'returncode':status,'direct_wait_joined':True});(p/'METADATA-COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n');assert status==0,phase;assert Path(command['stderr_path']).read_bytes()==b'',phase+' unexpected diagnostics'
   if phase=='provider-elf':
    phase='called-source-object-unique-owner-prejoin';decision=scheduler_checks.prejoin(q)
    (p/'OBJECT-CHECK.json').write_text(json.dumps(decision['actual_object_gate'],indent=2)+'\n')
    (p/'PREJOIN-CHECK.json').write_text(json.dumps(decision,indent=2)+'\n');prejoin_passed=True
  artifacts={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.iterdir() if f.is_file() and f.suffix in ('.stdout','.stderr','.metrics')};artifacts.update({str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in Path(q['output_directory']).iterdir() if f.is_file()});(p/'ARTIFACTS.json').write_text(json.dumps(artifacts,indent=2)+'\n')
  result={'status':'PASS_ACTUAL_SCHEDULER_OBJECT_METADATA_AND_PREJOIN_NO_LINK','request_sha256':hashlib.sha256(request.read_bytes()).hexdigest(),'compiled_input':q['compiled_input'],'actual_object_and_prejoin_called_persisted':prejoin_passed,'all2_direct_waits_joined':True,'commands':rows,'no_compile_replay_link_or_function_runtime':True};(p/'METADATA-RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0
 except BaseException as error:
  failure={'status':'FIRST_ACTUAL_FAILURE_STOP_FOCUSED_REVIEW_NO_AUTOMATIC_RETRY','phase':phase,'error_type':type(error).__name__,'error':str(error),'traceback':traceback.format_exc(),'commands':rows,'all_started_children_joined':all(row['pid'] is None or row['direct_wait_joined'] for row in rows)};(p/'METADATA-FIRST-FAILURE.json').write_text(json.dumps(failure,indent=2)+'\n');print(json.dumps(failure,indent=2));return 1
if __name__=='__main__':raise SystemExit(main())
