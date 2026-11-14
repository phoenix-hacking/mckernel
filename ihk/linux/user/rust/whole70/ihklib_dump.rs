//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Correctness successor of the separate frozen faithful-parity packet.
//! Included as a module in the existing libihk Rust root.
//! ABI constants/types must be generated from the admitting owner's selected real headers.

use core::ffi::{c_char, c_int, c_long, c_uint, c_ulong, c_void};
use core::mem::{offset_of, size_of};
use core::ptr::{addr_of_mut, null, null_mut};

mod abi {
    include!(env!("MCKERNEL_DUMP_ABI_RS"));
}

#[cfg(not(all(target_os = "linux", target_arch = "x86_64", target_pointer_width = "64")))]
compile_error!("dump qualification currently covers Linux x86_64 LP64 only");
#[cfg(ihklib_debug)]
compile_error!("DEBUG dump diagnostics need the existing library logging owner's ABI join");

#[repr(C)]
struct DumpArgs {
    cmd: c_int,
    level: c_uint,
    start: c_long,
    size: c_long,
    buf: *mut c_void,
    spare: [*mut c_void; 4],
}

#[repr(C)]
struct MemoryChunk {
    addr: c_ulong,
    size: c_ulong,
}

#[repr(C)]
struct MemoryChunks {
    nr_chunks: c_int,
    kernel_base: c_ulong,
    phys_start: c_ulong,
}

const _: [(); abi::DUMP_ARGS_SIZE] = [(); size_of::<DumpArgs>()];
const _: [(); abi::DUMP_ARGS_LEVEL] = [(); offset_of!(DumpArgs, level)];
const _: [(); abi::DUMP_ARGS_START] = [(); offset_of!(DumpArgs, start)];
const _: [(); abi::DUMP_ARGS_SIZE_FIELD] = [(); offset_of!(DumpArgs, size)];
const _: [(); abi::DUMP_ARGS_BUF] = [(); offset_of!(DumpArgs, buf)];
const _: [(); abi::DUMP_ARGS_SPARE] = [(); offset_of!(DumpArgs, spare)];
const _: [(); abi::MEMORY_CHUNK_SIZE] = [(); size_of::<MemoryChunk>()];
const _: [(); abi::MEMORY_CHUNK_SIZE_FIELD] = [(); offset_of!(MemoryChunk, size)];
const _: [(); abi::MEMORY_CHUNKS_SIZE] = [(); size_of::<MemoryChunks>()];
const _: [(); abi::MEMORY_CHUNKS_KERNEL_BASE] = [(); offset_of!(MemoryChunks, kernel_base)];
const _: [(); abi::MEMORY_CHUNKS_PHYS_START] = [(); offset_of!(MemoryChunks, phys_start)];

unsafe extern "C" {
    fn ihklib_os_open(index: c_int) -> c_int;
    fn ihk_os_get_status(index: c_int) -> c_int;
    fn __errno_location() -> *mut c_int;
    fn ioctl(fd: c_int, request: c_ulong, ...) -> c_int;
    fn close(fd: c_int) -> c_int;
    fn malloc(size: usize) -> *mut c_void;
    fn free(pointer: *mut c_void);
    fn time(result: *mut c_long) -> c_long;
    fn localtime(value: *const c_long) -> *mut c_void;
    fn asctime(value: *const c_void) -> *mut c_char;
    fn gethostname(name: *mut c_char, size: usize) -> c_int;
    fn getuid() -> c_uint;
    fn getpwuid(uid: c_uint) -> *mut c_void;
    fn strlen(value: *const c_char) -> usize;
    fn strrchr(value: *const c_char, character: c_int) -> *mut c_char;
    fn access(path: *const c_char, mode: c_int) -> c_int;
    fn snprintf(out: *mut c_char, size: usize, format: *const c_char, ...) -> c_int;
    fn bfd_init() -> c_uint;
    fn bfd_fopen(path: *const c_char, target: *const c_char, mode: *const c_char,
        fd: c_int) -> *mut c_void;
    fn bfd_set_format(file: *mut c_void, format: c_int) -> abi::BfdBool;
    fn bfd_make_section_anyway(file: *mut c_void, name: *const c_char) -> *mut c_void;
    fn bfd_set_section_size(section: *mut c_void, size: c_ulong) -> abi::BfdBool;
    fn bfd_set_section_flags(section: *mut c_void, flags: c_uint) -> abi::BfdBool;
    fn bfd_get_section_by_name(file: *mut c_void, name: *const c_char) -> *mut c_void;
    fn bfd_set_section_contents(file: *mut c_void, section: *mut c_void,
        contents: *const c_void, offset: c_long, size: c_ulong) -> abi::BfdBool;
    fn bfd_close(file: *mut c_void) -> abi::BfdBool;
}

