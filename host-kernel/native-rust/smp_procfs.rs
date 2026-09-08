// SPDX-License-Identifier: GPL-2.0-only
//! Live procfs sessions using the original traditional request and buffer ABI.
//! Namespace rundown never waits for the metadata worker to deliver a reply.

use super::{
    errno,
    memory::{Memory, ProcfsRegion},
};
use crate::{
    application_rpc::{Exchange, Token},
    procfs_objects::{self as vfs, Directory, File},
    smp_memory::BootPages,
};
use core::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use kernel::{
    bindings, c_str, fmt,
    prelude::*,
    str::CString,
    sync::{new_condvar, new_mutex, Arc, CondVar, Mutex},
};

const CAPACITY: usize = 64;
const CHAIN_PAGES: usize = 1024;
const REQUEST_BYTES: usize = 808;
const PA_NULL: u64 = u64::MAX;

fn bytes(length: usize) -> Result<Vec<u8>> {
    let mut output = Vec::with_capacity(length, GFP_KERNEL)?;
    for _ in 0..length {
        output.push(0, GFP_KERNEL)?;
    }
    Ok(output)
}
fn word(bytes: &[u8], offset: usize) -> u64 {
    u64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap())
}
fn integer(bytes: &[u8], offset: usize) -> i32 {
    i32::from_le_bytes(bytes[offset..offset + 4].try_into().unwrap())
}

/// Lightweight file identity. It cannot retain Runtime, its namespace, or the
/// application registry, so those owners cannot form a reference cycle.
struct Context {
    key: Token,
    pid: i32,
    cpu: i32,
    live: AtomicBool,
}

#[derive(Clone, Copy, PartialEq)]
enum Operation {
    Snapshot,
    Direct,
    Release,
}

struct Slot {
    key: Token,
    context: Arc<Context>,
    request: Option<BootPages>,
    data: Option<BootPages>,
    input: Vec<u8>,
    output: Vec<u8>,
    exchange: Option<Exchange>,
    operation: Option<Operation>,
    result: Option<Result<usize>>,
    head: u64,
    pages: Vec<ProcfsRegion>,
    sizes: Vec<usize>,
    cached: bool,
    closed: bool,
    quarantined: bool,
}

impl Slot {
    fn begin(
        &mut self,
        os: i32,
        operation: Operation,
        offset: i64,
        count: usize,
        write: bool,
    ) -> Result {
        if self
            .exchange
            .as_ref()
            .is_some_and(|exchange| exchange.result().is_none())
        {
            return Err(EBUSY);
        }
        let physical = match operation {
            Operation::Snapshot => PA_NULL,
            Operation::Direct => self.data.as_ref().ok_or(EIO)?.physical(),
            Operation::Release => self.head,
        };
        self.input[..36].fill(0);
        self.input[..8].copy_from_slice(&physical.to_le_bytes());
        self.input[8..16].copy_from_slice(&offset.to_le_bytes());
        self.input[16..20].copy_from_slice(&(count as i32).to_le_bytes());
        self.input[24..28].copy_from_slice(&EIO.to_errno().to_le_bytes());
        self.input[32..36].copy_from_slice(&i32::from(write).to_le_bytes());
        let request = self.request.as_mut().ok_or(EIO)?;
        request.put(0, &self.input)?;
        let mut exchange = Exchange::procfs(
            os,
            self.context.cpu,
            self.context.pid,
            request.physical(),
            operation == Operation::Release,
        )
        .map_err(errno)?;
        exchange.begin().map_err(errno)?;
        self.exchange = Some(exchange);
        self.operation = Some(operation);
        self.result = None;
        Ok(())
    }

