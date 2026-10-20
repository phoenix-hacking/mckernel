use crate::abi::CULong;
#[repr(C)]
#[derive(Clone, Copy)]
pub struct RbNode {
    pub(crate) __rb_parent_color: CULong,
    pub(crate) rb_right: *mut RbNode,
    pub(crate) rb_left: *mut RbNode,
}

#[repr(C)]
pub struct RbRoot {
    pub(crate) rb_node: *mut RbNode,
}

