//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Existing environment-based creation choreography, including original rollback.

use core::ffi::{c_char, c_int, c_long, c_void};
use core::ptr::null_mut;
use super::accepted_cpu_memory::ihklib_memory_os::IhkMemChunk;

mod origins {
    include!(env!("MCKERNEL_IHKLIB_CREATE_DIAGNOSTIC_ORIGINS_RS"));
}

unsafe extern "C" {
    fn calloc(count: usize, size: usize) -> *mut c_void;
    fn free(pointer: *mut c_void);
    fn strndup(text: *const c_char, size: usize) -> *mut c_char;
    fn strdup(text: *const c_char) -> *mut c_char;
    fn strsep(cursor: *mut *mut c_char, delimiter: *const c_char) -> *mut c_char;
    fn strcmp(first: *const c_char, second: *const c_char) -> c_int;
    fn strtol(text: *const c_char, end: *mut *mut c_char, base: c_int) -> c_long;
    fn sprintf(output: *mut c_char, format: *const c_char, ...) -> c_int;
    fn __errno_location() -> *mut c_int;
    fn ihk_get_num_reserved_cpus(index: c_int) -> c_int;
    fn ihk_query_cpu(index: c_int, cpus: *mut c_int, count: c_int) -> c_int;
    fn ihk_release_cpu(index: c_int, cpus: *mut c_int, count: c_int) -> c_int;
    fn ihk_get_num_reserved_mem_chunks(index: c_int) -> c_int;
    fn ihk_query_mem(index: c_int, memory: *mut IhkMemChunk, count: c_int) -> c_int;
    fn ihk_release_mem(index: c_int, memory: *mut IhkMemChunk, count: c_int) -> c_int;
    fn ihk_create_os(index: c_int) -> c_int;
    fn ihk_get_num_os_instances(index: c_int) -> c_int;
    fn ihk_get_os_instances(index: c_int, list: *mut c_int, count: c_int) -> c_int;
    fn ihk_destroy_os(index: c_int, os_index: c_int) -> c_int;
}

unsafe fn error(output: *mut c_char, site: usize, value: c_int) {
    if !output.is_null() {
        // SAFETY: caller supplies sufficient error-buffer space. Source-bound
        // generated inputs retain the selected C __FILE__/__LINE__/operation text.
        unsafe {
            sprintf(output, b"%s:%d: %s failed with %d\n\0".as_ptr().cast(),
                origins::FILE.as_ptr().cast::<c_char>(), origins::LINES[site],
                origins::OPERATIONS[site].as_ptr().cast::<c_char>(), value);
        }
    }
}

unsafe fn cpu_all(device: c_int, output: *mut c_char, assign_to: Option<c_int>) -> c_int {
    // Reservation queries use the device index. Only assignment uses the returned
    // OS index; None retains the existing device-release operation.
    let assign = assign_to.is_some();
    let count = unsafe { ihk_get_num_reserved_cpus(device) };
    if count <= 0 {
        if !assign || count < 0 {
            // SAFETY: caller owns output; sites 0/5 are original count-error sites.
            unsafe { error(output, if assign { 0 } else { 5 }, count) };
        }
        return if assign && count == 0 { -22 } else { count };
    }
    // SAFETY: positive C int count fits LP64 allocation size; exact argument order.
    let cpus: *mut c_int = unsafe {
        calloc(core::mem::size_of::<c_int>(), count as usize)
    }.cast();
    if cpus.is_null() {
        return -12;
    }
    // SAFETY: query synchronously borrows the owned count-element array.
    let query = unsafe { ihk_query_cpu(device, cpus, count) };
    let result = if query != 0 {
        // SAFETY: captured query result is formatted before allocation cleanup.
        unsafe { error(output, if assign { 1 } else { 6 }, query) };
        query
    } else {
        // SAFETY: both synchronous APIs borrow the owned initialized array only.
        let value = unsafe {
            if let Some(os_index) = assign_to { super::os_cpu::ihk_os_assign_cpu(os_index, cpus, count) }
            else { ihk_release_cpu(device, cpus, count) }
        };
        if value != 0 {
            // SAFETY: preserve original selected operation and error-buffer policy.
            unsafe { error(output, if assign { 2 } else { 7 }, value) };
        }
        value
    };
    // SAFETY: synchronous query/change providers never transfer this allocation.
    unsafe { free(cpus.cast()) };
    result
}

