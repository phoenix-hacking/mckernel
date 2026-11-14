pub unsafe extern "C" fn zeroobj_create(objp: *mut *mut Memobj) -> CInt {
    if objp.is_null() {
        return -EINVAL;
    }

    if THE_ZEROOBJ.is_null() {
        let error = alloc_zeroobj();
        if error != 0 {
            return error;
        }
    }

    let obj = &raw mut (*THE_ZEROOBJ).memobj;
    *objp = obj;
    memobj_ref(obj);
    0
}
