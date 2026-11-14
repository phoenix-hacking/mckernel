import ast,hashlib,json,pathlib,difflib
root=pathlib.Path(__file__).resolve().parent;oldroot=root.parent/'current290-quarantine-exception-read-source-1/custody-guard-correction-source-1';old=oldroot/'exact_root_guard_runner.py';sourceprofile=json.loads((oldroot/'EXACT-ACTOR-ROOT-READ-PROFILE.NOT-RELEASED.json').read_text());source=pathlib.Path(sourceprofile['source']['path']);tree=ast.parse(source.read_text());node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PROC_CODE' for t in n.targets));code=ast.literal_eval(node.value).encode();assert code.isascii()
def ref(path):
 path=pathlib.Path(path);raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
profile=dict(sourceprofile);profile['helper']=ref(root/'read_exact_root_command_result.gdb.py');profile['proc_code']=dict(source=sourceprofile['source'],sha256=hashlib.sha256(code).hexdigest(),bytes=len(code));profile['limits']=dict(sourceprofile['limits'],child_stdout_bytes=4194304,child_stderr_bytes=4194304,gdb_stdout_bytes=20971520,gdb_stderr_bytes=1048576,outer_capture_file_bytes=67108864);profile['root_command_limit_bytes']=1048576;profile['purpose']='Only exact retained Refusal traceback root_command.result CompletedProcess returncode/stdout/stderr plus actualPROC_CODEargvmetadata; no collector replay.'
p=root/'EXACT-ROOT-COMMAND-RESULT-PROFILE.NOT-RELEASED.json';p.write_text(json.dumps(profile,indent=2)+'\n');s=old.read_text().replace("PROFILE=ROOT/'EXACT-ACTOR-ROOT-READ-PROFILE.NOT-RELEASED.json'","PROFILE=ROOT/'EXACT-ROOT-COMMAND-RESULT-PROFILE.NOT-RELEASED.json'")
a=s.index("PROFILE_SHA='");z=s.index('\n',a);s=s[:a]+"PROFILE_SHA='"+ref(p)['sha256']+"'"+s[z:]
s=s.replace("'read-exact-recover-error '+profile['source']['path']+' Refusal'", "'read-exact-root-command-result '+profile['source']['path']+' '+profile['proc_code']['sha256']+' '+str(profile['proc_code']['bytes'])+' '+profile['actor']['starttime']")
a=s.index('def decode_result(');z=s.index('def perform(',a)
s=s[:a]+'''def decode_result(stdout,profile):
 answers=[json.loads(line) for line in stdout.decode('utf-8','strict').splitlines() if line.startswith('{')]
 need(len(answers)==1,'unique-json-result');answer=answers[0]
 need(answer.get('status')=='PASS_EXACT_ROOT_COMMAND_RESULT_READ' and answer.get('co_filename')==profile['source']['path'] and answer.get('co_name')=='root_command' and answer.get('local')=='result' and answer.get('exception_type')=='Refusal','exact-result-frame')
 rc=answer.get('returncode');need(type(rc) is int and -(1<<30)<rc<(1<<30),'bounded-child-returncode')
 for stream in ('stdout','stderr'):
  row=answer.get(stream);need(isinstance(row,dict) and set(row)=={'bytes','sha256','raw_hex'} and type(row['bytes']) is int and 0<=row['bytes']<=4<<20 and isinstance(row['raw_hex'],str) and len(row['raw_hex'])==2*row['bytes'],'bounded-child-byte-result')
  raw=bytes.fromhex(row['raw_hex']);need(len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'lossless-child-bytes-binding')
 meta=answer.get('argv') or {};code=profile['proc_code']
 need(meta.get('prefix')==['/usr/bin/python3','-I','-B','-c'] and meta.get('code_sha256')==code['sha256'] and meta.get('code_bytes')==code['bytes'] and meta.get('challenge_bytes')==48 and isinstance(meta.get('challenge_sha256'),str) and len(meta['challenge_sha256'])==64 and meta.get('caller_pid')==1060806 and meta.get('caller_starttime')=='80309560','exact-PROC_CODE-caller-metadata')
 need(rc or answer['stderr']['bytes'] or answer['stdout']['bytes']>profile['root_command_limit_bytes'],'actual-source-failure-condition')
 return answer
''' +s[z:]
s=s.replace("need(len(stdout)<=1<<20 and len(stderr)<=1<<20,'debugger-output-bound')", "need(len(stdout)<=profile['limits']['gdb_stdout_bytes'] and len(stderr)<=profile['limits']['gdb_stderr_bytes'],'debugger-output-bound')")
s=s.replace('PASS_EXACT_OWNED_QUARANTINE_ERROR_READ','PASS_EXACT_OWNED_ROOT_COMMAND_RESULT_READ')
new=root/'exact_root_result_guard_runner.py';compile(s,str(new),'exec');new.write_text(s);(root/'runner.patch').write_text(''.join(difflib.unified_diff(old.read_text().splitlines(True),s.splitlines(True),fromfile=str(old),tofile=str(new))))
print('profile',ref(p));print('runner',ref(new));print('proc',profile['proc_code'])