    fn finish(&mut self, memory: &Arc<Memory>) -> Result<usize> {
        let exchange = self.exchange.as_ref().ok_or(EIO)?;
        let error = exchange.result().ok_or(EBUSY)?;
        // Even an error reply proves retirement, but it may leave snapshot
        // ownership uncertain. Inspect only the retained Linux descriptor.
        self.request
            .as_ref()
            .ok_or(EIO)?
            .read_into(&mut self.output)?;
        let operation = self.operation.ok_or(EIO)?;
        if self.output[8..20] != self.input[8..20]
            || self.output[28..] != self.input[28..]
            || !(0..=1).contains(&integer(&self.output, 20))
            || operation != Operation::Snapshot && self.output[..8] != self.input[..8]
        {
            return Err(errno(-71));
        }
        if error != 0 {
            // Without a successful operation completion, do not infer whether
            // partially constructed guest buffers can be released safely.
            self.quarantined = true;
            return Err(errno(error));
        }
        let result = integer(&self.output, 24);
        if result < -4095 {
            return Err(errno(-71));
        }
        if operation == Operation::Snapshot {
            self.head = word(&self.output, 0);
            let mut physical = self.head;
            let mut position = 0u64;
            while physical != PA_NULL {
                if self.pages.len() == CHAIN_PAGES {
                    return Err(ENOMEM);
                }
                // Same Memory ledger rejects aliases, cycles, duplicate pages,
                // queues, sysfs data and pending syscall/CREATE responses.
                let page = memory.procfs(physical, false)?;
                self.pages.push(page, GFP_KERNEL)?;
                let mut header = [0; 24];
                self.pages.last().unwrap().read(0, &mut header)?;
                let next = word(&header, 0);
                let size = word(&header, 16);
                if word(&header, 8) != position || size > 4072 || next != PA_NULL && size != 4072 {
                    return Err(errno(-71));
                }
                self.sizes.push(size as usize, GFP_KERNEL)?;
                position = position.checked_add(size).ok_or(errno(-75))?;
                physical = next;
            }
            self.cached = true;
        } else if operation == Operation::Release {
            if result != 0 {
                return Err(errno(-71));
            }
            self.head = PA_NULL;
            self.pages.clear();
            self.sizes.clear();
        } else if result > integer(&self.input, 16) {
            return Err(errno(-71));
        }
        kernel::error::to_result(result).map(|()| result as usize)
    }

    fn snapshot(&self, position: i64, output: &mut [u8]) -> Result<usize> {
        if position < 0 {
            return Err(EINVAL);
        }
        self.result.ok_or(EIO)??;
        let mut base = 0usize;
        let mut copied = 0;
        let mut position = position as u64;
        for (page, size) in self.pages.iter().zip(&self.sizes) {
            let end = base + size;
            if position < end as u64 && copied < output.len() {
                let offset = (position - base as u64) as usize;
                let length = (size - offset).min(output.len() - copied);
                page.read(24 + offset, &mut output[copied..copied + length])?;
                position += length as u64;
                copied += length;
            }
            base = end;
        }
        Ok(copied)
    }
}

impl Drop for Slot {
    fn drop(&mut self) {
        if self.quarantined
            || self.head != PA_NULL
            || self
                .exchange
                .as_ref()
                .is_some_and(|exchange| exchange.result().is_none() && !exchange.queued())
        {
            // Uncertain retirement cannot return published Linux pages to the
            // allocator, even if a future teardown drops this remote owner.
            core::mem::forget(self.request.take());
            core::mem::forget(self.data.take());
        }
    }
}

#[pin_data]
pub(crate) struct Remote {
    memory: Arc<Memory>,
    active: AtomicBool,
    cursor: AtomicUsize,
    #[pin]
    slots: Mutex<Vec<Option<Slot>>>,
    #[pin]
    changed: CondVar,
}

impl Remote {
    pub(super) fn new(memory: Arc<Memory>) -> Result<Arc<Self>> {
        let mut slots = Vec::with_capacity(CAPACITY, GFP_KERNEL)?;
        for _ in 0..CAPACITY {
            slots.push(None, GFP_KERNEL)?;
        }
        Arc::pin_init(
            pin_init!(Self { memory, active: AtomicBool::new(false), cursor: AtomicUsize::new(0),
            slots <- new_mutex!(slots), changed <- new_condvar!() }),
            GFP_KERNEL,
        )
    }

