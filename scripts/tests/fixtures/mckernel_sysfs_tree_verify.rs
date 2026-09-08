// SPDX-License-Identifier: GPL-2.0-only
//! Actual Linux tree ownership plus an unchanged-C-body metadata trace.

use core::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use kernel::{bindings, fmt, prelude::*, str::CString, sync::Arc};

#[path = "../../../host-kernel/native-rust/sysfs_objects.rs"]
mod sysfs_objects;
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/sysfs_tree.rs"]
mod sysfs_tree;
use sysfs_objects::{AttributeOps, Directory};
use sysfs_tree::{Handle, Tree};

module! {
    type: TreeVerify,
    name: "mckernel_sysfs_tree_verify",
    author: "McKernel developers",
    description: "Native sysfs tree and callback lifetime verification",
    license: "GPL",
}

struct Text(Vec<u8>);
impl AttributeOps for Text {
    fn show(&self, output: &mut [u8]) -> Result<usize> {
        let target = output.get_mut(..self.0.len()).ok_or(EIO)?;
        target.copy_from_slice(&self.0);
        Ok(self.0.len())
    }
}

struct Number(AtomicU64);
impl AttributeOps for Number {
    fn show(&self, output: &mut [u8]) -> Result<usize> {
        let value = CString::try_from_fmt(fmt!("{}\n", self.0.load(Ordering::Acquire)))?;
        let bytes = value.as_bytes();
        output
            .get_mut(..bytes.len())
            .ok_or(EIO)?
            .copy_from_slice(bytes);
        Ok(bytes.len())
    }
    fn store(&self, input: &[u8]) -> Result<usize> {
        let digits = input.strip_suffix(b"\n").unwrap_or(input);
        if digits.is_empty() {
            return Err(EINVAL);
        }
        let mut value = 0_u64;
        for &digit in digits {
            if !digit.is_ascii_digit() {
                return Err(EINVAL);
            }
            value = value
                .checked_mul(10)
                .and_then(|value| value.checked_add((digit - b'0') as u64))
                .ok_or(EINVAL)?;
        }
        self.0.store(value, Ordering::Release);
        Ok(input.len())
    }
}

struct Slow(Arc<AtomicBool>);
impl AttributeOps for Slow {
    fn show(&self, output: &mut [u8]) -> Result<usize> {
        self.0.store(true, Ordering::Release);
        // SAFETY: Linux sysfs callbacks are sleepable; the owner must drain us.
        unsafe { bindings::msleep(1000) };
        output[..5].copy_from_slice(b"done\n");
        self.0.store(false, Ordering::Release);
        Ok(5)
    }
}
struct Active(Arc<AtomicBool>);
impl AttributeOps for Active {
    fn show(&self, output: &mut [u8]) -> Result<usize> {
        output[0] = b'0' + u8::from(self.0.load(Ordering::Acquire));
        output[1] = b'\n';
        Ok(2)
    }
}

fn trace(tree: &mut Tree) -> Result<Vec<u8>> {
    let mut result = Vec::new();
    for (index, line) in include_bytes!("native-sysfs-tree-cases.txt")
        .split(|&byte| byte == b'\n')
        .filter(|line| !line.is_empty())
        .enumerate()
    {
        let mut fields = line.split(|&byte| byte == b'|');
        let operation = fields.next().ok_or(EINVAL)?;
        let path = fields.next().ok_or(EINVAL)?;
        let argument = fields.next().ok_or(EINVAL)?;
        assert!(fields.next().is_none());
        let status = match operation {
            b"K" => tree.lookup(path).map(|_| ()),
            b"D" => tree.mkdir(path).map(|_| ()),
            b"F" => tree
                .create(path, 0o444, Number(AtomicU64::new(35)))
                .map(|_| ()),
            b"L" => tree
                .lookup(argument)
                .and_then(|target| tree.symlink(target, path))
                .map(|_| ()),
            b"U" => tree.unlink(path, (argument[0] - b'0') as u32),
            _ => return Err(EINVAL),
        }
        .map_or_else(|error| error.to_errno(), |_| 0);
        let line = CString::try_from_fmt(fmt!("{} {} {}\n", index, status, tree.len()))?;
        result.extend_from_slice(line.as_bytes(), GFP_KERNEL)?;
    }
    assert!(result.len() < 4095);
    Ok(result)
}

fn rejects<T>(result: Result<T>, code: i32) {
    assert_eq!(result.err().map(|error| error.to_errno()), Some(code));
}

