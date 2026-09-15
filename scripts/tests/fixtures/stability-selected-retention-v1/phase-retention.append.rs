
// VERIFICATION ONLY. The existing slots lock spans the original release-stage
// CAS and release-commit count store, and every matching Mailbox caller.
// A later verification error cannot undo an already authorized publication.
pub(crate) fn retention_released() -> bool {
    stage() == RELEASED && RELEASE_COMMITS.load(Ordering::Acquire) == 1
}
