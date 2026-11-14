from pathlib import Path
import hashlib,json,re,difflib,subprocess,resource,os
ROOT=Path(__file__).resolve().parent
SRC=Path('/home/holden/mckernel-work/scratch/nsd-c-47f591afb04634de97c05e2e8a405b8b')
RUST='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
API=Path('/home/holden/mckernel-work/scratch/mckernel-exact-candidate-scratch-22-authority3-output/source/linux-6.12.0-211.44.1.el10_2/rust/kernel/error.rs')
files=['os_runtime.rs','smp_application.rs','smp_fork_link.rs','smp_fork_ingress.rs','smp_application_image.rs']
def sha(b):return hashlib.sha256(b).hexdigest()
def fn(text,name):
 start=text.index('fn '+name+'('); pos=text.index('{',start); depth=1; end=pos+1
 while depth:
  depth += (text[end]=='{')-(text[end]=='}'); end+=1
 return text[start:end]
def limits():
 os.sched_setaffinity(0,{6}); resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3)); resource.setrlimit(resource.RLIMIT_CPU,(30,30))
def run(argv,name,success=True):
 r=subprocess.run(argv,capture_output=True,timeout=30,preexec_fn=limits)
 (ROOT/(name+'.stdout')).write_bytes(r.stdout);(ROOT/(name+'.stderr')).write_bytes(r.stderr)
 (ROOT/(name+'.status')).write_text(str(r.returncode)+'\n')
 assert (r.returncode==0)==success,(name,r.returncode,r.stderr.decode())
 return r
version=run([RUST,'--version'],'rust-version').stdout.decode().strip();assert '1.92.0' in version
(ROOT/'original').mkdir(exist_ok=True);(ROOT/'candidate').mkdir(exist_ok=True)
manifest={};patch=[];orig={};cand={}
for name in files:
 b=(SRC/'modules'/name).read_bytes();old=b.decode();new=old.replace('.ok_or(EOVERFLOW)?','.ok_or_else(|| errno(-75))?')
 assert new!=old
 (ROOT/'original'/name).write_bytes(b);(ROOT/'candidate'/name).write_text(new)
 orig[name]=old;cand[name]=new
 manifest[name]={'before':sha(b),'after':sha(new.encode()),'sites':old.count('.ok_or(EOVERFLOW)?')}
 patch.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
assert {n:manifest[n]['sites'] for n in files} == {'os_runtime.rs':1,'smp_application.rs':1,'smp_fork_link.rs':2,'smp_fork_ingress.rs':1,'smp_application_image.rs':1}
(ROOT/'repair.patch').write_text(''.join(patch))
for name in ['make.stderr','request.json']:
 (ROOT/('original-'+name)).write_bytes((SRC/'evidence'/name).read_bytes())
(ROOT/'kernel-error.rs').write_bytes(API.read_bytes())
# Extract actual checked-add expressions. Minimal surrounding objects are test doubles;
# compiler name resolution and checked arithmetic use unchanged production source.
exprs={name:re.findall(r'let (\w+) = ([^;\n]+checked_add\(1\)\.ok_or(?:_else)?\((?:EOVERFLOW|\|\| errno\(-75\))\)\?);',orig[name]) for name in files}
assert sum(map(len,exprs.values()))==4 # last_sequence uses assignment rather than let
seq=re.search(r'record.last_sequence = ([^;\n]+checked_add\(1\)\.ok_or(?:_else)?\((?:EOVERFLOW|\|\| errno\(-75\))\)\?);',orig['smp_fork_link.rs']).group(1)
api='pub '+fn(API.read_text(),'to_result')
pre='''#![allow(dead_code)]
#[derive(Debug,PartialEq,Eq,Clone,Copy)] struct Error(i32);
impl Error { fn from_errno(n:i32)->Self { assert!((-4095..0).contains(&n)); Self(n) } }
type Result<T=()> = core::result::Result<T,Error>;
const EIO:Error=Error(-5);
mod kernel { pub mod error { use crate::{Error,Result}; API } }
struct Counter { next_epoch:u64, fork_prepared_parent_refs:u32, last_sequence:u64, accesses:u32 }
'''.replace('API',api)
def check_body(expr,context):
 return 'fn probe(n:u64)->Result<u64> { '+context+' let result = '+expr+'; Ok(result as u64) }\n'
