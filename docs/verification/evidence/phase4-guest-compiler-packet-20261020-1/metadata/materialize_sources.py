"""Ordinary source-only preparation; requires dispatcher CPU6 admission."""
from pathlib import Path
import hashlib,json,os,shutil,posixpath
R=Path(__file__).resolve().parent

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def normalized_relatives(rows):
    normalized=[];seen=set()
    for row in rows:
        value=row['relative']
        assert isinstance(value,str) and value and '\x00' not in value
        relative=Path(posixpath.normpath(value))
        assert relative.parts and not relative.is_absolute() and '..' not in relative.parts
        key=relative.as_posix()
        assert key not in seen,'normalized destination collision: '+key
        seen.add(key);normalized.append(relative)
    return normalized

def main():
    plan=json.loads((R/'source-manifest.json').read_text())
    relatives=normalized_relatives(plan['rows'])
    target=R/'materialized-source'
    assert not target.exists(),'fresh source target required; preserve any failed materialization'
    target.mkdir(mode=0o700)
    for row,relative in zip(plan['rows'],relatives):
        original=Path(row['origin'])
        assert original.is_file() and not original.is_symlink()
        assert original.stat().st_size==row['bytes'] and digest(original)==row['sha256']
        destination=target/relative;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(original,destination)
        assert destination.stat().st_size==row['bytes'] and digest(destination)==row['sha256']
    work=R/'work';work.mkdir(mode=0o700)
    for name in ('output','home','tmp'):(work/name).mkdir(mode=0o700)
    result={'status':'SOURCE_MATERIALIZED_ONLY','source_identity':plan['source_identity'],'count':len(plan['rows']),
            'compiled':False,'image_or_guest_acceptance':False,'atime_excluded':True}
    with (R/'materialization-result.json').open('x') as out:json.dump(result,out,sort_keys=True);out.write('\n');out.flush();os.fsync(out.fileno())
    print(json.dumps({'status':result['status'],'count':result['count']}))
if __name__=='__main__':main()
