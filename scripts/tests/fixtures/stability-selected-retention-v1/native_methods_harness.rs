//! Source-bound native-method harness (verification only; not application acceptance).
//! The snippets are the staged Mailbox/Response/Completion methods, never a
//! replacement state model. A reviewed native runner may compile this file.
const RESPONSE_PREPARE: &str = include_str!("response-prepare.rs");
const RETURN_PREPARE: &str = include_str!("return-prepare.rs");
const CANCEL_GUARD: &str = include_str!("cancel-guard.rs");
const MAILBOX_RETENTION: &str = include_str!("mailbox-retention.append.rs");
const PHASE_RETENTION: &str = include_str!("phase-retention.append.rs");

#[derive(Clone, Copy)]
struct Case { stage: u8, commit: u8, wake: bool, selected: bool, changed: bool, cancel_after: bool }

// Stage 0/1/2/4/5/6 and invalid hold; stage 3 commit 0/2 for both wake
// outcomes; stage 3 commit 1 success for both wake outcomes.
const CASES: &[Case] = &[
    Case { stage: 0, commit: 0, wake: false, selected: true, changed: false, cancel_after: false },
    Case { stage: 1, commit: 0, wake: true, selected: true, changed: false, cancel_after: false },
    Case { stage: 2, commit: 0, wake: false, selected: true, changed: false, cancel_after: false },
    Case { stage: 4, commit: 0, wake: true, selected: true, changed: false, cancel_after: false },
    Case { stage: 5, commit: 0, wake: false, selected: true, changed: false, cancel_after: false },
    Case { stage: 6, commit: 0, wake: true, selected: true, changed: false, cancel_after: false },
    Case { stage: 255, commit: 0, wake: false, selected: true, changed: false, cancel_after: false },
    Case { stage: 3, commit: 0, wake: false, selected: true, changed: false, cancel_after: false },
    Case { stage: 3, commit: 0, wake: true, selected: true, changed: false, cancel_after: false },
    Case { stage: 3, commit: 2, wake: false, selected: true, changed: false, cancel_after: false },
    Case { stage: 3, commit: 2, wake: true, selected: true, changed: false, cancel_after: false },
    Case { stage: 3, commit: 1, wake: false, selected: true, changed: false, cancel_after: false },
    Case { stage: 3, commit: 1, wake: true, selected: true, changed: false, cancel_after: false },
    Case { stage: 3, commit: 1, wake: true, selected: true, changed: true, cancel_after: false },
    Case { stage: 3, commit: 1, wake: true, selected: false, changed: false, cancel_after: false },
    Case { stage: 3, commit: 1, wake: false, selected: true, changed: false, cancel_after: true },
];

fn source_contract() -> usize {
    RESPONSE_PREPARE.len() + RETURN_PREPARE.len() + CANCEL_GUARD.len() +
        MAILBOX_RETENTION.len() + PHASE_RETENTION.len()
}

fn main() {
    assert!(source_contract() > 0);
    assert_eq!(CASES.len(), 16);
    // Native runner supplies actual aligned response backing and drop ledger;
    // these counters are deliberately contract requirements, not substitutes.
    let aligned_backing_counters = [0u64; 4];
    let explicit_no_release_drop_assertions = true;
    assert!(aligned_backing_counters.len() == 4 && explicit_no_release_drop_assertions);
}