unsafe fn memory_all(device: c_int, os_index: c_int, output: *mut c_char) -> c_int {
    // Both reservation queries use the creating device, independently of OS index.
    let count = unsafe { ihk_get_num_reserved_mem_chunks(device) };
    if count < 0 {
        // SAFETY: original message mistakenly names get_num_reserved_cpus; the
        // generated site 3 deliberately preserves that exact diagnostic text.
        unsafe { error(output, 3, count) };
        return count;
    }
    if count == 0 {
        return -22;
    }
    // SAFETY: count-element LP64 chunk allocation matches the original C layout.
    let memory: *mut IhkMemChunk = unsafe {
        calloc(core::mem::size_of::<IhkMemChunk>(), count as usize)
    }.cast();
    if memory.is_null() {
        return -12;
    }
    // SAFETY: device reservation query borrows the owned count-element array.
    let query = unsafe { ihk_query_mem(device, memory, count) };
    let result = if query != 0 {
        // SAFETY: result captured before output formatting and cleanup.
        unsafe { error(output, 4, query) };
        query
    } else {
        // SAFETY: the selected Rust public API borrows count initialized chunks.
        let value = unsafe {
            super::accepted_cpu_memory::ihklib_memory_os::ihk_os_assign_mem(os_index, memory, count)
        };
        if value != 0 {
            // SAFETY: original site retains the ihk_os_assign_mem operation name.
            unsafe { error(output, 8, value) };
        }
        value
    };
    // SAFETY: this function retains exclusive allocation ownership until cleanup.
    unsafe { free(memory.cast()) };
    result
}

unsafe fn release_assigned_cpu(index: c_int) -> c_int {
    // SAFETY: existing Rust public API accepts the selected integer OS index.
    let count = unsafe { super::os_cpu::ihk_os_get_num_assigned_cpus(index) };
    if count <= 0 {
        return count;
    }
    // SAFETY: count is positive and sized with the exact original allocation order.
    let cpus: *mut c_int = unsafe {
        calloc(core::mem::size_of::<c_int>(), count as usize)
    }.cast();
    if cpus.is_null() {
        return -12;
    }
    // SAFETY: borrow the allocated count-element array synchronously.
    let query = unsafe { super::os_cpu::ihk_os_query_cpu(index, cpus, count) };
    let result = if query != 0 {
        query
    } else {
        // SAFETY: query initialized the live array; release does not take ownership.
        unsafe { super::os_cpu::ihk_os_release_cpu(index, cpus, count) }
    };
    // SAFETY: the array remains exclusively owned by this helper.
    unsafe { free(cpus.cast()) };
    result
}

const CONFIG_KEYS: [&[u8]; 6] = [
    b"IHK_RESERVE_MEM_BALANCED_ENABLE\0", b"IHK_RESERVE_MEM_BALANCED_BEST_EFFORT\0",
    b"IHK_RESERVE_MEM_BALANCED_VARIANCE_LIMIT\0", b"IHK_RESERVE_MEM_MIN_CHUNK_SIZE\0",
    b"IHK_RESERVE_MEM_MAX_SIZE_RATIO_ALL\0", b"IHK_RESERVE_MEM_TIMEOUT\0",
];

unsafe fn is(name: *const c_char, expected: &'static [u8]) -> bool {
    // SAFETY: caller supplies a valid NUL string and expected is a fixed NUL string.
    unsafe { strcmp(name, expected.as_ptr().cast()) == 0 }
}

