// SPDX-License-Identifier: GPL-2.0-only
//! Actual native sysfs owners, exercised through Linux in a disposable guest.

use core::{
    mem::{align_of, offset_of, size_of},
    sync::atomic::{AtomicBool, AtomicU64, AtomicUsize, Ordering},
};
use kernel::{bindings, prelude::*, sync::Arc};

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

enum RetireObject {
    Directory(Directory),
    File(File<Value>),
}

impl RetireObject {
    fn retire(self) {
        match self {
            Self::Directory(object) => drop(object),
            Self::File(object) => drop(object),
        }
    }
}

struct RetireJob {
    object: Option<RetireObject>,
    start: Arc<AtomicBool>,
    entered: Arc<AtomicBool>,
}

// SAFETY: start_retire_thread transfers exactly one Box to this callback.
// Module initialization joins every started thread before returning. Workers
// stay alive until kthread_stop, so their task pointers cannot retire early.
unsafe extern "C" fn retire_thread(data: *mut core::ffi::c_void) -> i32 {
    let mut job = unsafe { Box::from_raw(data.cast::<RetireJob>()) };
    job.entered.store(true, Ordering::Release);
    while !job.start.load(Ordering::Acquire) && !unsafe { bindings::kthread_should_stop() } {
        unsafe { bindings::msleep(1) };
    }
    job.object.take().unwrap().retire();
    while !unsafe { bindings::kthread_should_stop() } {
        unsafe { bindings::msleep(1) };
    }
    0
}

struct RetireThread(*mut bindings::task_struct);

impl Drop for RetireThread {
    fn drop(&mut self) {
        // SAFETY: The worker entered its callback before this owner was
        // returned and remains alive until this unique stop/join call.
        assert_eq!(unsafe { bindings::kthread_stop(self.0) }, 0);
    }
}

fn start_retire_thread(object: RetireObject, start: Arc<AtomicBool>) -> Result<RetireThread> {
    let entered = Arc::new(AtomicBool::new(false), GFP_KERNEL)?;
    let job = Box::new(
        RetireJob {
            object: Some(object),
            start,
            entered: entered.clone(),
        },
        GFP_KERNEL,
    )?;
    let data = Box::into_raw(job);
    // SAFETY: Linux starts only the resident callback with its owned Box.
    // NUMA_NO_NODE is -1 and the name is a constant variadic format.
    let task = unsafe {
        bindings::kthread_create_on_node(
            Some(retire_thread),
            data.cast(),
            -1,
            kernel::c_str!("mck-sysfs-test").as_char_ptr(),
        )
    };
    if (-4095..0).contains(&(task as isize)) {
        // SAFETY: An error pointer means Linux never started the callback.
        unsafe { drop(Box::from_raw(data)) };
        return Err(kernel::error::to_result(task as isize as i32)
            .err()
            .unwrap_or(EIO));
    }
    assert!(!task.is_null());
    unsafe { bindings::wake_up_process(task) };
    // Establish callback entry before kthread_stop can skip execution. The
    // outer disposable-guest deadline bounds an unexpected scheduler failure.
    while !entered.load(Ordering::Acquire) {
        unsafe { bindings::msleep(1) };
    }
    Ok(RetireThread(task))
}

fn namespace_races(root: &Directory) -> Result {
    for _ in 0..16 {
        let directory = Directory::new(Some(root), kernel::c_str!("race"))?;
        let file = File::new(
            &directory,
            kernel::c_str!("value"),
            0o444,
            Value::new(false, false),
        )?;
        let start = Arc::new(AtomicBool::new(false), GFP_KERNEL)?;
        let parent_thread = start_retire_thread(RetireObject::Directory(directory), start.clone())?;
        let file_thread = start_retire_thread(RetireObject::File(file), start.clone())?;
        start.store(true, Ordering::Release);
        drop(parent_thread);
        drop(file_thread);
        assert_eq!(LIVE.load(Ordering::Relaxed), 0);
        // Both retirements finished. The name must be immediately reusable.
        drop(Directory::new(Some(root), kernel::c_str!("race"))?);
    }
    pr_info!("MCKERNEL_SYSFS_VERIFY namespace_races=16 joined=32\n");
    Ok(())
}

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
        namespace_races(&root)?;
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
