// SPDX-License-Identifier: GPL-2.0-only
//! Native procfs owners tested through actual Linux VFS callbacks and rundown.
use core::{
    mem::{align_of, offset_of, size_of},
    sync::atomic::{AtomicBool, AtomicU64, AtomicUsize, Ordering},
};
use kernel::{bindings, prelude::*, sync::Arc};
#[path = "../../../host-kernel/native-rust/procfs_objects.rs"]
mod procfs_objects;
use procfs_objects::{Directory, File, FileOps, Session};

module! {
    type: ProcfsVerify,
    name: "mckernel_procfs_objects_verify",
    author: "McKernel developers",
    description: "Native procfs callback and open-session retirement verification",
    license: "GPL",
}

#[used]
#[link_section = ".mckernel_procfs_layout"]
static LAYOUT: [usize; 27] = [
    size_of::<procfs_objects::abi::Operations>(),
    align_of::<procfs_objects::abi::Operations>(),
    offset_of!(procfs_objects::abi::Operations, flags),
    offset_of!(procfs_objects::abi::Operations, open),
    offset_of!(procfs_objects::abi::Operations, read),
    offset_of!(procfs_objects::abi::Operations, read_iter),
    offset_of!(procfs_objects::abi::Operations, write),
    offset_of!(procfs_objects::abi::Operations, seek),
    offset_of!(procfs_objects::abi::Operations, release),
    offset_of!(procfs_objects::abi::Operations, poll),
    offset_of!(procfs_objects::abi::Operations, ioctl),
    offset_of!(procfs_objects::abi::Operations, compat_ioctl),
    offset_of!(procfs_objects::abi::Operations, mmap),
    offset_of!(procfs_objects::abi::Operations, get_unmapped_area),
    size_of::<bindings::inode>(),
    align_of::<bindings::inode>(),
    offset_of!(bindings::inode, i_private),
    size_of::<bindings::file>(),
    align_of::<bindings::file>(),
    offset_of!(bindings::file, private_data),
    offset_of!(bindings::file, f_pos),
    offset_of!(bindings::file, f_mode),
    size_of::<bindings::kuid_t>(),
    offset_of!(bindings::kuid_t, val),
    size_of::<bindings::kgid_t>(),
    offset_of!(bindings::kgid_t, val),
    cfg!(CONFIG_COMPAT) as usize,
];

static LIVE: AtomicUsize = AtomicUsize::new(0);
static ACTIVE: AtomicUsize = AtomicUsize::new(0);
static OPENED: AtomicUsize = AtomicUsize::new(0);
static RELEASED: AtomicUsize = AtomicUsize::new(0);
static DROPPED: AtomicUsize = AtomicUsize::new(0);
static DENIED: AtomicUsize = AtomicUsize::new(0);

