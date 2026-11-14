// HOST-only address observation/control; no production reference or kind decision.
pub(super) unsafe fn host_register_event_state(process:*mut crate::abi::Process,fd:crate::abi::CInt){
 let p=unsafe{core::ptr::addr_of_mut!((*process).mckfd_lock)};
 let flags=unsafe{super::syscall_mckfd_lock_bridge(p.cast())};
 let mut row=unsafe{(*process).mckfd.cast::<crate::abi::Mckfd>()};
 while !row.is_null()&&unsafe{(*row).fd!=fd}{row=unsafe{(*row).next};}
 assert!(!row.is_null());
 let pin=unsafe{descriptors::pin_managed_locked(process,row)};
 unsafe{super::syscall_mckfd_unlock_bridge(p.cast(),flags)};
 let pin=pin.expect("actual managed pin lookup").expect("real managed descriptor");
 let event=pin.event().expect("actual event edge");
 crate::host_effects::register_lock(event.host_state_lock_address(),crate::host_effects::LockClass::State);
 drop(event);drop(pin);
}
