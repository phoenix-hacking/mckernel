"""Functional OS only; no security testing. Data-only existing finite HOST API recipe.
No compiler, admission/guard, observation, process, grant or workload invocation.
"""
import argparse,copy,hashlib,importlib.util,json,os
from pathlib import Path
D=Path(__file__).resolve().parent

def need(ok,why):
 if not ok:raise ValueError(why)
def ref(p):
 p=Path(p);a=p.stat();b=p.read_bytes();z=p.stat();need(all(getattr(a,k)==getattr(z,k) for k in ['st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns']),'stable reference');return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def checked(r):
 need(ref(r['path'])==r,'exact input '+r['path']);return Path(r['path']).read_bytes()
def read(r):return json.loads(checked(r))
def module(r,name):
 checked(r);s=importlib.util.spec_from_file_location(name,r['path']);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def source_check():
 sk=json.loads((D/'INPUT-SKELETON.NOT-GRANTED.json').read_bytes());p=json.loads((D/'PRODUCER-SOURCE-INPUTS.NOT-GRANTED.json').read_bytes());profile=json.loads((D/'FIVE-STEP-PROFILE.INPUT-TEMPLATE.json').read_bytes())
 for r in sk['references'].values():checked(r)
 for r in [sk['compiler'],sk['env_tool'],sk['readelf'],*sk['finite_archive_refs'],p['source_ready'],p['compiled_caseprofile'],*p['actual_source_refs']]:checked(r)
 ready=read(p['source_ready']);case=read(p['compiled_caseprofile']);need(ready['prepared_controls']['total']==p['expected_test_count']==len(p['expected_test_names'])==22,'exact producer22 source controls')
 need(set(sk['retained_actual_test_names']).issubset(p['expected_test_names']) and len(set(p['expected_test_names']))==22,'retained16 plus6 meaningful controls')
 need(case['argv']==['/bin/mcexec','-t','1','0','app','A','','B'] and case['cwd']=='/case/work' and case['env']=={'PATH':'/usr/bin:/bin','COKERNEL_PATH':'/apps'},'original startup launch')
 need(len(bytes.fromhex(case['oracle']['stdout_hex']))==91 and case['oracle']['exit_code']==0 and case['oracle']['stderr_hex']=='','original91B oracle')
 need(case['payload_timeout_ms']==10000 and case['post_reap_retirement_ms']==5000 and case['stdout_limit_bytes']==case['stderr_limit_bytes']==1024,'no deadline/stream widening')
 need(p['source_review'] is None and p['actual_HOST_qualification'] is None and p['actual_collector_artifact'] is None and p['runtime_authority'] is None,'no unearned source/HOST/native authority')
 return sk,p,profile

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--check-inputs',action='store_true');a.add_argument('--root-inputs');a.add_argument('--root-inputs-sha256');args=a.parse_args();sk,p,profile=source_check()
 if args.check_inputs:
  print(json.dumps(dict(status='PASS_SOURCE_COMPILER_ARCHIVE_INPUTS_READONLY_NOT_EXECUTION',source_ready=p['source_ready'],source_modules=len(p['actual_source_refs']),finite_archive_refs=len(sk['finite_archive_refs']),prepared_controls=p['expected_test_count'],source_review=None,Root_grant=None)));return
 need(args.root_inputs and args.root_inputs_sha256,'Root actual fill input required');qpath=Path(args.root_inputs).resolve();q=read(dict(path=str(qpath),bytes=qpath.stat().st_size,sha256=args.root_inputs_sha256));need(q['author'] in ('/root','/root/mcexec_default_prepare'),'sourceprofile preparation author only, no execution authority')
 review=read(q['source_review']);need(review.get('implementation_ownership') is False and review.get('reviewer') not in (None,'/root') and str(review.get('decision','')).startswith('PASS') and p['source_ready']['sha256'] in json.dumps(review),'actual independent source decision binds exactREADY')
 output=Path(q['output_root']);capture=Path(q['capture_root']);need(output.is_absolute() and capture.is_absolute() and output!=capture and not os.path.lexists(output) and not os.path.lexists(capture),'fresh distinct future output/capture')
 need(str(output).startswith(str(D)+'/') and str(capture).startswith(str(D)+'/'),'private fresh outputs')
 commands=[]
 for i,row in enumerate(profile['steps']):
  argv=[z.replace('{source_root}',p['source_root']).replace('{output_root}',str(output)) for z in row['argv_template']]
  if i in (0,1,3):
   prefix=[sk['env_tool']['path'],'TMPDIR='+str(output)]
   if i==1:prefix+=['STARTUP_FAKEEXEC_PATH='+str(output/'startup-fakeexec')]
   argv=prefix+argv
  commands.append(dict(argv=argv,cwd=p['source_root'],purpose=row['label'],leaf='original-startup-retirement',argv_compact_json_LF_sha256=hashlib.sha256((json.dumps(argv,separators=(',',':'))+'\n').encode()).hexdigest()))
 bound=dict(task_id='NEW12H-ORDINARY-HOST-M15-STARTUP-RETIREMENT-1',scope=sk['scope'],goal=profile['goal'],fixed_deadline_UTC=profile['fixed_deadline_UTC'],fixed_cutoffs=profile['fixed_cutoffs'],resources=profile['resources'],host_growth_reserve_bytes=profile['host_growth_reserve_bytes'],capture_root=str(capture),commands=commands,leaves=[dict(name='original-startup-retirement',first=0,last=4,plan=ref(D/'PRODUCER-SOURCE-INPUTS.NOT-GRANTED.json'),output=str(output),expected_stdout=None)],inputs=[*sk['references'].values(),sk['compiler'],sk['env_tool'],sk['readelf'],*sk['finite_archive_refs'],p['source_ready'],p['compiled_caseprofile'],*p['actual_source_refs'],q['source_review'],ref(D/'check_actual_outputs.py')],expected_test_names=p['expected_test_names'],expected_test_count=p['expected_test_count'],production_output=str(output/'startup-supervisor'),retained_overlay_source=dict(path='/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/native-runtime-ready-1/native_diagnostic_overlay.py',bytes=26579,sha256='46d41bc0727fa77e4126e739f25352c53eadf2e1fa8e23ef06a6e46c9b3ba27d'),execution_route='EXISTING_FINITE_API_ONLY_NOT_CLI_LEAF_STDOUT_EQUALITY',source_review=q['source_review'],Root_grant=None,runtime_authority=None)
 checked(bound['retained_overlay_source']);bound['inputs'].append(bound['retained_overlay_source'])
 runner=module(sk['references']['ordinary_runner'],'retained_ordinary_profile_validation_only');runner.validate_profile(bound)
 with (D/'BOUND-RECIPE.NOT-GRANTED.json').open('x') as f:json.dump(bound,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps(dict(status='BOUND_FIVE_STEP_EXISTING_FINITE_API_RECIPE_NOT_EXECUTION',recipe=ref(D/'BOUND-RECIPE.NOT-GRANTED.json'),Root_grant=None,runtime_authority=None)))
if __name__=='__main__':main()
