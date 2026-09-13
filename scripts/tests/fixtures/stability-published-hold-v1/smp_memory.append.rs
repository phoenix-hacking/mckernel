// VERIFICATION OVERLAY ONLY. Private version 2; original version 1 fixture is unchanged.
pub(super) fn verification_phase_ioctl(argument: usize, compat: bool) -> Result<isize> {
    use crate::stability_phase as phase;
    if compat {
        return Err(kernel::error::to_result(-95).unwrap_err());
    }
    let begin = phase::now_ns();
    let mut bytes = [0u8; phase::BYTES];
    kernel::uaccess::UserSlice::new(argument, bytes.len())
        .reader()
        .read_slice(&mut bytes)?;
    let request = phase::Request::read(&bytes)
        .map_err(|error| kernel::error::to_result(error).unwrap_err())?;
    let _permit = phase::permit().map_err(|error| kernel::error::to_result(error).unwrap_err())?;
    request
        .validate()
        .map_err(|error| kernel::error::to_result(error).unwrap_err())?;
    let published = PUBLISHED.load(Ordering::Acquire);
    if published.is_null() {
        return Err(ENODEV);
    }
    let started = {
        // SAFETY: The active miscdevice file pins this module/context. Acquire
        // actual stored identity; never manufacture OsToken from user scalars.
        let context = unsafe { &*published }.lock();
        let image = context
            .images
            .get(request.os as usize)
            .and_then(Option::as_ref)
            .ok_or(EINVAL)?;
        if image.owner.slot() != request.os || image.owner.generation() != request.generation {
            return Err(kernel::error::to_result(-116).unwrap_err());
        }
        let boot = image.boot.as_ref().ok_or(EINVAL)?;
        if !boot.started {
            return Err(EBUSY);
        }
        boot.prepared.continuing.as_ref().ok_or(EBUSY)?.clone()
    };
    // No context/CPU/transport/slots/pager/ledger guard remains. Started owns
    // the actual runtime while this bounded call observes it, including failure.
    if request.phase == phase::SELECT_BLOCKED {
        let key = started.verification_select_read16(Some(request.pid))?;
        if key.os != request.os || key.generation != request.generation {
            return Err(EIO);
        }
        request.bind();
    }
    // From this point the operation is dispatched and cannot be retried.
    // Consume before a release can commit, even if copyout later fails.
    request.consume();
    let result = started.verification_phase_command(&request);
    let code = result.as_ref().err().map_or(0, |error| error.to_errno());
    phase::output(&mut bytes, result.as_ref().copied().unwrap_or(0), code, begin);
    drop(_permit);
    // Copyout is outside every production guard. Its failure never retries or
    // rolls back an already emitted snapshot or an immutable selection.
    kernel::uaccess::UserSlice::new(argument, bytes.len())
        .writer()
        .write_slice(&bytes)?;
    result.map(|_| 0)
}
