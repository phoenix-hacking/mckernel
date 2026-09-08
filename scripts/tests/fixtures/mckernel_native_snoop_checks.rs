// SPDX-License-Identifier: GPL-2.0-only
//! Tests of the included production mapping/snooping bodies, in real Linux.
use super::{errno, memory::{Claim, Memory, Span}, snoop::Snoop, wire, AcceptSuccess};
use super::super::super::{smp_resource::{MemoryExtent, MemoryMap, OsToken}, sysfs_objects::{AttributeOps, Directory, File}, sysfs_tree::Tree};
use core::{ptr, sync::atomic::{AtomicBool, AtomicI32, AtomicU32, AtomicU64, AtomicUsize, Ordering}};
use kernel::{bindings, fmt, prelude::*, str::CString, sync::{new_mutex, Arc, Mutex}};

const PAGE: usize = 4096;
const ORDER: u32 = 7;
const NUMBER: usize = 4 * PAGE;
const DESCRIPTOR: usize = 5 * PAGE;
const STRING: usize = 6 * PAGE;
const BITMAP: usize = 7 * PAGE;
const REQUEST: usize = 8 * PAGE;
const SLOW: usize = 100 * PAGE;
const INITIAL: u64 = 0xf123_4567_89ab_cde0;
const A64: u64 = 0xaaaa_aaaa_5555_5555;
const B64: u64 = 0x5555_5555_aaaa_aaaa;
const A32: u32 = 0xaa55_aa55;
const B32: u32 = 0x55aa_55aa;

extern "C" {
    fn mckernel_sysfs_snoop_oracle(operation: u64, data: *mut core::ffi::c_void,
        bits: i32, bytes: i32, output: *mut u8, size: usize) -> isize;
}

struct Pages(usize);
impl Pages {
    fn new() -> Result<Self> {
        // SAFETY: Private, bounded ordinary Linux allocation, freed at the
        // original order after all callbacks and fixture peers have retired.
        let address = unsafe { bindings::get_free_pages_noprof(bindings::GFP_KERNEL | bindings::__GFP_ZERO, ORDER) };
        if address == 0 { return Err(ENOMEM); }
        Ok(Self(address as usize))
    }
}
impl Drop for Pages {
    fn drop(&mut self) { unsafe { bindings::free_pages(self.0 as u64, ORDER) }; }
}

