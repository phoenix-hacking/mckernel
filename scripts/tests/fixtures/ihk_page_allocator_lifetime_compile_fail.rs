// SPDX-License-Identifier: GPL-2.0

#[path = "../../../host-kernel/native-rust/page_allocator.rs"]
mod page_allocator;

use page_allocator::{BitmapPageAllocator, PageAllocation};
use std::sync::atomic::AtomicU64;

fn escaped_lease<'borrow>() -> PageAllocation<'borrow, 'borrow> {
    let mut allocated: [AtomicU64; 1] = std::array::from_fn(|_| AtomicU64::new(0));
    let mut reserved: [AtomicU64; 1] = std::array::from_fn(|_| AtomicU64::new(0));
    let allocator =
        BitmapPageAllocator::new(0x1000, 64 * 4096, 4096, &mut allocated, &mut reserved)
            .unwrap();
    allocator.allocate(1).unwrap()
}

fn main() {}
