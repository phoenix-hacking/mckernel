#[repr(C)]
pub struct RbNode {
    pub(crate) __rb_parent_color: CULong,
    pub(crate) rb_right: *mut RbNode,
    pub(crate) rb_left: *mut RbNode,
}
