"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One owned shared record: exclusive archival, revalidation and one exact unlink.
No runtime action on import. Normal three-record/CID postflight is not fabricated.
"""
from pathlib import Path
import hashlib,json,os,stat,types
class Refusal(RuntimeError):pass
def need(ok,message):
 if not ok:raise Refusal(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def strict(raw):
 def pairs(items):
  result={}
  for key,value in items:need(key not in result,'duplicate JSON key');result[key]=value
  return result
 return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(Refusal('nonfinite JSON')))
def duplicate_pairs(items):
 need(len(dict(items))==len(items),'duplicate JSON key')
 return strict(json.dumps(dict(items)))
guard=types.SimpleNamespace(_duplicates=duplicate_pairs)
def safe_path(value, directory=True):
    path = Path(value)
    need(path.is_absolute() and str(path) == value and '..' not in path.parts,
         'canonical absolute path required')
    need(all(not p.is_symlink() for p in (path, *path.parents)), 'symlink path refused')
    if directory:
        need(path.is_dir(), 'existing directory required')
    else:
        need(path.is_file() and stat.S_ISREG(path.stat().st_mode), 'regular file required')
    return path

def record_snapshot(path, expected):
    safe_path(str(path), False)
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        need(before.st_nlink == 1 and stat.S_IMODE(before.st_mode) == 0o600 and
             before.st_uid == before.st_gid == 1000 and before.st_size <= 1 << 20,
             'owned record shape differs')
        raw = b''
        while len(raw) <= before.st_size:
            block = os.read(fd, min(65536, before.st_size + 1 - len(raw)))
            if not block:
                break
            raw += block
        after = os.fstat(fd)
        linked = path.lstat()
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink',
                  'st_size', 'st_mtime_ns', 'st_ctime_ns')
        need(all(getattr(before, k) == getattr(after, k) == getattr(linked, k) for k in fields) and
             len(raw) == before.st_size and json.loads(raw, object_pairs_hook=guard._duplicates) == expected,
             'owned record bytes/identity raced')
        need(expected.get('pid') == 867329 and expected.get('starttime') == '76715862',
             'exact independently retired original failed owner required')
        if 'inode' in expected:
            need(expected['inode'] == before.st_ino and expected.get('device', expected.get('dev')) == before.st_dev,
                 'owned exclusion inode differs')
        identity = dict(path=str(path), device=before.st_dev, inode=before.st_ino,
                        size=before.st_size, sha256=sha(raw), record=expected)
        return identity, raw
    finally:
        os.close(fd)

def _request_hash(request):
    return hashlib.sha256(json.dumps(request, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
STAT_FIELDS=('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
def fullstat(meta):return {key:getattr(meta,key) for key in STAT_FIELDS}
def bind_node(path,expected_record,expected_identity):
 before=path.lstat();identity,raw=record_snapshot(path,expected_record);after=path.lstat()
 need(fullstat(before)==fullstat(after),'owned shared stat changed during snapshot')
 row=dict(path=str(path),device=after.st_dev,inode=after.st_ino,size=after.st_size,mode=stat.S_IMODE(after.st_mode),uid=after.st_uid,gid=after.st_gid,nlink=after.st_nlink,sha256=sha(raw))
 need(row==expected_identity,'exact original shared node/bytes differ')
 return row,raw,fullstat(after),identity

def archive_and_unlink_one(path,expected_record,expected_identity,archive,safety,publish,mark_unlink_attempt,archive_parent_identity):
 """Caller holds permanent27:4; cooperative publishers are fenced by it.
 Copy before release, never rename between scratch and HOST. Every uncertain
 unlink response consumes the sole unlink budget; caller retains quarantine.
 """
 safety()
 row,raw,original_stat,snapshot=bind_node(path,expected_record,expected_identity)
 rawpath=archive/'shared.record.raw';statpath=archive/'shared.record.stat.json';manifestpath=archive/'shared.archive-manifest.json'
 publish(rawpath,raw)
 document={'original_identity':row,'original_stat':original_stat,'record_snapshot':snapshot,'raw_sha256':sha(raw),'raw_bytes':len(raw)}
 encoded=(json.dumps(document,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode();publish(statpath,encoded)
 need(rawpath.read_bytes()==raw and statpath.read_bytes()==encoded,'exclusive HOST raw/stat archive reread differs')
 manifest={'schema':'mckernel.current290.shared-only-record-archive.v1','original_record_path':str(path),'original_identity':row,'original_stat':original_stat,'raw_archive':{'path':str(rawpath),'sha256':sha(raw),'bytes':len(raw)},'stat_archive':{'path':str(statpath),'sha256':sha(encoded),'bytes':len(encoded)},'original_record':expected_record,'failed_owner_status_preserved':True}
 sealed=(json.dumps(manifest,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode();publish(manifestpath,sealed)
 need(manifestpath.read_bytes()==sealed,'exclusive HOST archive manifest reread differs')
 # Existing publish fsyncs every file and its directory. Require an additional
 # explicit archive-directory fsync before any shared-node release.
 # Pin the existing HOST parent and the exact newly created archive child.
 # File/child fsync alone cannot make the child's parent directory entry durable.
 safe_path(str(archive.parent))
 pfd=os.open(str(archive.parent),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
 afd=None
 def parent_identity(meta):return dict(path=str(archive.parent),device=meta.st_dev,inode=meta.st_ino,mode=stat.S_IMODE(meta.st_mode),uid=meta.st_uid,gid=meta.st_gid)
 try:
  parent_before=os.fstat(pfd)
  need(parent_identity(parent_before)==archive_parent_identity and parent_identity(archive.parent.lstat())==archive_parent_identity,'pinned existing archive parent identity differs')
  afd=os.open(archive.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=pfd)
  child_before=fullstat(os.fstat(afd));named_before=fullstat(os.stat(archive.name,dir_fd=pfd,follow_symlinks=False))
  need(child_before==named_before and stat.S_ISDIR(child_before['st_mode']) and child_before['st_dev']==archive_parent_identity['device'] and child_before['st_uid']==child_before['st_gid']==1000 and stat.S_IMODE(child_before['st_mode'])==0o700,'pinned archive child identity differs')
  os.fsync(afd)
  os.fsync(pfd)  # Must succeed before the attempted marker or sole scratch unlink.
  child_after=fullstat(os.fstat(afd));named_after=fullstat(os.stat(archive.name,dir_fd=pfd,follow_symlinks=False))
  need(parent_identity(os.fstat(pfd))==archive_parent_identity and parent_identity(archive.parent.lstat())==archive_parent_identity and child_after==child_before==named_after,'archive parent/child identity changed across parent fsync')
  parent_durability={'parent_identity':archive_parent_identity,'child_before':child_before,'child_after':child_after,'parent_fsync_completed_before_unlink':True}
 finally:
  if afd is not None:os.close(afd)
  os.close(pfd)
 safety()
 again,againraw,againstat,_=bind_node(path,expected_record,expected_identity)
 need(again==row and againraw==raw and againstat==original_stat,'shared record changed after archival')
 need(rawpath.read_bytes()==raw and statpath.read_bytes()==encoded and manifestpath.read_bytes()==sealed,'sealed archive changed before unlink')
 parent=os.open(str(path.parent),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
 try:
  parentmeta=os.fstat(parent);namedparent=path.parent.lstat()
  need((parentmeta.st_dev,parentmeta.st_ino)==(namedparent.st_dev,namedparent.st_ino),'scratch parent directory differs')
  need(fullstat(os.stat(path.name,dir_fd=parent,follow_symlinks=False))==original_stat,'same owned node differs immediately before unlink')
  mark_unlink_attempt()  # Must precede syscall; uncertain response is never retried.
  os.unlink(path.name,dir_fd=parent)
  os.fsync(parent)
  need(not os.path.lexists(path),'owned shared record remains after release')
 finally:os.close(parent)
 return {'archive_manifest':manifest,'archive_manifest_sha256':sha(sealed),'raw_archive_sha256':sha(raw),'stat_archive_sha256':sha(encoded),'active_shared_absent':True,'unlink_budget_consumed':1,'archive_parent_durability':parent_durability}
