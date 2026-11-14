"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,resource,time
D=Path(__file__).resolve().parent;REPO=Path('/home/holden/mckernel');E=REPO/'docs/verification/evidence/compute-idle-rust-cutover-20261023-1/page-free-callback-4'
SCOPE=__doc__
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
helperpath=REPO/'docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py';assert sha(helperpath)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec=importlib.util.spec_from_file_location('accepted',helperpath);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
profile=REPO/'docs/verification/evidence/compute-idle-rust-cutover-20261023-1/phys-to-virt-callback-1/PREPARED-COMMANDS.NOT-EXECUTED.json';pre=json.loads(profile.read_text())['preprocess']
os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
os.chdir(D);results=[];start=time.monotonic();error=None;status='FAIL_FIRST_COMMAND_RETAINED'
def run(label,argv):
 cap=D/(label+'-capture-1');cap.mkdir();command={'argv':argv,'purpose':SCOPE,'shell':False};write(cap/'command.json',command);j=h.owned_capture(command,cap,90,lambda:None);write(cap/'whole-join.json',j);results.append({'label':label,'whole_join':j});assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['error'] and not j['retirement_error'],'first failed '+label
 return (cap/'stdout').read_text()
try:
 bsrc=D/'preimage/arch/x86_64/kernel/memory.c';csrc=D/'candidate/arch/x86_64/kernel/memory.c'
 baseline=run('baseline-preprocess',pre[:-1]+[str(bsrc)]);candidate=run('candidate-preprocess',pre[:-1]+[str(csrc)])
 old=re.search(r'static void x86_clear_free_pages_user_bridge\(void \*addr, int nr_pages\)\s*\{[^}]+\}',baseline).group()
 data='\n'.join(re.findall(r'const (?:char|int) x86_clear_free_pages_user_(?:file|line|flag)[^;]*;',candidate))
 assert len(data.splitlines())==3
 (D/'actual-original-callback.c.inc').write_text(old+'\n');(D/'actual-candidate-data.c.inc').write_text(data+'\n')
 origline=next(i for i,l in enumerate(bsrc.read_text().splitlines(),1) if '_ihk_mc_free_pages(addr, nr_pages' in l)
 dataline=next(i for i,l in enumerate(csrc.read_text().splitlines(),1) if 'const char x86_clear_free_pages_user_file[]' in l)
 assert '"'+str(bsrc)+'", '+str(origline) in old
 assert '"'+str(csrc)+'"' in data and 'x86_clear_free_pages_user_line = '+str(dataline)+';' in data
 rust=(D/'candidate/kernel/rust/x86_memory_helpers.rs').read_text();m=re.search(r'#\[no_mangle\]\npub unsafe extern "C" fn x86_clear_free_pages_user_bridge\([^}]+\}',rust);assert m
 (D/'actual-rust-callback.rs.inc').write_text(m.group()+'\n')
 (D/'fixture.rs').write_text('use core::ffi::c_void;\ntype CInt=i32;\nunsafe extern "C" { fn _ihk_mc_free_pages(ptr:*mut c_void,npages:CInt,is_user:CInt,file:*mut i8,line:CInt); static x86_clear_free_pages_user_file:[i8;1]; static x86_clear_free_pages_user_line:CInt; static x86_clear_free_pages_user_flag:CInt; }\ninclude!("actual-rust-callback.rs.inc");\n')
 fixture=r"""#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
void _ihk_mc_free_pages(void*,int,int,char*,int);
extern void x86_clear_free_pages_user_bridge(void*,int);
#include "actual-candidate-data.c.inc"
#define x86_clear_free_pages_user_bridge original_callback
#include "actual-original-callback.c.inc"
#undef x86_clear_free_pages_user_bridge
static void *seen; static int nr,flag,line,calls; static char *file;
void _ihk_mc_free_pages(void *a,int n,int f,char *s,int l) { seen=a; nr=n; flag=f; file=s; line=l; ++calls; }
int main(void) {
 uintptr_t storage[2]={0}; void *ptrs[]={NULL,storage,(void*)(uintptr_t)1,(void*)(uintptr_t)UINTPTR_MAX};
 int nums[]={INT_MIN,-22,-1,0,1,37,INT_MAX}; unsigned vectors=0;
 for(unsigned p=0;p<4;p++) for(unsigned n=0;n<7;n++) {
  calls=0; original_callback(ptrs[p],nums[n]);
  if(calls!=1 || seen!=ptrs[p] || nr!=nums[n] || flag!=1 || line!=ORIGLINE || strcmp(file,ORIGFILE)) return 1;
  calls=0; x86_clear_free_pages_user_bridge(ptrs[p],nums[n]);
  if(calls!=1 || seen!=ptrs[p] || nr!=nums[n] || flag!=1 || flag!=x86_clear_free_pages_user_flag || line!=x86_clear_free_pages_user_line || line!=DATALINE || strcmp(file,x86_clear_free_pages_user_file) || strcmp(file,DATAFILE)) return 2;
  ++vectors;
 }
 printf("PASS %u exact callback pointer/signed-count/USER/file/line vectors; original C callsite and Rust C-data descriptor provenance checked separately\n",vectors);
 return 0;
}
"""
 fixture=fixture.replace('ORIGLINE',str(origline)).replace('DATALINE',str(dataline)).replace('ORIGFILE',json.dumps(str(bsrc))).replace('DATAFILE',json.dumps(str(csrc)));(D/'fixture.c').write_text(fixture)
 rustc='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
 run('rust-object',[rustc,'--edition=2021','--crate-type=lib','--emit=obj','-C','codegen-units=1','-C','opt-level=2','-C','panic=abort','fixture.rs','-o','fixture-rust.o'])
 run('fixture-link',['/usr/bin/gcc-9','-O2','-Werror=incompatible-pointer-types','fixture.c','fixture-rust.o','-o','fixture'])
 run('fixture-execute',[str(D/'fixture')]);status='PASS_PRIVATE_CALLBACK_28_EXACT_BOUNDARY_AND_PROVENANCE_VECTORS'
except BaseException as exc:error=repr(exc)
result={'scope':SCOPE,'status':status,'error':error,'seconds':time.monotonic()-start,'commands':results,'vectors':28 if status.startswith('PASS') else None,'provenance':'__FILE__/__LINE__/USER captured by data-only C declarations at replaced callback site. Original-C source and candidate descriptor paths naturally differ; exact source-site file/line values independently checked, Rust forwards descriptor bytes/value exactly. No old-binary immutable-line claim; no Rustfile!/line!, hardcoded production line, #line, padding or runtime C shim.','provider_boundary':'Existing Rust mem_helpers::_ihk_mc_free_pages ABI reused; fixture recorder observes exact call boundary, not allocator behavior acceptance.','canonical_modified':False,'default_link':False,'native':False,'whole_file_retirement':False,'input_pins':{str(q.relative_to(D)):sha(q) for q in [D/'preimage/arch/x86_64/kernel/memory.c',D/'preimage/kernel/rust/x86_memory_helpers.rs',D/'candidate/arch/x86_64/kernel/memory.c',D/'candidate/kernel/rust/x86_memory_helpers.rs']}}
write(D/'RESULT.json',result)
for q in D.rglob('*'):
 if q.is_file() and q.suffix!='.o' and q.name!='fixture':
  out=E/q.relative_to(D);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(q.read_bytes())
print(json.dumps({'status':status,'error':error,'commands':len(results),'seconds':result['seconds']}))
