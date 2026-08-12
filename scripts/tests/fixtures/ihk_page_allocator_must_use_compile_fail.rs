// SPDX-License-Identifier: GPL-2.0

#[path = "../../../host-kernel/native-rust/page_allocator.rs"]
mod page_allocator;

use page_allocator::BitmapPageAllocator;
use std::sync::atomic::AtomicU64;

fn main() {
    let mut allocated: [AtomicU64; 1] = std::array::from_fn(|_| AtomicU64::new(0));
    let mut reserved: [AtomicU64; 1] = std::array::from_fn(|_| AtomicU64::new(0));
    let allocator =
        BitmapPageAllocator::new(0x1000, 64 * 4096, 4096, &mut allocated, &mut reserved)
            .unwrap();

    allocator.allocate(1).unwrap();
    allocator.reserve(0x1000, 1).unwrap();
}
