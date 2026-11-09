mod dispatch_and_msr_entries {
    type IssueIpi = unsafe extern "C" fn(u32, u32);

    #[no_mangle]
    pub(crate) static mut x86_issue_ipi: Option<IssueIpi> = None;

    const _: () = {
        assert!(core::mem::size_of::<Option<IssueIpi>>() == 8);
        assert!(core::mem::align_of::<Option<IssueIpi>>() == 8);
    };
}