struct Backing {
    memory: Arc<Memory>,
    physical: u64,
    page: Pages,
}
impl Backing {
    fn new() -> Result<Arc<Self>> {
        let page = Pages::new()?;
        let direct = unsafe { bindings::page_offset_base } as u64;
        let physical = (page.0 as u64).checked_sub(direct).ok_or(EIO)?;
        let mut map = MemoryMap([None; 8]);
        map.0[0] = Some(MemoryExtent { physical, bytes: (112 * PAGE) as u64, identity: OsToken(1) });
        map.0[1] = Some(MemoryExtent { physical: physical + (112 * PAGE) as u64, bytes: (16 * PAGE) as u64, identity: OsToken(2) });
        let mut fixed = Vec::with_capacity(4, GFP_KERNEL)?;
        for index in 0..4 { fixed.push(Span::new(physical + (index * PAGE) as u64, PAGE)?, GFP_KERNEL)?; }
        // SAFETY: The fixture's original Linux allocation and module outlive
        // every returned mapping and joined peer. These are diagnostic extent
        // identities, not production OsTokens or an IHK authority claim.
        let memory = unsafe { Memory::new(&map, OsToken(1), direct, fixed)? };
        assert_eq!(memory.extents().len(), 1);
        assert_eq!(unsafe { Memory::new(&map, OsToken(3), direct, Vec::new()) }.err(), Some(EINVAL));
        Ok(Arc::new(Self { memory, physical, page }, GFP_KERNEL)?)
    }
    fn pa(&self, offset: usize) -> u64 { self.physical + offset as u64 }
    fn address(&self, offset: usize) -> *mut u8 { (self.page.0 + offset) as *mut u8 }
    fn word32(&self, offset: usize) -> &AtomicU32 {
        assert!(offset % 4 == 0 && offset + 4 <= PAGE << ORDER);
        // SAFETY: Aligned live scalar RAM; scalar peers use only same-width
        // atomics while callbacks can observe this location.
        unsafe { AtomicU32::from_ptr(self.address(offset).cast()) }
    }
    fn word64(&self, offset: usize) -> &AtomicU64 {
        assert!(offset % 8 == 0 && offset + 8 <= PAGE << ORDER);
        unsafe { AtomicU64::from_ptr(self.address(offset).cast()) }
    }
    fn busy(&self, kind: wire::Kind, offset: usize) -> &AtomicI32 {
        unsafe { AtomicI32::from_ptr(self.address(offset + kind.layout().busy).cast()) }
    }
    // Caller must have retired all earlier claims/views of these request bytes.
    fn initialize(&self, kind: wire::Kind, offset: usize) {
        let layout = kind.layout();
        assert!(offset + layout.bytes <= 112 * PAGE && offset % layout.alignment == 0);
        unsafe {
            ptr::write_bytes(self.address(offset), 0, layout.bytes);
            ptr::copy_nonoverlapping(b"/sys/probe\0".as_ptr(), self.address(offset + layout.path), 11);
            if kind == wire::Kind::Create { ptr::write(self.address(offset).cast::<i32>(), 0o444); }
            if kind == wire::Kind::Symlink { ptr::write(self.address(offset + 8).cast::<u64>(), 7); }
        }
        self.busy(kind, offset).store(1, Ordering::Release);
    }
    fn claim(&self, kind: wire::Kind, offset: usize) -> Result<Claim> {
        self.initialize(kind, offset);
        self.memory.claim(kind, self.pa(offset))
    }
    fn descriptor(&self, bits: i32, physical: u64) {
        unsafe {
            ptr::write(self.address(DESCRIPTOR).cast::<i32>(), bits);
            ptr::write(self.address(DESCRIPTOR + 8).cast::<u64>(), physical);
        }
    }
    fn snoop(&self, operation: u64, offset: usize, bits: i32) -> Result<Snoop> {
        let claim = self.claim(wire::Kind::Create, REQUEST)?;
        self.descriptor(bits, self.pa(offset));
        let instance = if (5..=7).contains(&operation) { self.pa(DESCRIPTOR) } else { self.pa(offset) };
        let result = Snoop::new(&claim, operation, instance);
        claim.complete(Ok(None))?;
        result
    }
}

