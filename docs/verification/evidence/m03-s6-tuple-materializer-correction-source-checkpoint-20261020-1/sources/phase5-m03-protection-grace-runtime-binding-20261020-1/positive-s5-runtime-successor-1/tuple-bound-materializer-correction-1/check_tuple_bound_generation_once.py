"""Four local no-effect vectors for the actual tuple-bound engine entry.
All generation uses a capture-only writer. Prior withdrawn proof is a fixture,
not authority for this unpublished corrected source or real materialization.
"""
from pathlib import Path
import copy,fcntl,hashlib,importlib.util,json,os,socket,subprocess
D=Path(__file__).resolve().parent

def exact(row):
 p=Path(row['path']);raw=p.read_bytes();assert p.lstat().st_mode==row['mode'] and len(raw)==row['size'] and hashlib.sha256(raw).hexdigest()==row['sha256'];return raw

def forbidden(*a,**kw):raise AssertionError('root/process/socket/exec/flock effect forbidden in local materializer fixture')

def main():
 cfg=json.loads((D/'CHECK-INPUTS.json').read_bytes());exact(cfg['candidate']);exact(cfg['prior_withdrawn_fixture_proof'])
 subprocess.Popen=forbidden;socket.socket=forbidden;os.execve=forbidden;fcntl.flock=forbidden
 spec=importlib.util.spec_from_file_location('actual_tuple_bound_materializer_entry',cfg['candidate']['path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 i=m.inputs();proof=cfg['prior_withdrawn_fixture_proof'];captured=[]
 def capture(path,value):
  raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode();captured.append((str(path),copy.deepcopy(value)))
  return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
 before={p:os.path.lexists(p) for p in cfg['forbidden_real_outputs']};assert not any(before.values())
 selected=m.generate(i,proof,capture)
 assert selected['packet']==Path(i['proposal']['static_inputs_template']['path']).parent
 assert [p for p,_ in captured]==[str(p) for p in selected['generated']]
 assert captured[-1][1]['materializer_source']==cfg['candidate']
 assert captured[-1][1]['materializer_argv_template'][3]==cfg['candidate']['path']
 assert captured[0][1]['binding']==i['static']['binding']
 results=[dict(vector='genuine_current_tuple_derives_packet6_actual_engine_body',prospective_outputs=[p for p,_ in captured],captured_writes=len(captured),fixture_only=True)]
 for name in ['stale_packet4','changed_parent','output_ref_collision']:
  wrong=copy.deepcopy(i);attempted=[]
  if name=='stale_packet4':wrong['proposal']['static_inputs_template']=wrong['cfg']['prior_Q4_static_inputs']
  elif name=='changed_parent':wrong['static']['binding']['attempt_parent']+='/wrong-parent'
  else:wrong['proposal']['final19_outputs'][0]=wrong['proposal']['static_inputs_template']['path']
  def must_not_write(path,value):attempted.append(str(path));raise AssertionError('negative reached outputwriter')
  try:m.generate(wrong,proof,must_not_write)
  except (AssertionError,ValueError,KeyError,FileNotFoundError) as error:
   assert not attempted;results.append(dict(vector=name,refused_before_writes=True,error=type(error).__name__))
  else:raise AssertionError(name+' accepted')
 assert {p:os.path.lexists(p) for p in cfg['forbidden_real_outputs']}==before
 assert exact(cfg['candidate']) and exact(cfg['original_engine'])
 O=D/'fixture-result-1';assert not os.path.lexists(O);O.mkdir(mode=0o700)
 result=dict(status='PASS',fixture_only=True,new_source_fetched_proof_available=False,real_DATA_materialization=False,prior_proof_role='Genuine withdrawn313bytes used ONLY in no-effect functional fixture; not candidatepublication/executionauthority',candidate=cfg['candidate'],original_engine=cfg['original_engine'],vectors=results,actual_engine_generation_calls=1,root_operations=0,real_output_writes=0,guest_runs=0)
 with (O/'RESULT.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps(dict(status='PASS',fixture_only=True,vectors=len(results),actual_engine_generation_calls=1,real_output_writes=0,guest_runs=0)))
if __name__=='__main__':main()
