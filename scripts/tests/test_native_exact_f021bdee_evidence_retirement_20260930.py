import importlib.util, os
from pathlib import Path
import pytest
PACKET=Path(__file__).parents[2]/'docs/verification/evidence/native-exact-f021bdee-evidence-retirement-20260930.py'
spec=importlib.util.spec_from_file_location('f021_retire',PACKET); M=importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
def test_frozen_artifacts_and_scope():
 t=PACKET.read_text(); assert M.ARCHIVE_ID=='66306:47496368' and M.MAP_ID=='66306:47496380'; assert M.ARCHIVE_SHA in t and M.MAP_SHA in t; assert 'PROTECTED' in t and '--retire' in t
def test_source_identity_guard():
 original=M.SOURCE_ID; M.SOURCE_ID='wrong'
 try:
  with pytest.raises(SystemExit): M.guard()
 finally: M.SOURCE_ID=original
def test_symlink_is_inert_bottom_up_fixture(tmp_path,monkeypatch):
 root=tmp_path/'e'; root.mkdir(); (root/'target').write_text('x'); (root/'link').symlink_to('target'); monkeypatch.setattr(M,'SOURCE',root); monkeypatch.setattr(M,'SOURCE_ID',f'{root.stat().st_dev}:{root.stat().st_ino}'); monkeypatch.setattr(M,'guard',lambda:True); rows=M.snapshot(); monkeypatch.setattr(M,'verify',lambda:{'members':rows}); monkeypatch.setattr(M,'RESULT',tmp_path/'result')
 M.retire(); assert not root.exists() and not (tmp_path/'target').exists()
def test_mutation_rejected_before_deletion(monkeypatch):
 monkeypatch.setattr(M,'guard',lambda: (_ for _ in ()).throw(SystemExit('changed')))
 with pytest.raises(SystemExit,match='changed'): M.verify()

def test_live_identity_replacement_rejected_before_reservation(tmp_path,monkeypatch):
 root=tmp_path/'e'; root.mkdir(); (root/'x').write_text('x'); monkeypatch.setattr(M,'SOURCE',root); monkeypatch.setattr(M,'SOURCE_ID',f'{root.stat().st_dev}:{root.stat().st_ino}'); monkeypatch.setattr(M,'guard',lambda:True); monkeypatch.setattr(M,'verify',lambda:{'members':[]}); first=M.live_identity(); changed=dict(first); changed['x']=dict(changed['x']); changed['x']['ino']+=1; monkeypatch.setattr(M,'live_identity',iter([first,changed]).__next__); monkeypatch.setattr(M,'RESULT',tmp_path/'result')
 with pytest.raises(SystemExit,match='entry changed'): M.retire()
 assert not (tmp_path/'result').exists() and root.exists()

def test_result_collision_blocks_delete(tmp_path,monkeypatch):
 root=tmp_path/'e'; root.mkdir(); monkeypatch.setattr(M,'SOURCE',root); monkeypatch.setattr(M,'SOURCE_ID',f'{root.stat().st_dev}:{root.stat().st_ino}'); monkeypatch.setattr(M,'guard',lambda:True); monkeypatch.setattr(M,'verify',lambda:{'members':[]}); monkeypatch.setattr(M,'live_identity',lambda:{}); result=tmp_path/'result'; result.write_text('existing'); monkeypatch.setattr(M,'RESULT',result)
 with pytest.raises(SystemExit,match='collision'): M.retire()
 assert result.read_text()=='existing' and root.exists()

