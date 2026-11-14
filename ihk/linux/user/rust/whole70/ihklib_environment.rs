//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Environment convenience contracts with transactional parser allocation ownership.

use core::ffi::{c_char, c_int, c_long, c_void};
use core::ptr::null_mut;

unsafe extern "C" {
    fn calloc(count: usize, size: usize) -> *mut c_void;
    fn strndup(text: *const c_char, length: usize) -> *mut c_char;
    fn strdup(text: *const c_char) -> *mut c_char;
    fn strsep(cursor: *mut *mut c_char, delimiters: *const c_char) -> *mut c_char;
    fn strcmp(first: *const c_char, second: *const c_char) -> c_int;
    fn strtol(text: *const c_char, end: *mut *mut c_char, base: c_int) -> c_long;
    fn free(pointer: *mut c_void);
    fn __errno_location() -> *mut c_int;
    fn _ihk_reserve_cpu_str(index: c_int, list: *mut c_char, error: *mut c_char) -> c_int;
    fn _ihk_reserve_mem_str(index: c_int, list: *mut c_char, error: *mut c_char) -> c_int;
    fn _ihk_os_assign_cpu_str(index: c_int, list: *mut c_char, error: *mut c_char) -> c_int;
    fn _ihk_os_set_ikc_map_str(index: c_int, list: *mut c_char, error: *mut c_char) -> c_int;
}

/// Split the original concatenated NUL-terminated environment entries.
///
/// # Safety
/// envp must supply num_env NUL-terminated strings within a readable 1MiB region.
/// On success, names_out and values_out must be writable pointer slots. Returned
/// arrays and strings use libc allocation. Failure releases all parser-owned
/// storage and leaves both output slots unchanged.
#[no_mangle]
pub unsafe extern "C" fn parse_env(
    envp: *const c_char,
    num_env: c_int,
    names_out: *mut *mut *mut c_char,
    values_out: *mut *mut *mut c_char,
) -> c_int {
    if envp.is_null() || num_env <= 0 || num_env > 1024 {
        return -22;
    }
    // SAFETY: validated count bounds the pointer arrays; libc supplies alignment.
    let names: *mut *mut c_char = unsafe {
        calloc(core::mem::size_of::<*mut c_char>(), num_env as usize)
    }.cast();
    if names.is_null() {
        return -12;
    }
    // SAFETY: same allocation contract; names remains exclusively parser-owned.
    let values: *mut *mut c_char = unsafe {
        calloc(core::mem::size_of::<*mut c_char>(), num_env as usize)
    }.cast();
    if values.is_null() {
        // SAFETY: names is the one live allocation; no output was published.
        unsafe { free(names.cast()) };
        return -12;
    }
    let result = (|| {
        let mut start = 0usize;
        let mut current = 0usize;
        for i in 0..num_env as usize {
            // SAFETY: caller supplies the readable prefix; each increment rejects
            // the 1MiB boundary before the next read.
            while unsafe { envp.add(current).read() } != 0 {
                current += 1;
                if current >= 1 << 20 {
                    return -22;
                }
            }
            // SAFETY: the bounded scan established this entry's readable bytes.
            let pair = unsafe { strndup(envp.add(start), current - start) };
            if pair.is_null() {
                // SAFETY: capture libc errno before cleanup can change it.
                return unsafe { -*__errno_location() };
            }
            let mut tail = pair;
            // SAFETY: pair is writable libc storage; '=' is NUL-terminated.
            let name = unsafe { strsep(&mut tail, b"=\0".as_ptr().cast()) };
            if tail.is_null() {
                // SAFETY: strsep returns a live first token for nonnull pair.
                if unsafe { name.read() } == 0 {
                    // SAFETY: pair has not transferred into either output array.
                    unsafe { free(pair.cast()) };
                    return -22;
                }
                tail = b"\0".as_ptr() as *mut c_char;
            }
            // SAFETY: both inputs are NUL-terminated and the array slot is live.
            let name_copy = unsafe { strdup(name) };
            if name_copy.is_null() {
                // SAFETY: capture errno before releasing this entry's scratch.
                let error = unsafe { -*__errno_location() };
                unsafe { free(pair.cast()) };
                return error;
            }
            // SAFETY: recording ownership immediately makes failure cleanup complete.
            unsafe { names.add(i).write(name_copy) };
            let value_copy = unsafe { strdup(tail) };
            if value_copy.is_null() {
                // SAFETY: name_copy is already owned by names; pair is still local.
                let error = unsafe { -*__errno_location() };
                unsafe { free(pair.cast()) };
                return error;
            }
            // SAFETY: record the second owned string before releasing scratch.
            unsafe {
                values.add(i).write(value_copy);
                free(pair.cast());
            }
            current += 1;
            if current >= 1 << 20 {
                return -22;
            }
            start = current;
        }
        0
    })();
    if result != 0 {
        // SAFETY: calloc zeroed every slot; each nonnull entry records a unique
        // libc allocation still owned by this parser, including a partial entry.
        unsafe {
            for i in 0..num_env as usize {
                free(names.add(i).read().cast());
                free(values.add(i).read().cast());
            }
            free(names.cast());
            free(values.cast());
        }
        return result;
    }
    // SAFETY: caller supplies writable slots; both complete arrays transfer only
    // after every allocation and original range/split check succeeds.
    unsafe {
        names_out.write(names);
        values_out.write(values);
    }
    0
}

