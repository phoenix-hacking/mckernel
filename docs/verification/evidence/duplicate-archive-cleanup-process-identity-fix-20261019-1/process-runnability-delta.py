#!/usr/bin/python3
"""Affected synthetic stat transitions through real production reader/caller; no live D/I claim."""
import argparse,hashlib,json,os,subprocess,sys,threading
from pathlib import Path
sys.dont_write_bytecode=True
import importlib.util
BASE=Path(__file__).resolve().parent

def load(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def case(out,m,pid,a,b,refusal):
 out.mkdir();proc=out/'proc';proc.mkdir();entry=proc/str(pid);entry.mkdir();task=entry/'task'/str(pid);task.mkdir(parents=True);(task/'ns').mkdir();(task/'fd').mkdir()
 oracle=json.loads((BASE/'all-retained-loop36-view-oracle.json').read_text());v=next(v for v in oracle['distinct_views'] if any(p['pid']==416 for p in v['PIDstart_members']))
 (task/'mountinfo').write_text('\n'.join(v['raw_loop36_rows'])+'\n');(task/'ns/mnt').symlink_to('SYNTHETIC_CANONICAL_NO_ALIAS_AUTHORITY');(task/'stat').symlink_to('/proc/%s/task/%s/stat'%(pid,pid))
 for n,p in [('cwd','/tmp'),('root','/'),('exe','/usr/bin/python3')]: (task/n).symlink_to(p)
 raw=Path('/proc',str(pid),'stat').read_bytes();left,sep,right=raw.rpartition(b') ');fields=right.split()
 def state(c):
  f=fields[:];f[0]=c.encode();return left+sep+b' '.join(f)+b'\n'
 (entry/'stat').write_bytes(state(a));os.mkfifo(task/'maps');errs=[]
 def writer():
  try:
   with (task/'maps').open('w'):(entry/'stat').write_bytes(state(b))
  except BaseException as e:errs.append(repr(e))
 t=threading.Thread(target=writer,daemon=True);t.start();error=None
 try:m.process_census({'rows':[],'target_fds':[],'parent_fds':[]},proc_root=proc,identity_root=proc)
 except BaseException as e:error=repr(e)
 t.join(3);assert not t.is_alive() and not errs,(t.is_alive(),errs)
 ok=(error is None) if refusal is None else error is not None and refusal in error and 'pid='+str(pid) in error
 r={'status':'PASS' if ok else 'FAIL','before':a,'after':b,'expected_refusal':refusal,'error':error,'production_caller':'process_census','production_reader':'proc_identity','synthetic_stat':True,'helper_mocks':False};(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');assert ok,r;return r

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args();out=Path(args.output);out.mkdir(exist_ok=False)
 new=load(BASE/'exact120.py','ordinary_runclass');old=load(BASE/'source-b8f5-RS-only-review-finding/exact120.py','old_rs');child=subprocess.Popen(['/usr/bin/python3','-I','-c','import time; time.sleep(20)'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);results=[];r={}
 try:
  for a in ('D','I'):results.append(case(out/('old-'+a+'-R'),old,child.pid,a,'R','scan/skip state changed'))
  for a,b in (('D','R'),('R','D'),('I','R'),('R','I')):results.append(case(out/(a+'-'+b),new,child.pid,a,b,None))
  for a,b in (('R','T'),('R','t'),('R','P'),('R','Z')):results.append(case(out/(a+'-'+b),new,child.pid,a,b,'terminal classification changed' if b=='Z' else 'scan/skip state changed'))
  r={'status':'PASS_AFFECTED_RUNNABILITY_CALLER_DELTA','cases':results,'source_sha256':hashlib.sha256((BASE/'exact120.py').read_bytes()).hexdigest(),'interpreter':sys.executable,'version':sys.version,'limits':'D/I transitions are synthetic stat inputs only; actual live R/S evidence reused, no original12 or mount suite replay; no historical root4 cause inferred','root_observer_replayed':False,'new_host_census':False}
 finally:
  child.terminate();r['owned_child_returncode']=child.wait(3);r['owned_child_joined']=True;(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps({'status':r['status'],'cases':len(results),'owned_child_joined':True}))
if __name__=='__main__':main()
