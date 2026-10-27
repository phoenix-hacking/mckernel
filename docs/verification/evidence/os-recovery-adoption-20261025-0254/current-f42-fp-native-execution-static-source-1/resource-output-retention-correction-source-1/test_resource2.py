"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Literal --output-path/--resource CLI tests with an explicit inert producer only.
"""
from pathlib import Path
import ast,hashlib,json,subprocess,tempfile
R=Path(__file__).resolve().parent;A=R.parent
PYTHON='/home/holden/anaconda3/bin/python3'
proof=json.loads((R/'DERIVATION-PATH-ONLY.json').read_bytes())
old=(A/'capture_fresh_fp_resource.py').read_text();new=(R/'capture_fresh_fp_resource2.py').read_text();reversed_source=new
for before,after in reversed(list(proof['literal_substitutions'].items())):
 assert reversed_source.count(after)==1;reversed_source=reversed_source.replace(after,before)
assert reversed_source==old
checks=1
# Copy exact production CLI/parser/exclusive-output prefix and final persistence
# suffix. Replace ONLY marked observation body with a conspicuous inert producer;
# production helper itself contains no test flag or observer bypass.
prefix,body=new.split('# BEGIN_UNCHANGED_OBSERVATION_BODY\n',1)
body,suffix=body.split('# END_UNCHANGED_OBSERVATION_BODY\n',1)
static=json.loads((A/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json').read_bytes())
inert=dict(scope='INERT_CLI_TEST_ONLY',observed_clocks=[1,2,3],runtime_authority=None,actual_latest_operation_postjoin_acceptance=static['latest_serial_operation_physical_acceptance'],boot_id='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb',no_existing_heavy=True,pids_current=0)
producer="with (R/'INERT-PRODUCER-RAN').open('ab') as marker:marker.write(b'X')\nresult="+repr(inert)+"\nintermediate_stdout.write(b'INERT');intermediate_stdout.close()\nintermediate_stderr.close()\n"

def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def run(argv):return subprocess.run(argv,capture_output=True)

with tempfile.TemporaryDirectory(prefix='literal-cli-resource2-',dir=R) as td:
 root=Path(td)
 for collision in ['output','stdout','stderr']:
  t=root/collision;t.mkdir();helper=t/'capture_fresh_fp_resource2.py';helper.write_text(prefix+producer+suffix)
  output=t/'ROOT-FRESH-NATIVE-RESOURCE-PHYSICAL-2.json'
  target=output if collision=='output' else output.with_name(output.stem+'.POSTNATIVE.'+collision)
  target.write_bytes(b'ORIGINAL_COLLISION_BYTES')
  argv=[PYTHON,'-I','-B',str(helper),'--output-path',str(output)]
  r=run(argv)
  assert r.returncode!=0 and b'FileExistsError' in r.stderr and not r.stdout
  assert target.read_bytes()==b'ORIGINAL_COLLISION_BYTES' and not (t/'INERT-PRODUCER-RAN').exists()
  if collision!='output':assert not output.exists()
  checks+=1
 t=root/'success';t.mkdir();helper=t/'capture_fresh_fp_resource2.py';helper.write_text(prefix+producer+suffix)
 output=t/'ROOT-FRESH-NATIVE-RESOURCE-PHYSICAL-2.json'
 argv=[PYTHON,'-I','-B',str(helper),'--output-path',str(output)]
 r=run(argv);assert r.returncode==0 and not r.stderr
 assert json.loads(output.read_bytes())==inert and json.loads(r.stdout)['retained_resource']==ref(output)
 assert (t/'INERT-PRODUCER-RAN').read_bytes()==b'X';checks+=1
 before=output.read_bytes();again=run(argv)
 assert again.returncode!=0 and output.read_bytes()==before and (t/'INERT-PRODUCER-RAN').read_bytes()==b'X';checks+=1
 # Literal binder CLI selects this exact retained Resource2, not any empty v1.
 (t/'ROOT-FRESH-NATIVE-RESOURCE-PHYSICAL-1.json').write_bytes(b'')
 (t/'bind_resource2.py').write_bytes((R/'bind_resource2.py').read_bytes())
 (t/'STATIC-NATIVE-BINDINGS.RESOURCE-2.NOT-RELEASED.json').write_text(json.dumps(static))
 (t/'ACTUAL-STATIC-SOURCE-PUBLICATION.json').write_text('{"scope":"INERT_BINDER_FIXTURE_ONLY","runtime_authority":null}')
 joined=dict(direct_child_joined=True,returncode=0,streams_closed=True,resource=ref(output),stderr=dict(bytes=0),argv=argv)
 (t/'RESOURCE-2-CAPTURE-JOIN.json').write_text(json.dumps(joined))
 bound=run([PYTHON,'-I','-B',str(t/'bind_resource2.py'),'--resource',str(output)])
 assert bound.returncode==0 and not bound.stderr
 packet=json.loads((t/'ROOT-EXECUTION-GRANT.PENDING-REVIEW.json').read_bytes())
 assert packet['fresh_resource_physical']==ref(output) and packet['nonce']==static['nonce'] and packet['exact_argv']==static['exact_argv'] and packet['runtime_authority'] is None;checks+=1
 wrong=run([PYTHON,'-I','-B',str(t/'bind_resource2.py'),'--resource',str(t/'ROOT-FRESH-NATIVE-RESOURCE-PHYSICAL-1.json')])
 assert wrong.returncode!=0 and b'exact Resource2 output only' in wrong.stderr;checks+=1
 # Unchanged binder resource guards, evaluated as pure functions only.
 tree=ast.parse((R/'bind_resource2.py').read_text());function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packet_for')
 env={'A':A,'__doc__':'INERT_PURE_BINDER_TEST'};exec(compile(ast.Module(body=[function],type_ignores=[]),'pure_binding','exec'),env)
 for key,bad in [('boot_id','wrong'),('no_existing_heavy',False),('pids_current',1),('actual_latest_operation_postjoin_acceptance',{})]:
  badvalue=dict(inert);badvalue[key]=bad
  try:env['packet_for'](static,{},badvalue,ref(output),{})
  except AssertionError:pass
  else:raise AssertionError('unchanged binder predicate weakened: '+key)
  checks+=1
print(json.dumps(dict(status='PASS_LITERAL_RESOURCE2_CLI_REGRESSIONS',checks=checks,production_cli_parser_and_output_code_exact=True,observation_body_only_inert_substitution=True,existing_output_and_both_intermediates_rejected_before_producer=True,helper_persists_json_without_caller_redirect=True,exact_resource2_binder_cli_selection=True,predicate_reverse_substitution_byte_exact=True,fresh_resource_observations=0,account_calls=0,docker_calls=0,guest_calls=0,runtime_authority=None)))