fn buffer(size: usize) -> Result<Vec<u8>> {
    let mut bytes = Vec::with_capacity(size, GFP_KERNEL)?;
    for _ in 0..size { bytes.push(0xa5, GFP_KERNEL)?; }
    Ok(bytes)
}
fn equivalent(backing: &Backing, operation: u64, offset: usize, bits: i32) -> Result {
    let value = backing.snoop(operation, offset, bits)?;
    let mut actual = buffer(PAGE + 8)?;
    let mut expected = buffer(PAGE + 8)?;
    let size = match operation { 1 | 3 | 8 => 4, 2 | 4 => 8, _ => (bits + 7) / 8 };
    // SAFETY: A separate oracle module contains the unchanged legacy C bodies.
    // Inputs are private and stable here, aligned for each legacy access, and
    // valid bounded cases fit both complete output allocations.
    let reference = unsafe { mckernel_sysfs_snoop_oracle(operation, backing.address(offset).cast(), bits, size, expected.as_mut_ptr(), PAGE) };
    let count = value.show(&mut actual[..PAGE])?;
    assert!(reference >= 0 && reference as usize == count);
    assert_eq!(&actual[..count], &expected[..count]);
    assert_eq!(&actual[PAGE..], &[0xa5; 8]);
    assert_eq!(&expected[PAGE..], &[0xa5; 8]);
    assert_eq!(value.store(b"x"), Err(ENOSPC));
    Ok(())
}
fn formats(backing: &Backing) -> Result<usize> {
    let mut cases = 0;
    for number in [0, 1, u64::MAX, i64::MAX as u64, i64::MIN as u64, INITIAL, A64, B64] {
        for operation in [1, 2, 3, 4, 8] {
            let offset = if matches!(operation, 1 | 3 | 8) { NUMBER + 16 } else { NUMBER };
            if matches!(operation, 1 | 3 | 8) { backing.word32(offset).store(number as u32, Ordering::Relaxed); }
            else { backing.word64(offset).store(number, Ordering::Relaxed); }
            equivalent(backing, operation, offset, 0)?; cases += 1;
        }
    }
    for text in [b"\0".as_slice(), b"bounded", b"abc\0ignored"] {
        unsafe { ptr::copy_nonoverlapping(text.as_ptr(), backing.address(STRING), text.len()) };
        equivalent(backing, 5, STRING, (text.len() * 8) as i32)?; cases += 1;
    }
    unsafe { ptr::write_bytes(backing.address(STRING), b'x', PAGE - 2); ptr::write(backing.address(STRING + PAGE - 2), 0); }
    equivalent(backing, 5, STRING, ((PAGE - 1) * 8) as i32)?; cases += 1;
    for bits in [0, 1, 7, 8, 9, 31, 32, 33, 63, 64, 65, 70, 127, 128, 129, 32768] {
        for byte in [0, 0xff, 0x55] {
            if bits == 32768 && byte == 0x55 { continue; }
            unsafe { ptr::write_bytes(backing.address(BITMAP), byte, PAGE) };
            for operation in [6, 7] {
                if bits == 32768 && operation == 7 { continue; }
                equivalent(backing, operation, BITMAP, bits)?; cases += 1;
            }
        }
    }
    assert_eq!(cases, 136);
    let number = backing.snoop(4, NUMBER, 0)?;
    assert_eq!(number.show(&mut [0u8; 2]), Err(errno(-75))); drop(number);
    unsafe { ptr::write_bytes(backing.address(STRING), b'x', PAGE) };
    let string = backing.snoop(5, STRING, (PAGE * 8) as i32)?;
    assert_eq!(string.show(&mut buffer(PAGE)?), Err(errno(-75))); drop(string);
    unsafe { ptr::write_bytes(backing.address(BITMAP), 0x55, PAGE) };
    let bitmap = backing.snoop(6, BITMAP, 32768)?;
    assert_eq!(bitmap.show(&mut buffer(PAGE)?), Err(errno(-75)));
    Ok(cases)
}

