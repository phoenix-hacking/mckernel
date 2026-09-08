// SPDX-License-Identifier: GPL-2.0-only
//! Actual native sysfs owners, exercised through Linux in a disposable guest.

use core::{
    mem::{align_of, offset_of, size_of},
    sync::atomic::{AtomicU64, AtomicUsize, Ordering},
};
use kernel::{bindings, prelude::*};

#[path = "../../../host-kernel/native-rust/sysfs_objects.rs"]
mod sysfs_objects;
use sysfs_objects::{AttributeOps, Directory, File, Link};

module! {
    type: SysfsVerify,
    name: "mckernel_sysfs_objects_verify",
    author: "McKernel developers",
    description: "Native sysfs ownership and callback retirement verification",
    license: "GPL",
}

#[used]
#[link_section = ".mckernel_sysfs_layout"]
static LAYOUT: [usize; 21] = [
    size_of::<bindings::kobject>(),
    align_of::<bindings::kobject>(),
    offset_of!(bindings::kobject, name),
    offset_of!(bindings::kobject, parent),
    offset_of!(bindings::kobject, ktype),
    offset_of!(bindings::kobject, sd),
    offset_of!(bindings::kobject, kref),
    size_of::<bindings::kobj_type>(),
    align_of::<bindings::kobj_type>(),
    offset_of!(bindings::kobj_type, release),
    offset_of!(bindings::kobj_type, sysfs_ops),
    size_of::<bindings::attribute>(),
    align_of::<bindings::attribute>(),
    offset_of!(bindings::attribute, name),
    offset_of!(bindings::attribute, mode),
    size_of::<bindings::kobj_attribute>(),
    align_of::<bindings::kobj_attribute>(),
    offset_of!(bindings::kobj_attribute, attr),
    offset_of!(bindings::kobj_attribute, show),
    offset_of!(bindings::kobj_attribute, store),
    bindings::PAGE_SIZE as usize,
];

static LIVE: AtomicUsize = AtomicUsize::new(0);
static ACTIVE: AtomicUsize = AtomicUsize::new(0);
static READS: AtomicUsize = AtomicUsize::new(0);

struct Value {
    value: AtomicU64,
    slow: bool,
    overflow: bool,
}

impl Value {
    fn new(slow: bool, overflow: bool) -> Self {
        LIVE.fetch_add(1, Ordering::Relaxed);
        Self {
            value: AtomicU64::new(35),
            slow,
            overflow,
        }
    }
}

impl Drop for Value {
    fn drop(&mut self) {
        // Per-fixture teardown removes the slow file first, then all others.
        if self.slow {
            assert_eq!(ACTIVE.load(Ordering::Acquire), 0);
        }
        LIVE.fetch_sub(1, Ordering::Relaxed);
    }
}

impl AttributeOps for Value {
    fn show(&self, output: &mut [u8]) -> Result<usize> {
        if self.overflow {
            return Ok(bindings::PAGE_SIZE as usize);
        }
        if self.slow {
            ACTIVE.fetch_add(1, Ordering::Release);
            pr_info!("MCKERNEL_SYSFS_VERIFY slow_enter\n");
            // SAFETY: Sysfs show is sleepable. Deliberately hold an active
            // callback while userspace asks rmmod to remove the module.
            unsafe { bindings::msleep(1000) };
        }
        let mut value = self.value.load(Ordering::Acquire);
        let mut digits = [0_u8; 20];
        let mut count = 0;
        loop {
            digits[count] = b'0' + (value % 10) as u8;
            count += 1;
            value /= 10;
            if value == 0 {
                break;
            }
        }
        for index in 0..count {
            output[index] = digits[count - 1 - index];
        }
        output[count] = b'\n';
        READS.fetch_add(1, Ordering::Relaxed);
        if self.slow {
            ACTIVE.fetch_sub(1, Ordering::Release);
            pr_info!("MCKERNEL_SYSFS_VERIFY slow_exit\n");
        }
        Ok(count + 1)
    }

    fn store(&self, input: &[u8]) -> Result<usize> {
        if self.overflow {
            return Ok(input.len() + 1);
        }
        let mut value = 0_u64;
        let number = input.strip_suffix(b"\n").unwrap_or(input);
        if number.is_empty() {
            return Err(EINVAL);
        }
        for digit in number {
            if !digit.is_ascii_digit() {
                return Err(EINVAL);
            }
            value = value
                .checked_mul(10)
                .and_then(|v| v.checked_add((digit - b'0') as u64))
                .ok_or(EINVAL)?;
        }
        self.value.store(value, Ordering::Release);
        Ok(input.len())
    }
}

struct Active;

impl AttributeOps for Active {
    fn show(&self, output: &mut [u8]) -> Result<usize> {
        output[0] = b'0' + ACTIVE.load(Ordering::Acquire).min(9) as u8;
        output[1] = b'\n';
        Ok(2)
    }
}