// Own only complete parse_env outputs; providers borrow selected values until
// their synchronous calls return. Keep these allocations live across every call.
struct ParsedEnvironment {
    names: *mut *mut c_char,
    values: *mut *mut c_char,
    count: usize,
}

impl Drop for ParsedEnvironment {
    fn drop(&mut self) {
        // SAFETY: construction follows successful parse_env, which transfers two
        // distinct libc arrays with count nonnull separately allocated strings.
        // No provider takes ownership of these arrays or their string storage.
        // libc supplies this thread's errno cell; preserve the value left by the
        // completed operation or parse path across cleanup's libc side effects.
        unsafe {
            let saved_errno = *__errno_location();
            for i in 0..self.count {
                free(self.names.add(i).read().cast());
                free(self.values.add(i).read().cast());
            }
            free(self.names.cast());
            free(self.values.cast());
            *__errno_location() = saved_errno;
        }
    }
}

type StringOperation = unsafe extern "C" fn(c_int, *mut c_char, *mut c_char) -> c_int;

unsafe fn first(
    index: c_int,
    envp: *const c_char,
    count: c_int,
    key: &'static [u8],
    operation: StringOperation,
) -> c_int {
    let mut names = null_mut();
    let mut values = null_mut();
    // SAFETY: wrappers forward the caller's environment contract and own slots.
    let result = unsafe { parse_env(envp, count, &mut names, &mut values) };
    if result != 0 {
        return result;
    }
    // Own successful parse outputs until the selected provider has returned,
    // including every early error and missing-key success path below.
    let _environment = ParsedEnvironment { names, values, count: count as usize };
    for i in 0..count as usize {
        // SAFETY: successful parse populated count nonnull string entries;
        // key supplies the matching static NUL-terminated comparison string.
        if unsafe { strcmp(names.add(i).read(), key.as_ptr().cast()) } == 0 {
            // SAFETY: operation is the matching public string helper, receives
            // its live owned value and no caller diagnostic buffer, as in C.
            return unsafe { operation(index, values.add(i).read(), null_mut()) };
        }
    }
    0
}

/// Reserve CPUs from the first IHK_CPUS entry.
///
/// # Safety
/// envp must satisfy parse_env's input contract; libc and device providers must
/// satisfy the selected ABI. Selected values stay live through provider return.
#[no_mangle]
pub unsafe extern "C" fn ihk_reserve_cpu_str(
    index: c_int, envp: *const c_char, count: c_int,
) -> c_int {
    // SAFETY: exact key and original public operation; caller owns input lifetime.
    unsafe { first(index, envp, count, b"IHK_CPUS\0", _ihk_reserve_cpu_str) }
}

/// Reserve memory from the first IHK_MEM entry.
///
/// # Safety
/// envp must satisfy parse_env's readable input contract; selected ABI applies.
#[no_mangle]
pub unsafe extern "C" fn ihk_reserve_mem_str(
    index: c_int, envp: *const c_char, count: c_int,
) -> c_int {
    // SAFETY: exact key and original public operation, with no diagnostic output.
    unsafe { first(index, envp, count, b"IHK_MEM\0", _ihk_reserve_mem_str) }
}

/// Assign CPUs from the first IHK_CPUS entry.
///
/// # Safety
/// envp must satisfy parse_env's readable input contract; selected ABI applies.
#[no_mangle]
pub unsafe extern "C" fn ihk_os_assign_cpu_str(
    index: c_int, envp: *const c_char, count: c_int,
) -> c_int {
    // SAFETY: exact key and original operation, preserving first-match behavior.
    unsafe { first(index, envp, count, b"IHK_CPUS\0", _ihk_os_assign_cpu_str) }
}