def test_result_short_write_loop(tmp_path,monkeypatch):
 monkeypatch.setattr(M,'RESULT',tmp_path/'result'); real=M.os.write; calls=[]
 def short(fd,data): calls.append(len(data)); return real(fd,data[:max(1,len(data)//2)])
 monkeypatch.setattr(M.os,'write',short); path,_=M.write_temp_result({'status':'RETIRE_PREPARED'}); assert path.exists() and len(calls)>1; path.unlink()

def test_container_parser_rejects_missing_wrong_oom_running_pid_exit():
 good={'Name':'/'+M.CONTAINER['name'],'State':{'Running':False,'OOMKilled':False,'Pid':0,'ExitCode':1,'Status':'exited'}}
 M.validate_container_json(good)
 for key,value in [('Name','/wrong'),('OOMKilled',True),('Running',True),('Pid',9),('ExitCode',2),('Status','running')]:
  d={'Name':'/'+M.CONTAINER['name'],'State':{'Running':False,'OOMKilled':False,'Pid':0,'ExitCode':1,'Status':'exited'}}
  (d.__setitem__('Name',value) if key=='Name' else d['State'].__setitem__(key,value))
  with pytest.raises(SystemExit): M.validate_container_json(d)

def test_fixed_payloads_are_same_length_and_pass_is_parseable():
 a,b=M.fixed_payloads({'status':'RETIRE_PREPARED'},{'status':'RETIRE_PASS','members':2})
 assert len(a)==len(b) and __import__('json').loads(b.rstrip())['status']=='RETIRE_PASS'

def test_nested_directory_identity_census(tmp_path,monkeypatch):
 root=tmp_path/'e'; (root/'a/b').mkdir(parents=True); (root/'a/b/f').write_text('x'); monkeypatch.setattr(M,'SOURCE',root); rows=M.live_identity(); assert 'a' in rows and 'a/b' in rows and 'a/b/f' in rows

def test_root_identity_change_is_rejected(monkeypatch):
 monkeypatch.setattr(M,'SOURCE_ID','wrong')
 with pytest.raises(SystemExit,match='source identity'): M.guard()

def test_prepared_status_is_nonpass():
 a,_=M.fixed_payloads({'status':'RETIRE_PREPARED'},{'status':'RETIRE_PASS'}); assert __import__('json').loads(a.rstrip())['status']=='RETIRE_PREPARED'

def setup_retire(tmp_path,monkeypatch):
 root=tmp_path/'e'; (root/'nested/deep').mkdir(parents=True); (root/'nested/deep'/'file').write_text('x'); (root/'nested'/'link').symlink_to('deep/file')
 monkeypatch.setattr(M,'SOURCE',root); monkeypatch.setattr(M,'SOURCE_ID',f'{root.stat().st_dev}:{root.stat().st_ino}'); monkeypatch.setattr(M,'guard',lambda:True); monkeypatch.setattr(M,'verify',lambda:{'members':[]}); monkeypatch.setattr(M,'RESULT',tmp_path/'result'); return root

def test_real_nested_retire_pass_json_and_fsync(monkeypatch,tmp_path):
 root=setup_retire(tmp_path,monkeypatch); original=M.os.fsync; calls=[]; monkeypatch.setattr(M.os,'fsync',lambda fd:(calls.append(fd),original(fd))[1]); M.retire(); assert not root.exists(); data=__import__('json').loads(M.RESULT.read_text()); assert data['status']=='RETIRE_PASS' and calls

def test_unlink_failure_leaves_prepared_and_partial_source(monkeypatch,tmp_path):
 root=setup_retire(tmp_path,monkeypatch); original=M.os.unlink; count=[0]
 def fail_after_one(path,*a,**kw):
  count[0]+=1
  if count[0]==2: raise OSError('injected unlink')
  return original(path,*a,**kw)
 monkeypatch.setattr(M.os,'unlink',fail_after_one)
 with pytest.raises(OSError,match='injected'): M.retire()
 data=__import__('json').loads(M.RESULT.read_text()); assert data['status']=='RETIRE_PREPARED' and root.exists() and count[0]>=2

def test_root_replacement_after_reservation_rejected(monkeypatch,tmp_path):
 root=setup_retire(tmp_path,monkeypatch); original=M.os.open; swapped=[False]
 def swap(name,flags,*a,**kw):
  if name==root.name and kw.get('dir_fd') is not None and not swapped[0]:
   swapped[0]=True; moved=root.with_name('old'); root.rename(moved); root.mkdir()
  return original(name,flags,*a,**kw)
 monkeypatch.setattr(M.os,'open',swap)
 with pytest.raises(SystemExit,match='root fd replacement'): M.retire()
 assert __import__('json').loads(M.RESULT.read_text())['status']=='RETIRE_PREPARED' and root.exists()

def test_result_replacement_before_pass_rejected(monkeypatch,tmp_path):
 root=setup_retire(tmp_path,monkeypatch); original=M.os.lstat; replaced=[False]
 def replace(path,*a,**kw):
  p=Path(path)
  if p==M.RESULT and not replaced[0] and p.exists():
   replaced[0]=True; p.unlink(); p.write_text('{"status":"ATTACKER"}')
  return original(path,*a,**kw)
 monkeypatch.setattr(M.os,'lstat',replace)
 with pytest.raises(SystemExit,match='reservation replaced'): M.retire()
 assert replaced[0] and M.RESULT.read_text()=='{"status":"ATTACKER"}'

def test_result_inode_is_canonical_and_not_temp_alias(monkeypatch,tmp_path):
 root=setup_retire(tmp_path,monkeypatch); M.retire(); st=M.RESULT.stat(); assert st.st_nlink==1 and st.st_size>0

def test_docker_inspect_argv_uses_full_id_without_invalid_flag(monkeypatch):
 calls=[]
 class P:
  returncode=0; stdout='[{"Name":"/'+M.CONTAINER['name']+'","State":{"Running":false,"OOMKilled":false,"Pid":0,"ExitCode":1,"Status":"exited"}}]'; stderr=''
 def run(argv,**kwargs):
  calls.append(argv)
  if argv[:3]==['sudo','-A','docker']: return P()
  q=P(); q.stdout='SOURCE FSTYPE MAJ:MIN TARGET\n/dev/loop39 ext4 7:39 /home/holden/mckernel-work/scratch\n' if 'findmnt' in argv else ''; return q
 monkeypatch.setattr(M.subprocess,'run',run); monkeypatch.setattr(M,'bound_bytes',lambda *a: b'0'); monkeypatch.setattr(M,'digest',lambda *a:'x'); monkeypatch.setattr(M,'FAILURE_SHA','x')
 M.guard()
 docker=[x for x in calls if x[:3]==['sudo','-A','docker']][0]; assert docker==['sudo','-A','docker','inspect',M.CONTAINER['id']] and '--no-trunc' not in docker

def test_live_file_identity_carries_allocated_bytes(tmp_path,monkeypatch):
 root=tmp_path/'e'; root.mkdir(); p=root/'f'; p.write_bytes(b'x'); monkeypatch.setattr(M,'SOURCE',root); rows=M.live_identity(); assert rows['f']['allocated_bytes']==p.stat().st_blocks*512

def test_allocated_bytes_mismatch_is_detectable():
 row={'allocated_bytes':4096}; changed=dict(row); changed['allocated_bytes']=8192; assert changed!=row

def test_snapshot_file_schema_includes_allocation(tmp_path,monkeypatch):
 root=tmp_path/'e'; root.mkdir(); (root/'f').write_text('x'); monkeypatch.setattr(M,'SOURCE',root); rows=M.snapshot(); row=next(x for x in rows if x['type']=='file'); assert set(row)=={'path','type','mode','uid','gid','mtime_ns','size','sha256','allocated_bytes'}

def test_schema_sets_are_distinct_and_complete():
 text=Path(M.__file__).read_text(); assert "'allocated_bytes'" in text and "'linkname'" in text and 'map member schema' in text
