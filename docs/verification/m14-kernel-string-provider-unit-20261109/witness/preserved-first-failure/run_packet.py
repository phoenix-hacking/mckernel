"""Six ordinary HOST commands; concrete caller/final-ELF gates before execution."""
from pathlib import Path
import hashlib,json,subprocess,sys,traceback
import witness_checks

def main():
 path=Path(sys.argv[1]);q=json.loads(path.read_text());p=path.parent;rows=[];phase='bindings';caller_passed=elf_passed=False
 try:
  for name,digest in q['inputs'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
  Path(q['output_directory']).mkdir(exist_ok=False);assert [c['label'] for c in q['commands']]==['caller-compile','caller-symbols','caller-disassembly','witness-link','witness-elf','witness-run']
  for c in q['commands']:
   phase=c['label']
   if phase=='witness-link':assert caller_passed
   if phase=='witness-run':assert caller_passed and elf_passed
   row={'label':phase,'argv':c['argv'],'pid':None,'proc_start_ticks':None,'returncode':None,'direct_wait_joined':False};rows.append(row)
   with Path(c['stdout_path']).open('xb') as stdout,Path(c['stderr_path']).open('xb') as stderr:
    child=subprocess.Popen(c['argv'],cwd=q['cwd'],env=q['environment_replace'],stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr);row['pid']=child.pid
    try:
     try:row['proc_start_ticks']=Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
     except OSError as error:row['birth_observation_error']=type(error).__name__
     (p/'COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n')
    finally:status=child.wait()
   row.update({'returncode':status,'direct_wait_joined':True});(p/'COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n');assert status==0,phase;assert Path(c['stderr_path']).read_bytes()==b'',phase+' unexpected diagnostics'
   if phase=='caller-disassembly':
    phase='called-caller-check';decision=witness_checks.caller(q);(p/'CALLER-CHECK.json').write_text(json.dumps(decision,indent=2)+'\n');caller_passed=True
   elif phase=='witness-elf':
    phase='called-final-ELF-check';decision=witness_checks.executable(q);(p/'EXECUTABLE-CHECK.json').write_text(json.dumps(decision,indent=2)+'\n');elf_passed=True
   elif phase=='witness-run':assert Path(c['stdout_path']).read_text()==q['expected_stdout'],'actual ordinary C ABI observations mismatch'
  result={'status':'PASS_ORDINARY_VALID_INPUT_C_ABI_ACTUAL_KERNEL_STRING_ROOTS','request_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'all6_direct_waits_joined':True,'caller_check_called_before_link':caller_passed,'actual_final_ELF_binding_check_called_before_run':elf_passed,'qualified_provider_sha256':q['provider_sha256'],'observations':'ValidNULempty/abc limits0/2/3/8; realowned16B count0/positive/negativebyteconversion andreturnptr/untouchedprefixsuffix','commands':rows,'no_kernel_state_privileged_function_boot_or_native_acceptance':True,'no_accepted_F04_replay_or_new_quota_score':True};(p/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0
 except BaseException as error:
  failure={'status':'FIRST_FAILURE_STOP_NO_AUTOMATIC_RETRY','phase':phase,'error_type':type(error).__name__,'error':str(error),'traceback':traceback.format_exc(),'commands':rows,'all_started_children_joined':all(r['pid'] is None or r['direct_wait_joined'] for r in rows)};(p/'FIRST-FAILURE.json').write_text(json.dumps(failure,indent=2)+'\n');print(json.dumps(failure,indent=2));return 1
if __name__=='__main__':raise SystemExit(main())
