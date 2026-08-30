// SPDX-License-Identifier: GPL-2.0
//
// Compile-fail shape for the per-file scalar provider-open receipt.  This is
// a language-ownership proof only; it is not a kernel build or runtime result.

struct ProviderOpenLease {
    receipt: i64,
}

impl Drop for ProviderOpenLease {
    fn drop(&mut self) {
        let _consumed_once = self.receipt;
    }
}

fn duplicate_receipt(owner: ProviderOpenLease) {
    let _first_owner = owner;
    let _second_owner = owner;
}

fn main() {
    duplicate_receipt(ProviderOpenLease { receipt: 1 });
}