    pub(super) fn activate(&self) {
        self.active.store(true, Ordering::Release);
    }

    fn open(
        self: &Arc<Self>,
        context: &Arc<Context>,
        path: &CStr,
        direct: bool,
    ) -> Result<Session> {
        if !self.active.load(Ordering::Acquire) || !context.live.load(Ordering::Acquire) {
            return Err(ENODEV);
        }
        let mut input = bytes(REQUEST_BYTES)?;
        let name = path.as_bytes_with_nul();
        if name.len() > REQUEST_BYTES - 36 {
            return Err(EINVAL);
        }
        input[36..36 + name.len()].copy_from_slice(name);
        let request = BootPages::allocate(REQUEST_BYTES, self.memory.direct_map)?;
        let data = if direct {
            Some(BootPages::allocate(4096, self.memory.direct_map)?)
        } else {
            None
        };
        let slot = Slot {
            key: Token::allocate().map_err(errno)?,
            context: context.clone(),
            request: Some(request),
            data,
            input,
            output: bytes(REQUEST_BYTES)?,
            exchange: None,
            operation: None,
            result: None,
            head: PA_NULL,
            pages: Vec::with_capacity(if direct { 0 } else { CHAIN_PAGES }, GFP_KERNEL)?,
            sizes: Vec::with_capacity(if direct { 0 } else { CHAIN_PAGES }, GFP_KERNEL)?,
            cached: false,
            closed: false,
            quarantined: false,
        };
        let key = slot.key;
        let mut slots = self.slots.lock();
        if !context.live.load(Ordering::Acquire) {
            return Err(ENODEV);
        }
        *slots.iter_mut().find(|slot| slot.is_none()).ok_or(EAGAIN)? = Some(slot);
        Ok(Session {
            remote: self.clone(),
            key,
            direct,
        })
    }

    fn io(
        &self,
        key: Token,
        position: i64,
        output: &mut [u8],
        input: Option<&[u8]>,
        direct: bool,
    ) -> Result<usize> {
        if position < 0 {
            return Err(EINVAL);
        }
        let length = input.map_or(output.len(), <[u8]>::len);
        if length > 4096 || (position as u64).checked_add(length as u64).is_none() {
            return Err(EINVAL);
        }
        let mut slots = self.slots.lock();
        let mut issued = false;
        loop {
            let slot = slots
                .iter_mut()
                .flatten()
                .find(|slot| slot.key == key)
                .ok_or(ENOENT)?;
            if slot.closed || slot.quarantined {
                return Err(EIO);
            }
            if !direct && slot.cached {
                return slot.snapshot(position, output);
            }
            if let Some(result) = slot.result {
                if !direct {
                    return result;
                }
                if issued {
                    let length = result?;
                    if input.is_none() {
                        slot.data
                            .as_ref()
                            .ok_or(EIO)?
                            .read_into(&mut output[..length])?;
                    }
                    return Ok(length);
                }
                // A previous interrupted direct I/O has now retired. Its
                // result is not delivered as the result of this new operation.
                slot.exchange = None;
                slot.result = None;
            }
            if slot.exchange.is_none() {
                if let Some(input) = input {
                    slot.data.as_mut().ok_or(EIO)?.put(0, input)?;
                }
                slot.begin(
                    self.memory.owner.slot() as i32,
                    if direct {
                        Operation::Direct
                    } else {
                        Operation::Snapshot
                    },
                    if direct { position } else { 0 },
                    if direct { length } else { 0 },
                    input.is_some(),
                )?;
                issued = true;
            }
            if self.changed.wait_interruptible(&mut slots) {
                return Err(EINTR);
            }
        }
    }

    fn close(&self, key: Token) {
        if let Some(slot) = self
            .slots
            .lock()
            .iter_mut()
            .flatten()
            .find(|slot| slot.key == key)
        {
            slot.closed = true;
        }
    }

    fn drained(&self, key: Token) -> bool {
        !self
            .slots
            .lock()
            .iter()
            .flatten()
            .any(|slot| slot.context.key == key)
    }

