"""Actual complete stage/typed/terminal records only; no live/root collection."""
import hashlib,importlib.util,json,os,socket,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent
calls=[]
def forbidden(*a,**k):calls.append('forbidden');raise AssertionError('no process/socket/exec factory in actual input validation')
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def main():
 for r in json.loads((P/'PURE-VALIDATION-INPUT-PINS.json').read_bytes()):
  if ref(r['path'])!=r:raise ValueError('exact pure validation source/data pin '+r['path'])
 subprocess.Popen=forbidden;socket.socket=forbidden;os.execve=forbidden
 m=load('two_complete_cycle_actual_snapshot_inputs',P/'root_manual_snapshot_two_cycle.py');b=json.loads((P/'ACTUAL-VALIDATOR-INPUTS.json').read_bytes())
 case,owner=m.validate_case_roles(b)
 terminal=m.checked3(b['physical_review']);m.terminal_joins(terminal,b)
 # The genuine current three-round receipt must be refused by the original
 # literal two-round contract. No fabricated receipt fields or approval shape.
 old=load('unchanged_prior_two_round_terminal_contract',m.ENGINE)
 try:old.terminal_joins(terminal,b)
 except old.Refusal as e:
  if 'native physical schema/decision' not in str(e):raise
 else:raise AssertionError('original different-case terminal contract unexpectedly accepted')
 if calls:raise AssertionError('forbidden actual factory called')
 result=dict(status='PASS_ACTUAL_COMPLETE_CASE_AND_TERMINAL_INPUT_VALIDATORS_ONLY',case=ref(b['complete_case']['path']),physical=ref(b['physical_review']['path']),producer=ref(P/'root_manual_snapshot_two_cycle.py'),input_binding=ref(P/'ACTUAL-VALIDATOR-INPUTS.json'),actual_stage_and_typed_join=1,actual_current_terminal_join=1,original_different_schema_refusal=1,forbidden_factory_calls=calls,whole_runtime_source_count=case['runtime_source_count'],native_cycles=0,root_operations=0,live_snapshot_collected=False)
 with (P/'actual-pure-validation-result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({k:result[k] for k in ('status','actual_stage_and_typed_join','actual_current_terminal_join','original_different_schema_refusal','native_cycles')}))
if __name__=='__main__':main()