def build(kind,data):
 def expression(name,index=0):return re.findall(r'let (\w+) = ([^;\n]+checked_add\(1\)\.ok_or(?:_else)?\((?:EOVERFLOW|\|\| errno\(-75\))\)\?);',data[name])[index][1]
 runtime='mod os_runtime { use super::*; use crate::kernel::error::to_result; '+fn(data['os_runtime.rs'],'errno')+'\n'+check_body(expression('os_runtime.rs'),'let table=Counter { next_epoch:n,fork_prepared_parent_refs:0,last_sequence:0,accesses:0 };')+'pub fn test(){ checks64(probe); } }\n'
 app='mod smp_application { use super::*; '+fn(data['smp_application.rs'],'errno')+'\n'+check_body(expression('smp_application.rs'),'let p=Counter { next_epoch:0,fork_prepared_parent_refs:n as u32,last_sequence:0,accesses:0 };')
 for child in ['smp_fork_link.rs','smp_fork_ingress.rs']:
  name=child.replace('.rs','');context='let p=Counter { next_epoch:0,fork_prepared_parent_refs:n as u32,last_sequence:0,accesses:0 };' if child.endswith('link.rs') else 'let slots=[Some(Counter { next_epoch:0,fork_prepared_parent_refs:n as u32,last_sequence:0,accesses:0 })]; let pi=0;'
  app+='mod '+name+' { use super::*; '+check_body(expression(child),context)
  if child.endswith('link.rs'):
   e=re.search(r'record.last_sequence = ([^;\n]+checked_add\(1\)\.ok_or(?:_else)?\((?:EOVERFLOW|\|\| errno\(-75\))\)\?);',data[child]).group(1)
   app+='fn sequence(n:u64)->Result<u64> { let record=Counter { next_epoch:0,fork_prepared_parent_refs:0,last_sequence:n,accesses:0 }; Ok('+e+') } pub fn test(){ checks32(probe); checks64(sequence); }'
  else: app+='pub fn test(){ checks32(probe); }'
  app+=' }\n'
 app+='pub fn test(){ checks32(probe); smp_fork_link::test(); smp_fork_ingress::test(); } }\n'
 image_matches=re.findall(r'self.accesses = ([^;\n]+checked_add\(1\)\.ok_or(?:_else)?\((?:EOVERFLOW|\|\| errno\(-75\))\)\?);',data['smp_application_image.rs'])
 assert len(image_matches)==1
 image='mod smp_application_image { use super::*; '+fn(data['smp_application_image.rs'],'errno')+'\n impl Counter { fn probe(&self)->Result<u64> { Ok('+image_matches[0]+') .map(|v| v as u64) } } fn probe(n:u64)->Result<u64>{ Counter { next_epoch:0,fork_prepared_parent_refs:0,last_sequence:0,accesses:n as u32 }.probe() } pub fn test(){checks32(probe);} }'
 end='''fn checks64(f:fn(u64)->Result<u64>){assert_eq!(f(0),Ok(1));assert_eq!(f(u64::MAX-1),Ok(u64::MAX));assert_eq!(f(u64::MAX),Err(Error(-75)));}
fn checks32(f:fn(u64)->Result<u64>){assert_eq!(f(0),Ok(1));assert_eq!(f(u32::MAX as u64-1),Ok(u32::MAX as u64));assert_eq!(f(u32::MAX as u64),Err(Error(-75)));}
fn main(){os_runtime::test();smp_application::test();smp_application_image::test();assert_ne!(Error(-75),EIO);assert_ne!(Error(-75),Error(-16));println!("six extracted production expressions: positive, boundary, overflow PASS; distinct errno -75 PASS");}
'''
 path=ROOT/(kind+'.rs');path.write_text(pre+runtime+app+image+end)
 r=run([RUST,'--edition=2021',str(path),'-o',str(ROOT/(kind+'-bin'))],kind+'-compile',kind=='candidate')
 if kind=='original':
  assert r.stderr.count(b'error[E0425]')==6 and r.stderr.count(b'cannot find value `EOVERFLOW`')==6,r.stderr.decode()
  assert not re.search(rb'error\[(?!E0425)',r.stderr),r.stderr.decode()
 else:run([str(ROOT/(kind+'-bin'))],kind+'-run')
build('original',orig);build('candidate',cand)
assert all((SRC/'modules'/n).read_bytes()==(ROOT/'original'/n).read_bytes() for n in files)
report={'status':'PASS','toolchain':version,'source_root':str(SRC/'modules'),'files':manifest,'original_make_stderr_sha256':sha((ROOT/'original-make.stderr').read_bytes()),'kernel_error_api_sha256':sha(API.read_bytes()),'kernel_api':'Error::from_errno is crate-private, non-const; use existing errno(-75) conversion','original_lexical_errors':6,'positive_expressions':6,'production_width_bindings':{'u64':2,'u32':4},'checks_per_expression':['0 => 1','MAX-1 => MAX','MAX => Error(-75)'],'limits':'CPU6, one job, 1GiB address space, 30s per invocation','scope':'Extracted real expressions and errno helpers; object scaffolding and Error representation are doubles. No Kbuild/module/runtime acceptance. Frozen source unchanged.','next':'Independent diff review, then rebuild fresh frozen candidate via previously reviewed native module Kbuild profile; default CREATE_PPD -95 path untouched.'}
(ROOT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
