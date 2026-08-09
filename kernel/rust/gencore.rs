use core::{
    ffi::{c_char, c_void},
    mem::{offset_of, size_of},
    ptr::{null_mut, read_volatile},
};

use crate::{
    abi::{
        AbiListHead, CInt, CLong, CULong, Coretable, Elf64Ehdr, ElfCoreNote, ElfPrstatus64,
        Process, ProcessVm, SizeT, Thread, VmRange,
    },
    object_helpers,
};

const EINVAL: CInt = 22;
const GENCORE_FILE: &[u8] = b"kernel/rust/gencore.rs\0";
const VM_NOT_FOUND_FMT: &[u8] = b"%s: ERROR: vm not found\n\0";
const ALLOC_PROGRAM_HEADER_FMT: &[u8] = b"%s: ERROR: allocating program header\n\0";
const ALLOC_NOTE_FMT: &[u8] = b"%s: ERROR: allocating NOTE\n\0";
const ALLOC_CORETABLE_FMT: &[u8] = b"%s: ERROR: allocating coretable\n\0";
const PT_ERROR_FMT: &[u8] = b"%s: error: ihk_mc_pt_virt_to_phys for %lx failed (%d)\n\0";
const GENCORE_NAME: &[u8] = b"gencore\0";

extern "C" {
    fn _kmalloc(size: CInt, flags: CInt, file: *mut c_char, line: CInt) -> *mut c_void;
    fn _kfree(ptr: *mut c_void, file: *mut c_char, line: CInt);
    fn phys_to_virt(phys: CULong) -> *mut c_void;
    fn virt_to_phys(virt: *mut c_void) -> CULong;
    fn ihk_mc_pt_virt_to_phys(
        page_table: *mut c_void,
        virt: *mut c_void,
        phys: *mut CULong,
    ) -> CInt;
    fn lookup_process_memory_range(vm: *mut ProcessVm, start: CULong, end: CULong) -> *mut VmRange;
    fn next_process_memory_range(vm: *mut ProcessVm, range: *mut VmRange) -> *mut VmRange;
    fn arch_fill_prstatus(
        prstatus: *mut ElfPrstatus64,
        thread: *mut Thread,
        regs: *mut c_void,
        sig: CInt,
    );
    fn arch_fill_thread_core_info(head: *mut ElfCoreNote, thread: *mut Thread, regs: *mut c_void);
    fn arch_get_thread_core_info_size() -> CInt;
    fn __mcs_rwlock_reader_lock_noirq(lock: *mut c_void, node: *mut c_void);
    fn __mcs_rwlock_reader_unlock_noirq(lock: *mut c_void, node: *mut c_void);
    fn kprintf(format: *const c_char, ...) -> CInt;
}

#[inline(always)]
fn file_ptr() -> *mut c_char {
    GENCORE_FILE.as_ptr() as *mut c_char
}

unsafe extern "C" fn gencore_alloc_bridge(size: SizeT, flags: CULong) -> *mut c_void {
    _kmalloc(size as CInt, flags as CInt, file_ptr(), line!() as CInt)
}

unsafe extern "C" fn gencore_free_bridge(ptr: *mut c_void) {
    _kfree(ptr, file_ptr(), line!() as CInt);
}

unsafe extern "C" fn gencore_zero_bridge(ptr: *mut c_void, size: SizeT) {
    if !ptr.is_null() {
        core::ptr::write_bytes(ptr, 0, size);
    }
}

unsafe extern "C" fn gencore_phys_to_virt_bridge(phys: CULong) -> *mut c_void {
    phys_to_virt(phys)
}

unsafe extern "C" fn gencore_virt_to_phys_bridge(vaddr: CULong) -> CULong {
    virt_to_phys(vaddr as *mut c_void)
}

unsafe extern "C" fn gencore_arch_fill_prstatus_bridge(
    prstatus: *mut c_void,
    thread: *mut c_void,
    regs: *mut c_void,
    sig: CInt,
) {
    arch_fill_prstatus(
        prstatus.cast::<ElfPrstatus64>(),
        thread.cast::<Thread>(),
        regs,
        sig,
    );
}

