// VERIFICATION OVERLAY ONLY. References below are the exact guest/server
// references field, not a fabricated Linux file refcount or Arc strong count.
#[allow(dead_code)]
impl Registry {
    #[inline(never)]
    pub(crate) fn verification_emit(&self, sequence: u64) -> bool {
        use crate::stability_observer as observer;
        let mut rows = observer::Rows::<observer::Pager, { observer::PAGERS }>::new();
        let slots;
        {
            let entries = self.entries.lock();
            slots = entries.len();
            for (index, pager) in entries
                .iter()
                .enumerate()
                .filter_map(|(index, pager)| pager.as_ref().map(|pager| (index, pager)))
            {
                rows.push(observer::Pager {
                    index,
                    token: pager.token.wire(),
                    references: pager.references,
                    readable_owner: &*pager.readable as *const File as usize,
                    writable_owner: pager
                        .writable
                        .as_ref()
                        .map(|file| &**file as *const File as usize),
                });
            }
        }
        kernel::pr_info!("STABILITY_OWNER_DOMAIN version={} sequence={} domain=pagers slots={} total={} emitted={} complete={} linux_file_refcount=not_observed\n",
            observer::VERSION, sequence, slots, rows.total, rows.used, rows.complete());
        for (index, row) in rows.rows.iter().flatten().enumerate() {
            kernel::pr_info!(
                "STABILITY_OWNER_PAGER version={} sequence={} ordinal={} row={:?}\n",
                observer::VERSION,
                sequence,
                index,
                row
            );
        }
        rows.complete()
    }
}
