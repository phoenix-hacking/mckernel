// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Contract-only private source proposal, never selected by this file.
#[cfg(f03_execveat_arity_proposal)]
mod f03_execveat_arity_proposal {
    use core::ffi::c_void;
    use core::ptr::{addr_of_mut, write};
    use crate::abi::{CInt, CLong, CULong, SyscallRequest};

    // Values are explicit protocol-owner decisions. This object does not choose
    // or imply zero, successful completion, ownership transfer or an ACK.
    #[repr(C)]
    pub struct ExecPhase1TransportSeed {
        pub rtid: CInt,
        pub ttid: CInt,
        pub valid: CULong,
        pub unused_arg5: CULong,
    }

    /// # Safety
    /// `out` points to exclusive writable aligned request storage. The protocol
    /// owner must approve all supplied transport seed values and exec_nr for
    /// the selected endpoint. filename/descriptor remain live for transport.
    /// Exact defined semantic arity is five: phase, dirfd, filename, pa, flags.
    #[no_mangle]
    pub unsafe extern "C" fn f03_execveat_phase1_declared_v1(
        out: *mut SyscallRequest, exec_nr: CULong, dirfd: CInt,
        filename: *const c_void, descriptor_pa: CULong, flags: CInt,
        seed: ExecPhase1TransportSeed,
    ) {
        write(out, SyscallRequest {
            rtid: seed.rtid, ttid: seed.ttid, valid: seed.valid, number: exec_nr,
            args: [1, dirfd as CLong as CULong, filename as CULong,
                   descriptor_pa, flags as CLong as CULong, seed.unused_arg5],
        });
    }

    /// # Safety
    /// `request` is the same live initialized request after phase one completed;
    /// it is exclusively mutable and no transport or host reader still borrows
    /// it. Phase one and transport have not invalidated or altered args3/4/5.
    /// Exact defined semantic arity is three: phase, descriptor pa, length.
    /// The owner must establish those premises; this function proves no ACK.
    #[no_mangle]
    pub unsafe extern "C" fn f03_execveat_phase2_declared_v1(
        request: *mut SyscallRequest, exec_nr: CULong,
        descriptor_pa: CULong, descriptor_bytes: CULong,
    ) {
        write(addr_of_mut!((*request).number), exec_nr);
        write(addr_of_mut!((*request).args[0]), 2);
        write(addr_of_mut!((*request).args[1]), descriptor_pa);
        write(addr_of_mut!((*request).args[2]), descriptor_bytes);
    }
    #[no_mangle]
    #[used]
    pub static f03_exec_request_arity_Rust_ABI_v1: [CULong; 13] = [
        core::mem::size_of::<SyscallRequest>() as CULong,
        core::mem::align_of::<SyscallRequest>() as CULong,
        core::mem::offset_of!(SyscallRequest, rtid) as CULong,
        core::mem::offset_of!(SyscallRequest, ttid) as CULong,
        core::mem::offset_of!(SyscallRequest, valid) as CULong,
        core::mem::offset_of!(SyscallRequest, number) as CULong,
        core::mem::offset_of!(SyscallRequest, args) as CULong,
        core::mem::size_of::<ExecPhase1TransportSeed>() as CULong,
        core::mem::align_of::<ExecPhase1TransportSeed>() as CULong,
        core::mem::offset_of!(ExecPhase1TransportSeed, rtid) as CULong,
        core::mem::offset_of!(ExecPhase1TransportSeed, ttid) as CULong,
        core::mem::offset_of!(ExecPhase1TransportSeed, valid) as CULong,
        core::mem::offset_of!(ExecPhase1TransportSeed, unused_arg5) as CULong,
    ];

}