fn mappings(backing: &Backing) -> Result {
    for kind in [wire::Kind::Create, wire::Kind::Mkdir, wire::Kind::Symlink, wire::Kind::Lookup, wire::Kind::Unlink] {
        let claim = backing.claim(kind, REQUEST)?;
        assert_eq!(claim.snapshot()?.path(), b"/sys/probe");
        assert_eq!(backing.memory.claim(kind, backing.pa(REQUEST)).err(), Some(EBUSY));
        assert_eq!(backing.memory.claim(kind, backing.pa(REQUEST + 8)).err(), Some(EBUSY));
        assert_eq!(claim.descriptor(backing.pa(REQUEST)).err(), Some(EBUSY));
        assert_eq!(claim.snoop(backing.pa(REQUEST), 4).err(), Some(EBUSY));
        assert_eq!(claim.snoop(backing.pa(112 * PAGE), 4).err(), Some(EINVAL));
        assert_eq!(claim.snoop(backing.pa(112 * PAGE - 4), 8).err(), Some(EINVAL));
        assert_eq!(claim.snoop(u64::MAX - 1, 8).err(), Some(EINVAL));
        for offset in [0, PAGE, 2 * PAGE, 3 * PAGE] {
            assert_eq!(claim.snoop(backing.pa(offset), 4).err(), Some(EBUSY));
            assert_eq!(claim.descriptor(backing.pa(offset)).err(), Some(EBUSY));
        }
        let handle = if matches!(kind, wire::Kind::Mkdir | wire::Kind::Lookup) { Some(7) } else { None };
        claim.complete(Ok(handle))?;
        assert_eq!(backing.busy(kind, REQUEST).load(Ordering::Acquire), 0);
        assert_eq!(unsafe { ptr::read(backing.address(REQUEST + kind.layout().error).cast::<i32>()) }, 0);
        assert_eq!(backing.memory.claim(kind, backing.pa(REQUEST)).err(), Some(EBUSY));
        drop(backing.claim(kind, REQUEST)?);
        assert_eq!(backing.busy(kind, REQUEST).load(Ordering::Acquire), 0);
        assert_eq!(unsafe { ptr::read(backing.address(REQUEST + kind.layout().error).cast::<i32>()) }, -5);
    }
    let claim = backing.claim(wire::Kind::Create, REQUEST)?;
    for operation in [1, 2, 3, 4, 8] {
        let width = if matches!(operation, 2 | 4) { 8 } else { 4 };
        for delta in 1..width { assert_eq!(Snoop::new(&claim, operation, backing.pa(NUMBER + delta)).err(), Some(EINVAL)); }
    }
    for operation in [0, 9, 1000, u64::MAX] { assert_eq!(Snoop::new(&claim, operation, backing.pa(NUMBER)).err(), Some(EINVAL)); }
    for (operation, bits) in [(5, 0), (5, 1), (5, -1), (6, -1), (7, 32769)] {
        backing.descriptor(bits, backing.pa(STRING));
        assert_eq!(Snoop::new(&claim, operation, backing.pa(DESCRIPTOR)).err(), Some(EINVAL));
    }
    let first = claim.snoop(backing.pa(SLOW), 4)?;
    let second = claim.snoop(backing.pa(SLOW), 4)?;
    assert_eq!(first.number()?, 0);
    assert_eq!(first.copy(&mut [0u8; 5]), Err(EINVAL));
    assert_eq!(claim.snoop(backing.pa(NUMBER + 1), 4)?.number(), Err(EINVAL));
    assert_eq!(claim.snoop(backing.pa(NUMBER), 3)?.number(), Err(EINVAL));
    assert_eq!(backing.memory.claim(wire::Kind::Mkdir, backing.pa(SLOW)).err(), Some(EBUSY));
    drop(first);
    assert_eq!(backing.memory.claim(wire::Kind::Mkdir, backing.pa(SLOW)).err(), Some(EBUSY));
    drop(second); claim.complete(Ok(None))?;
    backing.claim(wire::Kind::Mkdir, SLOW)?.complete(Ok(Some(9)))?;

    let mut held = Vec::with_capacity(66, GFP_KERNEL)?;
    for index in 0..66 { held.push(backing.claim(wire::Kind::Create, REQUEST + index * PAGE)?, GFP_KERNEL)?; }
    backing.initialize(wire::Kind::Create, REQUEST + 66 * PAGE);
    assert_eq!(backing.memory.claim(wire::Kind::Create, backing.pa(REQUEST + 66 * PAGE)).err(), Some(ENOMEM));
    assert_eq!(backing.busy(wire::Kind::Create, REQUEST + 66 * PAGE).load(Ordering::Acquire), 1);
    drop(held.remove(0));
    held.push(backing.memory.claim(wire::Kind::Create, backing.pa(REQUEST + 66 * PAGE))?, GFP_KERNEL)?;
    while let Some(claim) = held.pop() { claim.complete(Err(ENOMEM))?; }
    for index in 0..67 { assert_eq!(backing.busy(wire::Kind::Create, REQUEST + index * PAGE).load(Ordering::Acquire), 0); }

    let queue = backing.pa(80 * PAGE);
    assert_eq!(backing.memory.connect(queue, 4 * PAGE, || Err(EIO)), Err(EIO));
    let claim = backing.claim(wire::Kind::Create, REQUEST)?;
    drop(claim.snoop(queue, 4)?); claim.complete(Ok(None))?;
    backing.memory.connect(queue, 4 * PAGE, || Ok(AcceptSuccess { receive_queue: backing.pa(84 * PAGE), accepted_channel_cookie: 1 }))?;
    for offset in [80 * PAGE, 84 * PAGE] {
        assert_eq!(backing.memory.claim(wire::Kind::Create, backing.pa(offset)).err(), Some(EBUSY));
    }
    assert_eq!(backing.memory.claim(wire::Kind::Create, backing.pa(REQUEST + 1)).err(), Some(EINVAL));
    Ok(())
}

