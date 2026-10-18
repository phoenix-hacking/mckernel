"""Exact recorded GNU make probe evidence, shared by owner and proof exporter."""
import hashlib,json,os,re,stat
from pathlib import Path
IMAGE='sha256:0f8ad280e47d76b23554de4aec411752e1f779f9b2fc7fece6b0b3375dc9775d'
ARGV=['/usr/bin/make','--jobserver-style=pipe','-j2','-f','/probe/Makefile','all']
CAP=1024*1024

def need(ok,s):
    if not ok:raise ValueError(s)
def digest(data):return hashlib.sha256(data).hexdigest()
def read(path,cap=4*CAP):
    p=Path(path);need(p.is_absolute() and p.resolve()==p and not p.is_symlink(),'canonical evidence path')
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK)
    try:
        s=os.fstat(fd);need(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and s.st_size<=cap,'bounded regular evidence')
        data=b''
        while True:
            b=os.read(fd,min(65536,cap+1-len(data)))
            if not b:break
            data+=b;need(len(data)<=cap,'evidence cap')
        def ident(x):return (x.st_dev,x.st_ino,x.st_mode,x.st_nlink,x.st_size,x.st_mtime_ns,x.st_ctime_ns)
        need(ident(os.fstat(fd))==ident(p.lstat())==ident(s),'evidence identity changed');return data
    finally:os.close(fd)
def bound(ref):
    need(set(ref)=={'path','sha256'},'exact evidence reference');raw=read(ref['path']);need(digest(raw)==ref['sha256'],'evidence digest');return json.loads(raw)
def reference(path):return dict(path=str(path),sha256=digest(read(path)))

def validate_inner(v,work,source_rows):
    work=Path(work);need(v['status']=='PASS_RECURSIVE_MAKE_PIPE_OBSERVATION' and v['image_id']==IMAGE,'inner observation')
    need(v['image_identity_authenticated'] is False and v['observation_only'] is True and v['native_acceptance'] is False and v['target_build'] is False,'inner authority boundary')
    need(v['make_path']=='/usr/bin/make' and v['argv']==ARGV and v['returncode']==0 and v['direct_child_joined'] is True and v['pipe_jobserver_observed'] is True and v['fifo_count']==0,'inner make result')
    need(re.fullmatch('[0-9a-f]{64}',v['make_sha256']) is not None and v['make_version'].startswith('GNU Make '),'make executable/version')
    need(set(v['source_refs'])==set(source_rows)=={'Makefile','probe.py'},'two source observations')
    for n,r in source_rows.items():need(v['source_refs'][n]['sha256']==r['sha256'] and v['source_refs'][n]['bytes']==r['bytes'],'actual probe source')
    refs={}
    for label,argv in [('make-version',['/usr/bin/make','--version']),('recursive-pipe',ARGV)]:
        p=work/'evidence'/(label+'.status.json');row=json.loads(read(p));refs[label+'_status']=reference(p)
        need(row['argv']==argv and row['returncode']==0 and row['direct_child_joined'] is True and row['owned_group_absent'] is True and row['timed_out'] is False and row['cleanup_actions']==[],'actual child wait/group result')
        need(row==v['make_version_status' if label=='make-version' else 'make_status'],'inner/status join')
        for role in ('stdout','stderr'):
            r=row['captures'][role];expected='/work/evidence/'+label+'.'+role;need(r['path']==expected,'fixed stream path')
            path=work/'evidence'/(label+'.'+role);data=read(path,CAP);need(len(data)==r['bytes'] and digest(data)==r['sha256'],'actual child stream');refs[label+'_'+role]=reference(path)
    version=read(work/'evidence/make-version.stdout',CAP).decode();need(version==v['make_version'],'actual version stream')
    children=[]
    for label in ('a','b'):
        p=work/'evidence'/('child-'+label+'.json');row=json.loads(read(p));need(row==v['children'][len(children)],'child/raw join')
        need(row['label']==label and row['makelevel']==2 and row['pipe_jobserver_observed'] is True and row['pid']>0 and row['parent_pid']>0,'child identity')
        ends=row['endpoints'];need(len(ends)==2 and ends[0]['fd']!=ends[1]['fd'] and ends[0]['access_mode']==0 and ends[1]['access_mode']==1,'pipe endpoints')
        need(re.fullmatch(r'pipe:\[[0-9]+\]',ends[0]['link']) is not None and ends[0]['link']==ends[1]['link'] and ends[0]['inode']==ends[1]['inode'],'anonymous pipe pairing')
        need('--jobserver-auth='+str(ends[0]['fd'])+','+str(ends[1]['fd']) in row['makeflags'].split() and 'fifo:' not in row['makeflags'],'numeric pipe auth');children.append(row);refs['child_'+label]=reference(p)
    need(len(v['children'])==2 and children[0]['pid']!=children[1]['pid'] and children[0]['parent_pid']!=children[1]['parent_pid'] and children[0]['endpoints'][0]['link']==children[1]['endpoints'][0]['link'],'samepipe recursive branches')
    expected={'make-version.stdout','make-version.stderr','make-version.status.json','recursive-pipe.stdout','recursive-pipe.stderr','recursive-pipe.status.json','child-a.json','child-b.json','probe-result.json'}
    actual=set()
    for p in (work/'evidence').iterdir():
        s=p.lstat();need(stat.S_ISREG(s.st_mode) and s.st_nlink==1,'strict output inventory');actual.add(p.name)
    need(actual==expected,'exact probe output inventory')
    return dict(inner_result=reference(work/'evidence/probe-result.json'),records=refs,make_sha256=v['make_sha256'],source_rows=source_rows)
