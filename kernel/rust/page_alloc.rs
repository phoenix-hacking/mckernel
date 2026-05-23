use core::ffi::c_void;
use core::mem::{align_of, offset_of, size_of};
use core::ptr::{null_mut, read_volatile, write_volatile};
use core::sync::atomic::{compiler_fence, AtomicI32, AtomicPtr, Ordering};

use crate::abi::{CInt, CULong, IkcScdPacket, IkcScdPacketTraditional};
use crate::rbtree::{
    rb_erase, rb_first, rb_insert_color, rb_link_node, rb_next, rb_prev, rb_replace_node, RbNode,
    RbRoot,
};

const PAGE_SHIFT: CULong = 12;
const PAGE_SIZE: CULong = 1 << PAGE_SHIFT;
const EINVAL: CInt = 22;
const IHK_NUMA_FREE_DIRECT: CInt = 0;
const IHK_NUMA_FREE_DEFERRED: CInt = 1;
const IHK_NUMA_FREE_IGNORED: CInt = 2;
const IHK_NUMA_CPU_CACHE_FREE_NOT_TRIED: CInt = 0;
const IHK_NUMA_CPU_CACHE_FREE_SUCCESS: CInt = 1;
const IHK_NUMA_CPU_CACHE_FREE_FAILED: CInt = 2;
const SCD_MSG_SYSCALL_ONESIDE: CInt = 0x4;

type PageAllocIrqSaveFn = unsafe extern "C" fn() -> CULong;
type PageAllocIrqRestoreFn = unsafe extern "C" fn(CULong);
type PageAllocFreePagesFn = unsafe extern "C" fn(*mut c_void, CInt);
type PageAllocMcsLockFn = unsafe extern "C" fn(CULong, CULong);
type PageAllocMcsUnlockFn = unsafe extern "C" fn(CULong, CULong);

#[repr(C)]
#[derive(Clone, Copy)]
struct LListNode {
    next: *mut LListNode,
}

#[repr(C)]
struct LListHead {
    first: *mut LListNode,
}

#[repr(C)]
struct ListHead {
    next: *mut ListHead,
    prev: *mut ListHead,
}

#[repr(C)]
struct IhkAtomic {
    counter: CInt,
}

#[repr(C, align(64))]
struct McsLockNode {
    locked: CULong,
    next: *mut McsLockNode,
    irqsave: CULong,
}

#[repr(C)]
pub(crate) struct IhkPageAllocatorDesc {
    start: CULong,
    end: CULong,
    last: u32,
    count: u32,
    flag: u32,
    shift: u32,
    lock: McsLockNode,
    list: ListHead,
    map: [CULong; 0],
}

#[repr(C)]
pub(crate) struct FreeChunk {
    addr: CULong,
    size: CULong,
    node: RbNode,
    list: LListNode,
}

#[repr(C, align(64))]
pub(crate) struct IhkMcNumaNode {
    id: CInt,
    linux_numa_id: CInt,
    node_type: CInt,
    allocators: ListHead,
    nodes_by_distance: *mut c_void,
    zeroing_workers: IhkAtomic,
    nr_to_zero_pages: IhkAtomic,
    zeroed_list: LListHead,
    to_zero_list: LListHead,
    free_chunks: RbRoot,
    lock: McsLockNode,
    nr_pages: CULong,
    nr_free_pages: CULong,
    min_addr: CULong,
    max_addr: CULong,
}

const _: () = {
    assert!(size_of::<RbNode>() == 24);
    assert!(align_of::<RbNode>() == 8);
    assert!(size_of::<RbRoot>() == 8);
    assert!(align_of::<RbRoot>() == 8);
    assert!(size_of::<FreeChunk>() == 48);
    assert!(align_of::<FreeChunk>() == 8);
    assert!(offset_of!(FreeChunk, addr) == 0);
    assert!(offset_of!(FreeChunk, size) == 8);
    assert!(offset_of!(FreeChunk, node) == 16);
    assert!(offset_of!(FreeChunk, list) == 40);
    assert!(size_of::<LListHead>() == 8);
    assert!(align_of::<LListHead>() == 8);
    assert!(offset_of!(LListHead, first) == 0);
    assert!(size_of::<ListHead>() == 16);
    assert!(align_of::<ListHead>() == 8);
    assert!(size_of::<IhkAtomic>() == 4);
    assert!(align_of::<IhkAtomic>() == 4);
    assert!(offset_of!(IhkAtomic, counter) == 0);
    assert!(size_of::<McsLockNode>() == 64);
    assert!(align_of::<McsLockNode>() == 64);
    assert!(offset_of!(McsLockNode, locked) == 0);
    assert!(offset_of!(McsLockNode, next) == 8);
    assert!(offset_of!(McsLockNode, irqsave) == 16);
    assert!(size_of::<IhkPageAllocatorDesc>() == 192);
    assert!(align_of::<IhkPageAllocatorDesc>() == 64);
    assert!(offset_of!(IhkPageAllocatorDesc, start) == 0);
    assert!(offset_of!(IhkPageAllocatorDesc, end) == 8);
    assert!(offset_of!(IhkPageAllocatorDesc, last) == 16);
    assert!(offset_of!(IhkPageAllocatorDesc, count) == 20);
    assert!(offset_of!(IhkPageAllocatorDesc, flag) == 24);
    assert!(offset_of!(IhkPageAllocatorDesc, shift) == 28);
    assert!(offset_of!(IhkPageAllocatorDesc, lock) == 64);
    assert!(offset_of!(IhkPageAllocatorDesc, list) == 128);
    assert!(offset_of!(IhkPageAllocatorDesc, map) == 144);
    assert!(size_of::<IhkMcNumaNode>() == 256);
    assert!(align_of::<IhkMcNumaNode>() == 64);
    assert!(offset_of!(IhkMcNumaNode, id) == 0);
    assert!(offset_of!(IhkMcNumaNode, linux_numa_id) == 4);
    assert!(offset_of!(IhkMcNumaNode, node_type) == 8);
    assert!(offset_of!(IhkMcNumaNode, allocators) == 16);
    assert!(offset_of!(IhkMcNumaNode, nodes_by_distance) == 32);
    assert!(offset_of!(IhkMcNumaNode, zeroing_workers) == 40);
    assert!(offset_of!(IhkMcNumaNode, nr_to_zero_pages) == 44);
    assert!(offset_of!(IhkMcNumaNode, zeroed_list) == 48);
    assert!(offset_of!(IhkMcNumaNode, to_zero_list) == 56);
    assert!(offset_of!(IhkMcNumaNode, free_chunks) == 64);
    assert!(offset_of!(IhkMcNumaNode, lock) == 128);
    assert!(offset_of!(IhkMcNumaNode, nr_pages) == 192);
    assert!(offset_of!(IhkMcNumaNode, nr_free_pages) == 200);
    assert!(offset_of!(IhkMcNumaNode, min_addr) == 208);
    assert!(offset_of!(IhkMcNumaNode, max_addr) == 216);
};

