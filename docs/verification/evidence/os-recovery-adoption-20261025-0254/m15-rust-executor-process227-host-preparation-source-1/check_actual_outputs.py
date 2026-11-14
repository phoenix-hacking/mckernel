"""Functional OS only; no security testing. Read retained227 HOST evidence only.
No compiler, command runner, admission, account, native or resource operation.
"""
import argparse,hashlib,importlib.util,json,re
from pathlib import Path

def need(ok,why):
 if not ok:raise ValueError(why)
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def checked(r):
 need(ref(r['path'])==r,'exact retained evidence '+r['path']);return Path(r['path']).read_bytes()
def check_tests(raw,names):
 text=raw.decode('utf-8');lines=text.splitlines();count=len(names)
 need(sum(line==f'running {count} tests' for line in lines)==1,'exact finite harness count')
 actual=[]
 for line in lines:
  m=re.fullmatch(r'test ([A-Za-z0-9_:]+) \.\.\. ok',line)
  if m:actual.append(m.group(1));continue
  if not line or line==f'running {count} tests':continue
  need(re.fullmatch(r'test result: ok\. '+str(count)+r' passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in [0-9]+(?:\.[0-9]+)?s',line) is not None,'unexpected test output retained as failure')
 need(sorted(actual)==sorted(names) and len(set(actual))==count,'exact named controls, nofilter/ignore')
 need(sum(line.startswith('test result:') for line in lines)==1,'one full harness result')
 return True

def qualify(profile):
 """One source-bound actual receipt after all THREE genuine new commands.

 The actual production ELF and its old static/HOST proof are explicitly reused;
 the new227 oracle is compiled only into the HOSTfakeexec/test pair.
 """
 root=Path(profile['capture_root']);rows=[]
 for i,command in enumerate(profile['commands']):
  step=root/('step'+str(i));saved=json.loads((step/'command.json').read_bytes())
  need(saved==command,'actual exact command '+str(i))
  joined=json.loads((step/'whole-join.json').read_bytes())
  need(joined['returncode']==0 and joined['direct_child_joined'] is True and joined['group_absent'] is True
       and joined['closed_streams'] is True and not joined['error'] and not joined['retirement_error'],
       'complete positive actual join/group/stream proof '+str(i))
  need((step/'stderr').read_bytes()==b'','actual command diagnostics not empty '+str(i))
  if i<2:need((step/'stdout').read_bytes()==b'','actual compiler stdout not empty '+str(i))
  rows.append(dict(command=ref(step/'command.json'),whole_join=ref(step/'whole-join.json'),
                   stdout=ref(step/'stdout'),stderr=ref(step/'stderr')))
 need(len(rows)==3,'exact three new HOST commands')
 check_tests((root/'step2/stdout').read_bytes(),profile['expected_test_names'])
 case=json.loads(checked(profile['caseprofile']))
 need(Path(profile['expected_stdout_input']['path']).read_bytes()==bytes.fromhex(case['oracle']['stdout_hex'])
      and profile['expected_stdout_input']['bytes']==227,'exact original227 compiled HOST input')
 checked(profile['expected_stdout_input'])
 artifact=profile['reused_actual_collector_artifact'];checked(artifact)
 old=json.loads(checked(profile['reused_generic_HOST_qualification']))
 need(old['decision'].startswith('PASS') and old['actual_collector']==artifact,'genuine prior qualified production subject')
 checked(profile['reused_static_ELF_raw'])
 overlay=profile['retained_overlay_source'];checked(overlay)
 spec=importlib.util.spec_from_file_location('retained_collector_ELF_validator',overlay['path'])
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 module._check_collector(Path(artifact['path']).read_bytes())
 source_rows=profile['source_inputs'];qualified=profile['qualified_generic_source_inputs']
 need(len(source_rows)==len(qualified)==8,'exact generic source cohort')
 for new,prior in zip(source_rows,qualified):
  need(checked(new)==checked(prior),'qualified generic source mismatch')
 return dict(status='PASS_THREE_NEW227_HOST_STEPS_26_CONTROLS_REUSED_GENERIC_ELF_ONLY',
             case_id=case['case_id'],payload_argv=case['argv'],payload_cwd=case['cwd'],payload_env=case['env'],
             oracle=case['oracle'],source_caseprofile=profile['caseprofile'],source_ready=profile['source_ready'],
             source_review=profile['source_review'],actual_test_count=26,ignored=0,filtered=0,measured=0,
             actual_collector_artifact=artifact,startup_boot_argv=case['startup_boot_argv'],
             limits={k:case[k] for k in ['payload_timeout_ms','post_reap_retirement_ms','collector_timeout_seconds',
                                        'outer_native_timeout_seconds','stdout_limit_bytes','stderr_limit_bytes','frame_limit_bytes']},
             old_generic_HOST_reuse=dict(actual_test_count=26,qualification=profile['reused_generic_HOST_qualification'],
                                        scope='generic source/argv/env/deadlines/limits/staticELF only; old235 oracle not227 proof'),
             new227_HOST=dict(actual_test_count=26,commands=rows,expected_stdout_input=profile['expected_stdout_input'],
                             scope='genuine227 HOST fakeexec/test/frame input only; not native SIGTERM/resource restoration'),
             production_recompiled=False,readelf_replayed=False,native_acceptance=False,
             runtime_authority='NOT_GRANTED_BY_HOST_QUALIFICATION')

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--bound-recipe',required=True)
 a.add_argument('--bound-recipe-sha256',required=True);args=a.parse_args();path=Path(args.bound_recipe)
 raw=path.read_bytes();need(hashlib.sha256(raw).hexdigest()==args.bound_recipe_sha256,'exact bound recipe')
 print(json.dumps(qualify(json.loads(raw)),sort_keys=True))
if __name__=='__main__':main()
