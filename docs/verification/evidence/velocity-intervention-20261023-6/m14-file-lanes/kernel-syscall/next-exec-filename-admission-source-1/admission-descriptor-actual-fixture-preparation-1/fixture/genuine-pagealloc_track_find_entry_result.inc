#[no_mangle]
pub unsafe extern "C" fn pagealloc_track_find_entry_result(
    file: *mut i8,
    line: CInt,
    track_hash: *mut AbiListHead,
) -> *mut PageallocTrackEntry {
    if file.is_null() || track_hash.is_null() {
        return null_mut();
    }

    let hash = pagealloc_track_hash(file, line);
    let head = track_hash.add(hash as usize);
    let mut node = (*head).next;

    while node != head {
        let entry = pagealloc_track_entry_from_hash(node);
        if (*entry).line == line && strcmp((*entry).file, file) == 0 {
            return entry;
        }
        node = (*node).next;
    }

    null_mut()
}