unsafe extern "C" fn gencore_pt_virt_to_phys_bridge(
    page_table: *mut c_void,
    vaddr: CULong,
    phys: *mut CULong,
) -> CInt {
    ihk_mc_pt_virt_to_phys(page_table, vaddr as *mut c_void, phys)
}

unsafe extern "C" fn gencore_lookup_range_bridge(vm: *mut c_void) -> *mut c_void {
    lookup_process_memory_range(vm.cast::<ProcessVm>(), 0, CULong::MAX).cast::<c_void>()
}

unsafe extern "C" fn gencore_next_range_bridge(vm: *mut c_void, range: *mut c_void) -> *mut c_void {
    next_process_memory_range(vm.cast::<ProcessVm>(), range.cast::<VmRange>()).cast::<c_void>()
}

unsafe extern "C" fn gencore_range_start_bridge(range: *mut c_void) -> CULong {
    (*range.cast::<VmRange>()).start
}

unsafe extern "C" fn gencore_range_end_bridge(range: *mut c_void) -> CULong {
    (*range.cast::<VmRange>()).end
}

unsafe extern "C" fn gencore_range_flag_bridge(range: *mut c_void) -> CULong {
    (*range.cast::<VmRange>()).flag
}

unsafe extern "C" fn gencore_range_objoff_bridge(range: *mut c_void) -> CLong {
    (*range.cast::<VmRange>()).objoff
}

unsafe extern "C" fn gencore_range_log_bridge(
    _start: CULong,
    _end: CULong,
    _flag: CULong,
    _objoff: CLong,
) {
}

unsafe extern "C" fn gencore_coretable_log_bridge(
    _index: CInt,
    _len: CLong,
    _addr: CULong,
    _start: CULong,
) {
}

unsafe extern "C" fn gencore_alloc_error_log_bridge(stage: CInt) {
    match stage {
        1 => {
            kprintf(
                ALLOC_PROGRAM_HEADER_FMT.as_ptr().cast(),
                GENCORE_NAME.as_ptr(),
            );
        }
        2 => {
            kprintf(ALLOC_NOTE_FMT.as_ptr().cast(), GENCORE_NAME.as_ptr());
        }
        3 => {
            kprintf(ALLOC_CORETABLE_FMT.as_ptr().cast(), GENCORE_NAME.as_ptr());
        }
        _ => {}
    }
}

unsafe extern "C" fn gencore_pt_error_log_bridge(start: CULong, error: CInt) {
    kprintf(
        PT_ERROR_FMT.as_ptr().cast(),
        GENCORE_NAME.as_ptr(),
        start,
        error,
    );
}

unsafe fn gencore_thread_from_siblings(link: *mut AbiListHead) -> *mut Thread {
    link.cast::<u8>()
        .sub(offset_of!(Thread, siblings_list))
        .cast::<Thread>()
}

unsafe extern "C" fn gencore_first_thread_bridge(proc: *mut c_void) -> *mut c_void {
    let proc = proc.cast::<Process>();
    let head = &raw mut (*proc).threads_list;

    if read_volatile(&(*head).next) == head {
        return null_mut();
    }

    gencore_thread_from_siblings(read_volatile(&(*head).next)).cast::<c_void>()
}

unsafe extern "C" fn gencore_next_thread_bridge(
    proc: *mut c_void,
    thread: *mut c_void,
) -> *mut c_void {
    let proc = proc.cast::<Process>();
    let thread = thread.cast::<Thread>();
    let head = &raw mut (*proc).threads_list;
    let next = read_volatile(&(*thread).siblings_list.next);

    if next == head {
        return null_mut();
    }

    gencore_thread_from_siblings(next).cast::<c_void>()
}

unsafe extern "C" fn gencore_thread_tid_bridge(thread: *mut c_void) -> CInt {
    (*thread.cast::<Thread>()).tid
}

unsafe extern "C" fn gencore_thread_regs_bridge(thread: *mut c_void) -> *mut c_void {
    (*thread.cast::<Thread>()).coredump_regs
}