/// Set the IKC map from the first IHK_IKC_MAP entry.
///
/// # Safety
/// envp must satisfy parse_env's readable input contract; selected ABI applies.
#[no_mangle]
pub unsafe extern "C" fn ihk_os_set_ikc_map_str(
    index: c_int, envp: *const c_char, count: c_int,
) -> c_int {
    // SAFETY: exact key and original operation; no shared parser is duplicated.
    unsafe { first(index, envp, count, b"IHK_IKC_MAP\0", _ihk_os_set_ikc_map_str) }
}

const CONFIG_KEYS: [&[u8]; 6] = [
    b"IHK_RESERVE_MEM_BALANCED_ENABLE\0",
    b"IHK_RESERVE_MEM_BALANCED_BEST_EFFORT\0",
    b"IHK_RESERVE_MEM_BALANCED_VARIANCE_LIMIT\0",
    b"IHK_RESERVE_MEM_MIN_CHUNK_SIZE\0",
    b"IHK_RESERVE_MEM_MAX_SIZE_RATIO_ALL\0",
    b"IHK_RESERVE_MEM_TIMEOUT\0",
];

/// Apply recognized policy entries in environment order, retaining C int narrowing.
///
/// # Safety
/// envp must satisfy parse_env's input contract. Callers serialize configuration
/// updates as required by the existing non-atomic public state contract.
#[no_mangle]
pub unsafe extern "C" fn ihk_reserve_mem_conf_str(
    index: c_int, envp: *const c_char, count: c_int,
) -> c_int {
    let mut names = null_mut();
    let mut values = null_mut();
    // SAFETY: caller supplies input and local pointer slots are writable.
    let result = unsafe { parse_env(envp, count, &mut names, &mut values) };
    if result != 0 {
        return result;
    }
    // Own successful parse outputs until the selected provider has returned,
    // including every early error and missing-key success path below.
    let _environment = ParsedEnvironment { names, values, count: count as usize };
    for i in 0..count as usize {
        for (key, text) in CONFIG_KEYS.iter().enumerate() {
            // SAFETY: successful parse provides count nonnull string entries;
            // key is a static NUL-terminated string.
            if unsafe { strcmp(names.add(i).read(), text.as_ptr().cast()) } != 0 {
                continue;
            }
            let mut end = null_mut();
            // SAFETY: the selected entry is NUL-terminated; end is writable.
            let mut value = unsafe { strtol(values.add(i).read(), &mut end, 10) } as c_int;
            // SAFETY: strtol supplies a valid pointer into its original input.
            if unsafe { end.read() } != 0 {
                return -22;
            }
            // SAFETY: value is a live aligned C int; caller serializes state.
            let result = unsafe {
                super::runtime_state::ihk_reserve_mem_conf(
                    index, key as c_int, (&mut value as *mut c_int).cast(),
                )
            };
            if result != 0 {
                return result;
            }
        }
    }
    0
}

/// Set the first IHK_KARGS value, or the caller's unchanged default.
///
/// # Safety
/// envp must satisfy parse_env's input contract. The selected/default kargs must
/// satisfy ihk_os_kargs's readable string contract for the synchronous request.
#[no_mangle]
pub unsafe extern "C" fn ihk_os_kargs_str(
    index: c_int,
    envp: *const c_char,
    count: c_int,
    default_kargs: *const c_char,
) -> c_int {
    let mut names = null_mut();
    let mut values = null_mut();
    // SAFETY: caller input is forwarded unchanged and local slots are writable.
    let result = unsafe { parse_env(envp, count, &mut names, &mut values) };
    if result != 0 {
        return result;
    }
    // Own successful parse outputs until the selected provider has returned,
    // including every early error and missing-key success path below.
    let _environment = ParsedEnvironment { names, values, count: count as usize };
    let mut kargs = default_kargs as *mut c_char;
    for i in 0..count as usize {
        // SAFETY: successful parse produces the original valid entry pointers.
        if unsafe { strcmp(names.add(i).read(), b"IHK_KARGS\0".as_ptr().cast()) } == 0 {
            // SAFETY: index is within the populated array.
            kargs = unsafe { values.add(i).read() };
            break;
        }
    }
    // SAFETY: selected/default input remains live; original pointer is forwarded.
    unsafe { super::os_kargs::ihk_os_kargs(index, kargs) }
}