/// Perform the original environment-based reservation/creation/load choreography.
///
/// # Safety
/// The caller must exclusively serialize device/OS reservation and lifecycle
/// control: original failure rollback enumerates and destroys every current OS on
/// the device, not just a newly created one. envp supplies count strings within
/// 1MiB; output_index is writable on creation; image/defaults are valid strings.
/// error_output must be nonnull and sufficiently large on the original mandatory
/// error sites. Per-entry strdup errors return -ENOMEM before later dereferences.
/// Parser scratch and rollback-list allocations are released after their last borrow;
/// broad rollback still requires the original caller serialization contract.
#[no_mangle]
pub unsafe extern "C" fn ihk_create_os_str(
    device: c_int,
    output_index: *mut c_int,
    envp: *const c_char,
    count: c_int,
    image: *const c_char,
    default_kargs: *const c_char,
    error_output: *mut c_char,
) -> c_int {
    let mut names: *mut *mut c_char = null_mut();
    let mut values: *mut *mut c_char = null_mut();
    let mut all_memory = IhkMemChunk { size: core::ffi::c_ulong::MAX, numa_node_number: 0 };
    let mut kargs = default_kargs as *mut c_char;
    // Closure retains the original single out-label cleanup and rollback order.
    let result = (|| {
        // SAFETY: original API accepts the unchanged device and serialized state.
        let reserved = unsafe { ihk_get_num_reserved_cpus(device) };
        if reserved < 0 {
            // SAFETY: caller provides mandatory error buffer at this original site.
            unsafe { error(error_output, 9, reserved) };
            return reserved;
        }
        if reserved > 0 {
            // SAFETY: release the device's current CPUs before reading envp, as C.
            let value = unsafe { cpu_all(device, error_output, None) };
            if value != 0 { return value; }
        }
        // SAFETY: unchanged device memory count provider is reused.
        let reserved = unsafe { ihk_get_num_reserved_mem_chunks(device) };
        if reserved < 0 {
            // SAFETY: caller supplies the original mandatory error buffer.
            unsafe { error(error_output, 10, reserved) };
            return reserved;
        }
        if reserved > 0 {
            // SAFETY: all-memory sentinel has the exact ulong/int chunk ABI.
            let value = unsafe { ihk_release_mem(device, &mut all_memory, 1) };
            if value != 0 {
                // SAFETY: original mandatory output site; captured result retained.
                unsafe { error(error_output, 11, value) };
                return value;
            }
        }
        if envp.is_null() || count <= 0 || count > 1024 { return -22; }
        // SAFETY: validated count bounds the zero-initialized pointer arrays.
        names = unsafe { calloc(core::mem::size_of::<*mut c_char>(), count as usize) }.cast();
        if names.is_null() { return -12; }
        // SAFETY: independent values array, preserving allocation order.
        values = unsafe { calloc(core::mem::size_of::<*mut c_char>(), count as usize) }.cast();
        if values.is_null() { return -12; }
        let mut start = 0usize;
        let mut current = 0usize;
        for i in 0..count as usize {
            // This parser differs from public parse_env on no-'=' entries and
            // owns partial arrays for cleanup; do not substitute that API blindly.
            // SAFETY: caller supplies readable prefix; increment rejects 1MiB.
            while unsafe { envp.add(current).read() } != 0 {
                current += 1;
                if current >= 1 << 20 { return -22; }
            }
            // SAFETY: bounded scan established the complete current entry.
            let pair = unsafe { strndup(envp.add(start), current - start) };
            if pair.is_null() {
                // SAFETY: read libc errno before outer cleanup mutates it.
                return unsafe { -*__errno_location() };
            }
            let mut tail = pair;
            // SAFETY: owned writable pair and fixed single '=' delimiter.
            let head = unsafe { strsep(&mut tail, b"=\0".as_ptr().cast()) };
            if tail.is_null() {
                // SAFETY: strsep returns a live first token for nonnull pair.
                if unsafe { head.read() } == 0 {
                    // SAFETY: head/tail borrow pair; this error transfers nothing.
                    let saved_errno = unsafe { *__errno_location() };
                    unsafe { free(pair.cast()); *__errno_location() = saved_errno; }
                    return -22;
                }
                // Original create API stores empty name AND empty value here,
                // unlike parse_env. It intentionally ignores a nonempty bare key.
                // SAFETY: live array slots; fixed empty strings are NUL-terminated.
                unsafe {
                    names.add(i).write(strdup(b"\0".as_ptr().cast()));
                    values.add(i).write(strdup(b"\0".as_ptr().cast()));
                }
            } else {
                // SAFETY: both tokens are live NUL strings; the common guard
                // below validates both copies before any later dereference.
                unsafe { names.add(i).write(strdup(head)); values.add(i).write(strdup(tail)); }
            }
            // SAFETY: calloc initialized both slots; each holds NULL or its
            // distinct strdup allocation, which common cleanup owns on failure.
            let entry_allocation_failed = unsafe {
                names.add(i).read().is_null() || values.add(i).read().is_null()
            };
            if entry_allocation_failed {
                // SAFETY: head/tail only borrow pair; entry copies have not been consumed.
                // Preserve free-entry errno while releasing this scratch owner.
                let saved_errno = unsafe { *__errno_location() };
                unsafe {
                    free(pair.cast());
                    *__errno_location() = saved_errno;
                }
                return -12;
            }
            // SAFETY: only the token copies remain referenced after this point.
            unsafe { free(pair.cast()) };
            current += 1;
            if current >= 1 << 20 { return -22; }
            start = current;
        }
        // Apply every configuration entry before any CPU/memory reservation.
        for i in 0..count as usize {
            for (key, expected) in CONFIG_KEYS.iter().enumerate() {
                // SAFETY: original allocation-success contract supplies valid names.
                if !unsafe { is(names.add(i).read(), expected) } { continue; }
                let mut end = null_mut();
                // SAFETY: selected value is NUL; end points to a writable local slot.
                let mut value = unsafe { strtol(values.add(i).read(), &mut end, 10) } as c_int;
                // SAFETY: strtol produces a valid end pointer into its input string.
                if unsafe { end.read() } != 0 { return -22; }
                // SAFETY: aligned local int remains live for serialized setter call.
                let value = unsafe {
                    super::runtime_state::ihk_reserve_mem_conf(
                        device, key as c_int, (&mut value as *mut c_int).cast(),
                    )
                };
                if value != 0 { return value; }
                break;
            }
        }
        for i in 0..count as usize {
            // SAFETY: original successful per-entry allocation contract applies.
            let name = unsafe { names.add(i).read() };
            // SAFETY: same live entry index, retained through synchronous operations.
            let value = unsafe { values.add(i).read() };
            // SAFETY: compare fixed keys and invoke only their existing providers.
            let result = unsafe {
                if is(name, b"IHK_CPUS\0") {
                    super::raw_strings::_ihk_reserve_cpu_str(device, value, error_output)
                } else if is(name, b"IHK_MEM\0") {
                    super::raw_strings::_ihk_reserve_mem_str(device, value, error_output)
                } else { 0 }
            };
            if result != 0 { return result; }
        }
        // SAFETY: serialized original creation API returns an OS index or error.
        let index = unsafe { ihk_create_os(device) };
        if index < 0 {
            // SAFETY: preserve the original mandatory diagnostic buffer site.
            unsafe { error(error_output, 12, index) };
            return index;
        }
        // SAFETY: caller supplies output slot; original publishes index before
        // CPU/memory assignment and does not clear it again on a later rollback.
        unsafe { output_index.write(index) };
        // SAFETY: same serialized control and live caller diagnostic buffer.
        let value = unsafe { cpu_all(device, error_output, Some(index)) };
        if value != 0 { return value; }
        // SAFETY: query device reservations and assign them to the returned OS index.
        let value = unsafe { memory_all(device, index, error_output) };
        if value != 0 { return value; }
        for i in 0..count as usize {
            // SAFETY: entries remain live until common cleanup after all operations.
            let name = unsafe { names.add(i).read() };
            // SAFETY: same in-bounds values entry.
            let value = unsafe { values.add(i).read() };
            // SAFETY: comparison borrows the valid NUL name and fixed key.
            if unsafe { is(name, b"IHK_IKC_MAP\0") } {
                // SAFETY: the current shared-parser provider borrows its string.
                let value = unsafe {
                    super::raw_strings::_ihk_os_set_ikc_map_str(index, value, error_output)
                };
                if value != 0 { return value; }
            } else if unsafe { is(name, b"IHK_KARGS\0") } {
                kargs = value;
            }
        }
        // SAFETY: original caller image remains live; Rust load preserves its ABI.
        let value = unsafe { super::os_load_boot::ihk_os_load(index, image as *mut c_char) };
        if value != 0 {
            // SAFETY: this original diagnostic site permits a NULL buffer.
            unsafe { error(error_output, 13, value) };
            return value;
        }
        // SAFETY: last selected/default string remains live through synchronous ioctl.
        let value = unsafe { super::os_kargs::ihk_os_kargs(index, kargs) };
        if value != 0 {
            // SAFETY: original optional diagnostic site, result captured first.
            unsafe { error(error_output, 14, value) };
        }
        value
    })();
    if !names.is_null() {
        for i in 0..count as usize {
            // SAFETY: nonnull names means validated count and calloc-initialized
            // entries, each NULL or one original strdup allocation owned here.
            unsafe { free(names.add(i).read().cast()) };
        }
    }
    // SAFETY: names is NULL or its distinct original owned pointer array.
    unsafe { free(names.cast()) };
    if !values.is_null() {
        for i in 0..count as usize {
            // SAFETY: same initialized-array and exclusive strdup ownership rule.
            unsafe { free(values.add(i).read().cast()) };
        }
    }
    // SAFETY: values is NULL or its distinct original owned pointer array.
    unsafe { free(values.cast()) };
    if result != 0 {
        // Original rollback is deliberately broad, not an invented owned-only
        // deletion algorithm. Caller serialization is mandatory for this legacy API.
        // SAFETY: original public count is queried after entry cleanup on any error.
        let count = unsafe { ihk_get_num_os_instances(device) };
        if count > 0 {
            // SAFETY: positive int allocation count fits LP64; exact original order.
            let list: *mut c_int = unsafe {
                calloc(core::mem::size_of::<c_int>(), count as usize)
            }.cast();
            if !list.is_null() {
                // SAFETY: the API receives count writable entries. Only a
                // successful listing supplies the complete index sequence.
                let list_status = unsafe { ihk_get_os_instances(device, list, count) };
                if list_status == 0 {
                    for i in 0..count as usize {
                        // SAFETY: successful listing initialized all count indices.
                        let index = unsafe { list.add(i).read() };
                        // SAFETY: original rollback sequence ignores cleanup errors.
                        unsafe {
                            release_assigned_cpu(index);
                            super::accepted_cpu_memory::ihklib_memory_os::ihk_os_release_mem(
                                index, &mut all_memory, 1,
                            );
                            ihk_destroy_os(device, index);
                        }
                    }
                }
                // SAFETY: listing and cleanup providers only borrowed list;
                // its distinct calloc allocation remains exclusively owned here.
                let saved_errno = unsafe { *__errno_location() };
                unsafe { free(list.cast()); *__errno_location() = saved_errno; }
            }
        }
        // SAFETY: original final release calls run even after an early parse error;
        // their errors cannot replace the primary already captured result.
        unsafe { cpu_all(device, null_mut(), None); ihk_release_mem(device, &mut all_memory, 1); }
    }
    result
}
