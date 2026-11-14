// SPDX-License-Identifier: GPL-2.0

#[path = "../../../host-kernel/native-rust/page_allocator.rs"]
mod page_allocator;
#[path = "../../../host-kernel/native-rust/page_owner_registry.rs"]
mod page_owner_registry;

use core::sync::atomic::AtomicU64;
use page_allocator::BitmapPageAllocator;
use page_owner_registry::{RawPageOwnerRegistry, RawPageOwnerSlot};

fn escape_registry() -> RawPageOwnerRegistry<'static, 'static, 'static> {
    let mut allocated = [AtomicU64::new(0)];
    let mut reserved = [AtomicU64::new(0)];
    let allocator = BitmapPageAllocator::new(
        0x1000,
        64 * 0x1000,
        0x1000,
        &mut allocated,
        &mut reserved,
    )
    .unwrap();
    let mut slots = [RawPageOwnerSlot::empty()];
    RawPageOwnerRegistry::new(&allocator, &mut slots).unwrap()
}

fn main() {
    let _ = escape_registry();
}
