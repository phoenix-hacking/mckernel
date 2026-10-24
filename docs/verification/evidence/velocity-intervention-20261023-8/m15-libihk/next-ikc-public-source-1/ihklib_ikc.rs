//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Exact public IKC ABI; reuse sole common CPU parser, formatter allocator and logger.
use core::ffi::{c_char,c_int,c_void};
use core::ptr::null_mut;
use super::ihklib_cli_parsers::{cpu_array,append,log};
#[repr(C)]
pub struct IhkIkcReq {pub src_cpus:*mut c_int,pub dst_cpus:*mut c_int,pub num_cpus:c_int}
const _:()={assert!(core::mem::size_of::<IhkIkcReq>()==24);assert!(core::mem::offset_of!(IhkIkcReq,num_cpus)==16);};
unsafe extern "C" {
 fn __errno_location()->*mut c_int;
 fn strdup(s:*const c_char)->*mut c_char;
 fn strsep(s:*mut *mut c_char,delim:*const c_char)->*mut c_char;
 fn strtol(s:*const c_char,end:*mut *mut c_char,base:c_int)->core::ffi::c_long;
 fn malloc(size:usize)->*mut c_void;
 fn calloc(count:usize,size:usize)->*mut c_void;
 fn free(p:*mut c_void);
 fn memset(p:*mut c_void,value:c_int,size:usize)->*mut c_void;
 fn snprintf(p:*mut c_char,size:usize,format:*const c_char,...)->c_int;
}
unsafe fn parse(list:*mut c_char,limit:c_int,src:*mut c_int,dst:*mut c_int)->c_int {
 if list.is_null(){return 0;}
 let owned=unsafe {strdup(list)};if owned.is_null(){return unsafe {-*__errno_location()};}
 let mut cursor=owned;let mut total:c_int=0;let mut scratch=[0 as c_int;1024];
 let result=(||->c_int{
  let mut token=unsafe {strsep(&mut cursor,b"+\0".as_ptr().cast())};
  while !token.is_null(){
   if unsafe {*token}==0{return -22;}
   let cpus=unsafe {strsep(&mut token,b":\0".as_ptr().cast())};
   if unsafe {*cpus}==0||token.is_null(){return -22;}
   let count=unsafe {cpu_array(cpus,1024,scratch.as_mut_ptr())};if count<=0{return -22;}
   if unsafe {*token}==0{return -22;}
   let mut end=null_mut();let target=unsafe {strtol(token,&mut end,10)} as c_int;
   if unsafe {*end}!=0{return -22;}
   for i in 0..count {
    if !src.is_null()&&!dst.is_null()&&limit>total {
     // Same C validity domain: copying beyond the1024-entry scratch is not qualified.
     unsafe {src.offset(total as isize).write(scratch.as_ptr().offset(i as isize).read());dst.offset(total as isize).write(target);}
    }
    total=total.wrapping_add(1);
   }
   token=unsafe {strsep(&mut cursor,b"+\0".as_ptr().cast())};
  }
  total
 })();
 unsafe {free(owned.cast());}result
}
#[no_mangle]
pub unsafe extern "C" fn ikc_str2count(list:*mut c_char)->c_int {unsafe {parse(list,0,null_mut(),null_mut())}}
#[no_mangle]
pub unsafe extern "C" fn ikc_str2req(list:*mut c_char,limit:c_int,req:*mut IhkIkcReq)->c_int {
 if req.is_null(){unsafe {log(|p,z|{snprintf(p,z,b"ikc_str2req: error: invalid req pointer (NULL)\n\0".as_ptr().cast());});}return -22;}
 let n=unsafe {parse(list,limit,(*req).src_cpus,(*req).dst_cpus)};unsafe {(*req).num_cpus=n;}n
}
unsafe fn allocation_error(kind:u8){unsafe {log(|p,z|{
 let text=match kind {0=>b"ikc_req2str: error: allocating rank\n\0".as_ptr(),1=>b"ikc_req2str: error: allocating num_ikc_ssets\n\0".as_ptr(),_=>b"ikc_req2str: error: allocating ikc_sset_members\n\0".as_ptr()};
 snprintf(p,z,text.cast());
});}}
#[no_mangle]
pub unsafe extern "C" fn ikc_req2str(req:*mut IhkIkcReq)->*mut c_char {
 let mut capacity=64usize;let mut text=unsafe {malloc(capacity).cast::<c_char>()};if text.is_null(){return text;}
 unsafe {memset(text.cast(),0,capacity);}
 let rank=unsafe {calloc(core::mem::size_of::<c_int>(),1024).cast::<c_int>()};
 let mut sizes:*mut c_int=null_mut();let mut members:*mut *mut c_int=null_mut();
 let _=(||->(){
  if rank.is_null(){unsafe {allocation_error(0);}return;}
  sizes=unsafe {calloc(core::mem::size_of::<c_int>(),1024).cast()};if sizes.is_null(){unsafe {allocation_error(1);}return;}
  members=unsafe {calloc(core::mem::size_of::<*mut c_int>(),1024).cast()};if members.is_null(){unsafe {allocation_error(2);}return;}
  let mut max_dst:c_int=-1;
  for i in 0..unsafe {(*req).num_cpus} {
   let source=unsafe {(*req).src_cpus.offset(i as isize).read()};let target=unsafe {(*req).dst_cpus.offset(i as isize).read()};
   unsafe {rank.offset(source as isize).write(sizes.offset(target as isize).read());let p=sizes.offset(target as isize);p.write(p.read().wrapping_add(1));}
   if max_dst<target{max_dst=target;}
  }
  for i in 0..unsafe {(*req).num_cpus} {
   let source=unsafe {(*req).src_cpus.offset(i as isize).read()};let target=unsafe {(*req).dst_cpus.offset(i as isize).read()};
   let slot=unsafe {members.offset(target as isize)};
   if unsafe {slot.read().is_null()} {
    let count=unsafe {sizes.offset(target as isize).read()};let p=unsafe {calloc(core::mem::size_of::<c_int>(),count as usize).cast::<c_int>()};unsafe {slot.write(p);}
    if p.is_null(){unsafe {allocation_error(2);}return;}
   }
   unsafe {slot.read().offset(rank.offset(source as isize).read() as isize).write(source);}
  }
  let mut n:c_int=0;
  for target in 0..1024 {
   let count=unsafe {sizes.add(target).read()};if count==0{continue;}
   for i in 0..count {
    let source=unsafe {members.add(target).read().offset(i as isize).read()};
    n=n.wrapping_add(unsafe {append(&mut text,&mut capacity,n,2,source as usize,0)});
    if text.is_null(){return;} // Defined NULL extension where original next write would be UB.
    if i!=count-1{n=n.wrapping_add(unsafe {append(&mut text,&mut capacity,n,4,0,0)});if text.is_null(){return;}}
   }
   n=n.wrapping_add(unsafe {append(&mut text,&mut capacity,n,5,target,0)});if text.is_null(){return;}
   if target as c_int!=max_dst {n=n.wrapping_add(unsafe {append(&mut text,&mut capacity,n,6,0,0)});if text.is_null(){return;}}
  }
 })();
 if !members.is_null(){for target in 0..1024{unsafe {free(members.add(target).read().cast());}}}
 unsafe {free(members.cast());free(sizes.cast());free(rank.cast());}text
}
#[cfg(ihklib_ikc_fixture)]
#[no_mangle]
pub extern "C" fn ihklib_ikc_req_size()->usize{core::mem::size_of::<IhkIkcReq>()}
#[cfg(ihklib_ikc_fixture)]
#[no_mangle]
pub extern "C" fn ihklib_ikc_req_count_offset()->usize{core::mem::offset_of!(IhkIkcReq,num_cpus)}