// Preserve the original static buffer, including its contents if the second
// gethostname fails. Callers must serialize dump calls, as for the C implementation.
static mut HOSTNAME: [c_char; abi::HOSTNAME_CAPACITY] = [0; abi::HOSTNAME_CAPACITY];
const TRANSFER_SIZE: usize = 0x100000;
const NAME_SIZE: usize = 32;

unsafe fn neg_errno() -> c_int {
    // SAFETY: glibc returns this calling thread's live errno cell.
    unsafe { -*__errno_location() }
}

unsafe fn dump_command(fd: c_int, args: &mut DumpArgs, command: c_int) -> Result<(), c_int> {
    args.cmd = command;
    // SAFETY: args is an initialized, uniquely borrowed request for this synchronous ioctl.
    if unsafe { ioctl(fd, abi::IHK_OS_DUMP, args as *mut DumpArgs) } != 0 {
        Err(unsafe { neg_errno() })
    } else {
        Ok(())
    }
}

unsafe fn username(passwd: *mut c_void) -> *mut c_char {
    // SAFETY: successful getpwuid supplies a live libc record; the offset is header witnessed.
    unsafe { passwd.cast::<u8>().add(abi::PASSWD_NAME).cast::<*mut c_char>().read() }
}

// A passwd record may be absent without a libc error. Clear errno only around
// that lookup; successful/absent optional metadata must not reset the caller's errno.
unsafe fn lookup_username() -> Result<Option<*mut c_char>, c_int> {
    // SAFETY: libc supplies a live thread-local errno cell and serialized passwd storage.
    let cell = unsafe { __errno_location() };
    let saved_errno = unsafe { cell.read() };
    unsafe { cell.write(0) };
    let passwd = unsafe { getpwuid(getuid()) };
    let lookup_errno = unsafe { cell.read() };
    if passwd.is_null() && lookup_errno != 0 {
        return Err(-lookup_errno);
    }
    unsafe { cell.write(saved_errno) };
    if passwd.is_null() {
        return Ok(None);
    }
    // SAFETY: the successful lookup supplies the live, header-witnessed record.
    let name = unsafe { username(passwd) };
    if name.is_null() {
        Ok(None)
    } else {
        Ok(Some(name))
    }
}

unsafe fn free_owned(pointer: *mut c_void) {
    if !pointer.is_null() {
        // SAFETY: caller transfers one malloc allocation exactly once. Save errno
        // because allocation cleanup must not replace device/BFD/close error state.
        let cell = unsafe { __errno_location() };
        let saved_errno = unsafe { cell.read() };
        unsafe { free(pointer) };
        unsafe { cell.write(saved_errno) };
    }
}

unsafe fn section_size(section: *mut c_void) -> c_ulong {
    // SAFETY: live BFD section, generated aligned size offset; no Rust borrow of BFD storage.
    unsafe { section.cast::<u8>().add(abi::SECTION_SIZE).cast::<c_ulong>().read() }
}

unsafe fn chunk_at(chunks: *mut MemoryChunks, index: c_int) -> *mut MemoryChunk {
    // SAFETY: the successful kernel query supplies nr_chunks complete records in its allocation.
    unsafe {
        chunks.cast::<u8>().add(abi::MEMORY_CHUNKS_DATA)
            .cast::<MemoryChunk>().add(index as usize)
    }
}

unsafe fn create_section(file: *mut c_void, name: *const c_char, size: c_ulong,
    flags: c_uint) -> Result<*mut c_void, c_int> {
    // SAFETY: live BFD handle and NUL-terminated name retained through bfd_close.
    let section = unsafe { bfd_make_section_anyway(file, name) };
    if section.is_null() {
        return Err(-abi::EINVAL);
    }
    // SAFETY: each setter receives the live section and the real-header witnessed modern ABI.
    if unsafe { bfd_set_section_size(section, size) } == abi::BFD_FALSE
        || unsafe { bfd_set_section_flags(section, flags) } == abi::BFD_FALSE
    {
        return Err(-abi::EINVAL);
    }
    Ok(section)
}