struct State {
    value: AtomicU64,
    opens: AtomicUsize,
    releases: AtomicUsize,
    kind: u32,
}
struct Value(Arc<State>);
impl Value {
    fn new(kind: u32) -> Result<Self> {
        let state = Arc::new(
            State {
                value: AtomicU64::new(35),
                opens: AtomicUsize::new(0),
                releases: AtomicUsize::new(0),
                kind,
            },
            GFP_KERNEL,
        )?;
        LIVE.fetch_add(1, Ordering::Relaxed);
        Ok(Self(state))
    }
}
impl Drop for Value {
    fn drop(&mut self) {
        assert_eq!(
            self.0.opens.load(Ordering::Acquire),
            self.0.releases.load(Ordering::Acquire)
        );
        LIVE.fetch_sub(1, Ordering::Relaxed);
    }
}
struct OpenValue {
    state: Arc<State>,
    released: bool,
}
impl Drop for OpenValue {
    fn drop(&mut self) {
        assert!(self.released, "successful procfs open lacked release");
        DROPPED.fetch_add(1, Ordering::Relaxed);
    }
}
impl FileOps for Value {
    type Session = OpenValue;
    const WRITABLE: bool = true;
    fn open(&self) -> Result<OpenValue> {
        if self.0.kind == 3 {
            DENIED.fetch_add(1, Ordering::Relaxed);
            return Err(EPERM);
        }
        self.0.opens.fetch_add(1, Ordering::Relaxed);
        OPENED.fetch_add(1, Ordering::Relaxed);
        Ok(OpenValue {
            state: self.0.clone(),
            released: false,
        })
    }
}
impl Session for OpenValue {
    fn read(&mut self, position: i64, output: &mut [u8]) -> Result<usize> {
        assert!(!self.released);
        if self.state.kind == 2 {
            return Ok(output.len() + 1);
        }
        if position < 0 {
            return Ok(0);
        }
        if self.state.kind == 4 {
            let bytes = (8192usize.saturating_sub(position as usize)).min(output.len());
            output[..bytes].fill(b'Z');
            return Ok(bytes);
        }
        if self.state.kind == 1 {
            ACTIVE.fetch_add(1, Ordering::Release);
            pr_info!("MCKERNEL_PROCFS_VERIFY slow_enter\n");
            unsafe { bindings::msleep(1000) };
        }
        let mut number = self.state.value.load(Ordering::Acquire);
        let mut digits = [0u8; 20];
        let mut n = 0;
        loop {
            digits[n] = b'0' + (number % 10) as u8;
            n += 1;
            number /= 10;
            if number == 0 {
                break;
            }
        }
        let mut text = [0u8; 21];
        for i in 0..n {
            text[i] = digits[n - i - 1];
        }
        text[n] = b'\n';
        n += 1;
        let start = (position as usize).min(n);
        let bytes = output.len().min(n - start);
        output[..bytes].copy_from_slice(&text[start..start + bytes]);
        if self.state.kind == 1 {
            ACTIVE.fetch_sub(1, Ordering::Release);
            pr_info!("MCKERNEL_PROCFS_VERIFY slow_exit\n");
        }
        Ok(bytes)
    }
    fn write(&mut self, _position: i64, input: &[u8]) -> Result<usize> {
        assert!(!self.released);
        if self.state.kind == 2 {
            return Ok(input.len() + 1);
        }
        let digits = input.strip_suffix(b"\n").unwrap_or(input);
        if digits.is_empty() {
            return Err(EINVAL);
        }
        let mut value = 0u64;
        for byte in digits {
            if !byte.is_ascii_digit() {
                return Err(EINVAL);
            }
            value = value
                .checked_mul(10)
                .and_then(|n| n.checked_add((byte - b'0') as u64))
                .ok_or(EINVAL)?;
        }
        self.state.value.store(value, Ordering::Release);
        Ok(input.len())
    }
    fn release(&mut self) -> Result {
        assert!(!self.released, "duplicate procfs release");
        self.released = true;
        if self.state.kind == 1 {
            assert_eq!(ACTIVE.load(Ordering::Acquire), 0);
        }
        self.state.releases.fetch_add(1, Ordering::Release);
        RELEASED.fetch_add(1, Ordering::Relaxed);
        Ok(())
    }
}
struct Active;
impl FileOps for Active {
    type Session = Active;
    fn open(&self) -> Result<Active> {
        Ok(Active)
    }
}
impl Session for Active {
    fn read(&mut self, position: i64, output: &mut [u8]) -> Result<usize> {
        if position != 0 {
            return Ok(0);
        }
        let text = [b'0' + ACTIVE.load(Ordering::Acquire).min(9) as u8, b'\n'];
        let n = output.len().min(2);
        output[..n].copy_from_slice(&text[..n]);
        Ok(n)
    }
}

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
            kernel::c_str!("mck-proc-test").as_char_ptr(),
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
        let file = File::new(&directory, kernel::c_str!("value"), 0o444, Value::new(0)?)?;
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
    pr_info!("MCKERNEL_PROCFS_VERIFY namespace_races=16 joined=32\n");
    Ok(())
}

