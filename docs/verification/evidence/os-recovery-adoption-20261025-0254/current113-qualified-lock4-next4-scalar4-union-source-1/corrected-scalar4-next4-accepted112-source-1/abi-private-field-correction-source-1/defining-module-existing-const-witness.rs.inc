const _: () = {
    use core::mem::{align_of, offset_of, size_of};

    assert!(size_of::<IhkRwSpinlock>() == 4);
    assert!(align_of::<IhkRwSpinlock>() == 4);
    assert!(offset_of!(IhkRwSpinlock, counter) == 0);
    assert!(size_of::<McsLockNode>() == 64);
    assert!(align_of::<McsLockNode>() == 64);
    assert!(offset_of!(McsLockNode, locked) == 0);
    assert!(offset_of!(McsLockNode, next) == 8);
    assert!(offset_of!(McsLockNode, irqsave) == 16);
    assert!(size_of::<McsRwlockNodeIrqsave>() == 64);
    assert!(align_of::<McsRwlockNodeIrqsave>() == 64);
    assert!(offset_of!(McsRwlockNodeIrqsave, irqsave) == 0);
    assert!(size_of::<McsRwlockLock>() == 64);
    assert!(align_of::<McsRwlockLock>() == 64);
    assert!(offset_of!(McsRwlockLock, slock) == 0);
    assert!(size_of::<IhkMcRwlock>() == 8);
    assert!(align_of::<IhkMcRwlock>() == 8);
    assert!(offset_of!(IhkMcRwlock, lock) == 0);
};