unsafe extern "C" {
    static zero_at_free: CInt;

    fn phys_to_virt(p: CULong) -> *mut c_void;
    fn ihk_mc_get_nr_numa_nodes() -> CInt;
    fn ihk_mc_get_numa_node_by_distance(i: CInt) -> *mut IhkMcNumaNode;
}

#[inline(always)]
unsafe fn node_to_chunk(node: *mut RbNode) -> *mut FreeChunk {
    (node.cast::<u8>())
        .sub(offset_of!(FreeChunk, node))
        .cast::<FreeChunk>()
}

#[inline(always)]
unsafe fn chunk_node(chunk: *mut FreeChunk) -> *mut RbNode {
    &raw mut (*chunk).node
}

#[inline(always)]
unsafe fn list_to_chunk(node: *mut LListNode) -> *mut FreeChunk {
    (node.cast::<u8>())
        .sub(offset_of!(FreeChunk, list))
        .cast::<FreeChunk>()
}

#[inline(always)]
unsafe fn chunk_list(chunk: *mut FreeChunk) -> *mut LListNode {
    &raw mut (*chunk).list
}

#[inline(always)]
unsafe fn chunk_at_phys(addr: CULong) -> *mut FreeChunk {
    phys_to_virt(addr).cast::<FreeChunk>()
}

#[inline(always)]
unsafe fn llist_head_first(head: *mut LListHead) -> &'static AtomicPtr<LListNode> {
    AtomicPtr::from_ptr(&raw mut (*head).first)
}

#[inline(always)]
unsafe fn llist_add(node: *mut LListNode, head: *mut LListHead) {
    let first_slot = llist_head_first(head);
    let mut first = first_slot.load(Ordering::Acquire);

    loop {
        (*node).next = first;
        match first_slot.compare_exchange(first, node, Ordering::SeqCst, Ordering::SeqCst) {
            Ok(_) => return,
            Err(actual) => first = actual,
        }
    }
}

#[inline(always)]
unsafe fn llist_del_first(head: *mut LListHead) -> *mut LListNode {
    let first_slot = llist_head_first(head);
    let mut entry = first_slot.load(Ordering::Acquire);

    loop {
        if entry.is_null() {
            return null_mut();
        }

        let old_entry = entry;
        let next = read_volatile(&(*entry).next);
        match first_slot.compare_exchange(old_entry, next, Ordering::SeqCst, Ordering::SeqCst) {
            Ok(_) => return old_entry,
            Err(actual) => entry = actual,
        }
    }
}

#[inline(always)]
unsafe fn atomic_counter(atomic: *mut IhkAtomic) -> &'static AtomicI32 {
    AtomicI32::from_ptr(&raw mut (*atomic).counter)
}

#[inline(always)]
unsafe fn ihk_atomic_sub(value: CInt, atomic: *mut IhkAtomic) {
    atomic_counter(atomic).fetch_sub(value, Ordering::SeqCst);
}

#[inline(always)]
unsafe fn ihk_atomic_add(value: CInt, atomic: *mut IhkAtomic) {
    atomic_counter(atomic).fetch_add(value, Ordering::SeqCst);
}

#[inline(always)]
unsafe fn ihk_atomic_read(atomic: *mut IhkAtomic) -> CInt {
    atomic_counter(atomic).load(Ordering::SeqCst)
}

#[inline(always)]
unsafe fn desc_map(desc: *mut IhkPageAllocatorDesc) -> *mut CULong {
    desc.cast::<u8>()
        .add(offset_of!(IhkPageAllocatorDesc, map))
        .cast::<CULong>()
}

#[inline(always)]
unsafe fn desc_map_word(desc: *mut IhkPageAllocatorDesc, index: u32) -> *mut CULong {
    desc_map(desc).add(index as usize)
}

#[inline(always)]
unsafe fn read_map_word(desc: *mut IhkPageAllocatorDesc, index: u32) -> CULong {
    read_volatile(desc_map_word(desc, index))
}

#[inline(always)]
unsafe fn write_map_word(desc: *mut IhkPageAllocatorDesc, index: u32, value: CULong) {
    write_volatile(desc_map_word(desc, index), value);
}

#[inline(always)]
fn map_index(n: u32) -> u32 {
    n >> 6
}

#[inline(always)]
fn map_bit(n: u32) -> u32 {
    n & 0x3f
}

#[inline(always)]
fn fls_ulong(mut value: CULong) -> CInt {
    let mut bits = 0;

    while value != 0 {
        bits += 1;
        value >>= 1;
    }

    bits
}