    pub(super) fn queued_cpu(&self) -> Option<i32> {
        let slots = self.slots.lock();
        let start = self.cursor.fetch_add(1, Ordering::Relaxed);
        crate::smp_application_syscall::cyclic(start, slots.len()).find_map(|index| {
            slots[index]
                .as_ref()?
                .exchange
                .as_ref()
                .filter(|exchange| exchange.queued())
                .map(Exchange::cpu)
        })
    }

    pub(super) fn publish(
        &self,
        cpu: i32,
        send: impl FnOnce(&[u8; 128]) -> Result,
    ) -> Result<bool> {
        let mut slots = self.slots.lock();
        let Some(slot) = slots.iter_mut().flatten().find(|slot| {
            slot.exchange
                .as_ref()
                .is_some_and(|exchange| exchange.queued() && exchange.cpu() == cpu)
        }) else {
            return Ok(false);
        };
        let exchange = slot.exchange.as_mut().ok_or(EIO)?;
        let packet = exchange.outgoing().ok_or(EIO)?;
        if slot.operation == Some(Operation::Release) {
            self.memory
                .publish_procfs_release(&mut slot.pages, || send(&packet))?;
        } else {
            send(&packet)?;
        }
        exchange.published().map_err(errno)?;
        Ok(true)
    }

    pub(super) fn reply(&self, packet: &[u8; 128]) -> Result {
        let result = (|| {
            let mut slots = self.slots.lock();
            for slot in slots.iter_mut().flatten() {
                let Some(exchange) = &mut slot.exchange else {
                    continue;
                };
                match exchange.accept(packet) {
                    Ok(()) => {
                        let result = slot.finish(&self.memory);
                        // An ordinary guest operation errno has validated
                        // buffers; malformed/unbounded ownership stays retained.
                        if !slot.cached
                            && slot.operation == Some(Operation::Snapshot)
                            && result.is_err()
                            || slot.operation == Some(Operation::Release) && result.is_err()
                            || result
                                .as_ref()
                                .err()
                                .is_some_and(|error| error.to_errno() == -71)
                        {
                            slot.quarantined = true;
                        }
                        pr_info!("IHK-SMP: procfs answer os={} pid={} token={} release={} errno={} pages={} retained={}\n",
                            self.memory.owner.slot(), slot.context.pid, exchange_token(slot),
                            (slot.operation == Some(Operation::Release)) as u8,
                            result.as_ref().err().map_or(0, |error| error.to_errno()), slot.pages.len(), slot.quarantined as u8);
                        slot.result = Some(result);
                        return Ok(());
                    }
                    Err(-2 | -16) => continue,
                    Err(error) => return Err(errno(error)),
                }
            }
            Err(ENOENT)
        })();
        self.changed.notify_all();
        result
    }

    pub(super) fn advance(&self) {
        let mut slots = self.slots.lock();
        for entry in &mut *slots {
            let Some(slot) = entry.as_mut() else {
                continue;
            };
            if !slot.closed
                || slot.quarantined
                || slot
                    .exchange
                    .as_ref()
                    .is_some_and(|exchange| exchange.result().is_none())
            {
                continue;
            }
            if slot.head == PA_NULL {
                *entry = None;
            } else if slot
                .begin(
                    self.memory.owner.slot() as i32,
                    Operation::Release,
                    0,
                    0,
                    false,
                )
                .is_err()
            {
                slot.quarantined = true;
            }
        }
    }
}

fn exchange_token(slot: &Slot) -> u64 {
    slot.exchange.as_ref().unwrap().token().wire()
}

pub(crate) struct Session {
    remote: Arc<Remote>,
    key: Token,
    direct: bool,
}
impl vfs::Session for Session {
    fn read(&mut self, position: i64, output: &mut [u8]) -> Result<usize> {
        self.remote
            .io(self.key, position, output, None, self.direct)
    }
    fn write(&mut self, position: i64, input: &[u8]) -> Result<usize> {
        self.remote
            .io(self.key, position, &mut [], Some(input), true)
    }
    fn release(&mut self) -> Result {
        self.remote.close(self.key);
        Ok(())
    }
}

