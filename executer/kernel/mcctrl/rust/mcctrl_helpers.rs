#![no_std]

use core::ffi::{c_char, c_int, c_long, c_uint, c_ulong};

const NUL: c_char = 0;
const IHK_OS_AUX_PERF_NUM: c_uint = 0x1129_0100;
const IHK_OS_AUX_PERF_SET: c_uint = 0x1129_0101;
const IHK_OS_AUX_PERF_GET: c_uint = 0x1129_0102;
const IHK_OS_AUX_PERF_ENABLE: c_uint = 0x1129_0103;
const IHK_OS_AUX_PERF_DISABLE: c_uint = 0x1129_0104;
const IHK_OS_AUX_PERF_DESTROY: c_uint = 0x1129_0105;
const SCD_MSG_SYSCALL_ONESIDE: c_int = 0x4;
const MCCTRL_IKC_INIT_LAST_CHANNEL_PORT: c_int = 502;
const ETIME: c_int = 62;
const ENOSPC: c_int = 28;
const ENOENT: c_int = 2;
const ENAMETOOLONG: c_int = 36;
const FUTEX_WAIT: c_int = 0;
const FUTEX_WAKE: c_int = 1;
const FUTEX_REQUEUE: c_int = 3;
const FUTEX_CMP_REQUEUE: c_int = 4;
const FUTEX_WAKE_OP: c_int = 5;
const FUTEX_WAIT_BITSET: c_int = 9;
const FUTEX_WAKE_BITSET: c_int = 10;
const FUTEX_WAIT_REQUEUE_PI: c_int = 11;
const FUTEX_CMD_MASK: c_int = 0x7f;
const FUTEX_PRIVATE_FLAG: c_int = 128;
const FUTEX_CLOCK_REALTIME: c_int = 256;
const FUTEX_WAIT_LABEL: &[u8] = b"FUTEX_WAIT\0";
const FUTEX_WAIT_BITSET_LABEL: &[u8] = b"FUTEX_WAIT_BITSET\0";
const FUTEX_WAKE_LABEL: &[u8] = b"FUTEX_WAKE\0";
const FUTEX_WAKE_OP_LABEL: &[u8] = b"FUTEX_WAKE_OP\0";
const FUTEX_WAKE_BITSET_LABEL: &[u8] = b"FUTEX_WAKE_BITSET\0";
const FUTEX_CMP_REQUEUE_LABEL: &[u8] = b"FUTEX_CMP_REQUEUE\0";
const FUTEX_REQUEUE_LABEL: &[u8] = b"FUTEX_REQUEUE (NOT IMPL!)\0";
const FUTEX_UNKNOWN_LABEL: &[u8] = b"unknown\0";
const TOFU_DEV_PREFIX: &[u8] = b"/proc/tofu/dev/";
const TOFU_CQ_PREFIX: &[u8] = b"/proc/tofu/dev/tni";

unsafe fn c_byte(ptr: *const c_char, index: usize) -> u8 {
    *ptr.add(index) as u8
}

unsafe fn starts_with(ptr: *const c_char, prefix: &[u8]) -> bool {
    if ptr.is_null() {
        return false;
    }

    let mut i = 0usize;
    while i < prefix.len() {
        if c_byte(ptr, i) != *prefix.as_ptr().add(i) {
            return false;
        }
        i += 1;
    }
    true
}

unsafe fn equals_bytes(ptr: *const c_char, bytes: &[u8]) -> bool {
    if ptr.is_null() {
        return false;
    }

    let mut i = 0usize;
    while i < bytes.len() {
        if c_byte(ptr, i) != *bytes.as_ptr().add(i) {
            return false;
        }
        i += 1;
    }
    c_byte(ptr, i) == 0
}