unsafe fn write_named(file: *mut c_void, name: *const c_char, data: *const c_void,
    size: Option<c_ulong>) -> Result<(), c_int> {
    // SAFETY: live BFD and static NUL-terminated section name.
    let section = unsafe { bfd_get_section_by_name(file, name) };
    if !section.is_null() {
        let size = match size {
            Some(size) => size,
            None => unsafe { section_size(section) },
        };
        // SAFETY: matching metadata buffer remains live for the declared section's full size.
        if unsafe { bfd_set_section_contents(file, section, data, 0, size) } == abi::BFD_FALSE {
            return Err(-abi::EINVAL);
        }
    }
    Ok(())
}

struct DumpSession {
    fd: c_int,
    file: *mut c_void,
    args: DumpArgs,
    nmi_sent: bool,
    chunks: *mut MemoryChunks,
    buffer: *mut c_void,
    names: *mut c_char,
}

impl DumpSession {
    unsafe fn finish(&mut self, mut result: c_int) -> c_int {
        if self.nmi_sent {
            self.nmi_sent = false;
            // SAFETY: fd remains owned and open; continuation is attempted after any error.
            let _ = unsafe { dump_command(self.fd, &mut self.args, abi::DUMP_NMI_CONT) };
        }
        // Clear ownership before each close attempt; neither failed close is retried.
        // Keep section-name storage alive until BFD close has returned, even on failure.
        let file = core::mem::replace(&mut self.file, null_mut());
        if !file.is_null() {
            // SAFETY: this session owns the only close attempt for the live BFD handle.
            if unsafe { bfd_close(file) } == abi::BFD_FALSE {
                result = -abi::EINVAL;
            }
        }
        let fd = core::mem::replace(&mut self.fd, -1);
        if fd >= 0 {
            // SAFETY: this session owns the descriptor's single close attempt.
            if unsafe { close(fd) } != 0 {
                result = unsafe { neg_errno() };
            }
        }
        let names = core::mem::replace(&mut self.names, null_mut());
        let buffer = core::mem::replace(&mut self.buffer, null_mut());
        let chunks = core::mem::replace(&mut self.chunks, null_mut());
        // SAFETY: these are distinct owned malloc allocations, no longer borrowed by BFD
        // or any synchronous ioctl. Each free preserves the preceding cleanup errno.
        unsafe {
            free_owned(names.cast());
            free_owned(buffer);
            free_owned(chunks.cast());
        }
        result
    }

