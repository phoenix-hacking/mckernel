#!/usr/bin/env python3
"""Bind this one prepared probe request after root prepares its fresh work root."""
import argparse,hashlib,json,os,stat
from pathlib import Path
E=Path(__file__).resolve().parent

def need(ok,s):
    if not ok:raise ValueError(s)
def node(p):
    need(p.is_dir() and p.resolve()==p,'canonical directory');s=p.stat();return dict(path=str(p),device=s.st_dev,inode=s.st_ino,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid)
def finalize(draft_sha):
    p=E/'request-draft.json';raw=p.read_bytes();need(hashlib.sha256(raw).hexdigest()==draft_sha,'draft identity');d=json.loads(raw);need(d['status']=='NONRUNNABLE_PENDING_ROOT_FRESH_IDENTITIES_AND_EXACT_REVIEW','draft status');r=d['request']
    root=Path('/home/holden/mckernel-work/scratch');work=Path(r['candidate_root']);need(work.parent==root and work.name=='nsd-c-'+r['nonce'],'one fixed work root')
    identity=node(work);need(identity['device']==1828 and identity['mode']==0o700 and identity['uid']==identity['gid']==1000,'fresh work identity')
    need({x.name for x in work.iterdir()}=={'home','tmp'} and all((work/n).is_dir() and not any((work/n).iterdir()) for n in ('home','tmp')),'empty probe work layout')
    r['candidate_identity']=identity;r['basis_identity']=node(root/'mckernel-exact-candidate-scratch-22-authority3-output');r['input_identity']=node(Path(r['input_root']))
    prep=Path(r['preparation']['path']);need(hashlib.sha256(prep.read_bytes()).hexdigest()==r['preparation']['sha256'],'preparation hash');m=json.loads(prep.read_text());need(r['input_identity']==m['source_root_identity'],'source capsule identity')
    for name,row in m['source_rows'].items():
        f=Path(r['input_root'])/name;s=f.lstat();need(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and s.st_size==row['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==row['sha256'],'exact two source files')
    need({x.name for x in Path(r['input_root']).iterdir()}=={'probe.py','Makefile'},'source capsule names')
    need(not Path(r['owner_evidence_root']).exists(),'fresh evidence namespace');r['boot_id']=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    target=Path(r['request_path']);need(target==E/'request.json' and not target.exists(),'one fresh request output');data=(json.dumps(r,indent=2)+'\n').encode();fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
    with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    return dict(path=str(target),sha256=hashlib.sha256(data).hexdigest(),execution_release=False)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--draft-sha256',required=True);a=p.parse_args();print(json.dumps(finalize(a.draft_sha256)))
if __name__=='__main__':main()
