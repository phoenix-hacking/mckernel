// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private x86_64 Linux candidate. Port of pinned ihkconfig.c and its narrow
// private parsing/format helpers. libihk is a TEMPORARY C ABI dependency.
#![no_std]
#![no_main]
#![allow(non_upper_case_globals)]
#[cfg(not(all(target_os = "linux", target_arch = "x86_64")))]
compile_error!("This candidate is bound to the selected Linux x86_64 UAPI");
use core::ffi::{c_char, c_int, c_long, c_uint, c_ulong, c_void};
use core::ptr::null_mut;
macro_rules! c { ($s:literal) => { concat!($s, "\0").as_ptr().cast::<c_char>() }; }
const EINVAL: c_int = 22;
const ENOMEM: c_int = 12;
const CREATE: c_ulong = 0x112900;
const DESTROY: c_ulong = 0x112901;
const RELEASE_CPU: c_ulong = 0x112903;
const RELEASE_MEM: c_ulong = 0x112905;
const QUERY_CPU: c_ulong = 0x112906;
const QUERY_MEM: c_ulong = 0x112907;
const GET_BUILDID: c_ulong = 0x11290b;
const GET_NUM_CPUS: c_ulong = 0x11290c;
const DEBUG: c_ulong = 0x122900;
const BUILDID_CAPACITY: usize = env!("IHKCONFIG_BUILDID").len() + 1;
#[repr(C)]
struct CpuReq { cpus: *mut c_int, num_cpus: c_int }
#[repr(C)]
struct MemReq {
    sizes: *mut usize, numa_ids: *mut c_int, num_chunks: c_int,
    min_chunk_size: c_int, max_size_ratio_all: c_int, timeout: c_int,
}
#[repr(C)]
struct MemChunk { size: c_ulong, numa_node_number: c_int }
const _: [(); 16] = [(); core::mem::size_of::<CpuReq>()];
const _: [(); 32] = [(); core::mem::size_of::<MemReq>()];
const _: [(); 16] = [(); core::mem::size_of::<MemChunk>()];
extern "C" {
    static mut stderr: *mut c_void;
    fn printf(fmt: *const c_char, ...) -> c_int;
    fn fprintf(stream: *mut c_void, fmt: *const c_char, ...) -> c_int;
    fn snprintf(dst: *mut c_char, size: usize, fmt: *const c_char, ...) -> c_int;
    fn sprintf(dst: *mut c_char, fmt: *const c_char, ...) -> c_int;
    fn strcmp(a: *const c_char, b: *const c_char) -> c_int;
    fn strrchr(s: *const c_char, ch: c_int) -> *mut c_char;
    fn strchr(s: *const c_char, ch: c_int) -> *mut c_char;
    fn strdup(s: *const c_char) -> *mut c_char;
    fn strsep(s: *mut *mut c_char, delim: *const c_char) -> *mut c_char;
    fn strtol(s: *const c_char, end: *mut *mut c_char, base: c_int) -> c_long;
    fn strtoll(s: *const c_char, end: *mut *mut c_char, base: c_int) -> i64;
    fn atoi(s: *const c_char) -> c_int;
    fn calloc(n: usize, size: usize) -> *mut c_void;
    fn malloc(size: usize) -> *mut c_void;
    fn realloc(p: *mut c_void, size: usize) -> *mut c_void;
    fn free(p: *mut c_void);
    fn memset(p: *mut c_void, value: c_int, size: usize) -> *mut c_void;
    fn __errno_location() -> *mut c_int;
    fn open(path: *const c_char, flags: c_int, ...) -> c_int;
    fn close(fd: c_int) -> c_int;
    fn ioctl(fd: c_int, request: c_ulong, ...) -> c_int;
    fn pread(fd: c_int, buf: *mut c_void, size: usize, off: c_long) -> isize;
    fn pwrite(fd: c_int, buf: *const c_void, size: usize, off: c_long) -> isize;
    fn mmap(p: *mut c_void, size: usize, prot: c_int, flags: c_int, fd: c_int, off: c_long) -> *mut c_void;
    fn munmap(p: *mut c_void, size: usize) -> c_int;
    fn perror(label: *const c_char);
    fn abort() -> !;
    // Public ihklib.h ABI only. No _ihk_* or private parser imports.
    fn ihk_reserve_cpu(index: c_int, cpus: *mut c_int, count: c_int) -> c_int;
    fn ihk_reserve_mem(index: c_int, chunks: *mut MemChunk, count: c_int) -> c_int;
    fn ihk_get_num_os_instances(index: c_int) -> c_int;
    fn ihk_get_os_instances(index: c_int, indices: *mut c_int, count: c_int) -> c_int;
}
#[panic_handler]
fn panic(_: &core::panic::PanicInfo<'_>) -> ! { unsafe { abort() } }
#[no_mangle]
pub static mut __argc: c_int = 0;
#[no_mangle]
pub static mut __argv: *mut *mut c_char = null_mut();
unsafe fn arg(i: usize) -> *mut c_char { *__argv.add(i) }
unsafe fn is(s: *const c_char, t: *const c_char) -> bool { strcmp(s, t) == 0 }
unsafe fn checked_fail(func: *const c_char, call: *const c_char) -> c_int {
    printf(c!("%s,%s failed\n"), func, call); -1
}
unsafe fn usage() {
    let mut cmd = strrchr(arg(0), b'/' as c_int);
    if cmd.is_null() { cmd = arg(0); } else { cmd = cmd.add(1); }
    fprintf(stderr, c!("Usage: %s (dev #) (action)\n"), cmd);
    fprintf(stderr, c!("action:\n    create\n    destroy\n    scratch\n    sbox\n    read\n    mmap\n    ioctl\n    clear_kmsg\n    clear_kmsg_write\n    reserve cpu|mem [resources]\n    release cpu|mem [resources]\n    query cpu|mem\n    get os_instances\n    get buildid\n"));
}
// Exact defined parsing semantics of ihklib.c: a count-only pass intentionally
// does not validate individual non-range CPU tokens or memory sizes/node IDs.
unsafe fn cpu_array(list: *const c_char, count: c_int, cpus: *mut c_int) -> c_int {
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
unsafe fn mem_array(list: *const c_char, sizes: *mut usize, nodes: *mut c_int) -> c_int {
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
unsafe fn reserve(index: c_int) -> c_int {
    if __argc < 5 { usage(); return -1; }
    let list = arg(4);
    let cpu = is(arg(3), c!("cpu"));
    if !cpu && !is(arg(3), c!("mem")) { usage(); return -EINVAL; }
    let count = if cpu { cpu_array(list, 0, null_mut()) } else { mem_array(list, null_mut(), null_mut()) };
    let ret;
    if count <= 0 { ret = -EINVAL; }
    else if cpu {
        let cpus = calloc(4, count as usize).cast::<c_int>();
        ret = if cpus.is_null() { -ENOMEM }
            else if cpu_array(list, count, cpus) < 0 { -EINVAL }
            else { ihk_reserve_cpu(index, cpus, count) };
        free(cpus.cast());
    } else {
        let chunks = calloc(core::mem::size_of::<MemChunk>(), count as usize).cast::<MemChunk>();
        if chunks.is_null() { ret = -ENOMEM; }
        else {
            // Preserve mem_str2chunks' two extra count/allocation/parse passes.
            let again = mem_array(list, null_mut(), null_mut());
            if again <= 0 { ret = again; }
            else {
                let sizes = calloc(8, again as usize).cast::<usize>();
                let nodes = if sizes.is_null() { null_mut() } else { calloc(8, again as usize).cast::<c_int>() };
                if sizes.is_null() || nodes.is_null() { ret = -ENOMEM; }
                else {
                    let parsed = mem_array(list, sizes, nodes);
                    if parsed >= 0 {
                        for i in 0..again as usize {
                            (*chunks.add(i)).size = *sizes.add(i) as c_ulong;
                            (*chunks.add(i)).numa_node_number = *nodes.add(i);
                        }
                    }
                    // mem_str2chunks releases temporary arrays before the
                    // public reservation call in the original library.
                    free(sizes.cast()); free(nodes.cast());
                    ret = if parsed < 0 { parsed } else { ihk_reserve_mem(index, chunks, count) };
                }
                if sizes.is_null() || nodes.is_null() { free(sizes.cast()); free(nodes.cast()); }
            }
        }
        free(chunks.cast());
    }
    if ret != 0 {
        if cpu { printf(c!("do_reserve: error: reserving CPUs: %s\n"), list); }
        else { printf(c!("do_reserve: error: reserving memory: %s\n"), list); }
    }
    ret
}
unsafe fn zero_mem() -> MemReq {
    MemReq { sizes: null_mut(), numa_ids: null_mut(), num_chunks: 0,
        min_chunk_size: 0, max_size_ratio_all: 0, timeout: 0 }
}
unsafe fn release(fd: c_int) -> c_int {
    if __argc < 5 { usage(); return -1; }
    let mut cpu = CpuReq { cpus: null_mut(), num_cpus: 0 };
    let mut mem = zero_mem();
    let ret = (|| {
        if is(arg(3), c!("cpu")) {
            let count = cpu_array(arg(4), 0, null_mut());
            if count <= 0 { return checked_fail(c!("do_release"), c!("get num of requested cpus")); }
            cpu.cpus = calloc(4, count as usize).cast();
            if cpu.cpus.is_null() { return checked_fail(c!("do_release"), c!("allocate request space")); }
            cpu.num_cpus = cpu_array(arg(4), count, cpu.cpus);
            if cpu.num_cpus < 0 { return checked_fail(c!("do_release"), c!("parse provided cpulist string")); }
            let ret = ioctl(fd, RELEASE_CPU, &cpu as *const CpuReq);
            if ret != 0 { fprintf(stderr, c!("error: releasing CPUs: %s\n"), arg(4)); }
            ret
        } else if is(arg(3), c!("mem")) {
            let all = is(arg(4), c!("all"));
            let count = if all {
                if ioctl(fd, QUERY_MEM, &mut mem as *mut MemReq) != 0 { fprintf(stderr, c!("error: get mem chunks\n")); }
                mem.num_chunks
            } else {
                let n = mem_array(arg(4), null_mut(), null_mut());
                if n <= 0 { return checked_fail(c!("do_release"), c!("get num of requested mems")); }
                n
            };
            mem.sizes = calloc(8, count as usize).cast();
            if mem.sizes.is_null() { return checked_fail(c!("do_release"), c!("allocate request space")); }
            mem.numa_ids = calloc(4, count as usize).cast();
            if mem.numa_ids.is_null() { return checked_fail(c!("do_release"), c!("allocate request space")); }
            if all {
                if ioctl(fd, QUERY_MEM, &mut mem as *mut MemReq) != 0 { fprintf(stderr, c!("error: querying memory\n")); }
            } else {
                let n = mem_array(arg(4), null_mut(), null_mut());
                let parsed = if n <= 0 { n } else {
                    mem.num_chunks = n;
                    mem_array(arg(4), mem.sizes, mem.numa_ids)
                };
                if parsed < 0 { return checked_fail(c!("do_release"), c!("parse provided memlist string")); }
            }
            let ret = ioctl(fd, RELEASE_MEM, &mem as *const MemReq);
            if ret != 0 { fprintf(stderr, c!("error: releasing memory: %s\n"), arg(4)); }
            ret
        } else { usage(); -EINVAL }
    })();
    free(cpu.cpus.cast()); free(mem.sizes.cast()); free(mem.numa_ids.cast());
    ret
}
// Small printf-style append preserving the original 64-byte growth strategy.
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
unsafe fn query(fd: c_int) -> c_int {
    if __argc < 4 { usage(); return -1; }
    let mut cpu = CpuReq { cpus: null_mut(), num_cpus: 0 };
    let mut mem = zero_mem();
    let mut result = null_mut();
    let ret = (|| {
        let is_cpu = is(arg(3), c!("cpu"));
        let ret;
        if is_cpu {
            cpu.num_cpus = ioctl(fd, GET_NUM_CPUS);
            if cpu.num_cpus < 0 { fprintf(stderr, c!("error: querying num CPUs\n")); }
            cpu.cpus = calloc(4, cpu.num_cpus as usize).cast();
            if cpu.cpus.is_null() { return checked_fail(c!("do_query"), c!("allocate request space")); }
            ret = ioctl(fd, QUERY_CPU, &mut cpu as *mut CpuReq);
            if ret != 0 { fprintf(stderr, c!("error: querying CPUs\n")); }
        } else if is(arg(3), c!("mem")) {
            if ioctl(fd, QUERY_MEM, &mut mem as *mut MemReq) != 0 { fprintf(stderr, c!("error: get mem chunks\n")); }
            let count = mem.num_chunks;
            mem.sizes = calloc(8, count as usize).cast();
            if mem.sizes.is_null() { return checked_fail(c!("do_query"), c!("allocate request space")); }
            mem.numa_ids = calloc(4, count as usize).cast();
            if mem.numa_ids.is_null() { return checked_fail(c!("do_query"), c!("allocate request space")); }
            ret = ioctl(fd, QUERY_MEM, &mut mem as *mut MemReq);
            if ret != 0 { fprintf(stderr, c!("error: querying memory\n")); }
        } else { usage(); return -EINVAL; }
        result = query_string(&cpu, &mem, is_cpu);
        if result.is_null() { return checked_fail(c!("do_query"), c!("build result string")); }
        if ret == 0 { printf(c!("%s\n"), result); }
        ret
    })();
    free(cpu.cpus.cast()); free(mem.sizes.cast()); free(mem.numa_ids.cast()); free(result.cast());
    ret
}
unsafe fn get(index: c_int) -> c_int {
    if __argc < 4 { usage(); return -1; }
    if is(arg(3), c!("os_instances")) {
        let count = ihk_get_num_os_instances(index);
        if count < 0 { return checked_fail(c!("do_get_os_instances"), c!("ihk_get_num_os_instances")); }
        let indices = calloc(count as usize, 4).cast::<c_int>();
        if indices.is_null() { return checked_fail(c!("do_get_os_instances"), c!("calloc")); }
        let ret = if ihk_get_os_instances(index, indices, count) < 0 {
            checked_fail(c!("do_get_os_instances"), c!("ihk_get_os_instances"))
        } else {
            for i in 0..count as usize {
                if i != 0 { printf(c!(",")); }
                printf(c!("%d"), *indices.add(i));
            }
            printf(c!("\n")); 0
        };
        free(indices.cast()); ret
    } else if is(arg(3), c!("buildid")) {
        let mut path = [0 as c_char; 128];
        let mut result = [0 as c_char; BUILDID_CAPACITY];
        sprintf(path.as_mut_ptr(), c!("/dev/mcd%d"), index);
        let fd = open(path.as_ptr(), 0);
        if fd < 0 { return checked_fail(c!("do_get_buildid"), c!("open")); }
        let ret = if ioctl(fd, GET_BUILDID, result.as_mut_ptr()) != 0 {
            checked_fail(c!("do_get_buildid"), c!("IHK_DEVICE_GET_BUILDID"))
        } else {
            // The original prints indeterminate/nonterminated bytes if the
            // provider violates its string contract. Bound that case here.
            *result.as_mut_ptr().add(BUILDID_CAPACITY - 1) = 0;
            printf(c!("%s\n"), result.as_ptr()); 0
        };
        close(fd); ret
    } else {
        fprintf(stderr, c!("Unknown target : %s\n"), arg(3)); usage(); -1
    }
}
unsafe fn fd_action(fd: c_int, action: *const c_char) -> c_int {
    if is(action, c!("create")) {
        let r = ioctl(fd, CREATE, 0 as c_int);
        if r != 0 { fprintf(stderr, c!("error: creating OS instance\n")); } r
    } else if is(action, c!("destroy")) {
        if __argc < 4 { printf(c!("Usage: %s (dev #) destroy (os #)\n"), arg(0)); return 1; }
        let os = atoi(arg(3)); let r = ioctl(fd, DESTROY, os);
        if r != 0 { fprintf(stderr, c!("error: destroying OS instance %d\n"), os); } r
    } else if is(action, c!("scratch")) {
        let mut r: c_long = 0;
        for i in 0..16 as c_int { r = ioctl(fd, DEBUG, i) as c_long; printf(c!("Scratch %2d = %08lx\n"), i, r as c_ulong); }
        r as c_int
    } else if is(action, c!("sbox")) {
        let index = if __argc > 3 { strtol(arg(3), null_mut(), 16) as c_int } else { 0x1030 };
        let r = ioctl(fd, DEBUG + 1, index) as c_long;
        printf(c!("SBOX %04x = %08lx\n"), index as c_uint, r as c_ulong); r as c_int
    } else if is(action, c!("read")) || is(action, c!("mmap")) || is(action, c!("clear_kmsg")) || is(action, c!("clear_kmsg_write")) {
        if __argc <= 3 { fprintf(stderr, c!("Address is not specified!\n")); return 1; }
        let address = strtol(arg(3), null_mut(), 16);
        if is(action, c!("read")) {
            // Original's short-read tail is indeterminate. Zeroing gives defined
            // behavior; exact equivalence is claimed only for full reads/errors.
            let mut buf = [0u8; 16];
            if pread(fd, buf.as_mut_ptr().cast(), 16, address) < 0 { perror(c!("pread")); return 1; }
            for byte in buf { printf(c!("%02x "), byte as c_uint); }
            printf(c!("\n")); 0
        } else if is(action, c!("clear_kmsg_write")) {
            let zero = 0u32;
            if pwrite(fd, (&zero as *const u32).cast(), 4, address) < 0 { perror(c!("pwrite")); return 1; } 0
        } else {
            let p = mmap(null_mut(), 4096, 3, 1, fd, address);
            if p as usize == usize::MAX { perror(c!("mmap")); return 1; }
            if is(action, c!("clear_kmsg")) {
                printf(c!("Before write : %d\n"), core::ptr::read_unaligned(p.cast::<u32>()) as c_int);
                core::ptr::write_unaligned(p.cast::<u32>(), 0);
            } else {
                for i in 0..16 { printf(c!("%02x "), *p.cast::<u8>().add(i) as c_uint); }
                printf(c!("\n"));
            }
            munmap(p, 4096); 0
        }
    } else if is(action, c!("ioctl")) {
        if __argc <= 4 { fprintf(stderr, c!("No req or arg is specified.\n")); return 1; }
        let request = strtol(arg(3), null_mut(), 16) as c_uint;
        let argument = strtoll(arg(4), null_mut(), 16) as c_ulong;
        let r = ioctl(fd, request as c_ulong, argument);
        if r != 0 { fprintf(stderr, c!("error: ioctl()\n")); } r
    } else if cfg!(ihkconfig_krm_workaround) && is(action, c!("reserve_mem_max_ratio")) {
        if __argc <= 3 { fprintf(stderr, c!("error: specify reserve_mem_max_ratio.\n")); return 1; }
        let value = strtol(arg(3), null_mut(), 10) as c_ulong;
        let r = ioctl(fd, 0x11290e as c_ulong, value);
        if r != 0 { fprintf(stderr, c!("error: ioctl\n")); } r
    } else if is(action, c!("release")) { release(fd) }
    else if is(action, c!("query")) { query(fd) }
    else { fprintf(stderr, c!("Unknown action : %s\n"), action); usage(); 0 }
}
#[no_mangle]
pub unsafe extern "C" fn main(argc: c_int, argv: *mut *mut c_char) -> c_int {
    __argc = argc; __argv = argv;
    if argc < 3 { usage(); return 1; }
    let index = atoi(arg(1));
    if is(arg(2), c!("get")) { return get(index); }
    if is(arg(2), c!("reserve")) { return reserve(index); }
    let mut path = [0 as c_char; 128];
    sprintf(path.as_mut_ptr(), c!("/dev/mcd%d"), index);
    let fd = open(path.as_ptr(), 2);
    if fd < 0 { perror(c!("open")); return 1; }
    let r = fd_action(fd, arg(2)); close(fd); r
}