    /// # Safety
    /// dump_file is null or writable NUL-terminated storage; the device/provider returns
    /// valid chunk metadata. The caller serializes libc static metadata and dump calls.
    unsafe fn run(&mut self, index: c_int, dump_file: *mut c_char, level: c_int,
        interactive: c_int) -> Result<(), c_int> {
        // SAFETY: scalar index is forwarded to the existing Rust library provider.
        self.fd = unsafe { ihklib_os_open(index) };
        if self.fd < 0 {
            return Err(self.fd);
        }
        // SAFETY: existing status provider owns its separate query descriptor.
        let status = unsafe { ihk_os_get_status(index) };
        if status < 0 {
            return Err(status);
        }
        if status == abi::IHK_STATUS_INACTIVE {
            return Err(-abi::EINVAL);
        }
        // SAFETY: libc time/localtime contract, including process-static localtime storage.
        let timestamp = unsafe { time(null_mut()) };
        if timestamp == -1 {
            return Err(unsafe { neg_errno() });
        }
        let local = unsafe { localtime(&timestamp) };
        if local.is_null() {
            return Err(-abi::EINVAL);
        }
        let hostname = addr_of_mut!(HOSTNAME).cast::<c_char>();
        // SAFETY: static buffer is writable for its witnessed capacity, serialized by caller.
        if unsafe { gethostname(hostname, abi::HOSTNAME_CAPACITY) } != 0 {
            return Err(unsafe { neg_errno() });
        }
        // SAFETY: preserve the preliminary lookup order, distinguishing absence from error.
        let _ = unsafe { lookup_username() }?;
        self.args.level = level as c_uint;
        unsafe { dump_command(self.fd, &mut self.args, abi::DUMP_SET_LEVEL) }?;
        unsafe { dump_command(self.fd, &mut self.args, abi::DUMP_NMI) }?;
        self.nmi_sent = true;
        self.args.size = 0;
        unsafe { dump_command(self.fd, &mut self.args, abi::DUMP_QUERY_NUM_MEM_AREAS) }?;
        let memory_size = self.args.size;
        if memory_size < size_of::<MemoryChunks>() as c_long {
            return Err(-abi::EINVAL);
        }
        // SAFETY: the positive query size fits usize on the witnessed LP64 target.
        self.chunks = unsafe { malloc(memory_size as usize) }.cast::<MemoryChunks>();
        let chunks = self.chunks;
        if chunks.is_null() {
            return Err(-abi::ENOMEM);
        }
        // SAFETY: malloc owns memory_size writable bytes; original C zeroes this same allocation.
        unsafe { chunks.cast::<u8>().write_bytes(0, memory_size as usize) };
        self.args.buf = chunks.cast();
        unsafe { dump_command(self.fd, &mut self.args, abi::DUMP_QUERY_MEM_AREAS) }?;
        // SAFETY: the successful query initialized the chunk header in the allocated buffer.
        let count = unsafe { (*chunks).nr_chunks };
        let capacity = (memory_size as usize - abi::MEMORY_CHUNKS_DATA)
            / size_of::<MemoryChunk>();
        if count < 0 || count as usize > capacity {
            return Err(-abi::EINVAL);
        }
        // SAFETY: session ownership retains this storage through every early return.
        self.buffer = unsafe { malloc(TRANSFER_SIZE) };
        let buffer = self.buffer;
        if buffer.is_null() {
            return Err(-abi::ENOMEM);
        }
        // SAFETY: ordinary BFD process initialization; its return is ignored in the original.
        unsafe { bfd_init() };
        if dump_file.is_null() {
            return Err(-abi::EFAULT);
        }
        // SAFETY: caller supplied writable NUL-terminated path; separator is restored on all paths.
        let separator = unsafe { strrchr(dump_file, b'/' as c_int) };
        if !separator.is_null() {
            unsafe { separator.write(0) };
            let parent: *const c_char = if separator == dump_file {
                b"/\0".as_ptr().cast()
            } else {
                dump_file
            };
            let accessible = unsafe { access(parent, abi::W_OK) };
            let error = if accessible != 0 { unsafe { neg_errno() } } else { 0 };
            unsafe { separator.write(b'/' as c_char) };
            if accessible != 0 {
                return Err(error);
            }
        }
        // SAFETY: restored path is live; BFD owns any resulting output descriptor.
        self.file = unsafe { bfd_fopen(dump_file, null(), b"w\0".as_ptr().cast(), -1) };
        if self.file.is_null() {
            return Err(-abi::EINVAL);
        }
        if unsafe { bfd_set_format(self.file, abi::BFD_OBJECT) } == abi::BFD_FALSE {
            return Err(-abi::EINVAL);
        }
        // SAFETY: localtime's static record is still live and serialized by caller.
        let date = unsafe { asctime(local) };
        if !date.is_null() {
            let length = unsafe { strlen(date) }.wrapping_sub(1) as c_ulong;
            unsafe { create_section(self.file, b"date\0".as_ptr().cast(), length,
                abi::SEC_HAS_CONTENTS) }?;
        }
        // Preserve the repeated optional hostname/user queries and their original section order.
        if unsafe { gethostname(hostname, abi::HOSTNAME_CAPACITY) } == 0 {
            unsafe { create_section(self.file, b"hostname\0".as_ptr().cast(),
                strlen(hostname) as c_ulong, abi::SEC_HAS_CONTENTS) }?;
        }
        // SAFETY: serialized libc storage remains live until the user section is written.
        let user = unsafe { lookup_username() }?;
        if let Some(user) = user {
            unsafe { create_section(self.file, b"user\0".as_ptr().cast(),
                strlen(user) as c_ulong, abi::SEC_HAS_CONTENTS) }?;
        }
        let physical_flags = abi::SEC_ALLOC | abi::SEC_HAS_CONTENTS;
        unsafe { create_section(self.file, b"physchunks\0".as_ptr().cast(),
            memory_size as c_ulong, physical_flags) }?;
        if count != 0 {
            let names_size = (count as usize).checked_mul(NAME_SIZE).ok_or(-abi::ENOMEM)?;
            // SAFETY: the single names allocation is owned through the BFD close attempt.
            self.names = unsafe { malloc(names_size) }.cast();
            if self.names.is_null() {
                return Err(-abi::ENOMEM);
            }
        }
        for index in 0..count {
            // SAFETY: checked allocation has one disjoint NAME_SIZE slot per chunk.
            let name = unsafe { self.names.add(index as usize * NAME_SIZE) };
            unsafe {
                name.write_bytes(0, NAME_SIZE);
                snprintf(name, NAME_SIZE, b"physmem%d\0".as_ptr().cast(), index);
            }
            let chunk = unsafe { chunk_at(chunks, index) };
            let length = if interactive != 0 { abi::PAGE_SIZE } else { unsafe { (*chunk).size } };
            let section = unsafe { create_section(self.file, name, length, physical_flags) }?;
            // SAFETY: section is live; generated VMA offset has c_ulong type/alignment.
            unsafe {
                section.cast::<u8>().add(abi::SECTION_VMA).cast::<c_ulong>()
                    .write((*chunk).addr);
            }
        }
        unsafe {
            write_named(self.file, b"date\0".as_ptr().cast(), date.cast(), None)?;
            write_named(self.file, b"hostname\0".as_ptr().cast(), hostname.cast(), None)?;
        }
        if let Some(user) = user {
            // SAFETY: only a present passwd name can create and fill the user section.
            unsafe { write_named(self.file, b"user\0".as_ptr().cast(), user.cast(), None) }?;
        }
        unsafe {
            write_named(self.file, b"physchunks\0".as_ptr().cast(), chunks.cast(),
                Some(memory_size as c_ulong))?;
        }
        if interactive != 0 {
            return Ok(());
        }
        for index in 0..count {
            let mut name = [0 as c_char; NAME_SIZE];
            // SAFETY: bounded stack name is used only for synchronous BFD lookup.
            unsafe {
                snprintf(name.as_mut_ptr(), NAME_SIZE, b"physmem%d\0".as_ptr().cast(), index)
            };
            let section = unsafe { bfd_get_section_by_name(self.file, name.as_ptr()) };
            if section.is_null() {
                return Err(-abi::EINVAL);
            }
            let chunk = unsafe { chunk_at(chunks, index) };
            let start = unsafe { (*chunk).addr };
            let end = start.wrapping_add(unsafe { (*chunk).size });
            let mut address = start;
            let mut offset: c_ulong = 0;
            while address < end {
                let length = end.wrapping_sub(address).min(TRANSFER_SIZE as c_ulong);
                self.args.start = address as c_long;
                self.args.size = length as c_long;
                self.args.buf = buffer;
                unsafe { dump_command(self.fd, &mut self.args, abi::DUMP_READ) }?;
                // SAFETY: the ioctl filled length bytes; the section and offset remain valid.
                if unsafe { bfd_set_section_contents(self.file, section, buffer, offset as c_long,
                    length) } == abi::BFD_FALSE
                {
                    return Err(-abi::EINVAL);
                }
                address = address.wrapping_add(length);
                offset = offset.wrapping_add(length);
            }
        }
        Ok(())
    }
}

