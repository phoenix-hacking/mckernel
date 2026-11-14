#[repr(C, align(64))]
struct McsRwlockNode {
    count: IhkAtomic,
    type_: i8,
    locked: i8,
    dmy1: i8,
    dmy2: i8,
    next: *mut McsRwlockNode,
}

const _: () = {
    assert!(size_of::<McsRwlockNode>() == 64);
    assert!(align_of::<McsRwlockNode>() == 64);
    assert!(offset_of!(McsRwlockNode, count) == 0);
    assert!(offset_of!(McsRwlockNode, type_) == 4);
    assert!(offset_of!(McsRwlockNode, locked) == 5);
    assert!(offset_of!(McsRwlockNode, dmy1) == 6);
    assert!(offset_of!(McsRwlockNode, dmy2) == 7);
    assert!(offset_of!(McsRwlockNode, next) == 8);
};