#[no_mangle]
pub unsafe extern "C" fn pagealloc_init_layout_result(
    size: CULong,
    unit: CULong,
    desc_struct_size: CULong,
    page_shiftp: *mut CInt,
    mapsizep: *mut CInt,
    mapalignedp: *mut CInt,
    desc_pagesp: *mut CInt,
) -> CInt {
    if unit == 0 {
        return -EINVAL;
    }

    let page_shift = fls_ulong(unit) - 1;
    let mapsize = (size >> page_shift) as CInt;
    let mapaligned = ((mapsize + 63) >> 6) << 3;
    let descsize = desc_struct_size as CInt + mapaligned;
    let desc_pages = (descsize + PAGE_SIZE as CInt - 1) >> PAGE_SHIFT;

    if !page_shiftp.is_null() {
        unsafe {
            *page_shiftp = page_shift;
        }
    }
    if !mapsizep.is_null() {
        unsafe {
            *mapsizep = mapsize;
        }
    }
    if !mapalignedp.is_null() {
        unsafe {
            *mapalignedp = mapaligned;
        }
    }
    if !desc_pagesp.is_null() {
        unsafe {
            *desc_pagesp = desc_pages;
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn pagealloc_reserve_tail_result(map: *mut CULong, first: CInt, limit: CInt) {
    if map.is_null() {
        return;
    }

    let mut i = first;
    while i < limit {
        let index = map_index(i as u32) as usize;
        let bit = map_bit(i as u32);
        let word = map.add(index);
        let value = read_volatile(word) | ((1 as CULong) << bit);
        write_volatile(word, value);
        i += 1;
    }
}

#[no_mangle]
pub extern "C" fn pagealloc_init_end_result(start: CULong, size: CULong) -> CULong {
    start + size
}

#[no_mangle]
pub extern "C" fn pagealloc_init_count_result(mapaligned: CInt) -> CInt {
    mapaligned >> 3
}

#[no_mangle]
pub extern "C" fn pagealloc_destroy_pages_result(flag: CInt) -> CInt {
    flag
}

#[no_mangle]
pub unsafe extern "C" fn pagealloc_destroy_result(
    desc: *mut IhkPageAllocatorDesc,
    free_pages_fn: Option<PageAllocFreePagesFn>,
) -> CInt {
    let Some(free_pages_fn) = free_pages_fn else {
        return 0;
    };
    if desc.is_null() {
        return 0;
    }

    let pages = pagealloc_destroy_pages_result(unsafe { (*desc).flag as CInt });
    unsafe {
        free_pages_fn(desc.cast::<c_void>(), pages);
    }
    pages
}

#[no_mangle]
pub unsafe extern "C" fn pagealloc_desc_reset_result(
    desc: *mut IhkPageAllocatorDesc,
    desc_pages: CInt,
    page_size: CULong,
) {
    if desc.is_null() || desc_pages <= 0 || page_size == 0 {
        return;
    }

    unsafe {
        core::ptr::write_bytes(
            desc.cast::<u8>(),
            0,
            (desc_pages as usize).wrapping_mul(page_size as usize),
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn pagealloc_desc_init_result(
    desc: *mut IhkPageAllocatorDesc,
    start: CULong,
    size: CULong,
    page_shift: CInt,
    mapaligned: CInt,
    flag: CInt,
) {
    if desc.is_null() {
        return;
    }

    unsafe {
        (*desc).start = start;
        (*desc).end = pagealloc_init_end_result(start, size);
        (*desc).last = 0;
        (*desc).count = pagealloc_init_count_result(mapaligned) as u32;
        (*desc).shift = page_shift as u32;
        (*desc).flag = flag as u32;
    }
}

#[inline(always)]
unsafe fn desc_address(desc: *mut IhkPageAllocatorDesc, index: u32, bit: u32) -> CULong {
    (*desc)
        .start
        .wrapping_add((((index as CULong) * 64).wrapping_add(bit as CULong)) << (*desc).shift)
}

#[inline(always)]
unsafe fn zero_phys_page(addr: CULong) {
    let ptr = phys_to_virt(addr).cast::<CULong>();
    let mut i = 0usize;

    while i < (PAGE_SIZE as usize / size_of::<CULong>()) {
        write_volatile(ptr.add(i), 0);
        i += 1;
    }
}

#[inline(always)]
unsafe fn zero_phys_range(addr: CULong, size: CULong) {
    let ptr = phys_to_virt(addr);
    let words = (size as usize) / size_of::<CULong>();
    let bytes = (size as usize) % size_of::<CULong>();
    let word_ptr = ptr.cast::<CULong>();
    let byte_ptr = ptr.cast::<u8>().add(words * size_of::<CULong>());
    let mut i = 0usize;

    while i < words {
        write_volatile(word_ptr.add(i), 0);
        i += 1;
    }

    i = 0;
    while i < bytes {
        write_volatile(byte_ptr.add(i), 0);
        i += 1;
    }
}

#[inline(always)]
unsafe fn zero_chunk(chunk: *mut FreeChunk) {
    write_volatile(&raw mut (*chunk).addr, 0);
    write_volatile(&raw mut (*chunk).size, 0);
    write_volatile(&raw mut (*chunk).node.__rb_parent_color, 0);
    write_volatile(&raw mut (*chunk).node.rb_right, null_mut());
    write_volatile(&raw mut (*chunk).node.rb_left, null_mut());
    write_volatile(&raw mut (*chunk).list.next, null_mut());
}

#[inline(always)]
unsafe fn copy_chunk(dst: *mut FreeChunk, src: *const FreeChunk) {
    write_volatile(&raw mut (*dst).addr, read_volatile(&raw const (*src).addr));
    write_volatile(&raw mut (*dst).size, read_volatile(&raw const (*src).size));
    write_volatile(
        &raw mut (*dst).node.__rb_parent_color,
        read_volatile(&raw const (*src).node.__rb_parent_color),
    );
    write_volatile(
        &raw mut (*dst).node.rb_right,
        read_volatile(&raw const (*src).node.rb_right),
    );
    write_volatile(
        &raw mut (*dst).node.rb_left,
        read_volatile(&raw const (*src).node.rb_left),
    );
    write_volatile(
        &raw mut (*dst).list.next,
        read_volatile(&raw const (*src).list.next),
    );
}

#[no_mangle]
pub unsafe extern "C" fn __page_alloc_rbtree_free_range(
    root: *mut RbRoot,
    addr: CULong,
    size: CULong,
) -> CInt {
    let mut iter = &raw mut (*root).rb_node;
    let mut parent: *mut RbNode = null_mut();
    let new_chunk: *mut FreeChunk;

    while !(*iter).is_null() {
        let current = *iter;
        let ichunk = node_to_chunk(current);
        parent = current;

        if addr >= (*ichunk).addr && addr < (*ichunk).addr.wrapping_add((*ichunk).size) {
            return EINVAL;
        }

        if (*ichunk).addr.wrapping_add((*ichunk).size) == addr {
            (*ichunk).size = (*ichunk).size.wrapping_add(size);

            let right = rb_next(current);
            if !right.is_null() {
                let right_chunk = node_to_chunk(right);
                if (*ichunk).addr.wrapping_add((*ichunk).size) == (*right_chunk).addr {
                    (*ichunk).size = (*ichunk).size.wrapping_add((*right_chunk).size);
                    rb_erase(right, root);
                    zero_chunk(right_chunk);
                }
            }

            return 0;
        }

        if addr.wrapping_add(size) == (*ichunk).addr {
            (*ichunk).addr = (*ichunk).addr.wrapping_sub(size);
            (*ichunk).size = (*ichunk).size.wrapping_add(size);

            let left = rb_prev(current);
            if !left.is_null() {
                let left_chunk = node_to_chunk(left);
                if (*left_chunk).addr.wrapping_add((*left_chunk).size) == (*ichunk).addr {
                    (*ichunk).addr = (*ichunk).addr.wrapping_sub((*left_chunk).size);
                    (*ichunk).size = (*ichunk).size.wrapping_add((*left_chunk).size);
                    rb_erase(left, root);
                    zero_chunk(left_chunk);
                }
            }

            new_chunk = chunk_at_phys((*ichunk).addr);
            copy_chunk(new_chunk, ichunk);
            rb_replace_node(chunk_node(ichunk), chunk_node(new_chunk), root);
            zero_chunk(ichunk);

            return 0;
        }

        if addr < (*ichunk).addr {
            iter = &raw mut (*current).rb_left;
        } else {
            iter = &raw mut (*current).rb_right;
        }
    }

    new_chunk = chunk_at_phys(addr);
    (*new_chunk).addr = addr;
    (*new_chunk).size = size;
    rb_link_node(chunk_node(new_chunk), parent, iter);
    rb_insert_color(chunk_node(new_chunk), root);

    0
}

unsafe fn page_alloc_rbtree_mark_range_allocated(
    root: *mut RbRoot,
    chunk: *mut FreeChunk,
    aligned_addr: CULong,
    size: CULong,
) -> CInt {
    let mut right_chunk: *mut FreeChunk = null_mut();

    if aligned_addr.wrapping_add(size) < (*chunk).addr.wrapping_add((*chunk).size) {
        right_chunk = chunk_at_phys(aligned_addr.wrapping_add(size));
        (*right_chunk).addr = aligned_addr.wrapping_add(size);
        (*right_chunk).size = (*chunk)
            .addr
            .wrapping_add((*chunk).size)
            .wrapping_sub(aligned_addr.wrapping_add(size));
    }

    let left_chunk = if aligned_addr != (*chunk).addr {
        chunk
    } else {
        null_mut()
    };

    (*chunk).size = aligned_addr.wrapping_sub((*chunk).addr);

    if !left_chunk.is_null() {
        if !right_chunk.is_null()
            && __page_alloc_rbtree_free_range(root, (*right_chunk).addr, (*right_chunk).size) != 0
        {
            return EINVAL;
        }
    } else if !right_chunk.is_null() {
        rb_replace_node(chunk_node(chunk), chunk_node(right_chunk), root);
    } else {
        rb_erase(chunk_node(chunk), root);
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn __page_alloc_rbtree_alloc_pages(
    root: *mut RbRoot,
    npages: CInt,
    p2align: CInt,
) -> CULong {
    let size = PAGE_SIZE.wrapping_mul(npages as CULong);
    let align_shift = if p2align <= 0 { 0 } else { p2align as u32 };
    let align_size = PAGE_SIZE << align_shift;
    let align_mask = !(align_size - 1);
    let mut aligned_addr: CULong = 0;
    let mut node = rb_first(root);

    while !node.is_null() {
        let chunk = node_to_chunk(node);
        aligned_addr = ((*chunk).addr.wrapping_add(align_size - 1)) & align_mask;

        if aligned_addr.wrapping_add(size) <= (*chunk).addr.wrapping_add((*chunk).size) {
            break;
        }

        node = rb_next(node);
    }

    if node.is_null() {
        return 0;
    }

    let chunk = node_to_chunk(node);
    if page_alloc_rbtree_mark_range_allocated(root, chunk, aligned_addr, size) != 0 {
        return 0;
    }

    if zero_at_free != 0 {
        zero_chunk(chunk_at_phys(aligned_addr));
    }

    aligned_addr
}

#[no_mangle]
pub unsafe extern "C" fn __page_alloc_rbtree_reserve_pages(
    root: *mut RbRoot,
    aligned_addr: CULong,
    npages: CInt,
) -> CULong {
    if root.is_null() || npages <= 0 {
        return 0;
    }

    let size = PAGE_SIZE.wrapping_mul(npages as CULong);
    let mut node = rb_first(root);

    while !node.is_null() {
        let chunk = node_to_chunk(node);
        if aligned_addr >= (*chunk).addr
            && aligned_addr.wrapping_add(size) <= (*chunk).addr.wrapping_add((*chunk).size)
        {
            if page_alloc_rbtree_mark_range_allocated(root, chunk, aligned_addr, size) != 0 {
                return 0;
            }
            return aligned_addr;
        }

        node = rb_next(node);
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn __page_alloc_rbtree_get_root_chunk(root: *mut RbRoot) -> *mut FreeChunk {
    if root.is_null() {
        return null_mut();
    }

    let node = (*root).rb_node;
    if node.is_null() {
        return null_mut();
    }

    rb_erase(node, root);
    node_to_chunk(node)
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_numa_add_free_pages(
    node: *mut IhkMcNumaNode,
    addr: CULong,
    size: CULong,
) -> CInt {
    if node.is_null() {
        return EINVAL;
    }

    if zero_at_free != 0 {
        zero_phys_range(addr, size);
    }

    if __page_alloc_rbtree_free_range(&raw mut (*node).free_chunks, addr, size) != 0 {
        return EINVAL;
    }

    if addr < (*node).min_addr {
        (*node).min_addr = addr;
    }

    if addr.wrapping_add(size) > (*node).max_addr {
        (*node).max_addr = addr.wrapping_add(size);
    }

    let pages = size >> PAGE_SHIFT;
    (*node).nr_pages = (*node).nr_pages.wrapping_add(pages);
    (*node).nr_free_pages = (*node).nr_free_pages.wrapping_add(pages);

    0
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_numa_zero_free_pages_node(
    node: *mut IhkMcNumaNode,
    nr_pages: CInt,
) -> CInt {
    if node.is_null() {
        return 0;
    }

    let mut nr_zeroed_pages: CInt = 0;
    let requested_size = if nr_pages > 0 {
        (nr_pages as CULong) << PAGE_SHIFT
    } else {
        0
    };

    if nr_pages != 0 {
        let mut tmp = LListHead { first: null_mut() };

        loop {
            let llnode = llist_del_first(&raw mut (*node).to_zero_list);
            if llnode.is_null() {
                break;
            }

            let chunk = list_to_chunk(llnode);
            let addr = (*chunk).addr;
            let size = (*chunk).size;

            if size < requested_size {
                llist_add(llnode, &raw mut tmp);
                continue;
            }

            if size > size_of::<FreeChunk>() as CULong {
                zero_phys_range(
                    addr + size_of::<FreeChunk>() as CULong,
                    size - size_of::<FreeChunk>() as CULong,
                );
            }
            llist_add(chunk_list(chunk), &raw mut (*node).zeroed_list);
            compiler_fence(Ordering::SeqCst);
            ihk_atomic_sub(
                (size >> PAGE_SHIFT) as CInt,
                &raw mut (*node).nr_to_zero_pages,
            );
            nr_zeroed_pages = nr_zeroed_pages.wrapping_add(((*chunk).size >> PAGE_SHIFT) as CInt);
            break;
        }

        loop {
            let llnode = llist_del_first(&raw mut tmp);
            if llnode.is_null() {
                break;
            }
            llist_add(llnode, &raw mut (*node).to_zero_list);
        }
    } else {
        loop {
            let llnode = llist_del_first(&raw mut (*node).to_zero_list);
            if llnode.is_null() {
                break;
            }

            let chunk = list_to_chunk(llnode);
            let addr = (*chunk).addr;
            let size = (*chunk).size;

            if size > size_of::<FreeChunk>() as CULong {
                zero_phys_range(
                    addr + size_of::<FreeChunk>() as CULong,
                    size - size_of::<FreeChunk>() as CULong,
                );
            }
            llist_add(chunk_list(chunk), &raw mut (*node).zeroed_list);
            compiler_fence(Ordering::SeqCst);
            ihk_atomic_sub(
                (size >> PAGE_SHIFT) as CInt,
                &raw mut (*node).nr_to_zero_pages,
            );
            nr_zeroed_pages = nr_zeroed_pages.wrapping_add(((*chunk).size >> PAGE_SHIFT) as CInt);
        }
    }

    nr_zeroed_pages
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_numa_zero_free_pages_dispatch(
    explicit_node: *mut IhkMcNumaNode,
    nr_pages: CInt,
) -> CInt {
    if zero_at_free == 0 {
        return 0;
    }

    let max_i = if explicit_node.is_null() {
        ihk_mc_get_nr_numa_nodes()
    } else {
        1
    };
    let mut nr_zeroed_pages: CInt = 0;
    let mut i: CInt = 0;

    while i < max_i {
        let node = if explicit_node.is_null() {
            ihk_mc_get_numa_node_by_distance(i)
        } else {
            explicit_node
        };

        if node.is_null() {
            break;
        }

        nr_zeroed_pages =
            nr_zeroed_pages.wrapping_add(__ihk_numa_zero_free_pages_node(node, nr_pages));
        i += 1;
    }

    nr_zeroed_pages
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_numa_alloc_pages_nolock(
    node: *mut IhkMcNumaNode,
    npages: CInt,
    p2align: CInt,
) -> CULong {
    if node.is_null() {
        return 0;
    }

    let requested_pages = npages as CULong;

    loop {
        if zero_at_free != 0 {
            loop {
                let llnode = llist_del_first(&raw mut (*node).zeroed_list);
                if llnode.is_null() {
                    break;
                }

                let chunk = list_to_chunk(llnode);
                let addr = (*chunk).addr;
                let size = (*chunk).size;

                if __page_alloc_rbtree_free_range(&raw mut (*node).free_chunks, addr, size) == 0 {
                    (*node).nr_free_pages = (*node).nr_free_pages.wrapping_add(size >> PAGE_SHIFT);
                }
            }

            if (*node).nr_free_pages < requested_pages
                && (__ihk_numa_zero_free_pages_node(node, npages) as CULong) >= requested_pages
            {
                continue;
            }
        }

        if (*node).nr_free_pages < requested_pages {
            return 0;
        }

        let addr = __page_alloc_rbtree_alloc_pages(&raw mut (*node).free_chunks, npages, p2align);
        if addr != 0 {
            (*node).nr_free_pages = (*node).nr_free_pages.wrapping_sub(requested_pages);
        }

        return addr;
    }
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_numa_free_pages_to_tree_nolock(
    node: *mut IhkMcNumaNode,
    addr: CULong,
    npages: CInt,
) -> CInt {
    if node.is_null() || npages <= 0 {
        return EINVAL;
    }

    let size = (npages as CULong) << PAGE_SHIFT;
    if __page_alloc_rbtree_free_range(&raw mut (*node).free_chunks, addr, size) != 0 {
        return EINVAL;
    }

    (*node).nr_free_pages = (*node).nr_free_pages.wrapping_add(npages as CULong);
    0
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_numa_alloc_pages_locked_result(
    node: *mut IhkMcNumaNode,
    npages: CInt,
    p2align: CInt,
    lock_offset: CULong,
    lock_node_addr: CULong,
    lock_fn: Option<PageAllocMcsLockFn>,
    unlock_fn: Option<PageAllocMcsUnlockFn>,
) -> CULong {
    if node.is_null() {
        return 0;
    }
    let Some(lock) = lock_fn else {
        return 0;
    };
    let Some(unlock) = unlock_fn else {
        return 0;
    };

    let lock_addr = (node as CULong).wrapping_add(lock_offset);
    unsafe {
        lock(lock_addr, lock_node_addr);
        let addr = __ihk_numa_alloc_pages_nolock(node, npages, p2align);
        unlock(lock_addr, lock_node_addr);
        addr
    }
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_numa_free_pages_direct_locked_result(
    node: *mut IhkMcNumaNode,
    addr: CULong,
    npages: CInt,
    lock_offset: CULong,
    lock_node_addr: CULong,
    lock_fn: Option<PageAllocMcsLockFn>,
    unlock_fn: Option<PageAllocMcsUnlockFn>,
) -> CInt {
    if node.is_null() || npages <= 0 {
        return EINVAL;
    }
    let Some(lock) = lock_fn else {
        return EINVAL;
    };
    let Some(unlock) = unlock_fn else {
        return EINVAL;
    };

    let lock_addr = (node as CULong).wrapping_add(lock_offset);
    unsafe {
        lock(lock_addr, lock_node_addr);
        let rc = __ihk_numa_free_pages_to_tree_nolock(node, addr, npages);
        unlock(lock_addr, lock_node_addr);
        rc
    }
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_numa_defer_zero_free_pages(
    node: *mut IhkMcNumaNode,
    addr: CULong,
    npages: CInt,
) -> CInt {
    if node.is_null() || npages <= 0 {
        return EINVAL;
    }

    let chunk = chunk_at_phys(addr);
    (*chunk).addr = addr;
    (*chunk).size = (npages as CULong) << PAGE_SHIFT;
    ihk_atomic_add(npages, &raw mut (*node).nr_to_zero_pages);
    compiler_fence(Ordering::SeqCst);
    llist_add(chunk_list(chunk), &raw mut (*node).to_zero_list);

    0
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_numa_free_pages_prepare(
    node: *mut IhkMcNumaNode,
    addr: CULong,
    npages: CInt,
    defer_zero_at_free: CInt,
) -> CInt {
    if node.is_null() || npages <= 0 {
        return IHK_NUMA_FREE_IGNORED;
    }

    let size = (npages as CULong) << PAGE_SHIFT;
    if addr < (*node).min_addr || addr.wrapping_add(size) > (*node).max_addr {
        return IHK_NUMA_FREE_IGNORED;
    }

    if zero_at_free != 0 && defer_zero_at_free == 0 {
        zero_phys_range(addr, size);
    }

    return if zero_at_free == 0 || defer_zero_at_free == 0 {
        IHK_NUMA_FREE_DIRECT
    } else {
        IHK_NUMA_FREE_DEFERRED
    };
}

#[no_mangle]
pub extern "C" fn __ihk_numa_cpu_cache_try_result(cpu_initialized: CInt) -> CInt {
    (cpu_initialized != 0) as CInt
}

#[no_mangle]
pub extern "C" fn __ihk_numa_cpu_cache_alloc_hit_result(addr: CULong) -> CInt {
    (addr != 0) as CInt
}

#[no_mangle]
pub extern "C" fn __ihk_numa_cpu_cache_free_success_result(free_rc: CInt) -> CInt {
    (free_rc == 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_numa_cpu_cache_alloc_nolock(
    root: *mut RbRoot,
    npages: CInt,
    p2align: CInt,
) -> CULong {
    if root.is_null() {
        return 0;
    }

    __page_alloc_rbtree_alloc_pages(root, npages, p2align)
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_numa_cpu_cache_free_nolock(
    root: *mut RbRoot,
    addr: CULong,
    npages: CInt,
) -> CInt {
    if root.is_null() || npages <= 0 {
        return EINVAL;
    }

    __page_alloc_rbtree_free_range(root, addr, (npages as CULong) << PAGE_SHIFT)
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_numa_cpu_cache_alloc_try_result(
    cpu_initialized: CInt,
    root: *mut RbRoot,
    npages: CInt,
    p2align: CInt,
    irq_save_fn: Option<PageAllocIrqSaveFn>,
    irq_restore_fn: Option<PageAllocIrqRestoreFn>,
) -> CULong {
    if cpu_initialized == 0 {
        return 0;
    }
    let Some(irq_save) = irq_save_fn else {
        return 0;
    };
    let Some(irq_restore) = irq_restore_fn else {
        return 0;
    };

    let irqflags = unsafe { irq_save() };
    let addr = unsafe { __ihk_numa_cpu_cache_alloc_nolock(root, npages, p2align) };
    unsafe { irq_restore(irqflags) };

    addr
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_numa_cpu_cache_free_try_result(
    cpu_initialized: CInt,
    root: *mut RbRoot,
    addr: CULong,
    npages: CInt,
    irq_save_fn: Option<PageAllocIrqSaveFn>,
    irq_restore_fn: Option<PageAllocIrqRestoreFn>,
) -> CInt {
    if cpu_initialized == 0 {
        return IHK_NUMA_CPU_CACHE_FREE_NOT_TRIED;
    }
    let Some(irq_save) = irq_save_fn else {
        return IHK_NUMA_CPU_CACHE_FREE_NOT_TRIED;
    };
    let Some(irq_restore) = irq_restore_fn else {
        return IHK_NUMA_CPU_CACHE_FREE_NOT_TRIED;
    };

    let irqflags = unsafe { irq_save() };
    let rc = unsafe { __ihk_numa_cpu_cache_free_nolock(root, addr, npages) };
    unsafe { irq_restore(irqflags) };

    if rc == 0 {
        IHK_NUMA_CPU_CACHE_FREE_SUCCESS
    } else {
        IHK_NUMA_CPU_CACHE_FREE_FAILED
    }
}

#[no_mangle]
pub extern "C" fn __ihk_numa_linux_zero_request_action(
    cpu_initialized: CInt,
    has_current: CInt,
    is_idle: CInt,
    nohost: CInt,
    zeroing_workers: CInt,
) -> CInt {
    if cpu_initialized == 0 || has_current == 0 || is_idle != 0 || nohost != 0 {
        return 0;
    }
    if zeroing_workers > 0 {
        return 2;
    }
    1
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_numa_zeroing_worker_inc(node: *mut IhkMcNumaNode) {
    if node.is_null() {
        return;
    }

    ihk_atomic_add(1, &raw mut (*node).zeroing_workers);
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_numa_zero_request_packet_fill(
    packet: *mut IkcScdPacket,
    node_addr: CULong,
    cpu_ref: CInt,
    pid: CInt,
    syscall_number: CULong,
) {
    if packet.is_null() {
        return;
    }

    let words = packet.cast::<CULong>();
    let mut i = 0usize;
    while i < size_of::<IkcScdPacket>() / size_of::<CULong>() {
        write_volatile(words.add(i), 0);
        i += 1;
    }

    let traditional = (&raw mut (*packet).body).cast::<IkcScdPacketTraditional>();
    (*traditional).req.number = syscall_number;
    (*traditional).req.args[0] = node_addr;

    compiler_fence(Ordering::Release);
    write_volatile(&raw mut (*traditional).req.valid, 1);
    (*packet).msg = SCD_MSG_SYSCALL_ONESIDE;
    (*traditional).ref_ = cpu_ref;
    (*traditional).pid = pid;
    (*traditional).resp_pa = 0;
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_numa_linux_zero_request_prepare(
    node: *mut IhkMcNumaNode,
    packet: *mut IkcScdPacket,
    cpu_initialized: CInt,
    current_thread: CULong,
    idle_thread: CULong,
    thread_proc_offset: CULong,
    proc_nohost_offset: CULong,
    proc_pid_offset: CULong,
    cpu_ref: CInt,
    syscall_number: CULong,
) -> CInt {
    if node.is_null() || packet.is_null() || cpu_initialized == 0 || current_thread == 0 {
        return 0;
    }
    if current_thread == idle_thread {
        return 0;
    }

    let proc =
        unsafe { read_volatile(current_thread.wrapping_add(thread_proc_offset) as *const CULong) };
    if proc == 0 {
        return 0;
    }

    let nohost = unsafe { read_volatile(proc.wrapping_add(proc_nohost_offset) as *const CInt) };
    let action = __ihk_numa_linux_zero_request_action(cpu_initialized, 1, 0, nohost, unsafe {
        ihk_atomic_read(&raw mut (*node).zeroing_workers)
    });
    if action != 1 {
        return action;
    }

    let pid = unsafe { read_volatile(proc.wrapping_add(proc_pid_offset) as *const CInt) };
    unsafe {
        __ihk_numa_zeroing_worker_inc(node);
        __ihk_numa_zero_request_packet_fill(packet, node as CULong, cpu_ref, pid, syscall_number);
    }

    1
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_numa_free_pages_deferred_result(
    node: *mut IhkMcNumaNode,
    addr: CULong,
    npages: CInt,
    packet: *mut IkcScdPacket,
    cpu_initialized: CInt,
    current_thread: CULong,
    idle_thread: CULong,
    thread_proc_offset: CULong,
    proc_nohost_offset: CULong,
    proc_pid_offset: CULong,
    cpu_ref: CInt,
    syscall_number: CULong,
) -> CInt {
    unsafe {
        if __ihk_numa_defer_zero_free_pages(node, addr, npages) != 0 {
            return -EINVAL;
        }

        __ihk_numa_linux_zero_request_prepare(
            node,
            packet,
            cpu_initialized,
            current_thread,
            idle_thread,
            thread_proc_offset,
            proc_nohost_offset,
            proc_pid_offset,
            cpu_ref,
            syscall_number,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_pagealloc_large_nolock(
    desc: *mut IhkPageAllocatorDesc,
    npages: CInt,
    p2align: CInt,
) -> CULong {
    if desc.is_null() || npages <= 0 {
        return 0;
    }

    let align_shift = if p2align <= 0 { 0 } else { p2align as u32 };
    let align_mask = (PAGE_SIZE << align_shift).wrapping_sub(1);
    let count = (*desc).count;
    let mut nblocks = (npages / 64) as u32;
    let nfrags = (npages % 64) as u32;
    let mask = if nfrags > 0 {
        nblocks = nblocks.wrapping_add(1);
        (1 as CULong).wrapping_shl(nfrags).wrapping_sub(1)
    } else {
        !0
    };

    let mut i = 0;
    let mut mi = (*desc).last;
    while i < count {
        if mi >= count {
            mi = 0;
        }

        if mi.wrapping_add(nblocks) >= count || (desc_address(desc, mi, 0) & align_mask) != 0 {
            i = i.wrapping_add(1);
            mi = mi.wrapping_add(1);
            continue;
        }

        let mut j = mi;
        while j < mi.wrapping_add(nblocks).wrapping_sub(1) {
            if read_map_word(desc, j) != 0 {
                break;
            }
            j = j.wrapping_add(1);
        }

        if j == mi.wrapping_add(nblocks).wrapping_sub(1) && (read_map_word(desc, j) & mask) == 0 {
            let mut fill = mi;
            while fill < mi.wrapping_add(nblocks).wrapping_sub(1) {
                write_map_word(desc, fill, !0);
                fill = fill.wrapping_add(1);
            }
            write_map_word(desc, j, read_map_word(desc, j) | mask);
            return desc_address(desc, mi, 0);
        }

        i = i.wrapping_add(1);
        mi = mi.wrapping_add(1);
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_pagealloc_alloc_nolock(
    desc: *mut IhkPageAllocatorDesc,
    npages: CInt,
    p2align: CInt,
) -> CULong {
    if desc.is_null() || npages <= 0 {
        return 0;
    }

    if npages >= 32 || p2align >= 5 {
        return __ihk_pagealloc_large_nolock(desc, npages, p2align);
    }

    let mask = (1 as CULong).wrapping_shl(npages as u32).wrapping_sub(1);
    let jalign = if p2align <= 0 {
        1
    } else {
        1_i32 << (p2align as u32)
    };
    let count = (*desc).count;
    let mut i = 0;
    let mut mi = (*desc).last;

    while i < count {
        if mi >= count {
            mi = 0;
        }

        let v = read_map_word(desc, mi);
        if v == !0 {
            i = i.wrapping_add(1);
            mi = mi.wrapping_add(1);
            continue;
        }

        let mut j = 0;
        while j <= 64 - npages {
            if j % jalign == 0 {
                let shifted = mask << (j as u32);
                if (v & shifted) == 0 {
                    write_map_word(desc, mi, v | shifted);
                    return desc_address(desc, mi, j as u32);
                }
            }
            j += 1;
        }

        i = i.wrapping_add(1);
        mi = mi.wrapping_add(1);
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_pagealloc_reserve_nolock(
    desc: *mut IhkPageAllocatorDesc,
    start: CULong,
    end: CULong,
) {
    if desc.is_null() {
        return;
    }

    let unit = (1 as CULong) << (*desc).shift;
    let n = end
        .wrapping_add(unit)
        .wrapping_sub(1)
        .wrapping_sub((*desc).start)
        .wrapping_shr((*desc).shift) as CInt;
    let mut i = start
        .wrapping_sub((*desc).start)
        .wrapping_shr((*desc).shift) as CInt;
    if i < 0 || n < 0 {
        return;
    }

    while i < n {
        let index = map_index(i as u32);
        if (i & 63) == 0 && i + 63 < n {
            write_map_word(desc, index, !0);
            i += 64;
        } else {
            write_map_word(
                desc,
                index,
                read_map_word(desc, index) | ((1 as CULong) << map_bit(i as u32)),
            );
            i += 1;
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_pagealloc_free_nolock(
    desc: *mut IhkPageAllocatorDesc,
    address: CULong,
    npages: CInt,
    bad_address: *mut CULong,
) -> CInt {
    if desc.is_null() || npages <= 0 {
        return 0;
    }

    let mut mi = address
        .wrapping_sub((*desc).start)
        .wrapping_shr((*desc).shift) as u32;
    let mut i = 0;
    while i < npages {
        let bit = (1 as CULong) << map_bit(mi);
        let word = desc_map_word(desc, map_index(mi));
        let value = read_volatile(word);

        if (value & bit) == 0 {
            if !bad_address.is_null() {
                *bad_address = address.wrapping_add((i as CULong) * PAGE_SIZE);
            }
            return EINVAL;
        }

        write_volatile(word, value & !bit);
        i += 1;
        mi = mi.wrapping_add(1);
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_pagealloc_count_nolock(desc: *mut IhkPageAllocatorDesc) -> CULong {
    if desc.is_null() {
        return 0;
    }

    let mut n = 0;
    let mut i = 0;
    while i < (*desc).count {
        let v = read_map_word(desc, i);
        let mut j = 0;
        while j < 64 {
            if (v & ((1 as CULong) << j)) == 0 {
                n += 1;
            }
            j += 1;
        }
        i += 1;
    }

    n
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_pagealloc_query_free_nolock(
    desc: *mut IhkPageAllocatorDesc,
) -> CInt {
    if desc.is_null() {
        return 0;
    }

    let mut npages: CInt = 0;
    let mut mi = 0;
    while mi < (*desc).count {
        let v = read_map_word(desc, mi);
        if v != !0 {
            let mut j = 0;
            while j < 64 {
                if (v & ((1 as CULong) << j)) == 0 {
                    npages += 1;
                }
                j += 1;
            }
        }
        mi += 1;
    }

    npages
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_pagealloc_zero_free_pages_nolock(desc: *mut IhkPageAllocatorDesc) {
    if desc.is_null() {
        return;
    }

    let mut mi = 0;
    while mi < (*desc).count {
        let v = read_map_word(desc, mi);
        if v != !0 {
            let mut j = 0;
            while j < 64 {
                if (v & ((1 as CULong) << j)) == 0 {
                    zero_phys_page(desc_address(desc, mi, j));
                }
                j += 1;
            }
        }
        mi += 1;
    }
}

#[inline(always)]
unsafe fn pagealloc_lock_addr(desc: *mut IhkPageAllocatorDesc, lock_offset: CULong) -> CULong {
    (desc as CULong).wrapping_add(lock_offset)
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_pagealloc_alloc_locked_result(
    desc: *mut IhkPageAllocatorDesc,
    npages: CInt,
    p2align: CInt,
    lock_offset: CULong,
    lock_node_addr: CULong,
    lock_fn: Option<PageAllocMcsLockFn>,
    unlock_fn: Option<PageAllocMcsUnlockFn>,
) -> CULong {
    if desc.is_null() {
        return 0;
    }
    let Some(lock) = lock_fn else {
        return 0;
    };
    let Some(unlock) = unlock_fn else {
        return 0;
    };

    let lock_addr = pagealloc_lock_addr(desc, lock_offset);
    lock(lock_addr, lock_node_addr);
    let addr = __ihk_pagealloc_alloc_nolock(desc, npages, p2align);
    unlock(lock_addr, lock_node_addr);
    addr
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_pagealloc_reserve_locked_result(
    desc: *mut IhkPageAllocatorDesc,
    start: CULong,
    end: CULong,
    lock_offset: CULong,
    lock_node_addr: CULong,
    lock_fn: Option<PageAllocMcsLockFn>,
    unlock_fn: Option<PageAllocMcsUnlockFn>,
) -> CInt {
    if desc.is_null() {
        return 0;
    }
    let Some(lock) = lock_fn else {
        return 0;
    };
    let Some(unlock) = unlock_fn else {
        return 0;
    };

    let lock_addr = pagealloc_lock_addr(desc, lock_offset);
    lock(lock_addr, lock_node_addr);
    __ihk_pagealloc_reserve_nolock(desc, start, end);
    unlock(lock_addr, lock_node_addr);
    1
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_pagealloc_free_locked_result(
    desc: *mut IhkPageAllocatorDesc,
    address: CULong,
    npages: CInt,
    bad_address: *mut CULong,
    lock_offset: CULong,
    lock_node_addr: CULong,
    lock_fn: Option<PageAllocMcsLockFn>,
    unlock_fn: Option<PageAllocMcsUnlockFn>,
) -> CInt {
    if desc.is_null() {
        return EINVAL;
    }
    let Some(lock) = lock_fn else {
        return EINVAL;
    };
    let Some(unlock) = unlock_fn else {
        return EINVAL;
    };

    let lock_addr = pagealloc_lock_addr(desc, lock_offset);
    lock(lock_addr, lock_node_addr);
    let rc = __ihk_pagealloc_free_nolock(desc, address, npages, bad_address);
    unlock(lock_addr, lock_node_addr);
    rc
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_pagealloc_count_locked_result(
    desc: *mut IhkPageAllocatorDesc,
    lock_offset: CULong,
    lock_node_addr: CULong,
    lock_fn: Option<PageAllocMcsLockFn>,
    unlock_fn: Option<PageAllocMcsUnlockFn>,
) -> CULong {
    if desc.is_null() {
        return 0;
    }
    let Some(lock) = lock_fn else {
        return 0;
    };
    let Some(unlock) = unlock_fn else {
        return 0;
    };

    let lock_addr = pagealloc_lock_addr(desc, lock_offset);
    lock(lock_addr, lock_node_addr);
    let n = __ihk_pagealloc_count_nolock(desc);
    unlock(lock_addr, lock_node_addr);
    n
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_pagealloc_query_free_locked_result(
    desc: *mut IhkPageAllocatorDesc,
    lock_offset: CULong,
    lock_node_addr: CULong,
    lock_fn: Option<PageAllocMcsLockFn>,
    unlock_fn: Option<PageAllocMcsUnlockFn>,
) -> CInt {
    if desc.is_null() {
        return 0;
    }
    let Some(lock) = lock_fn else {
        return 0;
    };
    let Some(unlock) = unlock_fn else {
        return 0;
    };

    let lock_addr = pagealloc_lock_addr(desc, lock_offset);
    lock(lock_addr, lock_node_addr);
    let n = __ihk_pagealloc_query_free_nolock(desc);
    unlock(lock_addr, lock_node_addr);
    n
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_pagealloc_zero_free_pages_locked_result(
    desc: *mut IhkPageAllocatorDesc,
    lock_offset: CULong,
    lock_node_addr: CULong,
    lock_fn: Option<PageAllocMcsLockFn>,
    unlock_fn: Option<PageAllocMcsUnlockFn>,
) -> CInt {
    if desc.is_null() {
        return 0;
    }
    let Some(lock) = lock_fn else {
        return 0;
    };
    let Some(unlock) = unlock_fn else {
        return 0;
    };

    let lock_addr = pagealloc_lock_addr(desc, lock_offset);
    lock(lock_addr, lock_node_addr);
    __ihk_pagealloc_zero_free_pages_nolock(desc);
    unlock(lock_addr, lock_node_addr);
    1
}
