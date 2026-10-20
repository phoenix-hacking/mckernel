import hashlib,importlib.util,json,os,socket,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent
calls=[]
def forbidden(*a,**k):calls.append('forbidden');raise AssertionError('no live/process/socket effect')
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 assert os.sched_getaffinity(0)=={7}
 for r in json.loads((P/'PURE-INPUT-PINS.json').read_bytes()):
  data=Path(r['path']).read_bytes();assert len(data)==r['bytes'] and hashlib.sha256(data).hexdigest()==r['sha256']
 subprocess.Popen=forbidden;socket.socket=forbidden;os.execve=forbidden
 m=load('exact_failed_sdk_terminal',P/'root_manual_snapshot_two_cycle_sdk.py');b=json.loads((P/'ACTUAL-TERMINAL-INPUTS.json').read_bytes());t=m.checked(b['physical_review']);m.terminal_joins(t,b)
 try:m.prior.terminal_joins(t,b)
 except m.prior.Refusal as e:assert 'native physical schema/decision' in str(e)
 else:raise AssertionError('old native contract accepted SDK schema')
 assert calls==[]
 d=dict(status='PASS_GENUINE_FAILED_SDK_TERMINAL_JOIN_ONLY',physical=b['physical_review'],positive=1,original_native_schema_refusal=1,forbidden_calls=calls,live_snapshot=False,native_cycles=0)
 with (P/'actual-terminal-result.json').open('x') as f:json.dump(d,f,indent=2);f.write(chr(10))
 print(json.dumps(dict(status=d['status'],positive=1,original_native_schema_refusal=1,live_snapshot=False)))
if __name__=='__main__':main()