struct Node<const WRITE: bool> {
    remote: Arc<Remote>,
    context: Arc<Context>,
    path: CString,
    direct: bool,
}
impl<const WRITE: bool> vfs::FileOps for Node<WRITE> {
    type Session = Session;
    const WRITABLE: bool = WRITE;
    fn open(&self) -> Result<Session> {
        self.remote.open(&self.context, &self.path, self.direct)
    }
}

/// Stored on the existing application Entry. The namespace retains another
/// reference only while nodes are published, so its final VFS drop happens on
/// the independent metadata worker, never under the application state lock.
pub(crate) struct Process {
    remote: Arc<Remote>,
    context: Arc<Context>,
    uid: u32,
    gid: u32,
    published: AtomicBool,
}
impl Process {
    pub(crate) fn new(
        remote: Arc<Remote>,
        key: Token,
        pid: i32,
        cpu: i32,
        uid: u32,
        gid: u32,
    ) -> Result<Arc<Self>> {
        Ok(Arc::new(
            Self {
                remote,
                context: Arc::new(
                    Context {
                        key,
                        pid,
                        cpu,
                        live: AtomicBool::new(true),
                    },
                    GFP_KERNEL,
                )?,
                uid,
                gid,
                published: AtomicBool::new(false),
            },
            GFP_KERNEL,
        )?)
    }
    pub(crate) fn close(&self) {
        self.context.live.store(false, Ordering::Release);
    }
    pub(crate) fn drained(&self) -> bool {
        !self.published.load(Ordering::Acquire) && self.remote.drained(self.context.key)
    }
}

struct Tid {
    tid: i32,
    _root: Directory,
    _stat: File<Node<false>>,
    _mem: File<Node<true>>,
}
struct Published {
    process: Arc<Process>,
    _root: Directory,
    task: Directory,
    _files: Vec<File<Node<false>>>,
    _mem: File<Node<true>>,
    tids: Vec<Tid>,
}

pub(super) struct Service {
    root: Directory,
    _files: Vec<File<Node<false>>>,
    processes: Vec<Published>,
}

fn node<const WRITE: bool>(process: &Process, path: CString, direct: bool) -> Node<WRITE> {
    Node {
        remote: process.remote.clone(),
        context: process.context.clone(),
        path,
        direct,
    }
}
fn file<const WRITE: bool>(
    process: &Process,
    parent: &Directory,
    base: &CStr,
    name: &CStr,
    mode: u16,
    direct: bool,
) -> Result<File<Node<WRITE>>> {
    File::owned(
        parent,
        name,
        mode,
        node(
            process,
            CString::try_from_fmt(fmt!("{}/{}", base, name))?,
            direct,
        ),
        bindings::kuid_t { val: process.uid },
        bindings::kgid_t { val: process.gid },
    )
}

impl Service {
    pub(super) fn new(remote: Arc<Remote>) -> Result<Self> {
        let name = CString::try_from_fmt(fmt!("mcos{}", remote.memory.owner.slot()))?;
        let root = Directory::new(None, &name)?;
        let process = Process::new(remote, Token::allocate().map_err(errno)?, 0, 0, 0, 0)?;
        let mut files = Vec::with_capacity(2, GFP_KERNEL)?;
        for leaf in [c_str!("stat"), c_str!("mckernel")] {
            files.push(
                File::new(
                    &root,
                    leaf,
                    0o444,
                    node::<false>(
                        &process,
                        CString::try_from_fmt(fmt!("{}/{}", &*name, leaf))?,
                        false,
                    ),
                )?,
                GFP_KERNEL,
            )?;
        }
        Ok(Self {
            root,
            _files: files,
            processes: Vec::with_capacity(crate::smp_application::CAPACITY, GFP_KERNEL)?,
        })
    }