unsafe extern "C" fn gencore_arch_thread_info_size_bridge() -> CInt {
    arch_get_thread_core_info_size()
}

unsafe extern "C" fn gencore_fill_prstatus_note_bridge(
    note: *mut c_void,
    thread: *mut c_void,
    sig: CInt,
) {
    fill_prstatus(note.cast::<ElfCoreNote>(), thread.cast::<Thread>(), sig);
}

unsafe extern "C" fn gencore_arch_fill_thread_info_bridge(
    note: *mut c_void,
    thread: *mut c_void,
    regs: *mut c_void,
) {
    arch_fill_thread_core_info(note.cast::<ElfCoreNote>(), thread.cast::<Thread>(), regs);
}

unsafe extern "C" fn gencore_fill_prpsinfo_note_bridge(
    note: *mut c_void,
    proc: *mut c_void,
    cmdline: *mut c_char,
) {
    fill_prpsinfo(note.cast::<ElfCoreNote>(), proc.cast::<Process>(), cmdline);
}

unsafe extern "C" fn gencore_fill_auxv_note_bridge(note: *mut c_void, proc: *mut c_void) {
    fill_auxv(note.cast::<ElfCoreNote>(), proc.cast::<Process>());
}

unsafe extern "C" fn gencore_get_note_size_bridge(proc: *mut c_void) -> CInt {
    get_note_size(proc.cast::<Process>())
}

unsafe extern "C" fn gencore_fill_note_bridge(
    note: *mut c_void,
    proc: *mut c_void,
    cmdline: *mut c_char,
    sig: CInt,
) {
    fill_note(note, proc.cast::<Process>(), cmdline, sig);
}

#[no_mangle]
pub unsafe extern "C" fn fill_elf_header(eh: *mut Elf64Ehdr, segs: CInt) {
    let _ = object_helpers::gencore_fill_elf_header_body_result(eh, segs);
}

#[no_mangle]
pub extern "C" fn get_prstatus_size() -> CInt {
    object_helpers::gencore_prstatus_size_result()
}

#[no_mangle]
pub extern "C" fn get_prpsinfo_size() -> CInt {
    object_helpers::gencore_prpsinfo_size_result()
}

#[no_mangle]
pub extern "C" fn get_auxv_size() -> CInt {
    object_helpers::gencore_auxv_size_result()
}