unsafe fn contains_bytes(ptr: *const c_char, needle: &[u8]) -> bool {
    if ptr.is_null() {
        return false;
    }
    if needle.is_empty() {
        return true;
    }

    let mut i = 0usize;
    while c_byte(ptr, i) != 0 {
        let mut j = 0usize;
        while j < needle.len() && c_byte(ptr, i + j) != 0 {
            if c_byte(ptr, i + j) != *needle.as_ptr().add(j) {
                break;
            }
            j += 1;
        }
        if j == needle.len() {
            return true;
        }
        i += 1;
    }
    false
}

fn is_ascii_space(byte: u8) -> bool {
    matches!(byte, b' ' | b'\t' | b'\n' | b'\r' | 0x0b | 0x0c)
}

unsafe fn parse_i32_at(ptr: *const c_char, pos: &mut usize, out: *mut c_int) -> bool {
    if out.is_null() {
        return false;
    }

    let mut value = 0 as c_int;
    let mut digits = 0usize;
    while c_byte(ptr, *pos).is_ascii_digit() {
        value = value
            .wrapping_mul(10)
            .wrapping_add((c_byte(ptr, *pos) - b'0') as c_int);
        *pos += 1;
        digits += 1;
    }

    if digits == 0 {
        return false;
    }

    *out = value;
    true
}

#[no_mangle]
pub extern "C" fn mcctrl_align_wait_buf_result(size: usize) -> usize {
    size.wrapping_add(63) & !63usize
}

