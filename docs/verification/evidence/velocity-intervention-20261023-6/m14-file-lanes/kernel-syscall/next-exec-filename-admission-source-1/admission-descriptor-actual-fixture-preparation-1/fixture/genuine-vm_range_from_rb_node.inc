#[inline(always)]
unsafe fn vm_range_from_rb_node(node: *mut RbNode) -> *mut VmRange {
    node.cast::<VmRange>()
}
