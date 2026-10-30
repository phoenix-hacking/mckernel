"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare data32 source map from frozen ledgers and exactly three changed inputs.
No tree enumeration, compiler, validator, snapshot adoption, or native work.
"""
import hashlib,json,os,stat
from pathlib import Path
B=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1')
D=Path(__file__).resolve().parent
P=B/'sdk21-nonheld13-data32-compile-preparation-1/SDK21-COMPILE.SOURCE-ONLY.json'
DELTA=P.parent/'BINDING-DELTA.SOURCE-ONLY.json'
Q=B/'sdk21-nonheld13-input-validation-source-1/SDK13-DATA32-ADMISSION.SOURCE-ONLY.json'
M=B/'sdk21-nonheld13-source-map-1/SDK13-SOURCE-MAP.PROPOSED.json'
A=B/'f06-debug-constants-align32-host-1/ADMISSION.ACTUAL.json'
R=B/'f06-debug-constants-align32-host-1/src/kernel/rust'
EXPECTED={P:'e6a8462b10b409e86a7192d34328de33307cccd5c8e53d75b6312c85042c1ec3', DELTA:'140292a67e9a07a2df3d2f7c5f96e879b548477c78949c00b168c8d62fc92584',Q:'b9e0fbad132ae43fcd79459b9f2baee776679b4a972e4647d583f0d8ba26b594',M:'3ab7abb82522c42f00c301f2d246c4918ec85bc789c20d4fb48f56468ac46e07',A:'17553d05dc5df02be0d33489a10b736f6e5ea8b1e2131d749de720167e8aa349'}
def load(p):
 data=p.read_bytes()
 if hashlib.sha256(data).hexdigest()!=EXPECTED[p]:raise ValueError('bound metadata differs: '+str(p))
 return json.loads(data)
def ident(s):return {k:getattr(s,'st_'+k) for k in ('dev','ino','mode','uid','gid','nlink','size','mtime_ns','ctime_ns')}
def checked_file(path,expected):
 before=os.lstat(path)
 if not stat.S_ISREG(before.st_mode):raise ValueError('not regular: '+str(path))
 with path.open('rb') as f:
  first=os.fstat(f.fileno());data=f.read();last=os.fstat(f.fileno())
 if ident(before)!=ident(first) or ident(first)!=ident(last) or ident(last)!=ident(os.lstat(path)):raise ValueError('changed during read: '+str(path))
 sha=hashlib.sha256(data).hexdigest()
 if sha!=expected:raise ValueError('changed input differs: '+str(path))
 return {'path':str(path),'sha256':sha,'bytes':len(data),'identity':ident(first)}
def write(name,value):
 with (D/name).open('x') as f:json.dump(value,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
profile=load(P);delta=load(DELTA);proposal=load(Q);m=load(M);a=load(A)
old=m['trees']['/src/kernel/rust']; oldfiles={x['relative']:(x['bytes'],x['sha256']) for x in old['entries'] if x['kind']=='file'}
closure={}
for entry in a['source_closure']:
 path=Path(entry['path'])
 try:rel=path.relative_to(R).as_posix()
 except ValueError:continue
 if rel in closure:raise ValueError('duplicate HOST Rust closure')
 closure[rel]={'relative':rel,'kind':'file','bytes':entry['bytes'],'sha256':entry['sha256']}
if len(closure)!=157 or len(oldfiles)!=156 or set(closure)-set(oldfiles)!={'f06_debug_constants.rs'} or set(oldfiles)-set(closure):raise ValueError('Rust closure membership differs')
if [x for x in oldfiles if (closure[x]['bytes'],closure[x]['sha256'])!=oldfiles[x]]!=['lib.rs']:raise ValueError('unexpected Rust source delta')
mounts={x['container']:x for x in profile['readonly_shared_inputs']}
if mounts['/src/kernel/rust']['host']!=str(R) or mounts['/src']['host']!=m['trees']['/src']['root'] or mounts['/nightly']['host']!=m['trees']['/nightly']['root']:raise ValueError('profile tree mount differs')
changed=profile['source_bindings']['data32_three_postimages']
if set(changed)!={'arch/x86_64/kernel/syscall.c','kernel/rust/lib.rs','kernel/rust/f06_debug_constants.rs'}:raise ValueError('changed input set differs')
observed={name:checked_file(Path(row['candidate_path']),row['candidate_sha256']) for name,row in changed.items()}
if mounts['/src/arch/x86_64/kernel/syscall.c']['host']!=observed['arch/x86_64/kernel/syscall.c']['path']:raise ValueError('C overlay differs')
for n in ('lib.rs','f06_debug_constants.rs'):
 if closure[n]['sha256']!=observed['kernel/rust/'+n]['sha256'] or closure[n]['bytes']!=observed['kernel/rust/'+n]['bytes']:raise ValueError('Rust closure changed input differs')
m['profile_sha256']=EXPECTED[P];m['proposal_sha256']=EXPECTED[Q]
m['trees']['/src/kernel/rust']={'root':str(R),'entries':[x for x in old['entries'] if x['kind']=='dir']+[closure[x] for x in sorted(closure)]}
write('SDK13-DATA32-SOURCE-MAP.PROPOSED.json',m)
write('THREE-CHANGED-INPUTS.OBSERVED.json',{'scope':__doc__.splitlines()[0],'status':'SOURCE_DATA_PENDING_REVIEW','bindings':{str(k):v for k,v in EXPECTED.items()},'observed':observed,'unchanged_final_rust_files':155,'unchanged_final_rust_hashes':'HOST163_ADMISSION_CLOSURE_ONLY_NO_HASH_IDENTITY_BINDING','rust_tree_membership':'PENDING_LIVE_ADOPTION','source6153_and_nightly_content_reads':False,'authority':None})
