"""Finite future 14-file candidate staging. Not released by preparation success."""
from pathlib import Path
import hashlib,json,os,stat
import native_running_external_modules_owner as owner
P=Path(__file__).absolute().parent
PLAN=P/'materialization-proposal.json'
def digest(raw):return hashlib.sha256(raw).hexdigest()
def validate_inputs(plan):
 rows=plan['files'];owner.need(len(rows)==17 and len({r['source'] for r in rows})==17,'exact17 existing data inputs')
 for row in rows:
  path=owner.safe_path(row['source'],False);meta=path.lstat()
  owner.need(meta.st_dev==1828 and meta.st_nlink==1 and meta.st_uid==meta.st_gid==1000,'input identity/type/device')
  fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
  with os.fdopen(fd,'rb') as f:
   before=os.fstat(f.fileno());raw=f.read();after=os.fstat(f.fileno())
  owner.need(before==after and before==meta and digest(raw)==row['sha256'] and len(raw)==row['bytes'],'fixed17 input bytes drift')
 return rows

def execute(release_path,release_sha):
 # No release with this status is supplied by this preparation packet.
 release=owner.bound(dict(path=str(release_path),sha256=release_sha))
 owner.need(release.get('status')=='PASS_ORDINARY_MATERIALIZATION' and release.get('implementation_ownership') is False and release.get('reviewer'),'independent ordinary staging release required')
 owner.need(release.get('materializer_sha256')==digest(Path(__file__).read_bytes()) and release.get('plan_sha256')==digest(PLAN.read_bytes()),'exact staging source/plan release')
 owner.need(os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000,'ordinary holden only')
 plan=json.loads(PLAN.read_text());validate_inputs(plan)
 target=Path(plan['candidate']);owner.need(target.parent==owner.HOST_ROOT and target.name=='nsd-c-'+plan['nonce'] and not os.path.lexists(target),'fresh host candidate namespace')
 owner.host_storage_admission()
 owner.host.measure(str(owner.HOST_ROOT),str(owner.ROOT),18320719872,13488881664)
 parent=os.open(owner.HOST_ROOT,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
 try:
  owner.need(os.fstat(parent).st_ino==owner.HOST_ROOT_NODE['inode'] and os.fstat(parent).st_dev==owner.HOST_DEVICE,'host parent FD differs')
  os.mkdir(target.name,0o700,dir_fd=parent)
  fd=os.open(target.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=parent)
  try:
   for name in ('modules','home','tmp'):os.mkdir(name,0o700,dir_fd=fd)
   mod=os.open('modules',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd)
   try:
    os.mkdir('abi',0o700,dir_fd=mod)
    for row in plan['files']:
     if row['role']!='module_sources':continue
     rel=Path(row['relative']);owner.need(not rel.is_absolute() and '..' not in rel.parts and len(rel.parts)<=2 and (len(rel.parts)==1 or rel.parts[0]=='abi'),'fixed source path escape')
     raw=owner.safe_path(row['source'],False).read_bytes();owner.need(digest(raw)==row['sha256'],'source changed before write')
     destdir=mod if len(rel.parts)==1 else os.open('abi',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=mod)
     try:
      out=os.open(rel.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=destdir)
      with os.fdopen(out,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
     finally:
      if destdir!=mod:os.close(destdir)
   finally:os.close(mod)
  finally:os.close(fd)
 finally:os.close(parent)
 # All failures preserve partial candidate for review. Never remove/retry it.
 return dict(status='MATERIALIZED_ONLY_NOT_EXECUTION',candidate_identity=owner.node(target),inputs_reused=3,sources_staged=14)
if __name__=='__main__':
 import argparse
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--release',required=True);a.add_argument('--release-sha256',required=True);args=a.parse_args()
 print(json.dumps(execute(Path(args.release),args.release_sha256),sort_keys=True))
