struct InheritedRoot {root:u64,start:u64,end:u64,uid:u32,gid:u32,control_cpu:i32,nonce:u64}
enum ForkResponseLocation {Ticket,Mailbox,MailboxQuarantined}
pub(crate) struct PreparedForkIngress {
    remote: core::mem::ManuallyDrop<Arc<Remote>>,
    child_task: core::mem::ManuallyDrop<ChildTaskMm>,
    response: core::mem::ManuallyDrop<super::smp_application_syscall::ForkResponse<SyscallResponse>>,
    parent: Token,
    child: Token,
    finished: bool,
    response_location:ForkResponseLocation,
    sealed:AtomicBool,
    carrier_nonce:u64,
    first_return_written:bool,
    first_return_committed:bool,
    first_return_published:bool,
    lease:core::mem::ManuallyDrop<Option<BackendForkLeaseV4>>,
    host_revoke:Option<current_fork_control::OwnedRevoke>,
}
struct BackendForkLeaseV4 {owner:*mut core::ffi::c_void,release:super::application_abi::ForkLeaseReleaseV4}
impl Drop for BackendForkLeaseV4 {fn drop(&mut self){unsafe {(self.release)(self.owner)};}}