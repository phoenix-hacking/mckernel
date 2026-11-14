// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[cfg(f03_sync_child_event_candidate)]
mod f03_perf_alloc_entry_v1 {
    use core::{ffi::c_void,mem::{offset_of,size_of}};
    use crate::abi::{CInt,CLong,CULong,SizeT};
    use crate::f03_perf_attr_callbacks::PerfEventAttr;
    use crate::x86_perfctr::HwPerfEventExtra;
    use super::f03_sync_child_layout_v2::{FullMcPerfEvent,HwPerfEvent};
    use super::{perf_event_alloc_body_result,SyscallPolicyAllocFn,SyscallMckfdFreeFn,
        SyncChildAtomic64SetFn,PerfEventMapFn,PerfEventValidateFn,PerfExtraRegIdFn,
        PerfExtraRegMsrFn,PerfExtraRegIdxFn,PerfHwEventInitFn};

    #[repr(C)]
    struct PerfAllocationBinding {
        alloc_flags:CULong,hardware_type:CULong,cache_type:CULong,raw_type:CULong,reference_cycles:CULong,
        allocate:Option<SyscallPolicyAllocFn>,release:Option<SyscallMckfdFreeFn>,
        atomic_set:Option<SyncChildAtomic64SetFn>,hardware_map:Option<PerfEventMapFn>,
        cache_map:Option<PerfEventMapFn>,cache_extra_map:Option<PerfEventMapFn>,raw_map:Option<PerfEventMapFn>,
        validate:Option<PerfEventValidateFn>,extra_id:Option<PerfExtraRegIdFn>,
        extra_msr:Option<PerfExtraRegMsrFn>,extra_index:Option<PerfExtraRegIdxFn>,initialize:Option<PerfHwEventInitFn>,
    }
    unsafe extern "C" { static f03_perf_allocation_binding_v1:PerfAllocationBinding; }

    /// Keep the original event allocation, initialized bytes and publication protocol.
    ///
    /// # Safety
    /// Nonnull attributes are aligned, initialized genuine perf_event_attr objects
    /// retained during this synchronous call; nonnull output is writable pointer
    /// storage. Providers retain their existing allocation/lifetime contracts.
    /// The complete existing Rust body releases a failed allocation exactly once
    /// and publishes output only on success. This entry does not own a live PMU.
    #[no_mangle]
    pub unsafe extern "C" fn f03_perf_event_allocate_v1(output:*mut *mut c_void,attribute:*mut c_void)->CInt {
        let attribute=attribute.cast::<PerfEventAttr>();
        let (event_type,config,frequency,sample_frequency,sample_period)=if attribute.is_null() {
            (0,0,0,0,0)
        } else {
            // SAFETY: Raw scalar/union reads preserve the original initialized C
            // bitfield allocation unit, without borrowing a whole foreign object.
            unsafe { ((*attribute).type_ as CULong,(*attribute).config,
                (((*attribute).flags>>PerfEventAttr::FREQUENCY_SHIFT)&1) as CInt,
                (*attribute).sampling.sample_freq,(*attribute).sampling.sample_period) }
        };
        unsafe {
            let binding=&f03_perf_allocation_binding_v1;
            perf_event_alloc_body_result(output,attribute.cast(),size_of::<FullMcPerfEvent>(),size_of::<PerfEventAttr>(),
                binding.alloc_flags,offset_of!(FullMcPerfEvent,attr),offset_of!(FullMcPerfEvent,group_entry),
                offset_of!(FullMcPerfEvent,sibling_list),offset_of!(FullMcPerfEvent,sample_freq),
                offset_of!(FullMcPerfEvent,nr_siblings),offset_of!(FullMcPerfEvent,count),
                offset_of!(FullMcPerfEvent,child_count_total),offset_of!(FullMcPerfEvent,parent),
                offset_of!(FullMcPerfEvent,hw)+offset_of!(HwPerfEvent,sample_period),
                offset_of!(FullMcPerfEvent,hw)+offset_of!(HwPerfEvent,last_period),
                offset_of!(FullMcPerfEvent,hw)+offset_of!(HwPerfEvent,period_left),
                offset_of!(FullMcPerfEvent,use_invariant_tsc),offset_of!(FullMcPerfEvent,hw_config),
                offset_of!(FullMcPerfEvent,hw_config_ext),offset_of!(FullMcPerfEvent,extra_reg)+offset_of!(HwPerfEventExtra,config),
                offset_of!(FullMcPerfEvent,extra_reg)+offset_of!(HwPerfEventExtra,reg),
                offset_of!(FullMcPerfEvent,extra_reg)+offset_of!(HwPerfEventExtra,idx),
                event_type,config,frequency,sample_frequency,sample_period,
                binding.hardware_type,binding.cache_type,binding.raw_type,binding.reference_cycles,
                binding.allocate,binding.release,binding.atomic_set,binding.hardware_map,binding.cache_map,
                binding.cache_extra_map,binding.raw_map,binding.validate,binding.extra_id,binding.extra_msr,
                binding.extra_index,binding.initialize) as CInt
        }
    }