#[no_mangle]
pub extern "C" fn mcctrl_partition_list_evict_result(len: c_int, max_len: c_int) -> c_int {
    (len >= max_len) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_partition_count_mismatch_result(
    existing: c_int,
    requested: c_int,
) -> c_int {
    (existing != requested) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_partition_join_allowed_result(joined: c_int, total: c_int) -> c_int {
    (joined < total) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_partition_last_process_result(left: c_int) -> c_int {
    (left == 0) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_partition_wait_required_result(
    left: c_int,
    woke_any: c_int,
    woke_self: c_int,
) -> c_int {
    (left != 0 || (woke_any != 0 && woke_self == 0)) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_partition_wait_timeout_msecs_result(nr_processes: c_int) -> c_uint {
    10_000u32.wrapping_add((nr_processes as u32).wrapping_mul(100))
}

#[no_mangle]
pub extern "C" fn mcctrl_partition_wake_next_result(left: c_int) -> c_int {
    (left != 0) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_release_user_space_len_result(start: c_ulong, end: c_ulong) -> c_ulong {
    end.wrapping_sub(start)
}

#[no_mangle]
pub extern "C" fn mcctrl_control_request_needs_root_result(request: c_uint) -> c_int {
    matches!(
        request,
        IHK_OS_AUX_PERF_NUM
            | IHK_OS_AUX_PERF_SET
            | IHK_OS_AUX_PERF_GET
            | IHK_OS_AUX_PERF_ENABLE
            | IHK_OS_AUX_PERF_DISABLE
            | IHK_OS_AUX_PERF_DESTROY
    ) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_free_addrs_owner_result(free_addrs_count: c_int) -> c_int {
    (free_addrs_count != 0) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_desc_free_at_put_result(allocated_internally: c_int) -> c_int {
    (allocated_internally != 0) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_wait_mode_result(timeout: c_long) -> c_int {
    if timeout < 0 {
        -1
    } else if timeout > 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_busy_timeout_msecs_result(timeout: c_long) -> c_ulong {
    timeout.wrapping_neg() as c_ulong
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_wait_abort_return_result(wait_ret: c_int) -> c_int {
    if wait_ret < 0 {
        wait_ret
    } else {
        -ETIME
    }
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_release_packet_after_handler_result(msg: c_int) -> c_int {
    (msg != SCD_MSG_SYSCALL_ONESIDE) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_cpu_nonnegative_result(cpu: c_int) -> c_int {
    (cpu >= 0) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_cpu_index_valid_result(cpu: c_int, num_channels: c_int) -> c_int {
    (cpu >= 0 && cpu < num_channels) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_linux_cpu_valid_result(linux_cpu: c_int, nr_cpu_ids: c_int) -> c_int {
    (linux_cpu <= nr_cpu_ids) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_init_uses_last_channel_result(port: c_int) -> c_int {
    (port == MCCTRL_IKC_INIT_LAST_CHANNEL_PORT) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_cpu_count_valid_result(n_cpus: c_int) -> c_int {
    (n_cpus >= 1) as c_int
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_lwk_to_linux_index_result(
    mapping: *const c_int,
    count: c_int,
    index: c_int,
) -> c_int {
    if mapping.is_null() || index < 0 || index >= count {
        return -1;
    }

    *mapping.add(index as usize)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_linux_to_lwk_index_result(
    mapping: *const c_int,
    count: c_int,
    linux_id: c_int,
) -> c_int {
    if mapping.is_null() || count <= 0 {
        return -1;
    }

    let mut i = 0;
    while i < count {
        if *mapping.add(i as usize) == linux_id {
            return i;
        }
        i += 1;
    }

    -1
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_fill_sequential_bitset_result(
    bits: *mut c_ulong,
    bit_count: c_int,
    word_count: c_int,
    bits_per_word: c_int,
) {
    if bits.is_null() || bit_count < 0 || word_count <= 0 || bits_per_word <= 0 {
        return;
    }

    let mut word = 0;
    while word < word_count {
        core::ptr::write_volatile(bits.add(word as usize), 0);
        word += 1;
    }

    let limit = (word_count as c_long).wrapping_mul(bits_per_word as c_long);
    let mut bit = 0;
    while bit < bit_count && (bit as c_long) < limit {
        let word_index = bit / bits_per_word;
        let bit_index = bit % bits_per_word;
        let word_ptr = bits.add(word_index as usize);
        let value = core::ptr::read_volatile(word_ptr) | ((1 as c_ulong) << (bit_index as usize));
        core::ptr::write_volatile(word_ptr, value);
        bit += 1;
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_read_buffer_status_result(
    buf: *mut c_char,
    size: usize,
    bytes_read: c_long,
) -> c_int {
    if bytes_read < 0 {
        return bytes_read as c_int;
    }
    if buf.is_null() || bytes_read as usize >= size {
        return -ENOSPC;
    }

    *buf.add(bytes_read as usize) = NUL;
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_parse_long_result(
    buf: *const c_char,
    value_out: *mut c_long,
) -> c_int {
    if buf.is_null() || value_out.is_null() {
        return 0;
    }

    let mut pos = 0usize;
    while is_ascii_space(c_byte(buf, pos)) {
        pos += 1;
    }

    let mut negative = false;
    if c_byte(buf, pos) == b'-' {
        negative = true;
        pos += 1;
    } else if c_byte(buf, pos) == b'+' {
        pos += 1;
    }

    let mut saw_digit = false;
    let mut value = 0 as c_long;
    loop {
        let byte = c_byte(buf, pos);
        if !byte.is_ascii_digit() {
            break;
        }

        saw_digit = true;
        value = value.wrapping_mul(10).wrapping_add((byte - b'0') as c_long);
        pos += 1;
    }

    if !saw_digit {
        return 0;
    }

    *value_out = if negative {
        value.wrapping_neg()
    } else {
        value
    };
    1
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_pci_realpath_valid_result(path: *const c_char) -> c_int {
    starts_with(path, b"../../../devices/") as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_ptr_hash_result(ptr: c_ulong, mask: c_ulong) -> c_int {
    (ptr & mask) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_ptr_eq_result(a: c_ulong, b: c_ulong) -> c_int {
    (a == b) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_file_to_pidfd_lookup_match_result(
    entry_filp: c_ulong,
    filp: c_ulong,
    entry_group_leader: c_ulong,
    group_leader: c_ulong,
) -> c_int {
    (entry_filp == filp && entry_group_leader == group_leader) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_file_to_pidfd_remove_match_result(
    entry_filp: c_ulong,
    filp: c_ulong,
    entry_os: c_ulong,
    os: c_ulong,
    entry_group_leader: c_ulong,
    group_leader: c_ulong,
    entry_fd: c_int,
    fd: c_int,
) -> c_int {
    (entry_filp == filp && entry_os == os && entry_group_leader == group_leader && entry_fd == fd)
        as c_int
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_tofu_dev_path_result(path: *const c_char) -> c_int {
    starts_with(path, TOFU_DEV_PREFIX) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_tofu_dev_tail_offset_result() -> usize {
    TOFU_DEV_PREFIX.len()
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_tofu_dev_name_copy_result(
    dst: *mut c_char,
    dst_size: usize,
    path: *const c_char,
) {
    if dst.is_null() || dst_size == 0 || path.is_null() {
        return;
    }

    let src = path.add(TOFU_DEV_PREFIX.len());
    let mut i = 0usize;
    let mut pad = false;
    while i < dst_size {
        let byte = if pad { 0 } else { c_byte(src, i) };
        *dst.add(i) = byte as c_char;
        if byte == 0 {
            pad = true;
        }
        i += 1;
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_tofu_cq_path_parse_result(
    path: *const c_char,
    tni_out: *mut c_int,
    cq_out: *mut c_int,
) -> c_int {
    if path.is_null() || tni_out.is_null() || cq_out.is_null() {
        return 0;
    }

    if !starts_with(path, TOFU_CQ_PREFIX) {
        return 0;
    }

    let mut pos = TOFU_CQ_PREFIX.len();
    if !parse_i32_at(path, &mut pos, tni_out) {
        return 0;
    }

    if c_byte(path, pos) != b'c' || c_byte(path, pos + 1) != b'q' {
        return 0;
    }
    pos += 2;

    if !parse_i32_at(path, &mut pos, cq_out) {
        return 0;
    }

    (c_byte(path, pos) == 0) as c_int
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_sysfs_path_error_result(
    path: *const c_char,
    written: c_long,
    path_size: usize,
) -> c_int {
    if written as usize >= path_size {
        return -ENAMETOOLONG;
    }

    if path.is_null() || c_byte(path, 0) != b'/' {
        return -ENOENT;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_binfmt_skip_path_result(path: *const c_char) -> c_int {
    if path.is_null() {
        return 1;
    }

    let mut i = 0usize;
    let mut slash = usize::MAX;
    while c_byte(path, i) != 0 {
        if c_byte(path, i) == b'/' {
            slash = i;
        }
        i += 1;
    }
    if slash != usize::MAX {
        let tail = path.add(slash);
        return (equals_bytes(tail, b"/mcexec")
            || equals_bytes(tail, b"/ihkosctl")
            || equals_bytes(tail, b"/ihkconfig")) as c_int;
    }

    1
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_path_allowed_result(
    file: *const c_char,
    list: *const c_char,
) -> c_int {
    if file.is_null() || list.is_null() {
        return 0;
    }
    if *list == NUL {
        return 1;
    }

    let mut p = 0usize;
    while *list.add(p) != NUL {
        let mut q = p;
        while *list.add(q) != NUL && *list.add(q) != b':' as c_char {
            q += 1;
        }

        let mut end = q;
        while end > p && *list.add(end - 1) == b'/' as c_char {
            end -= 1;
        }

        let mut matched = true;
        let mut i = p;
        while i < end {
            if *file.add(i - p) != *list.add(i) {
                matched = false;
                break;
            }
            i += 1;
        }

        if matched && *file.add(end - p) == b'/' as c_char {
            return 1;
        }

        if *list.add(q) == NUL {
            break;
        }
        p = q + 1;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_pager_treat_as_device_path_result(path: *const c_char) -> c_int {
    let ompi = starts_with(path, b"/tmp/ompi.");
    let dev_shm = starts_with(path, b"/dev/shm/");
    let ple = starts_with(path, b"/var/opt/FJSVtcs/ple/daemonif/")
        && !contains_bytes(path, b"dstore_sm.lock");

    (ompi || dev_shm || ple) as c_int
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_pager_should_populate_path_result(path: *const c_char) -> c_int {
    (starts_with(path, b"/tmp/ompi.")
        || starts_with(path, b"/dev/shm/")
        || starts_with(path, b"/var/opt/FJSVtcs/ple/daemonif/")) as c_int
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_fs_is_tmpfs_result(name: *const c_char) -> c_int {
    equals_bytes(name, b"tmpfs") as c_int
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_fs_is_proc_result(name: *const c_char) -> c_int {
    equals_bytes(name, b"proc") as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_special_char_device_result(major: u32, minor: u32) -> c_int {
    (major == 1 && (minor == 1 || minor == 5)) as c_int
}

unsafe fn write_decimal_name(
    buf: *mut c_char,
    buflen: usize,
    prefix: &[u8],
    value: c_int,
) -> c_int {
    if buf.is_null() || buflen == 0 {
        return -1;
    }

    let mut tmp = [0u8; 16];
    let negative = value < 0;
    let mut n = if negative {
        (-(value as i64)) as u64
    } else {
        value as u64
    };
    let mut digits = 0usize;

    loop {
        *tmp.as_mut_ptr().add(digits) = b'0' + (n % 10) as u8;
        digits += 1;
        n /= 10;
        if n == 0 {
            break;
        }
    }

    let sign_len = negative as usize;
    let total = prefix.len() + sign_len + digits;
    if total + 1 > buflen {
        return -1;
    }

    let mut pos = 0usize;
    while pos < prefix.len() {
        *buf.add(pos) = *prefix.as_ptr().add(pos) as c_char;
        pos += 1;
    }
    if negative {
        *buf.add(pos) = b'-' as c_char;
        pos += 1;
    }
    while digits > 0 {
        digits -= 1;
        *buf.add(pos) = *tmp.as_ptr().add(digits) as c_char;
        pos += 1;
    }
    *buf.add(pos) = NUL;
    pos as c_int
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_format_mcos_name_result(
    buf: *mut c_char,
    buflen: usize,
    osnum: c_int,
) -> c_int {
    write_decimal_name(buf, buflen, b"mcos", osnum)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_format_decimal_name_result(
    buf: *mut c_char,
    buflen: usize,
    value: c_int,
) -> c_int {
    write_decimal_name(buf, buflen, b"", value)
}

#[no_mangle]
pub extern "C" fn mcctrl_futex_cmd_result(op: c_int) -> c_int {
    op & FUTEX_CMD_MASK
}

#[no_mangle]
pub extern "C" fn mcctrl_futex_is_private_result(op: c_int) -> c_int {
    ((op & FUTEX_PRIVATE_FLAG) != 0) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_futex_clock_realtime_result(op: c_int) -> c_int {
    ((op & FUTEX_CLOCK_REALTIME) != 0) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_futex_realtime_cmd_valid_result(cmd: c_int) -> c_int {
    (cmd == FUTEX_WAIT_BITSET || cmd == FUTEX_WAIT_REQUEUE_PI) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_futex_wait_uses_timeout_result(cmd: c_int) -> c_int {
    (cmd == FUTEX_WAIT_BITSET || cmd == FUTEX_WAIT) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_futex_arg3_is_val2_result(cmd: c_int) -> c_int {
    (cmd == FUTEX_CMP_REQUEUE || cmd == FUTEX_WAKE_OP) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_futex_op_label_result(cmd: c_int) -> *const c_char {
    let label = match cmd {
        FUTEX_WAIT => FUTEX_WAIT_LABEL,
        FUTEX_WAIT_BITSET => FUTEX_WAIT_BITSET_LABEL,
        FUTEX_WAKE => FUTEX_WAKE_LABEL,
        FUTEX_WAKE_OP => FUTEX_WAKE_OP_LABEL,
        FUTEX_WAKE_BITSET => FUTEX_WAKE_BITSET_LABEL,
        FUTEX_CMP_REQUEUE => FUTEX_CMP_REQUEUE_LABEL,
        FUTEX_REQUEUE => FUTEX_REQUEUE_LABEL,
        _ => FUTEX_UNKNOWN_LABEL,
    };

    label.as_ptr() as *const c_char
}