/// Create the existing BFD memory dump, including interactive metadata-only mode.
///
/// # Safety
/// `dump_file` must be null or point to writable NUL-terminated storage for this call.
/// Serialize calls against other users of libc static localtime/passwd and this buffer.
/// The selected device must initialize its declared chunk metadata and honor read sizes.
/// Query allocation/header bounds are checked before chunk access. All acquired allocations
/// are released after the BFD close attempt, preserving cleanup errno and return precedence.
#[no_mangle]
pub unsafe extern "C" fn ihk_os_makedumpfile(index: c_int, dump_file: *mut c_char,
    dump_level: c_int, interactive: c_int) -> c_int {
    let mut session = DumpSession {
        fd: -1,
        file: null_mut(),
        args: DumpArgs {
            cmd: 0, level: 0, start: 0, size: 0, buf: null_mut(), spare: [null_mut(); 4],
        },
        nmi_sent: false,
        chunks: null_mut(),
        buffer: null_mut(),
        names: null_mut(),
    };
    // SAFETY: the public contract supplies the path/device/static-storage invariants.
    let result = match unsafe { session.run(index, dump_file, dump_level, interactive) } {
        Ok(()) => 0,
        Err(error) => error,
    };
    // SAFETY: session exclusively owns its handles, whether run succeeded or returned early.
    unsafe { session.finish(result) }
}
