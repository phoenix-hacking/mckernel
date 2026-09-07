// SPDX-License-Identifier: GPL-2.0

#[path = "../../../host-kernel/native-rust/page_allocator.rs"]
mod page_allocator;
#[path = "../../../host-kernel/native-rust/page_owner_registry.rs"]
mod page_owner_registry;

use page_owner_registry::RawPageOwnerRegistry;

fn assert_sync<T: Sync>() {}

fn main() {
    assert_sync::<RawPageOwnerRegistry<'static, 'static, 'static>>();
}
