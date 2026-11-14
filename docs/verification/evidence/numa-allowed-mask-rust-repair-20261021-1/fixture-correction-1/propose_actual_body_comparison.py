#!/usr/bin/env python3
"""Focused actual-body comparison, using existing source-slice harness pattern.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
UNRUN proposal: root supplies ordinary grant; no image/app/root/Docker/guest work.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess
R=Path(__file__).resolve().parent.parent
BASE='75b89149aa031076ae547248e0aab64eda5a7b75162952a954489e86067f0b2d'
CAND='da1e612baa6af6cd3e5ddad39f26d0c8aa582faee1920a5b7a86ce507d7b99af'
REPO=Path('/home/holden/mckernel')
def sha(b):return hashlib.sha256(b).hexdigest()
def function(text,name):
 match=list(re.finditer(r'(?m)^(?:(?:pub\s+)?(?:unsafe\s+)?(?:extern\s+"C"\s+)?)fn\s+'+re.escape(name)+r'\(',text));assert len(match)==1,name
 start=match[0].start();opening=text.index('{',start);depth=1;i=opening+1
 while depth:
  depth+=(text[i]=='{')-(text[i]=='}');i+=1
 return text[start:i]
MAIN=r'''
static mut FAIL_COPY:bool=false;
static mut COPIES:usize=0;
static mut BYTES:usize=0;
static mut LOG_CALLS:usize=0;
static mut LOG_EVENT:CInt=0;
static mut LOG_VALUE:CInt=0;
unsafe extern "C" fn log(event:CInt,_:CULong,value:CInt){LOG_CALLS+=1;LOG_EVENT=event;LOG_VALUE=value;}
unsafe extern "C" fn copy_to(addr:CULong,src:*const u8,len:SizeT)->CLong {
 COPIES+=1;BYTES=len;
 if FAIL_COPY{return 1;}
 if len!=0{copy_nonoverlapping(src,addr as *mut u8,len);}0
}
unsafe fn call(vm:&mut ProcessVm,nodes:CInt,max:CULong,flags:CInt,fail:bool)->(CLong,[u64;6],usize,usize){
 let mut mask=[0x137bd9958db6ff4du64,0,0,0,0,0x137bd9958db6ff4du64];
 COPIES=0;BYTES=0;FAIL_COPY=fail;LOG_CALLS=0;LOG_EVENT=0;LOG_VALUE=0;
 let rc=get_mempolicy_body_result(0,mask[1..].as_mut_ptr() as CULong,max,0,flags,vm,nodes,Some(copy_to),None,None,None,None,None,Some(log));
 assert_eq!(mask[0],0x137bd9958db6ff4d);assert_eq!(mask[5],0x137bd9958db6ff4d);
 (rc,mask,COPIES,BYTES)
}
fn main(){unsafe{
 assert_eq!(core::mem::offset_of!(ProcessVm,numa_mask),208);
 let mut count=0;
 for (nodes,expected) in [(1,[1,0,0,0]),(4,[15,0,0,0]),(65,[u64::MAX,1,0,0]),(256,[u64::MAX;4])]{
  for mode in [MPOL_DEFAULT,MPOL_PREFERRED,MPOL_BIND,MPOL_INTERLEAVE]{
   for original in [[0;4],[1,0,0,0],[u64::MAX;4]]{
    let mut vm:ProcessVm=core::mem::zeroed();vm.numa_mem_policy=mode;vm.numa_mask=original;
    let (rc,got,copies,bytes)=call(&mut vm,nodes,256,MPOL_F_MEMS_ALLOWED,false);
    assert_eq!(rc,0);assert_eq!(copies,1);assert_eq!(bytes,32);
    let wanted=if cfg!(allowed_candidate){expected}else{original};assert_eq!(&got[1..5],&wanted);
    assert_eq!(vm.numa_mem_policy,mode);assert_eq!(vm.numa_mask,original);
    count+=1;
   }
  }
 }
 // Preserve exact original equivalence vector: BIND mask0x1234/nodes4/max257.
 let mut original:ProcessVm=core::mem::zeroed();original.numa_mem_policy=MPOL_BIND;original.numa_mask=[0x1234,0,0,0];
 let (rc,mask,copies,bytes)=call(&mut original,4,257,MPOL_F_MEMS_ALLOWED,false);
 assert_eq!(rc,0);assert_eq!(copies,1);assert_eq!(bytes,32);assert_eq!(LOG_CALLS,1);assert_eq!(LOG_EVENT,1);assert_eq!(LOG_VALUE,256);
 assert_eq!(mask[1],if cfg!(allowed_candidate){0xf}else{0x1234});assert_eq!(original.numa_mask,[0x1234,0,0,0]);assert_eq!(original.numa_mem_policy,MPOL_BIND);
 let mut vm:ProcessVm=core::mem::zeroed();vm.numa_mem_policy=MPOL_DEFAULT;
 let (rc,mask,_,bytes)=call(&mut vm,1,256,MPOL_F_MEMS_ALLOWED,true);assert_eq!(rc,-14);assert_eq!(mask[1..5],[0;4]);assert_eq!(bytes,32);
 let (rc,mask,copies,_)=call(&mut vm,4,1,MPOL_F_MEMS_ALLOWED,false);assert_eq!(rc,-22);assert_eq!(copies,0);assert_eq!(mask[1..5],[0;4]);
 let (rc,mask,copies,bytes)=call(&mut vm,1,0,MPOL_F_MEMS_ALLOWED,false);assert_eq!(rc,0);assert_eq!(copies,1);assert_eq!(bytes,0);assert_eq!(mask[1..5],[0;4]);
 // Ordinary nondefault policy queries continue returning the process policy mask.
 for mode in [MPOL_PREFERRED,MPOL_BIND,MPOL_INTERLEAVE]{
  let mut vm:ProcessVm=core::mem::zeroed();vm.numa_mem_policy=mode;vm.numa_mask=[5,0,0,0];
  let mut modeout=-1;let mut mask=[0u64;4];COPIES=0;FAIL_COPY=false;
  let rc=get_mempolicy_body_result((&mut modeout as *mut CInt) as CULong,mask.as_mut_ptr() as CULong,256,0,0,&mut vm,4,Some(copy_to),None,None,None,None,None,None);
  assert_eq!(rc,0);assert_eq!(modeout,mode);assert_eq!(mask,[5,0,0,0]);assert_eq!(COPIES,2);
 }
 println!("PASS actual_body allowed_cases={} copyfault/maxnode/guards/policy_preservation=true candidate={}",count,cfg!(allowed_candidate));
}}
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--rustc',required=True);a=p.parse_args();a.out.mkdir(mode=0o700)
 abi=(REPO/'kernel/rust/abi.rs').read_bytes();(a.out/'abi.rs').write_bytes(abi)
 records=[]
 for name,pin,cfg in [('baseline',BASE,False),('candidate',CAND,True)]:
  path=R/('syscall_policy.before.rs' if name=='baseline' else 'syscall_policy.proposed.rs');raw=path.read_bytes();assert sha(raw)==pin;text=raw.decode()
  names=['mempolicy_nodemask_bits_is_clamped','policy_mask_zero','policy_mask_set','policy_mask_set_all_nodes','get_mempolicy_validate','get_mempolicy_body_result']
  bodies=[function(text,n) for n in names]
  constants='\n'.join(line for line in text.splitlines() if re.match(r'^const (?:EINVAL|EFAULT|PROCESS_NUMA_MASK_BITS|MPOL_DEFAULT|MPOL_PREFERRED|MPOL_BIND|MPOL_INTERLEAVE|MPOL_F_NODE|MPOL_F_ADDR|MPOL_F_MEMS_ALLOWED|GET_MEMPOLICY_LOG_CLAMPED|GET_MEMPOLICY_LOG_INVALID_RANGE):',line))
  types='\n'.join(line for line in text.splitlines() if re.match(r'^type Syscall(?:CopyToUser|GetMempolicyLog|Rwlock|LookupNode|LookupRange|PolicySearch)Fn\b',line))
  source='#![allow(dead_code,static_mut_refs)]\nmod abi;\nuse core::ffi::c_void;\nuse core::mem::size_of;\nuse core::ptr::{write,read_volatile,write_volatile,copy_nonoverlapping};\nuse abi::{CInt,CLong,CULong,SizeT,ProcessVm,VmRange,VmRangeNumaPolicy,PROCESS_NUMA_MASK_WORDS};\n'+constants+'\n'+types+'\n'+'\n'.join(bodies)+'\n'+MAIN
  out=a.out/(name+'.rs');out.write_text(source);binary=a.out/name
  argv=[a.rustc,'--edition=2021','-C','opt-level=0',str(out),'-o',str(binary)]+(['--cfg','allowed_candidate'] if cfg else [])
  env={k:os.environ[k] for k in ['PATH','HOME','USER'] if k in os.environ};env.update(LANG='C',LC_ALL='C')
  for role,command in [('compile',argv),('actual_body',[str(binary)])]:
   cp=subprocess.run(command,capture_output=True,env=env,check=False);(a.out/(name+'.'+role+'.stdout')).write_bytes(cp.stdout);(a.out/(name+'.'+role+'.stderr')).write_bytes(cp.stderr)
   row={'role':name+'.'+role,'argv':command,'returncode':cp.returncode};records.append(row)
   (a.out/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
   if cp.returncode:raise SystemExit(cp.returncode)
  (a.out/(name+'.source-binding.json')).write_text(json.dumps({'production_source':str(path),'sha256':pin,'abi_sha256':sha(abi),'whole_actual_function_body_sha256':dict(zip(names,[sha(x.encode()) for x in bodies]))},indent=2)+'\n')
 print(json.dumps({'status':'PASS_BASELINE_BUG_REPRODUCED_AND_CANDIDATE_TOPOLOGY_ALLOWED_MASK','baseline_keeps_old_policy_mask_bug':True,'C_reference_unchanged':True,'native_acceptance':False,'records':records},sort_keys=True))
if __name__=='__main__':main()
