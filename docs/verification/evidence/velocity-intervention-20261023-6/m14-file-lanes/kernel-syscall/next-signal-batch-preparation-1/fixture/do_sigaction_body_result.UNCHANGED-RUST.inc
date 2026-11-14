#[no_mangle]
pub unsafe extern "C" fn do_sigaction_body_result(
    sig: CInt,
    act: *const KSigAction,
    oact: *mut KSigAction,
    sigcommon: *mut c_void,
    action_offset: SizeT,
    action_stride: SizeT,
    lock_offset: SizeT,
    lock_node: *mut c_void,
    lock_fn: Option<SyscallSigcommonLockFn>,
    unlock_fn: Option<SyscallSigcommonLockFn>,
    forward_fn: Option<SyscallSigactionForwardFn>,
) -> CInt {
    let error = sigaction_validate(sig, (!act.is_null()) as CInt);
    if error != 0 {
        return error;
    }
    if sigcommon.is_null() || lock_node.is_null() || action_stride < size_of::<KSigAction>() {
        return -EFAULT;
    }

    let Some(lock) = lock_fn else {
        return -EFAULT;
    };
    let Some(unlock) = unlock_fn else {
        return -EFAULT;
    };
    let forward = if act.is_null() {
        None
    } else {
        match forward_fn {
            Some(callback) => Some(callback),
            None => return -EFAULT,
        }
    };

    let action_index = (sig - 1) as SizeT;
    let Some(action_delta) = action_stride
        .checked_mul(action_index)
        .and_then(|delta| action_offset.checked_add(delta))
    else {
        return -EINVAL;
    };

    let sigcommon_bytes = sigcommon.cast::<u8>();
    let action = sigcommon_bytes.add(action_delta).cast::<KSigAction>();
    let lock_ptr = sigcommon_bytes.add(lock_offset).cast::<c_void>();

    lock(lock_ptr, lock_node);
    if !oact.is_null() {
        copy_nonoverlapping(action.cast::<u8>(), oact.cast::<u8>(), action_stride);
    }
    if !act.is_null() {
        copy_nonoverlapping(act.cast::<u8>(), action.cast::<u8>(), action_stride);
    }
    unlock(lock_ptr, lock_node);

    if let Some(callback) = forward {
        callback(sig, act.cast::<c_void>());
    }

    0
}
