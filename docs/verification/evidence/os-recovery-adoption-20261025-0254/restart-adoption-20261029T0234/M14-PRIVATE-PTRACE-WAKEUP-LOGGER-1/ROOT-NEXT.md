Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The requested exact port is blocked at source-contract scope; no Rust replacement
or patch is generated. Original callback and Rust entry fragments are retained
with exact canonical source hashes. Callback is void(int,int,int), event4 only;
format is ptrace_wakeup_sig,pid=%d,data=%08x followed by newline. Argument order
is value/result, both int. Rust calls it with pid/data-as-CInt before negative
signal-data validation. Example data=-1 reaches signed result=-1 at that call.

Both retained C formatter paths consume the%x argument as unsigned int. Signed
negative int and unsigned-int consumption are not the same defined vararg domain.
We cannot choose result-as-u32 or claim a signed-vararg parity oracle without an
explicit functional contract decision. No cast, format change, narrowed input,
ignored negative vector or expected-output rewrite was introduced.

Separately, original logger uses dkprintf, which emits static __verbose metadata
and checks its flags. A direct ungated kprintf leaf would change normal behavior
and risk original389 descriptor identities. A later exact candidate must preserve
that existing identity/gating rather than add an invented descriptor or rewrite
the oracle. No descriptor, export/API, ptrace body or canonical source changed.

Settid source packet remains independent and unchanged. No settid patch is copied
here. Later Root composition must merge/rebase small sibling-module and CMake
source-dependency insertions rather than overwrite shared full postimages. Ptrace
candidate remains unimplemented pending the precise signed-hex/domain and original
descriptor ownership decision, then compiler/link/behavior/native evidence.
Weekly-only100%stop/reset1793774133 upperbound; M15 paused. No live handle or work.
