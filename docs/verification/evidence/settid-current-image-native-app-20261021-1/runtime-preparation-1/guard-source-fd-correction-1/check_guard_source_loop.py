"""Actual guard source reader and its production loop only; no root or runtime.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
from pathlib import Path
import copy,hashlib,importlib.util,json,os,socket,subprocess,sys
D=Path(__file__).resolve().parent

def ref(path):
 path=Path(path);raw=path.read_bytes();return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def forbidden(*a,**k):raise AssertionError('no process/socket/root/workload in source-loop check')
def main():
 subprocess.Popen=forbidden;socket.socket=forbidden;os.execve=forbidden
 pins=json.loads((D/'CHECK-INPUT-PINS.json').read_bytes())
 for row in pins:assert ref(row['path'])==row
 c=json.loads((D/'STATIC-NONTEMPORAL-INPUTS.json').read_bytes())
 assert Path(sys.executable).resolve()==Path(c['interpreter']['path']).resolve()
 guard_path=D/'native-packet-1/review_final_threads_release.py'
 spec=importlib.util.spec_from_file_location('actual_source_fd_guard',guard_path);guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
 cfg=json.loads((D/'SOURCE-LOOP-CHECK-CONFIG.json').read_bytes())
 source_map=json.loads((D/'RUNTIME-SOURCE-FD-IDENTITIES.json').read_bytes())
 rows=cfg['runtime_source_refs'];identities=source_map['identities']
 # NonJSON rows are exactly the successor binder's existing source-ref formula;
 # the prototype JSON rows remain genuine prior canonical controls and physical
 # mapping because future successor canonical19 is honestly ungenerated.
 decoder=json.loads((D/'CURRENT-PHYSICAL-DECODER-SOURCE.json').read_bytes())
 expected=c['runtime_source_refs']+[ref(D/'root_manual_snapshot_threads.py'),decoder,ref(D/'root_manual_snapshot_threads.py')]
 assert [r for r in rows if not r['path'].endswith('.json')]==[r for r in expected if not r['path'].endswith('.json')]
 assert set(identities)=={r['path'] for r in expected if not r['path'].endswith('.json')}
 count=guard.check_runtime_sources(cfg)
 assert count==len(rows)==11 and len(identities)==8
 for row in rows:
  if not row['path'].endswith('.json'):
   _,actual,_=guard.read_source(row,identities[row['path']]);assert actual==row
 cases=[dict(case='genuine-eight-source-full-FD-map-and-actual-eleven-row-production-loop',result='PASS')]
 runner=next(r for r in rows if r['path'].endswith('/native_diagnostic_runner.py'));assert identities[runner['path']]['st_nlink']==2
 def refuse(name,fn,label):
  try:fn()
  except ValueError as e:
   assert label in str(e),str(e);cases.append(dict(case=name,result='REFUSED'));return
  raise AssertionError('required refusal not observed: '+name)
 def mapped(name,value):
  p=D/(name+'.fixture-map.json');raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode();p.open('xb').write(raw)
  altered=copy.deepcopy(cfg);altered['runtime_source_fd_identity_map']=ref(p);return altered
 for field,value,name in [('st_nlink',1,'wrong-exact-nlink'),('st_ino',identities[runner['path']]['st_ino']+1,'wrong-source-inode'),('st_mode',identities[runner['path']]['st_mode']^0o100,'wrong-source-mode')]:
  bad=copy.deepcopy(source_map);bad['identities'][runner['path']][field]=value
  refuse(name,lambda badcfg=mapped(name,bad):guard.check_runtime_sources(badcfg),'exact selected source FD identity')
 badcfg=copy.deepcopy(cfg)
 for row in badcfg['runtime_source_refs']:
  if row['path']==runner['path']:row['sha256']='0'*64
 refuse('wrong-source-hash',lambda:guard.check_runtime_sources(badcfg),'runtime source hash/bytes')
 bad=copy.deepcopy(source_map);del bad['identities'][runner['path']]
 refuse('missing-mandatory-source-pin',lambda:guard.check_runtime_sources(mapped('missing-source-pin',bad)),'exact selected runtime source FD map set')
 assert len(cases)==6
 result=dict(status='PASS_ACTUAL_GUARD_READER_AND_FULL_PRODUCTION_SOURCE_LOOP_ONLY',cases=cases,guard=ref(guard_path),source_fd_map=ref(D/'RUNTIME-SOURCE-FD-IDENTITIES.json'),source_loop_config=ref(D/'SOURCE-LOOP-CHECK-CONFIG.json'),selected_unique_nonJSON_sources=8,production_source_rows=11,canonical_source_paths_preserved=True,full_guard_main_executed=False,prototype_JSON_rows='genuine prior canonical controls; successor canonical19 future',source_fetched_proof=None,successor_final19=None,LAST_snapshot=None,runtime_release=False,root_operations=0,guest_runs=0)
 (D/'actual-source-loop-result.json').open('x').write(json.dumps(result,sort_keys=True,indent=2)+'\n')
 print(json.dumps(dict(status=result['status'],cases=6,sources=8,production_rows=11,root_operations=0,guest_runs=0)))
if __name__=='__main__':main()
