"""Actual capture_logs/root_command bodies, retained completed-child data; no Docker."""
from pathlib import Path
import ast,base64,contextlib,hashlib,io,json,os,subprocess,sys,types
HERE=Path(__file__).resolve().parent
INPUTS=HERE/'LOGS-BODY-CHECK-INPUTS.json'
INPUTS_SHA='9b20ccb2d0b4fe21ca8f91d344518b7b29ae23daa372fca2fdf0c771f43a4d77'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(row):
 raw=Path(row['path']).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256'];return raw
assert sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:3]==(3,9,12)
raw=INPUTS.read_bytes();assert sha(raw)==INPUTS_SHA;inputs=json.loads(raw)
src=load(inputs['engine']).decode();previous=load(inputs['previous_engine']).decode();basis=json.loads(load(inputs['current_cleanup_release']));load(inputs['observer'])
ob=(json.dumps(basis['observation'],sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode();assert sha(ob)==inputs['reused_actual_observation_tuple']['canonical_sha256']
tree=ast.parse(src);before=ast.parse(previous)
oldf={n.name:ast.dump(n,include_attributes=False) for n in before.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
newf={n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
assert oldf.keys()==newf.keys() and all(oldf[k]==newf[k] for k in oldf if k!='capture_logs')
case=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PRECOMPILER_CASE' for t in n.targets))
rows=[json.loads(x) for x in load(inputs['actual_diagnostic_stdout']).decode().splitlines()]
actual=next(x['row'] for x in rows if x.get('row',{}).get('argv',[None,None,None])[2:3]==['logs'])
assert actual['returncode']==0 and actual['stdout']['complete'] and actual['stderr']['complete'] and actual['stdout']['observed_bytes']==0
out=base64.b64decode(actual['stdout']['retained_base64']);err=base64.b64decode(actual['stderr']['retained_base64']);expected=load(inputs['pinned_expected_log']);assert err==expected and len(err)==746 and sha(err)==case['log']['sha256']
for key,value in [('stdout',out),('stderr',err)]:assert sha(value)==actual[key]['observed_sha256']
class Refusal(RuntimeError):pass
responses=[];calls=[]
def run(args,**kw):
 assert args==actual['argv'] and kw==dict(env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'},stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,check=False)
 calls.append(args);rc,a,b=responses.pop(0);return subprocess.CompletedProcess(args,rc,a,b)
ns=dict(Path=Path,json=json,hashlib=hashlib,Refusal=Refusal,PROTECTED_LIMIT=128<<20,RELEASE={'observation':{'target':basis['observation']['target']}},PRECOMPILER_CASE=case,CONTAINER=case['target']['container_id'],CAPTURE=Path('/home/holden/mckernel-work/scratch/settid-current-precompiler-terminal-logs-correction-20261021-1.docker-logs.capture'),EVIDENCE=Path(inputs['pinned_expected_log']['path']).parent.parent,os=types.SimpleNamespace(path=os.path,geteuid=lambda:0),subprocess=types.SimpleNamespace(run=run,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE))
assert not os.path.lexists(ns['CAPTURE'])
def read_bounded(path,maximum):assert path==Path(inputs['pinned_expected_log']['path']) and len(expected)<=maximum;return expected
ns['read_bounded']=read_bounded
ns['run_privileged_large']=lambda args:(_ for _ in ()).throw(AssertionError('unexpected legacy path'))
for name in ('canonical','digest','capture_logs','root_command'):
 node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
 exec(compile(ast.Module(body=[node],type_ignores=[]),inputs['engine']['path'],'exec'),ns)
results=[]
for name,rc,a,b,want in [('actual_stderr_log_success',0,out,err,None),('controlled_nonzero_Docker_error_on_identical_retained_payload',1,out,err,'exact-precompiler-docker-log-channels'),('unexpected_stdout_channel_refused',0,err,b'','exact-precompiler-docker-log-channels')]:
 responses.append((rc,a,b));printed=io.StringIO()
 with contextlib.redirect_stdout(printed):
  try:ns['capture_logs'](True,execute=False)
  except Refusal as error:assert str(error)==want
  else:assert want is None
 results.append(dict(name=name,passed=True,controlled_returncode=rc,refusal=want,diagnostic_rows=[json.loads(x) for x in printed.getvalue().splitlines()]))
responses.append((0,out,err))
try:ns['root_command'](actual['argv'],128<<20)
except Refusal as error:assert str(error)=='root-command-failed:/usr/bin/docker'
else:raise AssertionError('global empty-stderr oracle weakened')
results.append(dict(name='global_root_command_stderr_refusal_preserved',passed=True))
assert not responses and len(calls)==4
result=dict(scope=inputs['scope'],status='PASS_ACTUAL_LOGS_CAPTURE_BODY_AND_STRICT_ERROR_REFUSALS_ONLY',engine=inputs['engine'],inputs_sha256=INPUTS_SHA,actual_retained_log_sha256=sha(err),cases=results,case_count=4,actual_body_functions=['capture_logs','root_command'],actual_Docker_commands_executed=0,engine_import_configure_or_cleanup_executed=False,controlled_failure_vectors_are_not_actual_Docker_observations=True)
with (HERE/'ACTUAL-LOGS-BODY-CHECK-RESULT.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps(result,sort_keys=True))