struct ProcfsVerify {
    files: Vec<File<Value>>,
    active: Option<File<Active>>,
    directories: Vec<Directory>,
    root: Option<Directory>,
}
impl kernel::Module for ProcfsVerify {
    fn init(_module: &'static ThisModule) -> Result<Self> {
        let root = Directory::new(None, kernel::c_str!("mckernel_procfs_verify"))?;
        for name in [
            kernel::c_str!(""),
            kernel::c_str!("."),
            kernel::c_str!(".."),
            kernel::c_str!("a/b"),
        ] {
            assert_eq!(Directory::new(Some(&root), name).err(), Some(EINVAL));
            assert_eq!(
                File::new(&root, name, 0o644, Value::new(0)?).err(),
                Some(EINVAL)
            );
        }
        assert_eq!(
            File::new(&root, kernel::c_str!("badmode"), 0o1000, Value::new(0)?).err(),
            Some(EINVAL)
        );
        assert_eq!(LIVE.load(Ordering::Relaxed), 0);
        namespace_races(&root)?;
        let child = Directory::new(Some(&root), kernel::c_str!("child"))?;
        assert_eq!(
            Directory::new(Some(&root), kernel::c_str!("child")).err(),
            Some(EEXIST)
        );
        let value = File::owned(
            &child,
            kernel::c_str!("value"),
            0o644,
            Value::new(0)?,
            bindings::kuid_t { val: 1000 },
            bindings::kgid_t { val: 1000 },
        )?;
        assert_eq!(
            File::new(&child, kernel::c_str!("value"), 0o644, Value::new(0)?).err(),
            Some(EEXIST)
        );
        let old = Directory::new(Some(&root), kernel::c_str!("reused"))?;
        let old_child = Directory::new(Some(&old), kernel::c_str!("nested"))?;
        let old_file = File::new(&old_child, kernel::c_str!("value"), 0o444, Value::new(0)?)?;
        drop(old);
        assert_eq!(
            Directory::new(Some(&old_child), kernel::c_str!("late")).err(),
            Some(ENODEV)
        );
        assert_eq!(
            File::new(&old_child, kernel::c_str!("late"), 0o444, Value::new(0)?).err(),
            Some(ENODEV)
        );
        let replacement = Directory::new(Some(&root), kernel::c_str!("reused"))?;
        let replacement_child = Directory::new(Some(&replacement), kernel::c_str!("nested"))?;
        let replacement_file = File::new(
            &replacement_child,
            kernel::c_str!("value"),
            0o444,
            Value::new(0)?,
        )?;
        drop(old_file);
        drop(old_child);
        let mut files = Vec::with_capacity(6, GFP_KERNEL)?;
        files.push(value, GFP_KERNEL)?;
        files.push(replacement_file, GFP_KERNEL)?;
        for (name, kind, mode) in [
            (kernel::c_str!("slow"), 1, 0o444),
            (kernel::c_str!("overflow"), 2, 0o644),
            (kernel::c_str!("denied"), 3, 0o444),
            (kernel::c_str!("large"), 4, 0o444),
        ] {
            files.push(
                File::new(&child, name, mode, Value::new(kind)?)?,
                GFP_KERNEL,
            )?;
        }
        let active = File::new(&root, kernel::c_str!("active"), 0o444, Active)?;
        let mut directories = Vec::with_capacity(3, GFP_KERNEL)?;
        directories.push(child, GFP_KERNEL)?;
        directories.push(replacement_child, GFP_KERNEL)?;
        directories.push(replacement, GFP_KERNEL)?;
        assert_eq!(LIVE.load(Ordering::Relaxed), 6);
        pr_info!("MCKERNEL_PROCFS_VERIFY published live=6 invalid_names=4 duplicate_directory=1 duplicate_file=1 parent_before_children=1 stale_parent_rejections=2 layout_values=27\n");
        Ok(Self {
            files,
            active: Some(active),
            directories,
            root: Some(root),
        })
    }
}
impl Drop for ProcfsVerify {
    fn drop(&mut self) {
        pr_info!(
            "MCKERNEL_PROCFS_VERIFY retiring active={}\n",
            ACTIVE.load(Ordering::Acquire)
        );
        // Remove the root before descendants, including a currently executing
        // read and idle duplicated fds. Linux must drain and release each once.
        drop(self.root.take());
        assert_eq!(ACTIVE.load(Ordering::Acquire), 0);
        assert_eq!(
            OPENED.load(Ordering::Relaxed),
            RELEASED.load(Ordering::Relaxed)
        );
        assert_eq!(
            OPENED.load(Ordering::Relaxed),
            DROPPED.load(Ordering::Relaxed)
        );
        self.files.clear();
        drop(self.active.take());
        self.directories.clear();
        assert_eq!(LIVE.load(Ordering::Relaxed), 0);
        assert_eq!(DENIED.load(Ordering::Relaxed), 1);
        pr_info!("MCKERNEL_PROCFS_VERIFY retired live=0 active=0 opened={} released={} dropped={} denied=1\n",
            OPENED.load(Ordering::Relaxed), RELEASED.load(Ordering::Relaxed), DROPPED.load(Ordering::Relaxed));
    }
}
