//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Sole shared parser/formatter implementation for future private libihk consumers.
//! Bodies reused from frozen CLI459 b4d9; no CLI command implementation included.
use core::ffi::{c_char,c_int,c_long,c_ulong,c_void};
use core::ptr::null_mut;
const EINVAL:c_int=22;
macro_rules! c { ($s:literal) => {concat!($s,"\0").as_ptr().cast::<c_char>()}; }
#[repr(C)]
pub struct CpuReq {cpus:*mut c_int,num_cpus:c_int}
#[repr(C)]
pub struct MemReq {sizes:*mut usize,numa_ids:*mut c_int,num_chunks:c_int,min_chunk_size:c_int,max_size_ratio_all:c_int,timeout:c_int}
unsafe extern "C" {
 static mut loglevel:c_int;
 fn __errno_location()->*mut c_int;
 fn strcmp(a:*const c_char,b:*const c_char)->c_int;
 fn strchr(s:*const c_char,c:c_int)->*mut c_char;
 fn strdup(s:*const c_char)->*mut c_char;
 fn strsep(s:*mut *mut c_char,delim:*const c_char)->*mut c_char;
 fn strtol(s:*const c_char,end:*mut *mut c_char,base:c_int)->c_long;
 fn malloc(size:usize)->*mut c_void;
 fn realloc(p:*mut c_void,size:usize)->*mut c_void;
 fn free(p:*mut c_void);
 fn memset(p:*mut c_void,value:c_int,size:usize)->*mut c_void;
 fn snprintf(p:*mut c_char,size:usize,format:*const c_char,...)->c_int;
 fn geteuid()->u32;
 fn open(path:*const c_char,flags:c_int,...)->c_int;
 fn close(fd:c_int)->c_int;
 fn strnlen(p:*const c_char,max:usize)->usize;
 fn write(fd:c_int,p:*const c_void,size:usize)->isize;
}
unsafe fn is(s: *const c_char, t: *const c_char) -> bool { strcmp(s, t) == 0 }

pub(super) unsafe fn cpu_array(list: *const c_char, count: c_int, cpus: *mut c_int) -> c_int {
    if list.is_null() { return 0; }
    let owned = strdup(list);
    if owned.is_null() { return -*__errno_location(); }
    let mut cursor = owned;
    let mut rank: c_int = 0;
    let mut result = 0;
    let mut token = strsep(&mut cursor, c!(","));
    while !token.is_null() {
        if *token == 0 { result = -EINVAL; break; }
        let minus = strchr(token, b'-' as c_int);
        if !minus.is_null() {
            if *minus.add(1) == 0 { result = -EINVAL; break; }
            *minus = 0;
            let mut end = null_mut();
            let start = strtol(token, &mut end, 10) as c_int;
            if *end != 0 { result = -EINVAL; break; }
            let last = strtol(minus.add(1), &mut end, 10) as c_int;
            if *end != 0 { result = -EINVAL; break; }
            let mut i = start;
            while i <= last {
                if !cpus.is_null() && count > rank { *cpus.add(rank as usize) = i; }
                rank = rank.wrapping_add(1);
                // C's increment at INT_MAX is undefined; not an equivalence claim.
                if i == c_int::MAX { break; }
                i += 1;
            }
        } else {
            if !cpus.is_null() && count > rank {
                let mut end = null_mut();
                *cpus.add(rank as usize) = strtol(token, &mut end, 10) as c_int;
                if *end != 0 { result = -EINVAL; break; }
            }
            rank = rank.wrapping_add(1);
        }
        token = strsep(&mut cursor, c!(","));
    }
    free(owned.cast());
    if result < 0 { result } else { rank }
}

unsafe fn mem_parse(token: *const c_char) -> c_long {
    if is(token, c!("all")) || is(token, c!("ALL")) { return -1; }
    let mut end = null_mut();
    let value = strtol(token, &mut end, 10);
    let shift = match *end as u8 {
        b'e'|b'E' => 60, b'p'|b'P' => 50, b't'|b'T' => 40,
        b'g'|b'G' => 30, b'm'|b'M' => 20, b'k'|b'K' => 10,
        0 => 0, _ => return -(EINVAL as c_long),
    };
    value.wrapping_shl(shift)
}

pub(super) unsafe fn mem_array(list: *const c_char, sizes: *mut usize, nodes: *mut c_int) -> c_int {
    if list.is_null() { return 0; }
    let owned = strdup(list);
    if owned.is_null() { return -*__errno_location(); }
    let mut cursor = owned;
    let mut count: c_int = 0;
    let mut result = 0;
    let mut token = strsep(&mut cursor, c!(","));
    while !token.is_null() {
        if *token == 0 { result = -EINVAL; break; }
        let mut tail = token;
        token = strsep(&mut tail, c!("@"));
        if !tail.is_null() && (*token == 0 || *tail == 0) { result = -EINVAL; break; }
        if !sizes.is_null() {
            let size = mem_parse(token);
            if size < 0 && size != -1 { result = size as c_int; break; }
            *sizes.add(count as usize) = size as usize;
            if !nodes.is_null() && !tail.is_null() {
                let mut end = null_mut();
                let node = strtol(tail, &mut end, 10);
                if *end != 0 { result = -EINVAL; break; }
                *nodes.add(count as usize) = node as c_int;
            }
        }
        count = count.wrapping_add(1);
        token = strsep(&mut cursor, c!(","));
    }
    free(owned.cast());
    if result < 0 { result } else { count }
}

