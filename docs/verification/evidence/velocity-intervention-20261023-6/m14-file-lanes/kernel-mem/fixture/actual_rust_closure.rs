#![no_std]
#![allow(dead_code)]
#[path="actual_abi.rs"] mod abi;
use core::ffi::c_void;
use abi::{CInt,CULong,ProcessVm,AddressSpace,TlbFlushEntry,CPU_SET_WORDS};

type MemRdtscFn=unsafe extern "C" fn()->CULong;
type MemCurrentCpuFn=unsafe extern "C" fn()->CInt;
type MemGetVectorFn=unsafe extern "C" fn(CInt)->CInt;
type MemInterruptCpuFn=unsafe extern "C" fn(CInt,CInt);
type MemNoirqLockFn=unsafe extern "C" fn(CULong);
type MemAtomicSetFn=unsafe extern "C" fn(CULong,CInt);
type MemAtomicIncFn=unsafe extern "C" fn(CULong);
type MemAtomicDecFn=unsafe extern "C" fn(CULong);
type MemAtomicReadFn=unsafe extern "C" fn(CULong)->CInt;
type MemFlushTlbSingleFn=unsafe extern "C" fn(CULong);
type MemFlushTlbAllFn=unsafe extern "C" fn();
type MemPauseFn=unsafe extern "C" fn();
type MemKmallocIrqSaveFn=unsafe extern "C" fn()->CULong;
type MemKmallocIrqRestoreFn=unsafe extern "C" fn(CULong);
const EINVAL:CInt=22;
const PAGE_SHIFT:CULong=12;
const PAGE_SIZE:CULong=1<<PAGE_SHIFT;
const PAGE_MASK:CULong=!(PAGE_SIZE-1);
unsafe extern "C" {
 fn ihk_mc_get_processor_id()->CInt;
 fn ihk_mc_get_vector(type_:CInt)->CInt;
 fn ihk_mc_interrupt_cpu(cpu:CInt,vector:CInt)->CInt;
 #[link_name="tlb_flush_vector"] static mut MEM_TLB_FLUSH_VECTOR_FIRST:TlbFlushEntry;
 static mem_remote_tlb_geometry:[CInt;3];
 fn mem_tlb_rdtsc_bridge()->CULong;
 fn mem_tlb_noirq_lock_bridge(addr:CULong);
 fn mem_tlb_noirq_unlock_bridge(addr:CULong);
 fn mem_tlb_atomic_set_bridge(addr:CULong,value:CInt);
 fn mem_tlb_atomic_inc_bridge(addr:CULong);
 fn mem_tlb_atomic_read_bridge(addr:CULong)->CInt;
 fn mem_tlb_flush_single_bridge(addr:CULong);
 fn mem_tlb_flush_all_bridge();
 fn mem_tlb_pause_bridge();
}

#[no_mangle]
pub unsafe extern "C" fn mem_tlb_current_cpu_bridge() -> CInt {
    unsafe { ihk_mc_get_processor_id() }
}

#[no_mangle]
pub unsafe extern "C" fn mem_tlb_get_vector_bridge(type_: CInt) -> CInt {
    unsafe { ihk_mc_get_vector(type_) }
}

#[no_mangle]
pub unsafe extern "C" fn mem_tlb_interrupt_cpu_bridge(cpu: CInt, vector: CInt) {
    let _ = unsafe { ihk_mc_interrupt_cpu(cpu, vector) };
}