fn properties(tree: &mut Tree, outer: &Directory) -> Result {
    let original = tree.len();
    for value in [0, 1_u64 << 63, u64::MAX] {
        rejects(Handle::from_wire(value), -22);
    }
    let root = tree.lookup(b"/")?;
    assert!(root.wire() > 0 && root.wire() < i64::MAX as u64);
    tree.create(b"/sys/protected/keep", 0o444, Number(AtomicU64::new(35)))?;
    for path in [&b"/"[..], b"/sys", b"///sys///"] {
        rejects(tree.unlink(path, 0), -1);
    }
    tree.lookup(b"/sys/protected/keep")?;
    rejects(tree.symlink(root, b"/sys/no-prefix/link"), -22);
    rejects(tree.lookup(b"/sys/no-prefix"), -2);
    for path in [
        &b"/sys/no-prefix/../bad"[..],
        b"/sys/no-prefix/./bad",
        b"/sys/no-prefix/bad\0tail",
    ] {
        rejects(tree.mkdir(path), -22);
        rejects(tree.lookup(path), -22);
        rejects(tree.unlink(path, 0), -22);
        rejects(tree.lookup(b"/sys/no-prefix"), -2);
    }
    let mut long = [b'x'; 1024];
    long[..5].copy_from_slice(b"/sys/");
    rejects(tree.mkdir(&long[..261]), -36);
    rejects(tree.mkdir(&long), -36);
    rejects(
        tree.create(b"/sys/no-prefix/value", 0o1000, Number(AtomicU64::new(0))),
        -22,
    );
    rejects(tree.lookup(b"/sys/no-prefix"), -2);
    let stale = tree.mkdir(b"/sys/stale")?;
    tree.unlink(b"/sys/stale", 0)?;
    let replacement = tree.mkdir(b"/sys/stale")?;
    assert_ne!(stale, replacement);
    rejects(tree.symlink(stale, b"/sys/no-prefix/link"), -2);
    rejects(
        tree.symlink(Handle::from_wire(i64::MAX as u64)?, b"/sys/no-prefix/link"),
        -2,
    );
    rejects(tree.lookup(b"/sys/no-prefix"), -2);
    let other_parent = Directory::new(Some(outer), kernel::c_str!("other"))?;
    let mut other = Tree::new(Directory::new(Some(&other_parent), kernel::c_str!("sys"))?)?;
    let foreign = other.mkdir(b"/sys/target")?;
    rejects(tree.symlink(foreign, b"/sys/no-prefix/link"), -2);
    rejects(other.symlink(replacement, b"/sys/no-prefix/link"), -2);
    drop(other);
    let mut other = Tree::new(Directory::new(Some(&other_parent), kernel::c_str!("sys"))?)?;
    let new = other.mkdir(b"/sys/target")?;
    assert_ne!(foreign, new);
    rejects(other.symlink(foreign, b"/sys/no-prefix/link"), -2);
    drop(other);
    drop(other_parent);
    tree.unlink(b"/sys/stale", 0)?;
    tree.unlink(b"/sys/protected", 0)?;
    // Deep teardown must not allocate a recursive kernel-stack traversal.
    let mut deep = [0_u8; 1023];
    deep[..4].copy_from_slice(b"/sys");
    for index in 0..509 {
        deep[4 + index * 2] = b'/';
        deep[5 + index * 2] = b'a';
    }
    tree.mkdir(&deep[..1022])?;
    tree.lookup(&deep[..1022])?;
    tree.unlink(b"/sys/a", 0)?;
    assert_eq!(tree.len(), original);
    pr_info!("MCKERNEL_SYSFS_TREE_VERIFY properties=PASS deep_directories=509 stale=1 cross_tree=1 protected_roots=1\n");
    Ok(())
}

struct TreeVerify {
    tree: Option<Tree>,
    active: Arc<AtomicBool>,
    _outer: Directory,
}

impl kernel::Module for TreeVerify {
    fn init(_module: &'static ThisModule) -> Result<Self> {
        let outer = Directory::new(None, kernel::c_str!("mckernel_sysfs_tree_verify"))?;
        let mut tree = Tree::new(Directory::new(Some(&outer), kernel::c_str!("sys"))?)?;
        let result = trace(&mut tree)?;
        properties(&mut tree, &outer)?;
        tree.create(b"/sys/trace", 0o444, Text(result))?;
        tree.create(b"/sys/live/value", 0o644, Number(AtomicU64::new(35)))?;
        let live = tree.lookup(b"/sys/live")?;
        tree.symlink(live, b"/sys/alias")?;
        let active = Arc::new(AtomicBool::new(false), GFP_KERNEL)?;
        tree.create(b"/sys/live/active", 0o444, Active(active.clone()))?;
        tree.create(b"/sys/live/slow", 0o444, Slow(active.clone()))?;
        pr_info!("MCKERNEL_SYSFS_TREE_VERIFY READY nodes={}\n", tree.len());
        Ok(Self {
            tree: Some(tree),
            active,
            _outer: outer,
        })
    }
}

impl Drop for TreeVerify {
    fn drop(&mut self) {
        pr_info!(
            "MCKERNEL_SYSFS_TREE_VERIFY retiring active={}\n",
            u8::from(self.active.load(Ordering::Acquire))
        );
        drop(self.tree.take());
        assert!(!self.active.load(Ordering::Acquire));
        pr_info!("MCKERNEL_SYSFS_TREE_VERIFY retired tree=empty active=0\n");
    }
}
