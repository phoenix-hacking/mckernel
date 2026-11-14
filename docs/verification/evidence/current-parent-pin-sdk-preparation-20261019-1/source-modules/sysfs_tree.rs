// SPDX-License-Identifier: GPL-2.0-only
//! Owned native sysfs tree, adapting the legacy mcctrl lookup/dig/remove bodies.
//!
//! Handles are checked identities, never addresses. &mut Tree serializes all
//! name mutations; file callbacks use their own stable synchronized payloads
//! and must not reacquire this tree's outer lock while removal drains them.

use core::sync::atomic::{AtomicU64, Ordering};
use kernel::{
    prelude::*,
    str::{CStr, CString},
};

use super::sysfs_objects::{AttributeOps, Directory, File, Link};

const PATH_BYTES: usize = 1024;
const KEEP_ANCESTOR: u32 = 1;
static NEXT_HANDLE: AtomicU64 = AtomicU64::new(1);

fn errno(code: i32) -> Error {
    kernel::error::to_result(code).err().unwrap_or(EIO)
}

/// A positive long-sized identity. Constructing a value proves representation
/// only; Tree checks live membership before using any referenced node.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct Handle(u64);

impl Handle {
    pub(crate) fn from_wire(value: u64) -> Result<Self> {
        if value == 0 || value > i64::MAX as u64 {
            return Err(EINVAL);
        }
        Ok(Self(value))
    }

    pub(crate) fn wire(self) -> u64 {
        self.0
    }

    fn allocate() -> Result<Self> {
        let value = NEXT_HANDLE
            .fetch_update(Ordering::Relaxed, Ordering::Relaxed, |value| {
                (value < i64::MAX as u64).then(|| value + 1)
            })
            .map_err(|_| errno(-75))?;
        Ok(Self(value))
    }
}

fn validate_path(path: &[u8]) -> Result {
    if path.len() >= PATH_BYTES {
        return Err(errno(-36));
    }
    if path.contains(&0) {
        return Err(EINVAL);
    }
    for name in path.split(|&byte| byte == b'/') {
        if name == b"." || name == b".." {
            return Err(EINVAL);
        }
        if name.len() > 255 {
            return Err(errno(-36));
        }
    }
    Ok(())
}

fn component(name: &[u8]) -> Result<CString> {
    if name.is_empty() || name.len() > 255 {
        return Err(EINVAL);
    }
    let mut bytes = [0_u8; 256];
    bytes[..name.len()].copy_from_slice(name);
    let name = CStr::from_bytes_with_nul(&bytes[..name.len() + 1]).map_err(|_| EINVAL)?;
    Ok(CString::try_from(name)?)
}

struct Operations(Box<dyn AttributeOps>);

impl AttributeOps for Operations {
    fn show(&self, output: &mut [u8]) -> Result<usize> {
        self.0.show(output)
    }
    fn store(&self, input: &[u8]) -> Result<usize> {
        self.0.store(input)
    }
}

enum Object {
    Root,
    Directory(Directory),
    File(File<Operations>),
    Link(Link),
}

struct Node {
    handle: Handle,
    parent: Handle,
    name: CString,
    object: Object,
}

/// Flat publication order keeps every parent before its descendants. Deleting
/// nodes preserves that order; handles do not encode vector indices or addresses.
pub(crate) struct Tree {
    nodes: Vec<Node>,
}

impl Tree {
    /// The caller transfers the already OS-bound sys directory. No setup
    /// marker or guest completion is implied by constructing this owner.
    pub(crate) fn new(sys: Directory) -> Result<Self> {
        let root = Handle::allocate()?;
        let child = Handle::allocate()?;
        let mut nodes = Vec::with_capacity(2, GFP_KERNEL)?;
        nodes.push(
            Node {
                handle: root,
                parent: root,
                name: CString::try_from(kernel::c_str!("(the_root)"))?,
                object: Object::Root,
            },
            GFP_KERNEL,
        )?;
        nodes.push(
            Node {
                handle: child,
                parent: root,
                name: CString::try_from(kernel::c_str!("sys"))?,
                object: Object::Directory(sys),
            },
            GFP_KERNEL,
        )?;
        Ok(Self { nodes })
    }