#[no_mangle]
pub unsafe extern "C" fn remote_flush_tlb_array_cpumask(
    vm: *mut ProcessVm, addr: *mut CULong, nr_addr: CInt, cpu_id: CInt,
) {
    let geometry = unsafe { core::ptr::read(core::ptr::addr_of!(mem_remote_tlb_geometry)) };
    let _ = unsafe {
        mem_remote_flush_tlb_array_body_result(
            vm, addr, nr_addr, cpu_id,
            core::ptr::addr_of_mut!(MEM_TLB_FLUSH_VECTOR_FIRST),
            geometry[0], geometry[1], geometry[2],
            Some(mem_tlb_rdtsc_bridge), Some(mem_tlb_current_cpu_bridge),
            Some(mem_tlb_get_vector_bridge), Some(mem_tlb_interrupt_cpu_bridge),
            Some(mem_tlb_noirq_lock_bridge), Some(mem_tlb_noirq_unlock_bridge),
            Some(mem_tlb_atomic_set_bridge), Some(mem_tlb_atomic_inc_bridge),
            Some(mem_tlb_atomic_read_bridge), Some(mem_tlb_flush_single_bridge),
            Some(mem_tlb_flush_all_bridge), Some(mem_tlb_pause_bridge),
        )
    };
}

#[no_mangle]
pub unsafe extern "C" fn mem_remote_flush_tlb_array_body_result(
    vm: *mut ProcessVm,
    addr: *mut CULong,
    nr_addr: CInt,
    _cpu_id: CInt,
    tlb_flush_vector: *mut TlbFlushEntry,
    vector_size: CInt,
    vector_start: CInt,
    cpu_set_bits: CInt,
    rdtsc_fn: Option<MemRdtscFn>,
    current_cpu_fn: Option<MemCurrentCpuFn>,
    get_vector_fn: Option<MemGetVectorFn>,
    interrupt_cpu_fn: Option<MemInterruptCpuFn>,
    lock_fn: Option<MemNoirqLockFn>,
    unlock_fn: Option<MemNoirqLockFn>,
    atomic_set_fn: Option<MemAtomicSetFn>,
    atomic_inc_fn: Option<MemAtomicIncFn>,
    atomic_read_fn: Option<MemAtomicReadFn>,
    flush_single_fn: Option<MemFlushTlbSingleFn>,
    flush_all_fn: Option<MemFlushTlbAllFn>,
    pause_fn: Option<MemPauseFn>,
) -> CInt {
    let (
        Some(rdtsc),
        Some(current_cpu),
        Some(get_vector),
        Some(interrupt_cpu),
        Some(lock),
        Some(unlock),
        Some(atomic_set),
        Some(atomic_inc),
        Some(atomic_read),
        Some(flush_single),
        Some(flush_all),
        Some(pause),
    ) = (
        rdtsc_fn,
        current_cpu_fn,
        get_vector_fn,
        interrupt_cpu_fn,
        lock_fn,
        unlock_fn,
        atomic_set_fn,
        atomic_inc_fn,
        atomic_read_fn,
        flush_single_fn,
        flush_all_fn,
        pause_fn,
    )
    else {
        return -EINVAL;
    };

    if vm.is_null()
        || addr.is_null()
        || nr_addr <= 0
        || tlb_flush_vector.is_null()
        || vector_size <= 0
        || cpu_set_bits <= 0
    {
        return -EINVAL;
    }

    let aspace: *mut AddressSpace = (*vm).address_space;
    if aspace.is_null() {
        return -EINVAL;
    }

    let first_addr = *addr;
    let flush_ind = if first_addr != 0 {
        ((first_addr >> PAGE_SHIFT) % (vector_size as CULong)) as CInt
    } else {
        (rdtsc() % (vector_size as CULong)) as CInt
    };
    let flush_entry = tlb_flush_vector.add(flush_ind as usize);

    let bits_per_word = core::mem::size_of::<CULong>() * 8;
    let max_bits = cpu_set_bits as usize;
    let mut cpu_word_count = (max_bits + bits_per_word - 1) / bits_per_word;
    if cpu_word_count > CPU_SET_WORDS {
        cpu_word_count = CPU_SET_WORDS;
    }
    let mut cpu_bits = core::mem::MaybeUninit::<[CULong; CPU_SET_WORDS]>::uninit();
    let cpu_bits_ptr = cpu_bits.as_mut_ptr().cast::<CULong>();
    lock((&raw mut (*aspace).cpu_set_lock).cast::<c_void>() as CULong);
    let mut i = 0usize;
    while i < cpu_word_count {
        let word = core::ptr::read_volatile(&raw const (*aspace).cpu_set.bits[i]);
        core::ptr::write_volatile(cpu_bits_ptr.add(i), word);
        i += 1;
    }
    unlock((&raw mut (*aspace).cpu_set_lock).cast::<c_void>() as CULong);

    lock((&raw mut (*flush_entry).lock).cast::<c_void>() as CULong);
    (*flush_entry).vm = vm;
    (*flush_entry).addr = addr;
    (*flush_entry).nr_addr = nr_addr;
    atomic_set(
        (&raw mut (*flush_entry).pending).cast::<c_void>() as CULong,
        0,
    );

    let mut word_index = 0usize;
    while word_index < cpu_word_count {
        let mut word = core::ptr::read_volatile(cpu_bits_ptr.add(word_index));
        while word != 0 {
            let bit = word.trailing_zeros() as usize;
            let cpu = word_index * bits_per_word + bit;
            if cpu >= max_bits {
                break;
            }
            if current_cpu() != cpu as CInt {
                atomic_inc((&raw mut (*flush_entry).pending).cast::<c_void>() as CULong);
                let vector = get_vector(flush_ind + vector_start);
                interrupt_cpu(cpu as CInt, vector);
            }
            word &= word - 1;
        }
        word_index += 1;
    }

    if first_addr != 0 {
        let mut index = 0isize;
        while index < nr_addr as isize {
            flush_single(*addr.offset(index) & PAGE_MASK);
            index += 1;
        }
    } else {
        flush_all();
    }

    while atomic_read((&raw mut (*flush_entry).pending).cast::<c_void>() as CULong) != 0 {
        pause();
    }
    unlock((&raw mut (*flush_entry).lock).cast::<c_void>() as CULong);

    flush_ind
}

