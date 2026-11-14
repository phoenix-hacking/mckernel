// VERIFICATION OVERLAY ONLY. All observations below copy host ledger metadata.
#[allow(dead_code)]
impl SyscallResponse {
    fn verification_claim(&self) -> crate::stability_observer::Claim {
        use crate::stability_observer as observer;
        observer::Claim {
            os: self.memory.owner.slot(),
            generation: self.memory.owner.generation(),
            response: observer::Tag {
                index: self.slot,
                serial: Some(self.tag.serial),
                physical: self.tag.span.physical,
                end: self.tag.span.end,
            },
            payload: self.payload.as_ref().map(|(tag, _, _)| observer::Tag {
                index: self.slot,
                serial: Some(tag.serial),
                physical: tag.span.physical,
                end: tag.span.end,
            }),
        }
    }
}
#[allow(dead_code)]
impl Memory {
    #[inline(never)]
    pub(super) fn verification_emit_ledger(&self, sequence: u64) -> bool {
        let mut complete = true;
        // Each class is an independent, internally locked sample. Never claim
        // these seven samples are one atomic snapshot of the full ledger.
        for class in 0..7 {
            complete &= self.verification_emit_class(sequence, class);
        }
        complete
    }

    #[inline(never)]
    fn verification_emit_class(&self, sequence: u64, class: usize) -> bool {
        use crate::stability_observer as observer;
        let mut rows = observer::Rows::<observer::Tag, { observer::TAGS }>::new();
        let serial;
        let slots;
        let name;
        {
            let ledger = self.ledger.lock();
            serial = ledger.serial;
            if class == 0 {
                name = "fixed";
                slots = ledger.fixed.len();
                rows.total = slots;
                for (index, span) in ledger.fixed.iter().take(observer::TAGS).enumerate() {
                    rows.rows[rows.used] = Some(observer::Tag {
                        index,
                        serial: None,
                        physical: span.physical,
                        end: span.end,
                    });
                    rows.used += 1;
                }
            } else if class <= 3 {
                let entries = match class {
                    1 => {
                        name = "requests";
                        &ledger.requests
                    }
                    2 => {
                        name = "responses";
                        &ledger.responses
                    }
                    _ => {
                        name = "payloads";
                        &ledger.payloads
                    }
                };
                slots = entries.len();
                for (index, tag) in entries
                    .iter()
                    .enumerate()
                    .filter_map(|(index, tag)| tag.as_ref().map(|tag| (index, tag)))
                {
                    rows.push(observer::Tag {
                        index,
                        serial: Some(tag.serial),
                        physical: tag.span.physical,
                        end: tag.span.end,
                    });
                }
            } else {
                let entries = match class {
                    4 => {
                        name = "snoops";
                        &ledger.snoops
                    }
                    5 => {
                        name = "procfs";
                        &ledger.procfs
                    }
                    _ => {
                        name = "zeroing";
                        &ledger.zeroing
                    }
                };
                slots = entries.len();
                rows.total = slots;
                for (index, tag) in entries.iter().take(observer::TAGS).enumerate() {
                    rows.rows[rows.used] = Some(observer::Tag {
                        index,
                        serial: Some(tag.serial),
                        physical: tag.span.physical,
                        end: tag.span.end,
                    });
                    rows.used += 1;
                }
            }
        }
        kernel::pr_info!("STABILITY_OWNER_DOMAIN version={} sequence={} domain=ledger class={} os={} generation={} last_serial={} slots={} total={} emitted={} complete={}\n",
            observer::VERSION, sequence, name, self.owner.slot(), self.owner.generation(), serial, slots,
            rows.total, rows.used, rows.complete());
        for (index, row) in rows.rows.iter().flatten().enumerate() {
            kernel::pr_info!(
                "STABILITY_OWNER_TAG version={} sequence={} class={} ordinal={} row={:?}\n",
                observer::VERSION,
                sequence,
                name,
                index,
                row
            );
        }
        rows.complete()
    }
}