    pub(crate) fn len(&self) -> usize {
        self.nodes.len()
    }

    /// Roll back a failed initial setup while preserving both protected roots.
    /// Reverse publication order drains attributes/links before their parents.
    pub(crate) fn clear_contents(&mut self) {
        while self.nodes.len() > 2 {
            drop(self.nodes.pop());
        }
    }

    fn index(&self, handle: Handle) -> Result<usize> {
        self.nodes
            .iter()
            .position(|node| node.handle == handle)
            .ok_or(ENOENT)
    }

    fn directory(&self, index: usize) -> Result<&Directory> {
        match &self.nodes[index].object {
            Object::Directory(directory) => Ok(directory),
            Object::Root => Err(EPERM),
            _ => Err(errno(-20)),
        }
    }

    /// Same type/name traversal as mcctrl_sysfs_lookup_i_body_result. Links
    /// are leaf objects here; kernel/user sysfs resolution remains Linux-owned.
    fn child(&self, parent: usize, name: &[u8]) -> Result<Option<usize>> {
        if !matches!(
            self.nodes[parent].object,
            Object::Root | Object::Directory(_)
        ) {
            return Err(errno(-20));
        }
        let handle = self.nodes[parent].handle;
        Ok(self.nodes.iter().position(|node| {
            node.handle != handle && node.parent == handle && node.name.as_bytes() == name
        }))
    }

    fn walk(&self, path: &[u8]) -> Result<usize> {
        let mut parent = 0;
        for name in path
            .split(|&byte| byte == b'/')
            .filter(|name| !name.is_empty())
        {
            parent = self.child(parent, name)?.ok_or(ENOENT)?;
        }
        Ok(parent)
    }

    pub(crate) fn lookup(&self, path: &[u8]) -> Result<Handle> {
        validate_path(path)?;
        Ok(self.nodes[self.walk(path)?].handle)
    }

    /// Reserve metadata before Linux publication. A push after this reserve
    /// cannot allocate; an unexpected push error still drops its owned object.
    fn reserve_node(&mut self) -> Result<Handle> {
        self.nodes.reserve(1, GFP_KERNEL)?;
        Handle::allocate()
    }

    fn add_directory(&mut self, parent: usize, name: &[u8]) -> Result<usize> {
        if parent == 0 && name != b"sys" {
            return Err(EPERM);
        }
        if self.child(parent, name)?.is_some() {
            return Err(EEXIST);
        }
        let name = component(name)?;
        let handle = self.reserve_node()?;
        let directory = Directory::new(Some(self.directory(parent)?), &name)?;
        let parent = self.nodes[parent].handle;
        let index = self.nodes.len();
        self.nodes.push(
            Node {
                handle,
                parent,
                name,
                object: Object::Directory(directory),
            },
            GFP_KERNEL,
        )?;
        Ok(index)
    }

    fn dig(&mut self, path: &[u8]) -> Result<usize> {
        let mut parent = 0;
        for name in path
            .split(|&byte| byte == b'/')
            .filter(|name| !name.is_empty())
        {
            parent = match self.child(parent, name)? {
                Some(index) => index,
                None => self.add_directory(parent, name)?,
            };
        }
        if parent != 0 {
            self.directory(parent)?;
        }
        Ok(parent)
    }

