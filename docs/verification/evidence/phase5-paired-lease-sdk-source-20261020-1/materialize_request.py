"""One concrete source-only nsd materialization; never compiles or runs an owner."""
from pathlib import Path
import argparse,hashlib,json,os,stat
F=Path(__file__).resolve().parent

def load(p):return json.loads(p.read_text())
def rawref(r):
 p=Path(r['path']);a=p.lstat();assert stat.S_ISREG(a.st_mode) and a.st_nlink==1
 with p.open('rb') as f:b=f.read()
 z=p.lstat();fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns');assert all(getattr(a,k)==getattr(z,k) for k in fields)
 assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'];return b

def node(p):
 s=p.stat();return dict(path=str(p),device=s.st_dev,inode=s.st_ino,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid)

def main():
 a=argparse.ArgumentParser();g=a.add_mutually_exclusive_group(required=True);g.add_argument('--check-only',action='store_true');g.add_argument('--materialize',action='store_true');args=a.parse_args()
 index=load(F/'CAPSULE-AND-MATERIALIZATION-INDEX.json');q=load(F/'request-TEMPLATE.json');rows=load(F/'materialization-files.json');srcmap=load(F/'source-sha256.json');c=F/'capsule'
 assert len(srcmap)==11 and len(rows)==81
 for n,h in srcmap.items():assert hashlib.sha256((c/n).read_bytes()).hexdigest()==h
 for k in ('owner','driver','preparation','request_template','materialization_files','source_map'):rawref(index[k])
 p=load(Path(q['preparation']['path']));assert p['host_fork_adoption_opt_in'] is True
 assert len(p['closure'])==66 and p['source_candidate_sha']=='50557b7836fd42a49ad3f356e75fa5aeb49dce71b27657dc19e721d4dc89e263'
 assert sum(r['bytes'] for r in p['closure'])==p['closure_bytes']==1311488
 roots=[Path(q[k]) for k in ('candidate_root','input_root','owner_evidence_root')];assert all(not os.path.lexists(x) for x in roots)
 assert not Path(q['request_path']).exists() and q['candidate_identity'] is None and q['input_identity'] is None
 assert node(Path(q['basis_identity']['path']))==q['basis_identity']
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==q['boot_id']
 for r in rows:
  d=Path(r['destination']);assert any(x in d.parents for x in roots[:2]);rawref(r['source'])
 if args.check_only:
  print(json.dumps(dict(status='PASS_SOURCE_BINDINGS_ONLY_NO_MATERIALIZATION',source_files=66,capsule_sources=11,copy_rows=len(rows),namespace_absent=True)));return
 # Unprivileged operation requiring its separate admitted source-materialization command.
 for r in roots[:2]:r.mkdir(mode=0o700)
 for n in ('modules','home','tmp'):(roots[0]/n).mkdir(mode=0o700)
 for r in rows:
  d=Path(r['destination']);d.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
  with d.open('xb') as out:out.write(rawref(r['source']))
 q['candidate_identity']=node(roots[0]);q['input_identity']=node(roots[1]);out=Path(q['request_path'])
 with out.open('x') as f:json.dump(q,f,sort_keys=True,indent=2);f.write('\n')
 b=out.read_bytes();print(json.dumps(dict(status='MATERIALIZED_SOURCE_REQUEST_ONLY_NO_BUILD',request=dict(path=str(out),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b)),source_files=66)))
if __name__=='__main__':main()