#[no_mangle]
pub unsafe extern "C" fn fill_prstatus(head: *mut ElfCoreNote, thread: *mut Thread, sig: CInt) {
    let regs = if thread.is_null() {
        null_mut()
    } else {
        (*thread).coredump_regs
    };

    let _ = object_helpers::gencore_fill_prstatus_body_result(
        head,
        thread.cast::<c_void>(),
        regs,
        sig,
        Some(gencore_arch_fill_prstatus_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn fill_prpsinfo(
    head: *mut ElfCoreNote,
    proc: *mut Process,
    cmdline: *mut c_char,
) {
    if proc.is_null() {
        return;
    }

    let _ = object_helpers::gencore_fill_prpsinfo_body_result(
        head,
        (*proc).status,
        (*proc).pid,
        cmdline,
    );
}

#[no_mangle]
pub unsafe extern "C" fn fill_auxv(head: *mut ElfCoreNote, proc: *mut Process) {
    if proc.is_null() {
        return;
    }

    let _ = object_helpers::gencore_fill_auxv_body_result(head, (*proc).saved_auxv.as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn get_note_size(proc: *mut Process) -> CInt {
    if proc.is_null() {
        return -EINVAL;
    }

    __mcs_rwlock_reader_lock_noirq((&raw mut (*proc).threads_lock).cast::<c_void>(), null_mut());
    let note = object_helpers::gencore_note_size_threads_body_result(
        proc.cast::<c_void>(),
        (*proc).pid,
        Some(gencore_first_thread_bridge),
        Some(gencore_next_thread_bridge),
        Some(gencore_thread_tid_bridge),
        Some(gencore_arch_thread_info_size_bridge),
    );
    __mcs_rwlock_reader_unlock_noirq((&raw mut (*proc).threads_lock).cast::<c_void>(), null_mut());

    note
}

#[no_mangle]
pub unsafe extern "C" fn fill_note(
    note: *mut c_void,
    proc: *mut Process,
    cmdline: *mut c_char,
    sig: CInt,
) {
    if proc.is_null() {
        return;
    }

    __mcs_rwlock_reader_lock_noirq((&raw mut (*proc).threads_lock).cast::<c_void>(), null_mut());
    let _ = object_helpers::gencore_fill_note_threads_body_result(
        note,
        proc.cast::<c_void>(),
        cmdline,
        sig,
        (*proc).pid,
        null_mut(),
        Some(gencore_first_thread_bridge),
        Some(gencore_next_thread_bridge),
        Some(gencore_thread_tid_bridge),
        Some(gencore_thread_regs_bridge),
        Some(gencore_arch_thread_info_size_bridge),
        Some(gencore_fill_prstatus_note_bridge),
        Some(gencore_arch_fill_thread_info_bridge),
        Some(gencore_fill_prpsinfo_note_bridge),
        Some(gencore_fill_auxv_note_bridge),
    );
    __mcs_rwlock_reader_unlock_noirq((&raw mut (*proc).threads_lock).cast::<c_void>(), null_mut());
}

#[no_mangle]
pub unsafe extern "C" fn gencore(
    proc: *mut Process,
    coretable: *mut *mut Coretable,
    chunks: *mut CInt,
    cmdline: *mut c_char,
    sig: CInt,
) -> CInt {
    if proc.is_null() || coretable.is_null() || chunks.is_null() {
        return -EINVAL;
    }

    *chunks = 3;
    let vm = (*proc).vm;
    if vm.is_null() {
        kprintf(VM_NOT_FOUND_FMT.as_ptr().cast(), GENCORE_NAME.as_ptr());
        return -EINVAL;
    }
    let address_space = (*vm).address_space;
    let page_table = (*address_space).page_table;

    let mut segs = 1;
    let scan_error = object_helpers::gencore_scan_ranges_for_counts_body_result(
        vm.cast::<c_void>(),
        page_table,
        chunks,
        &mut segs,
        Some(gencore_lookup_range_bridge),
        Some(gencore_next_range_bridge),
        Some(gencore_range_start_bridge),
        Some(gencore_range_end_bridge),
        Some(gencore_range_flag_bridge),
        Some(gencore_range_objoff_bridge),
        Some(gencore_range_log_bridge),
        Some(gencore_pt_virt_to_phys_bridge),
    );
    if scan_error != 0 {
        return scan_error;
    }

    object_helpers::gencore_generate_image_body_result(
        proc.cast::<c_void>(),
        vm.cast::<c_void>(),
        page_table,
        coretable,
        chunks,
        segs,
        (*vm).region.user_start,
        (*vm).region.user_end,
        cmdline,
        sig,
        size_of::<Elf64Ehdr>(),
        size_of::<crate::abi::Elf64Phdr>(),
        size_of::<Coretable>(),
        Some(gencore_alloc_bridge),
        Some(gencore_zero_bridge),
        Some(gencore_free_bridge),
        Some(gencore_get_note_size_bridge),
        Some(gencore_fill_note_bridge),
        Some(gencore_virt_to_phys_bridge),
        Some(gencore_lookup_range_bridge),
        Some(gencore_next_range_bridge),
        Some(gencore_range_start_bridge),
        Some(gencore_range_end_bridge),
        Some(gencore_range_flag_bridge),
        Some(gencore_pt_virt_to_phys_bridge),
        Some(gencore_coretable_log_bridge),
        Some(gencore_alloc_error_log_bridge),
        Some(gencore_pt_error_log_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn freecore(coretable: *mut *mut Coretable) {
    let _ = object_helpers::gencore_freecore_body_result(
        coretable,
        Some(gencore_phys_to_virt_bridge),
        Some(gencore_free_bridge),
    );
}