struct Race {
    backing: Arc<Backing>,
    epoch: AtomicUsize,
    attempted: AtomicUsize,
    finished: AtomicUsize,
    winners: AtomicUsize,
}
struct Stats {
    gate: AtomicBool,
    phase: AtomicBool,
    reclaimed: AtomicBool,
    writing: AtomicBool,
    writes: AtomicU64,
}
enum Job { Race(Arc<Race>), Writer(Arc<Backing>, Arc<Stats>) }
struct Entry { job: Job, entered: Arc<AtomicBool> }
fn sleep() { unsafe { bindings::msleep(1) }; }
fn wait(predicate: impl Fn() -> bool) {
    for _ in 0..10000 { if predicate() { return; } sleep(); }
    panic!("snoop fixture timeout");
}
unsafe extern "C" fn worker(data: *mut core::ffi::c_void) -> i32 {
    // SAFETY: Exactly one retained thread entry owns this box until stop/join.
    let entry = unsafe { Box::from_raw(data.cast::<Entry>()) };
    entry.entered.store(true, Ordering::Release);
    match &entry.job {
        Job::Race(race) => {
            for epoch in 1..=64 {
                while race.epoch.load(Ordering::Acquire) < epoch {
                    if unsafe { bindings::kthread_should_stop() } { return 0; } sleep();
                }
                let result = race.backing.memory.claim(wire::Kind::Create, race.backing.pa(REQUEST));
                if result.is_ok() { race.winners.fetch_add(1, Ordering::Relaxed); }
                else { assert_eq!(result.as_ref().err(), Some(&EBUSY)); }
                race.attempted.fetch_add(1, Ordering::AcqRel);
                wait(|| race.attempted.load(Ordering::Acquire) == 2);
                if let Ok(claim) = result { claim.complete(Err(EIO)).unwrap(); }
                race.finished.fetch_add(1, Ordering::AcqRel);
            }
        }
        Job::Writer(backing, stats) => {
            while !unsafe { bindings::kthread_should_stop() } {
                if stats.writing.load(Ordering::Acquire) {
                    for _ in 0..256 {
                        backing.word64(NUMBER).store(A64, Ordering::Relaxed);
                        backing.word32(NUMBER + 16).store(A32, Ordering::Relaxed);
                        backing.word64(NUMBER).store(B64, Ordering::Relaxed);
                        backing.word32(NUMBER + 16).store(B32, Ordering::Relaxed);
                    }
                    stats.writes.fetch_add(512, Ordering::Release);
                }
                sleep();
            }
        }
    }
    while !unsafe { bindings::kthread_should_stop() } { sleep(); }
    0
}
struct Thread(*mut bindings::task_struct);
// SAFETY: The private pointer is used only for unique stop/join, after entry.
unsafe impl Send for Thread {}
unsafe impl Sync for Thread {}
impl Thread {
    fn start(job: Job) -> Result<Self> {
        let entered = Arc::new(AtomicBool::new(false), GFP_KERNEL)?;
        let entry = Box::into_raw(Box::new(Entry { job, entered: entered.clone() }, GFP_KERNEL)?);
        let task = unsafe { bindings::kthread_create_on_node(Some(worker), entry.cast(), -1, kernel::c_str!("mck-snoop-check").as_char_ptr()) };
        if (-4095..0).contains(&(task as isize)) { unsafe { drop(Box::from_raw(entry)) }; return Err(errno(task as isize as i32)); }
        assert!(!task.is_null());
        unsafe { bindings::wake_up_process(task) };
        wait(|| entered.load(Ordering::Acquire));
        Ok(Self(task))
    }
}
impl Drop for Thread { fn drop(&mut self) { assert_eq!(unsafe { bindings::kthread_stop(self.0) }, 0); } }
fn races(backing: Arc<Backing>) -> Result {
    let race = Arc::new(Race { backing, epoch: AtomicUsize::new(0), attempted: AtomicUsize::new(0), finished: AtomicUsize::new(0), winners: AtomicUsize::new(0) }, GFP_KERNEL)?;
    let first = Thread::start(Job::Race(race.clone()))?;
    let second = Thread::start(Job::Race(race.clone()))?;
    for epoch in 1..=64 {
        race.backing.initialize(wire::Kind::Create, REQUEST);
        race.attempted.store(0, Ordering::Relaxed);
        race.finished.store(0, Ordering::Relaxed);
        race.winners.store(0, Ordering::Relaxed);
        race.epoch.store(epoch, Ordering::Release);
        wait(|| race.finished.load(Ordering::Acquire) == 2);
        assert_eq!(race.winners.load(Ordering::Acquire), 1);
        assert_eq!(race.backing.busy(wire::Kind::Create, REQUEST).load(Ordering::Acquire), 0);
    }
    drop(first); drop(second);
    Ok(())
}

