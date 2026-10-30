from pathlib import Path
import json,hashlib
p=Path(__file__).parent;b=p.parent.parent
m=json.loads((p.parent/'m14-root-and-nonheld-composite-1/MOUNT-MANIFEST.json').read_text())['on_source_mount_proposal'];base=Path(m['/src']);c=Path(m['/src/kernel/syscall.c']);rust=Path(m['/src/kernel/rust']);policy=rust/'syscall_policy.rs';abi=rust/'abi.rs';h=base/'kernel/include/syscall.h';q=base/'ihk/ikc/include/ikc/queue.h'
# Inputs are exact existing source bytes; output stays in this private fixture.
def block(text, marker):
 pos=text.index(marker); brace=text.index('{',pos); depth=0
 for i in range(brace,len(text)):
  if text[i]=='{':depth+=1
  if text[i]=='}':
   depth-=1
   if depth==0:return text[pos:i+1]
 raise ValueError(marker)
rs=policy.read_text(); cs=c.read_text();hs=h.read_text();qs=q.read_text()
rparts=[block(rs,'unsafe fn zero_syscall_ikc_scd_packet('),block(rs,'pub unsafe extern "C" fn syscall_eventfd_packet_prepare_result('),block(rs,'pub unsafe extern "C" fn syscall_eventfd_send_result('),block(rs,'unsafe extern "C" fn f03_eventfd_send('),block(rs,'pub unsafe extern "C" fn eventfd(')]
cparts=[block(cs,'syscall_eventfd_packet_prepare_result(struct ikc_scd_packet *packet, int msg,'),block(cs,'syscall_eventfd_send_result(void *channel, int msg, int eventfd_type,'),block(cs,'static int syscall_ikc_send_bridge(void *channel, void *packet, int opt)'),block(cs,'void eventfd(int type)')]
structs=[block(qs,'struct ihk_ikc_packet_header {')+';',block(hs,'struct syscall_request {')+';',block(hs,'enum mcctrl_os_cpu_operation {')+';',block(hs,'struct ikc_scd_packet {')+';']
(p/'actual_bodies.rs').write_text('\n\n'.join(rparts)+'\n');(p/'actual_bodies.c').write_text('int '+cparts[0]+'\nint '+cparts[1]+'\n'+cparts[2]+'\n'+cparts[3]+'\n');(p/'actual_structs.c').write_text('\n'.join(structs)+'\n')
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest();(p/'INPUTS.json').write_text(json.dumps({str(x):sha(x) for x in (c,policy,abi,h,q)},indent=2)+'\n')
(p/'rust-main.rs').write_text('''#![allow(dead_code,unused_imports)]
#[path="'''+str(abi)+'''\"] mod abi;
use core::ffi::c_void;use core::mem::{size_of,MaybeUninit};use core::ptr::{write,write_volatile};use abi::{CInt,CULong,IkcScdPacket};
const EINVAL:CInt=22;type SyscallIkcSendFn=unsafe extern "C" fn(*mut c_void,*mut c_void,CInt)->CInt;
static mut PACKET:[u8;128]=[0;128]; static mut CPU:i32=-1; static mut CHANNEL:usize=0;static mut OPT:i32=-1;static mut RET:i32=0;static mut CALLS:i32=0;
mod cls { use core::ffi::c_void; #[repr(C)] pub struct FakeCpu {pub ikc2linux:*mut c_void} static mut CPU0:FakeCpu=FakeCpu{ikc2linux:0x1234usize as *mut c_void};pub unsafe fn get_cpu_local_var(n:i32)->*mut FakeCpu{crate::CPU=n; core::ptr::addr_of_mut!(CPU0)} }
mod ikc_manycore {use core::ffi::c_void;pub unsafe fn ihk_ikc_send(c:*mut c_void,p:*mut c_void,o:i32)->i32 {crate::CHANNEL=c as usize;crate::OPT=o;crate::CALLS+=1;core::ptr::copy_nonoverlapping(p.cast::<u8>(),core::ptr::addr_of_mut!(crate::PACKET).cast::<u8>(),128);crate::RET}}
include!("actual_bodies.rs");
fn main(){assert_eq!(size_of::<IkcScdPacket>(),128);assert_eq!(unsafe{syscall_eventfd_packet_prepare_result(core::ptr::null_mut(),1,2)},-22);assert_eq!(unsafe{syscall_eventfd_send_result(core::ptr::null_mut(),1,2,None)},-22);for val in [0, -7, i32::MAX] {for ret in [0,-11,5] {unsafe {RET=ret;CPU=-1;CALLS=0;CHANNEL=0;OPT=-1;eventfd(val);print!("{} {} {} {} {} {} ",val,ret,CPU,CHANNEL,OPT,CALLS);for x in PACKET {print!("{:02x}",x)}println!();}}}}
''')
(p/'c-main.c').write_text('''#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
#define EINVAL 22
#define SCD_MSG_EVENTFD 0x46
struct ihk_ikc_channel_desc {int unused;};
#include "actual_structs.c"
typedef int (*syscall_ikc_send_fn_t)(void *,void *,int);
static unsigned char capture[128];static int cpu,callcount,retvalue,optvalue;static uintptr_t channel;
struct cpulocal {struct ihk_ikc_channel_desc *ikc2linux;};
static struct cpulocal cl={.ikc2linux=(void *)0x1234};
static struct cpulocal *get_cpu_local_var(int n){cpu=n;return &cl;}
static int ihk_ikc_send(struct ihk_ikc_channel_desc *c,void *p,int o){channel=(uintptr_t)c;optvalue=o;callcount++;memcpy(capture,p,128);return retvalue;}
#include "actual_bodies.c"
int main(void){_Static_assert(sizeof(struct ikc_scd_packet)==128,"packet size");if(syscall_eventfd_packet_prepare_result(NULL,1,2)!=-22||syscall_eventfd_send_result(NULL,1,2,NULL)!=-22)return 2;int vals[]={0,-7,INT_MAX};int rets[]={0,-11,5};for(int i=0;i<3;i++)for(int j=0;j<3;j++){int v=vals[i],r=rets[j];retvalue=r;cpu=-1;channel=0;optvalue=-1;callcount=0;eventfd(v);printf("%d %d %d %lu %d %d ",v,r,cpu,(unsigned long)channel,optvalue,callcount);for(int k=0;k<128;k++)printf("%02x",capture[k]);puts("");}return 0;}
''')