    /// The complete path is checked first, so malformed suffixes cannot leave
    /// intermediate directories. Empty final names remain invalid for create.
    fn parent<'a>(&mut self, path: &'a [u8]) -> Result<(usize, &'a [u8])> {
        validate_path(path)?;
        let (prefix, name) = match path.iter().rposition(|&byte| byte == b'/') {
            Some(index) => (&path[..index], &path[index + 1..]),
            None => (&b""[..], path),
        };
        if name.is_empty() {
            return Err(EINVAL);
        }
        Ok((self.dig(prefix)?, name))
    }

    pub(crate) fn mkdir(&mut self, path: &[u8]) -> Result<Handle> {
        let (parent, name) = self.parent(path)?;
        let index = self.add_directory(parent, name)?;
        Ok(self.nodes[index].handle)
    }

    pub(crate) fn create<T: AttributeOps + 'static>(
        &mut self,
        path: &[u8],
        mode: u16,
        operations: T,
    ) -> Result<Handle> {
        if mode & !0o777 != 0 {
            return Err(EINVAL);
        }
        let (parent, name) = self.parent(path)?;
        self.directory(parent)?;
        if self.child(parent, name)?.is_some() {
            return Err(EEXIST);
        }
        let name = component(name)?;
        let handle = self.reserve_node()?;
        let operations: Box<dyn AttributeOps> = Box::new(operations, GFP_KERNEL)?;
        let file = File::new(self.directory(parent)?, &name, mode, Operations(operations))?;
        let parent = self.nodes[parent].handle;
        self.nodes.push(
            Node {
                handle,
                parent,
                name,
                object: Object::File(file),
            },
            GFP_KERNEL,
        )?;
        Ok(handle)
    }

    pub(crate) fn symlink(&mut self, target: Handle, path: &[u8]) -> Result<Handle> {
        // Resolve before creating any prefix; an arbitrary or another tree's
        // identity cannot cause side effects or become a pointer dereference.
        let target = self.index(target)?;
        if !matches!(self.nodes[target].object, Object::Directory(_)) {
            return Err(EINVAL);
        }
        let (parent, name) = self.parent(path)?;
        self.directory(parent)?;
        if self.child(parent, name)?.is_some() {
            return Err(EEXIST);
        }
        let name = component(name)?;
        let handle = self.reserve_node()?;
        // dig only appends, so the checked target's vector index is unchanged.
        let link = Link::new(self.directory(parent)?, self.directory(target)?, &name)?;
        let parent = self.nodes[parent].handle;
        self.nodes.push(
            Node {
                handle,
                parent,
                name,
                object: Object::Link(link),
            },
            GFP_KERNEL,
        )?;
        Ok(handle)
    }

    fn has_child(&self, handle: Handle) -> bool {
        self.nodes
            .iter()
            .any(|node| node.handle != handle && node.parent == handle)
    }

    /// Adapt remove's iterative leaf-first walk. Removal and Drop never allocate
    /// a traversal stack, including for a maximally deep bounded request path.
    fn remove_branch(&mut self, target: Handle) -> Result {
        let mut current = target;
        loop {
            if let Some(child) = self
                .nodes
                .iter()
                .rev()
                .find(|node| node.parent == current && node.handle != current)
            {
                current = child.handle;
                continue;
            }
            let index = self.index(current)?;
            let parent = self.nodes[index].parent;
            drop(self.nodes.remove(index));
            if current == target {
                return Ok(());
            }
            current = parent;
        }
    }

    pub(crate) fn unlink(&mut self, path: &[u8], flags: u32) -> Result {
        validate_path(path)?;
        let index = self.walk(path)?;
        let target = self.nodes[index].handle;
        let mut parent = self.nodes[index].parent;
        let root = self.nodes[0].handle;
        // Protect both roots BEFORE visiting any child. A failed protected
        // unlink must not partially empty the live OS namespace.
        if target == root || parent == root {
            return Err(EPERM);
        }
        self.remove_branch(target)?;
        if flags & KEEP_ANCESTOR == 0 {
            loop {
                let index = self.index(parent)?;
                let next = self.nodes[index].parent;
                if parent == root || next == root || self.has_child(parent) {
                    break;
                }
                drop(self.nodes.remove(index));
                parent = next;
            }
        }
        Ok(())
    }
}

impl Drop for Tree {
    fn drop(&mut self) {
        // All children were published after their parents. Preserve that order
        // on removal, then drain every file/link before its parent's last put.
        while let Some(node) = self.nodes.pop() {
            drop(node);
        }
    }
}
