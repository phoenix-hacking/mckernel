// SPDX-License-Identifier: GPL-2.0
#![allow(dead_code)]

#[path = "../../../host-kernel/native-rust/ihk_mapping.rs"]
mod ihk_mapping;

use ihk_mapping::{
    LinuxErrno, MmapProtection, MmapProtectionPolicy, MmapTransaction,
    PageGeometry, PhysicalRange, UserMmapRequest,
};

fn request() -> UserMmapRequest {
    let pages = PageGeometry::new(12).unwrap();
    UserMmapRequest::validate(
        0x1000,
        0x2000,
        1,
        pages,
        PhysicalRange::new(0x1000, 0x1000).unwrap(),
        MmapProtection {
            readable: true,
            writable: false,
            executable: false,
            shared: true,
        },
        MmapProtectionPolicy {
            require_readable: true,
            allow_write: false,
            allow_execute: false,
            require_shared: true,
        },
    )
    .unwrap()
}

fn discard_transaction() {
    MmapTransaction::new(request());
}

fn discard_rollback_plan() {
    let mut transaction = MmapTransaction::new(request());
    transaction.rollback(LinuxErrno::ENOMEM).unwrap();
}

fn main() {}