struct Status(Arc<Stats>);
impl AttributeOps for Status {
    fn show(&self, output: &mut [u8]) -> Result<usize> {
        let text = CString::try_from_fmt(fmt!("{} {} {}\n", self.0.phase.load(Ordering::Acquire) as u8, self.0.reclaimed.load(Ordering::Acquire) as u8, self.0.writes.load(Ordering::Acquire)))?;
        output[..text.as_bytes().len()].copy_from_slice(text.as_bytes()); Ok(text.as_bytes().len())
    }
}
struct Control { stats: Arc<Stats>, writer: bool }
impl AttributeOps for Control {
    fn store(&self, input: &[u8]) -> Result<usize> {
        let enabled = match input { b"0\n" => false, b"1\n" => true, _ => return Err(EINVAL) };
        if self.writer { self.stats.writing.store(enabled, Ordering::Release); }
        else { self.stats.gate.store(enabled, Ordering::Release); }
        Ok(input.len())
    }
}
struct Slow { inner: Snoop, stats: Arc<Stats> }
impl AttributeOps for Slow {
    fn show(&self, output: &mut [u8]) -> Result<usize> {
        self.stats.phase.store(true, Ordering::Release);
        wait(|| self.stats.gate.load(Ordering::Acquire));
        self.inner.show(output)
    }
}
struct Remove { tree: Arc<Mutex<Tree>>, backing: Arc<Backing>, stats: Arc<Stats> }
impl AttributeOps for Remove {
    fn store(&self, input: &[u8]) -> Result<usize> {
        if input != b"1\n" { return Err(EINVAL); }
        assert_eq!(self.backing.memory.claim(wire::Kind::Mkdir, self.backing.pa(SLOW)).err(), Some(EBUSY));
        self.tree.lock().unlink(b"/sys/slow", 1)?;
        let claim = self.backing.memory.claim(wire::Kind::Mkdir, self.backing.pa(SLOW))?;
        assert_eq!(claim.snapshot()?.path(), b"/sys/probe");
        claim.complete(Ok(Some(9)))?;
        self.stats.reclaimed.store(true, Ordering::Release);
        Ok(input.len())
    }
}