    #[no_mangle]
    pub static F03_PERF_ALLOCATION_ABI:[CULong;52]=[
        (size_of::<FullMcPerfEvent>()) as CULong,
        (core::mem::align_of::<FullMcPerfEvent>()) as CULong,
        (size_of::<PerfEventAttr>()) as CULong,
        (core::mem::align_of::<PerfEventAttr>()) as CULong,
        (offset_of!(PerfEventAttr,type_)) as CULong,
        (offset_of!(PerfEventAttr,config)) as CULong,
        (offset_of!(PerfEventAttr,sampling)) as CULong,
        (offset_of!(PerfEventAttr,flags)) as CULong,
        (offset_of!(FullMcPerfEvent,attr)) as CULong,
        (offset_of!(FullMcPerfEvent,group_entry)) as CULong,
        (offset_of!(FullMcPerfEvent,sibling_list)) as CULong,
        (offset_of!(FullMcPerfEvent,sample_freq)) as CULong,
        (offset_of!(FullMcPerfEvent,nr_siblings)) as CULong,
        (offset_of!(FullMcPerfEvent,count)) as CULong,
        (offset_of!(FullMcPerfEvent,child_count_total)) as CULong,
        (offset_of!(FullMcPerfEvent,parent)) as CULong,
        (offset_of!(FullMcPerfEvent,hw)+offset_of!(HwPerfEvent,sample_period)) as CULong,
        (offset_of!(FullMcPerfEvent,hw)+offset_of!(HwPerfEvent,last_period)) as CULong,
        (offset_of!(FullMcPerfEvent,hw)+offset_of!(HwPerfEvent,period_left)) as CULong,
        (offset_of!(FullMcPerfEvent,use_invariant_tsc)) as CULong,
        (offset_of!(FullMcPerfEvent,hw_config)) as CULong,
        (offset_of!(FullMcPerfEvent,hw_config_ext)) as CULong,
        (offset_of!(FullMcPerfEvent,extra_reg)+offset_of!(HwPerfEventExtra,config)) as CULong,
        (offset_of!(FullMcPerfEvent,extra_reg)+offset_of!(HwPerfEventExtra,reg)) as CULong,
        (offset_of!(FullMcPerfEvent,extra_reg)+offset_of!(HwPerfEventExtra,idx)) as CULong,
        (size_of::<PerfAllocationBinding>()) as CULong,
        (core::mem::align_of::<PerfAllocationBinding>()) as CULong,
        (offset_of!(PerfAllocationBinding,alloc_flags)) as CULong,
        (offset_of!(PerfAllocationBinding,hardware_type)) as CULong,
        (offset_of!(PerfAllocationBinding,cache_type)) as CULong,
        (offset_of!(PerfAllocationBinding,raw_type)) as CULong,
        (offset_of!(PerfAllocationBinding,reference_cycles)) as CULong,
        (offset_of!(PerfAllocationBinding,allocate)) as CULong,
        (offset_of!(PerfAllocationBinding,release)) as CULong,
        (offset_of!(PerfAllocationBinding,atomic_set)) as CULong,
        (offset_of!(PerfAllocationBinding,hardware_map)) as CULong,
        (offset_of!(PerfAllocationBinding,cache_map)) as CULong,
        (offset_of!(PerfAllocationBinding,cache_extra_map)) as CULong,
        (offset_of!(PerfAllocationBinding,raw_map)) as CULong,
        (offset_of!(PerfAllocationBinding,validate)) as CULong,
        (offset_of!(PerfAllocationBinding,extra_id)) as CULong,
        (offset_of!(PerfAllocationBinding,extra_msr)) as CULong,
        (offset_of!(PerfAllocationBinding,extra_index)) as CULong,
        (offset_of!(PerfAllocationBinding,initialize)) as CULong,
        (2) as CULong,
        (0) as CULong,
        (3) as CULong,
        (4) as CULong,
        (9) as CULong,
        (size_of::<CULong>()) as CULong,
        (size_of::<CLong>()) as CULong,
        (size_of::<CInt>()) as CULong
    ];
}