unsafe fn zero_mem() -> MemReq {
    MemReq { sizes: null_mut(), numa_ids: null_mut(), num_chunks: 0,
        min_chunk_size: 0, max_size_ratio_all: 0, timeout: 0 }
}

unsafe fn append(s: &mut *mut c_char, capacity: &mut usize, offset: c_int, kind: u8, a: usize, b: c_int) -> c_int {
    loop {
        let p = (*s).offset(offset as isize);
        let room = capacity.wrapping_sub(offset as usize);
        let written = match kind {
            0 => snprintf(p, room, c!("%d,"), a as c_int),
            1 => snprintf(p, room, c!("%d-"), a as c_int),
            2 => snprintf(p, room, c!("%d"), a as c_int),
            3 => snprintf(p, room, c!("%lu@%d"), a as c_ulong, b),
            _ => snprintf(p, room, c!(",")),
        };
        if written < 0 || room >= (written as usize + 1) { return written; }
        while capacity.wrapping_sub(offset as usize) < written as usize + 1 { *capacity = capacity.wrapping_mul(2); }
        let next = realloc((*s).cast(), *capacity).cast::<c_char>();
        if next.is_null() { free((*s).cast()); *s = null_mut(); return -1; }
        *s = next;
    }
}

unsafe fn query_string(cpu: &CpuReq, mem: &MemReq, is_cpu: bool) -> *mut c_char {
    let mut capacity = 64;
    let mut s = malloc(capacity).cast::<c_char>();
    if s.is_null() { return s; }
    memset(s.cast(), 0, capacity);
    let mut n: c_int = 0;
    if is_cpu {
        let mut previous: c_int = -10;
        let mut sequence = false;
        for i in 0..cpu.num_cpus.max(0) as usize {
            let current = *cpu.cpus.add(i);
            if previous != current.wrapping_sub(1) {
                if previous > 0 { n += append(&mut s, &mut capacity, n, 0, previous as usize, 0); }
                sequence = false;
            } else if !sequence {
                n += append(&mut s, &mut capacity, n, 1, previous as usize, 0);
                sequence = true;
            }
            if s.is_null() { return s; }
            previous = current;
        }
        if previous >= 0 { append(&mut s, &mut capacity, n, 2, previous as usize, 0); }
    } else {
        for i in 0..mem.num_chunks.max(0) as usize {
            n += append(&mut s, &mut capacity, n, 3, *mem.sizes.add(i), *mem.numa_ids.add(i));
            if s.is_null() { return s; }
            if i != mem.num_chunks as usize - 1 { n += append(&mut s, &mut capacity, n, 4, 0, 0); }
            if s.is_null() { return s; }
        }
    }
    s
}
unsafe fn log<F:FnOnce(*mut c_char,usize)>(format:F) {
 if unsafe {loglevel}<1 || unsafe {geteuid()}!=0 {return;}
 let mut text=[0 as c_char;3840];format(text.as_mut_ptr(),text.len());
 let fd=unsafe {open(c!("/dev/kmsg"),1)};
 let len=unsafe {strnlen(text.as_ptr(),3839)}+1;let mut offset=0;
 while offset<len {let n=unsafe {write(fd,text.as_ptr().add(offset).cast(),len-offset)};if n<=0 {break;}offset+=n as usize;}
 unsafe {close(fd);}
}
#[no_mangle]
pub unsafe extern "C" fn cpu_str2count(list:*mut c_char)->c_int {unsafe {cpu_array(list,0,null_mut())}}
#[no_mangle]
pub unsafe extern "C" fn cpu_str2req(list:*mut c_char,count:c_int,req:*mut CpuReq)->c_int {
 if req.is_null(){unsafe {log(|p,z|{snprintf(p,z,c!("cpu_str2req: error: invalid req pointer (NULL)\n"));});}return -22;}
 let result=unsafe {cpu_array(list,count,(*req).cpus)};unsafe {(*req).num_cpus=result;}result
}
#[no_mangle]
pub unsafe extern "C" fn cpu_req2str(req:*mut CpuReq)->*mut c_char {
 unsafe {query_string(&*req,&zero_mem(),true)}
}
#[no_mangle]
pub unsafe extern "C" fn mem_str2count(list:*mut c_char)->c_int {unsafe {mem_array(list,null_mut(),null_mut())}}
#[no_mangle]
pub unsafe extern "C" fn mem_str2req(list:*mut c_char,req:*mut MemReq)->c_int {
 let count=unsafe {mem_str2count(list)};if count<=0{return count;}
 unsafe {(*req).num_chunks=count;}
 let result=unsafe {mem_array(list,(*req).sizes,(*req).numa_ids)};if result<0 {result}else{0}
}
#[no_mangle]
pub unsafe extern "C" fn mem_req2str(req:*mut MemReq)->*mut c_char {
 unsafe {query_string(&CpuReq{cpus:null_mut(),num_cpus:0},&*req,false)}
}