pub(crate) struct Verifier {
    tree: Arc<Mutex<Tree>>,
    remove: Option<File<Remove>>,
    status: Option<File<Status>>,
    gate: Option<File<Control>>,
    writer_control: Option<File<Control>>,
    writer: Option<Thread>,
    stats: Arc<Stats>,
    _backing: Arc<Backing>,
    _root: Directory,
}
impl kernel::Module for Verifier {
    fn init(_module: &'static ThisModule) -> Result<Self> {
        let root = Directory::new(None, kernel::c_str!("mckernel_sysfs_snoop_verify"))?;
        let backing = Backing::new()?;
        let cases = formats(&backing)?;
        mappings(&backing)?;
        races(backing.clone())?;
        backing.word64(NUMBER).store(INITIAL, Ordering::Relaxed);
        backing.word32(NUMBER + 16).store(INITIAL as u32, Ordering::Relaxed);
        unsafe {
            ptr::copy_nonoverlapping(b"snoop(remote)\0".as_ptr(), backing.address(STRING), 14);
            ptr::write_bytes(backing.address(BITMAP), 0, PAGE);
            ptr::write(backing.address(BITMAP).cast::<u64>(), (1 << 63) | 13);
            ptr::write(backing.address(BITMAP + 8).cast::<u64>(), 0x21);
        }
        let stats = Arc::new(Stats { gate: AtomicBool::new(true), phase: AtomicBool::new(false), reclaimed: AtomicBool::new(false), writing: AtomicBool::new(false), writes: AtomicU64::new(0) }, GFP_KERNEL)?;
        let tree = Arc::pin_init(new_mutex!(Tree::new(Directory::new(Some(&root), kernel::c_str!("sys"))?)?), GFP_KERNEL)?;
        for (operation, path, offset, bits) in [
            (1, b"/sys/d32".as_slice(), NUMBER + 16, 0), (2, b"/sys/d64", NUMBER, 0),
            (3, b"/sys/u32", NUMBER + 16, 0), (4, b"/sys/u64", NUMBER, 0),
            (5, b"/sys/s", STRING, 14 * 8), (6, b"/sys/pbl", BITMAP, 70),
            (7, b"/sys/pb", BITMAP, 70), (8, b"/sys/u32K", NUMBER + 16, 0),
        ] { tree.lock().create(path, 0o444, backing.snoop(operation, offset, bits)?)?; }
        backing.initialize(wire::Kind::Mkdir, SLOW);
        backing.word32(SLOW).store(4242, Ordering::Relaxed);
        tree.lock().create(b"/sys/slow", 0o444, Slow { inner: backing.snoop(3, SLOW, 0)?, stats: stats.clone() })?;
        let remove = File::new(&root, kernel::c_str!("remove_slow"), 0o222, Remove { tree: tree.clone(), backing: backing.clone(), stats: stats.clone() })?;
        let status = File::new(&root, kernel::c_str!("status"), 0o444, Status(stats.clone()))?;
        let gate = File::new(&root, kernel::c_str!("gate"), 0o222, Control { stats: stats.clone(), writer: false })?;
        let writer_control = File::new(&root, kernel::c_str!("writer"), 0o222, Control { stats: stats.clone(), writer: true })?;
        let writer = Thread::start(Job::Writer(backing.clone(), stats.clone()))?;
        pr_info!("MCKERNEL_SYSFS_SNOOP_VERIFY READY formats={} claim_races=64 capacity=66 files=9\n", cases);
        Ok(Self { tree, remove: Some(remove), status: Some(status), gate: Some(gate), writer_control: Some(writer_control), writer: Some(writer), stats, _backing: backing, _root: root })
    }
}
impl Drop for Verifier {
    fn drop(&mut self) {
        self.stats.gate.store(true, Ordering::Release);
        self.remove.take(); self.status.take(); self.gate.take(); self.writer_control.take();
        self.writer.take();
        self.tree.lock().clear_contents();
        assert!(self.stats.reclaimed.load(Ordering::Acquire));
        assert!(self.stats.writes.load(Ordering::Acquire) > 0);
        pr_info!("MCKERNEL_SYSFS_SNOOP_VERIFY DRAINED mapping_reclaimed=1 workers_joined=3\n");
    }
}