#[no_mangle]
pub unsafe extern "C" fn mem_tlb_flush_handler_body_result(
    vector: CInt,
    tlb_flush_vector: *mut TlbFlushEntry,
    vector_size: CInt,
    vector_start: CInt,
    irq_save_fn: Option<MemKmallocIrqSaveFn>,
    irq_restore_fn: Option<MemKmallocIrqRestoreFn>,
    flush_single_fn: Option<MemFlushTlbSingleFn>,
    flush_all_fn: Option<MemFlushTlbAllFn>,
    atomic_dec_fn: Option<MemAtomicDecFn>,
) -> CInt {
    let (Some(irq_save), Some(irq_restore), Some(flush_single), Some(flush_all), Some(atomic_dec)) = (
        irq_save_fn,
        irq_restore_fn,
        flush_single_fn,
        flush_all_fn,
        atomic_dec_fn,
    ) else {
        return -EINVAL;
    };

    if tlb_flush_vector.is_null() || vector_size <= 0 {
        return -EINVAL;
    }

    let index = vector - vector_start;
    if index < 0 || index >= vector_size {
        return -EINVAL;
    }

    let flags = irq_save();
    let flush_entry = tlb_flush_vector.add(index as usize);
    let addr = (*flush_entry).addr;
    if !addr.is_null() && *addr != 0 {
        let mut i = 0isize;
        while i < (*flush_entry).nr_addr as isize {
            flush_single(*addr.offset(i) & PAGE_MASK);
            i += 1;
        }
    } else {
        flush_all();
    }
    atomic_dec((&raw mut (*flush_entry).pending).cast::<c_void>() as CULong);
    irq_restore(flags);

    0
}

#[no_mangle]
pub static F01_ACTUAL_LAYOUT:[usize;7]=[
 core::mem::offset_of!(ProcessVm,address_space),
 core::mem::offset_of!(AddressSpace,cpu_set),
 core::mem::offset_of!(AddressSpace,cpu_set_lock),
 core::mem::size_of::<TlbFlushEntry>(),core::mem::align_of::<TlbFlushEntry>(),
 core::mem::offset_of!(TlbFlushEntry,pending),core::mem::size_of::<CInt>(),
];
