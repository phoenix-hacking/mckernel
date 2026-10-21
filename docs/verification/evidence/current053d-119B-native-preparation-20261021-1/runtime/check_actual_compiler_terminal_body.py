"""One actual retained compiler producer-body comparison, no root/native operation."""
from pathlib import Path
import copy,importlib.util,json,os,socket,subprocess
D=Path(__file__).resolve().parent
def main():
 def forbidden(*a,**k):raise AssertionError('no child/socket/root operation')
 subprocess.Popen=forbidden;os.execve=forbidden;socket.socket=forbidden
 data=json.loads((D/'ACTUAL-COMPILER-LATEST-NATIVE-ANCESTOR-AND-119B-NORM-DATA-1.json').read_bytes())
 path=D/'root_manual_snapshot_threads.compiler-latest-UNBOUND.py';spec=importlib.util.spec_from_file_location('actual_compiler_join_body',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 rows={k:m.checked(v) for k,v in data['compiler_producer_refs'].items()}
 def apply(x):return m.compiler_producer_join(x['receipt'],x['postflight'],x['status'],x['archive'],x['child'],x['direct_join'],data['physical_predecessor']['filesystem_uuid'])
 assert apply(rows)==data['physical_predecessor']
 bad=copy.deepcopy(rows);bad['postflight']['all_clients_reaped']=False
 try:apply(bad)
 except m.Refusal as e:assert str(e)=='complete actual compiler postflight'
 else:raise AssertionError('unreaped compiler must refuse')
 bad=copy.deepcopy(rows);bad['child']['start']+=1
 try:apply(bad)
 except m.Refusal as e:assert str(e)=='exact compiler owned OS child birth/argv'
 else:raise AssertionError('wrong owner birth must refuse')
 print(json.dumps(dict(status='PASS_ACTUAL_COMPILER_PRODUCER_JOIN_POSITIVE_AND_TWO_REFUSALS_ONLY',cases=3,guest_runs=0,root_operations=0)))
if __name__=='__main__':main()