struct SysfsVerify {
    slow: Option<File<Value>>,
    value: Option<File<Value>>,
    overflow: Option<File<Value>>,
    active: Option<File<Active>>,
    replacement_file: Option<File<Value>>,
    replacement_child: Option<Directory>,
    replacement: Option<Directory>,
    link: Option<Link>,
    child: Option<Directory>,
    root: Option<Directory>,
}

impl kernel::Module for SysfsVerify {
    fn init(_module: &'static ThisModule) -> Result<Self> {
        assert_eq!(LIVE.load(Ordering::Relaxed), 0);
        let root = Directory::new(None, kernel::c_str!("mckernel_sysfs_verify"))?;
        for name in [
            kernel::c_str!(""),
            kernel::c_str!("."),
            kernel::c_str!(".."),
            kernel::c_str!("a/b"),
        ] {
            assert_eq!(Directory::new(Some(&root), name).err(), Some(EINVAL));
            assert_eq!(
                File::new(&root, name, 0o644, Value::new(false, false)).err(),
                Some(EINVAL)
            );
        }
        assert_eq!(LIVE.load(Ordering::Relaxed), 0);
        let child = Directory::new(Some(&root), kernel::c_str!("child"))?;
        pr_info!("MCKERNEL_SYSFS_VERIFY expected_duplicate_begin\n");
        assert_eq!(
            Directory::new(Some(&root), kernel::c_str!("child")).err(),
            Some(EEXIST)
        );
        let value = File::new(
            &child,
            kernel::c_str!("value"),
            0o644,
            Value::new(false, false),
        )?;
        assert_eq!(
            File::new(
                &child,
                kernel::c_str!("value"),
                0o644,
                Value::new(false, false)
            )
            .err(),
            Some(EEXIST)
        );
        let link = Link::new(&root, &child, kernel::c_str!("alias"))?;
        assert_eq!(
            Link::new(&root, &child, kernel::c_str!("alias")).err(),
            Some(EEXIST)
        );
        pr_info!("MCKERNEL_SYSFS_VERIFY expected_duplicate_end\n");
        assert_eq!(
            Link::new(&root, &child, kernel::c_str!("..")).err(),
            Some(EINVAL)
        );

        // Remove a parent before its still-owned descendants, recreate its
        // name, then retire the old owners. They must not remove the new tree.
        let old = Directory::new(Some(&root), kernel::c_str!("reused"))?;
        let old_child = Directory::new(Some(&old), kernel::c_str!("nested"))?;
        let old_file = File::new(
            &old_child,
            kernel::c_str!("value"),
            0o444,
            Value::new(false, false),
        )?;
        let old_link = Link::new(&old_child, &child, kernel::c_str!("alias"))?;
        drop(old);
        let replacement = Directory::new(Some(&root), kernel::c_str!("reused"))?;
        let replacement_child = Directory::new(Some(&replacement), kernel::c_str!("nested"))?;
        let replacement_file = File::new(
            &replacement_child,
            kernel::c_str!("value"),
            0o444,
            Value::new(false, false),
        )?;
        drop(old_file);
        drop(old_link);
        drop(old_child);

        let slow = File::new(
            &child,
            kernel::c_str!("slow"),
            0o444,
            Value::new(true, false),
        )?;
        let overflow = File::new(
            &child,
            kernel::c_str!("overflow"),
            0o644,
            Value::new(false, true),
        )?;
        let active = File::new(&root, kernel::c_str!("active"), 0o444, Active)?;
        assert_eq!(LIVE.load(Ordering::Relaxed), 4);
        pr_info!("MCKERNEL_SYSFS_VERIFY published live=4 invalid_names=4 duplicate_directory=1 duplicate_file=1 duplicate_link=1 parent_before_children=1 layout_values=21\n");
        Ok(Self {
            slow: Some(slow),
            value: Some(value),
            overflow: Some(overflow),
            active: Some(active),
            replacement_file: Some(replacement_file),
            replacement_child: Some(replacement_child),
            replacement: Some(replacement),
            link: Some(link),
            child: Some(child),
            root: Some(root),
        })
    }
}

impl Drop for SysfsVerify {
    fn drop(&mut self) {
        let active = ACTIVE.load(Ordering::Acquire);
        pr_info!("MCKERNEL_SYSFS_VERIFY retiring active={}\n", active);
        drop(self.slow.take());
        drop(self.link.take());
        drop(self.value.take());
        drop(self.overflow.take());
        drop(self.active.take());
        drop(self.replacement_file.take());
        drop(self.replacement_child.take());
        drop(self.replacement.take());
        drop(self.child.take());
        drop(self.root.take());
        assert_eq!(ACTIVE.load(Ordering::Acquire), 0);
        assert_eq!(LIVE.load(Ordering::Relaxed), 0);
        pr_info!(
            "MCKERNEL_SYSFS_VERIFY retired live=0 active=0 reads={}\n",
            READS.load(Ordering::Relaxed)
        );
    }
}
