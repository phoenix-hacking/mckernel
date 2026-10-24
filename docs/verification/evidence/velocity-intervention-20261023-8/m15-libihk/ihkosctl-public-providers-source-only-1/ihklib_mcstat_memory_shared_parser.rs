//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Source-only actual total-memory sysfs/parser successor. No second executable queue.
use core::ffi::{c_char,c_int,c_long,c_ulong,c_void};
use core::ptr::null_mut;
const EINVAL:c_int=22;
macro_rules! c { ($s:literal) => {concat!($s,"\0").as_ptr().cast::<c_char>()}; }
#[repr(C)]
#[derive(Clone,Copy)]
struct MemChunk {size:c_ulong,numa_node_number:c_int}
// stat fields are never read. Selected Linux x86_64 glibc ABI is 144B/alignment8;
// future actual header consumer must compare this storage before execution.
#[repr(C,align(8))]
struct StatStorage([u8;144]);
unsafe extern "C" {
 static mut loglevel:c_int;
 fn __errno_location()->*mut c_int;
 #[cfg(ihklib_stat_abi_stat)]
 fn stat(path:*const c_char,out:*mut StatStorage)->c_int;
 #[cfg(ihklib_stat_abi_xstat1)]
 fn __xstat(version:c_int,path:*const c_char,out:*mut StatStorage)->c_int;
 fn fopen(path:*const c_char,mode:*const c_char)->*mut c_void;
 fn fclose(file:*mut c_void)->c_int;
 fn getline(line:*mut *mut c_char,capacity:*mut usize,file:*mut c_void)->isize;
 fn snprintf(out:*mut c_char,size:usize,format:*const c_char,...)->c_int;
 fn sscanf(input:*const c_char,format:*const c_char,...)->c_int;
 fn strcmp(a:*const c_char,b:*const c_char)->c_int;
 fn strdup(s:*const c_char)->*mut c_char;
 fn strsep(s:*mut *mut c_char,delimiters:*const c_char)->*mut c_char;
 fn strtol(s:*const c_char,end:*mut *mut c_char,base:c_int)->c_long;
 fn calloc(count:usize,size:usize)->*mut c_void;
 fn free(p:*mut c_void);
 fn memset(p:*mut c_void,byte:c_int,size:usize)->*mut c_void;
 fn geteuid()->u32;
 fn open(path:*const c_char,flags:c_int,...)->c_int;
 fn close(fd:c_int)->c_int;
 fn strnlen(p:*const c_char,max:usize)->usize;
 fn write(fd:c_int,p:*const c_void,size:usize)->isize;
}
unsafe fn is(a:*const c_char,b:*const c_char)->bool {unsafe {strcmp(a,b)==0}}
// Reuse of the existing current Rust ihkconfig mem_parse/mem_array bodies follows.
use super::ihklib_cli_parsers::mem_array;
// Logging copies the actual selected eprintf/printk policy and error strings.
unsafe fn log<F:FnOnce(*mut c_char,usize)>(format:F) {
 if unsafe {loglevel}<1 || unsafe {geteuid()}!=0 {return;}
 let mut text=[0 as c_char;3840];format(text.as_mut_ptr(),text.len());
 let fd=unsafe {open(c!("/dev/kmsg"),1)};
 let len=unsafe {strnlen(text.as_ptr(),3839)}+1;let mut offset=0;
 while offset<len {let n=unsafe {write(fd,text.as_ptr().add(offset).cast(),len-offset)};if n<=0 {break;}offset+=n as usize;}
 unsafe {close(fd);}
}
#[cfg(not(any(ihklib_stat_abi_stat,ihklib_stat_abi_xstat1)))]
compile_error!("Bind the selected actual libc/header stat ABI; no guessed runtime provider");
#[cfg(all(ihklib_stat_abi_stat,ihklib_stat_abi_xstat1))]
compile_error!("Exactly one selected libc stat ABI is required");
#[cfg(any(ihklib_stat_abi_stat,ihklib_stat_abi_xstat1))]
unsafe fn stat_path(path:*const c_char,out:*mut StatStorage)->c_int {
 #[cfg(ihklib_stat_abi_stat)]
 {unsafe {stat(path,out)}}
 #[cfg(all(ihklib_stat_abi_xstat1,not(ihklib_stat_abi_stat)))]
 {unsafe {__xstat(1,path,out)}}
}
unsafe fn mem_path(out:*mut c_char,index:c_int,node:c_int) {
 unsafe {snprintf(out,4096,c!("/sys/devices/virtual/mcos/mcos%d/sys/devices/system/node/node%d/meminfo"),index,node);}
}
#[no_mangle]
pub unsafe extern "C" fn ihklib_os_query_mem_sysfs(index:c_int,result:*mut c_char,capacity:isize,kind:*const c_char)->c_int {
 if result.is_null()||capacity<=0||kind.is_null(){return -22;}
 unsafe {memset(result.cast(),0,capacity as usize);}
 let mut path=[0 as c_char;4096];let mut node:c_int=0;let mut len:c_int=0;
 let mut st=core::mem::MaybeUninit::<StatStorage>::uninit();
 unsafe {mem_path(path.as_mut_ptr(),index,node);}
 // Just as C: the first missing/unreadable node ends enumeration, not a fabricated gap.
 while unsafe {stat_path(path.as_ptr(),st.as_mut_ptr())} != -1 {
  let mut kb:c_ulong=0;let mut line:*mut c_char=null_mut();let mut line_capacity=0usize;
  let file=unsafe {fopen(path.as_ptr(),c!("r"))};if file.is_null(){return -22;}
  while unsafe {getline(&mut line,&mut line_capacity,file)} != -1 {
   let mut scan_node:c_int=0;let mut format=[0 as c_char;1024];
   let n=unsafe {snprintf(format.as_mut_ptr(),format.len(),c!("Node %%d %s:%%16lu kB"),kind)};
   if n as usize>=format.len(){
    unsafe {log(|p,z|{snprintf(p,z,c!("ihklib_os_query_mem_sysfs: error: type string (%s) is too long\n"),kind);});fclose(file);}
    // Original error path retains line ownership; no unreviewed leak fix hidden here.
    return -1;
   }
   if unsafe {sscanf(line,format.as_ptr(),&mut scan_node,&mut kb)}==2 {
    if node>0 {let n=unsafe {snprintf(result.offset(len as isize),capacity.wrapping_sub(len as isize) as usize,c!(","))};len=len.wrapping_add(n);}
    let n=unsafe {snprintf(result.offset(len as isize),capacity.wrapping_sub(len as isize) as usize,c!("%lu@%d"),kb.wrapping_mul(1024),node)};len=len.wrapping_add(n);
   }
   unsafe {free(line.cast());}line=null_mut();
  }
  // getline may retain a buffer on EOF; original C does not free it here either.
  unsafe {fclose(file);}node=node.wrapping_add(1);unsafe {mem_path(path.as_mut_ptr(),index,node);}
 }
 if len==0 {-1} else {0}
}
unsafe fn mem_chunks(list:*mut c_char,out:*mut MemChunk)->c_int {
 let count=unsafe {mem_array(list,null_mut(),null_mut())};if count<=0{return count;}
 // C passes sizeof(unsigned long) first in BOTH calls, including the int array.
 let sizes=unsafe {calloc(core::mem::size_of::<c_ulong>(),count as usize).cast::<usize>()};
 let mut nodes:*mut c_int=null_mut();
 let ret=if sizes.is_null(){-12}else{
  nodes=unsafe {calloc(core::mem::size_of::<c_ulong>(),count as usize).cast()};
  if nodes.is_null(){-12}else{
   let n=unsafe {mem_array(list,sizes,nodes)};
   if n<0 {n}else{
    for i in 0..count as usize {unsafe {core::ptr::addr_of_mut!((*out.add(i)).size).write(sizes.add(i).read() as c_ulong);core::ptr::addr_of_mut!((*out.add(i)).numa_node_number).write(nodes.add(i).read());}}
    0
   }
  }
 };
 unsafe {free(sizes.cast());free(nodes.cast());}ret
}
unsafe fn query_mem(index:c_int,result:*mut c_ulong,count:c_int,kind:*const c_char)->c_int {
 if result.is_null(){return -14;}
 let fd=unsafe {super::ihklib_mcstat::ihklib_os_open(index)};
 if fd<0 {
  unsafe {log(|p,z|{snprintf(p,z,c!("ihklib_os_query_mem: error: ihklib_os_open\n"));});}
  if fd != -1 {unsafe {close(fd);}}return fd;
 }
 let ret=(||->c_int{
  let mut text=[0 as c_char;16*1024];
  if unsafe {ihklib_os_query_mem_sysfs(index,text.as_mut_ptr(),text.len() as isize,kind)}!=0{return -22;}
  let actual=unsafe {mem_array(text.as_ptr(),null_mut(),null_mut())};
  if actual!=count {
   unsafe {log(|p,z|{snprintf(p,z,c!("ihklib_os_query_mem: error: actual # of NUMA nodes (%d) != requested (%d)\n"),actual,count);});}
   return -22;
  }
  let mut chunks=[MemChunk{size:0,numa_node_number:0};1024];
  // Original C ignores this parser return: preserve output/error ordering explicitly.
  unsafe {mem_chunks(text.as_mut_ptr(),chunks.as_mut_ptr());}
  for i in 0..actual {
   let chunk=unsafe {chunks.as_ptr().offset(i as isize).read()};
   if chunk.numa_node_number<0||chunk.numa_node_number>=count{return -22;}
   unsafe {result.offset(chunk.numa_node_number as isize).write(chunk.size);}
  }
  0
 })();
 unsafe {close(fd);}ret
}
#[no_mangle]
pub unsafe extern "C" fn ihk_os_query_total_mem(index:c_int,result:*mut c_ulong,count:c_int)->c_int {
 unsafe {query_mem(index,result,count,c!("MemTotal"))}
}
// Same shared internal path already supplies the existing companion public API.
#[no_mangle]
pub unsafe extern "C" fn ihk_os_query_free_mem(index:c_int,result:*mut c_ulong,count:c_int)->c_int {
 unsafe {query_mem(index,result,count,c!("MemFree"))}
}
#[cfg(ihklib_mcstat_fixture)]
#[no_mangle]
pub extern "C" fn ihklib_mcstat_stat_storage_size()->usize {core::mem::size_of::<StatStorage>()}
#[cfg(ihklib_mcstat_fixture)]
#[no_mangle]
pub extern "C" fn ihklib_mcstat_stat_storage_align()->usize {core::mem::align_of::<StatStorage>()}