    pub(super) fn create(&mut self, process: Arc<Process>, tid: i32) -> Result {
        if tid <= 0 || !process.context.live.load(Ordering::Acquire) {
            return Err(EINVAL);
        }
        if !self
            .processes
            .iter()
            .any(|entry| entry.process.context.key == process.context.key)
        {
            self.processes.reserve(1, GFP_KERNEL)?;
            process.published.store(true, Ordering::Release);
            let result = self.publish_process(process.clone());
            match result {
                Ok(entry) => self.processes.push(entry, GFP_KERNEL)?,
                Err(error) => {
                    process.close();
                    process.published.store(false, Ordering::Release);
                    return Err(error);
                }
            }
        }
        let entry = self
            .processes
            .iter_mut()
            .find(|entry| entry.process.context.key == process.context.key)
            .ok_or(EIO)?;
        if entry.tids.iter().any(|entry| entry.tid == tid) {
            return Err(EEXIST);
        }
        entry.tids.reserve(1, GFP_KERNEL)?;
        let name = CString::try_from_fmt(fmt!("{}", tid))?;
        let root = Directory::new(Some(&entry.task), &name)?;
        let base = CString::try_from_fmt(fmt!(
            "mcos{}/{}/task/{}",
            process.remote.memory.owner.slot(),
            process.context.pid,
            tid
        ))?;
        let stat = file(&process, &root, &base, c_str!("stat"), 0o444, false)?;
        let mem = file(&process, &root, &base, c_str!("mem"), 0o600, true)?;
        entry.tids.push(
            Tid {
                tid,
                _root: root,
                _stat: stat,
                _mem: mem,
            },
            GFP_KERNEL,
        )?;
        Ok(())
    }

    fn publish_process(&self, process: Arc<Process>) -> Result<Published> {
        let name = CString::try_from_fmt(fmt!("{}", process.context.pid))?;
        let root = Directory::new(Some(&self.root), &name)?;
        let task = Directory::owned(
            Some(&root),
            c_str!("task"),
            bindings::kuid_t { val: process.uid },
            bindings::kgid_t { val: process.gid },
        )?;
        let base = CString::try_from_fmt(fmt!(
            "mcos{}/{}",
            process.remote.memory.owner.slot(),
            process.context.pid
        ))?;
        let mut files = Vec::with_capacity(7, GFP_KERNEL)?;
        for (name, mode, direct) in [
            (c_str!("auxv"), 0o400, false),
            (c_str!("cmdline"), 0o444, false),
            (c_str!("comm"), 0o644, false),
            (c_str!("maps"), 0o444, false),
            (c_str!("pagemap"), 0o444, true),
            (c_str!("stat"), 0o444, false),
            (c_str!("status"), 0o444, false),
        ] {
            files.push(
                file(&process, &root, &base, name, mode, direct)?,
                GFP_KERNEL,
            )?;
        }
        let mem = file(&process, &root, &base, c_str!("mem"), 0o600, true)?;
        Ok(Published {
            process,
            _root: root,
            task,
            _files: files,
            _mem: mem,
            tids: Vec::new(),
        })
    }

    pub(super) fn delete(&mut self, process: &Process, tid: i32) -> Result {
        let entry = self
            .processes
            .iter_mut()
            .find(|entry| entry.process.context.key == process.context.key)
            .ok_or(ENOENT)?;
        let index = entry
            .tids
            .iter()
            .position(|entry| entry.tid == tid)
            .ok_or(ENOENT)?;
        drop(entry.tids.remove(index));
        Ok(())
    }

    pub(super) fn retire(&mut self) {
        let mut index = 0;
        while index < self.processes.len() {
            if self.processes[index]
                .process
                .context
                .live
                .load(Ordering::Acquire)
            {
                index += 1;
                continue;
            }
            let entry = self.processes.remove(index);
            let process = entry.process.clone();
            drop(entry); // Linux drains callbacks and closes sessions first.
            process.published.store(false, Ordering::Release);
        }
    }
}

pub(super) struct Event {
    pub(super) process: Arc<Process>,
    pub(super) tid: i32,
    pub(super) completion: Option<ProcfsRegion>,
}
