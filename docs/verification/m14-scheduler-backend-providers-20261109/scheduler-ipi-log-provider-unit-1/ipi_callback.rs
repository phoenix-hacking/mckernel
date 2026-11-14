mod remaining_cpu_callbacks {
    use core::ptr::addr_of;
    use crate::abi::{CInt, CULong};

    unsafe extern "C" {
        static mut x86_issue_ipi: Option<unsafe extern "C" fn(u32, u32)>;
    }

    type IssueIpi = unsafe extern "C" fn(u32, u32);

    const _: () = {
        assert!(core::mem::size_of::<Option<IssueIpi>>() == 8);
        assert!(core::mem::align_of::<Option<IssueIpi>>() == 8);
    };

    /// Call the same selected IPI transaction target.
    ///
    /// # Safety
    /// The real boot-selected callback and APIC destination/vector satisfy their
    /// original contracts; C implicitly narrowed both arguments to unsigned32.
    #[no_mangle]
    pub unsafe extern "C" fn x86_issue_ipi_bridge(apic_id: CULong, vector: CInt) {
    unsafe {
        addr_of!(x86_issue_ipi).read().unwrap_unchecked()(apic_id as u32, vector as u32);
    }
    }
}
