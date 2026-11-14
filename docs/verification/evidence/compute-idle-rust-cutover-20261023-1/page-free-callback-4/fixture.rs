use core::ffi::c_void;
type CInt=i32;
unsafe extern "C" { fn _ihk_mc_free_pages(ptr:*mut c_void,npages:CInt,is_user:CInt,file:*mut i8,line:CInt); static x86_clear_free_pages_user_file:[i8;1]; static x86_clear_free_pages_user_line:CInt; static x86_clear_free_pages_user_flag:CInt; }
include!("actual-rust-callback.rs.inc");
