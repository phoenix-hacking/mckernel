Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

BODY12 ports actual CURRENT116 selected64-byte
`syscall_util_register_desc_log_bridge`. The original callback takes an int TID
and unsigned-long descriptor address; it performs no CPU/thread lookup. The
existing Rust caller still owns that lookup and registration operation. This
port preserves only the exact formatter, independent any-nonzero8-bit debug
gate, scalar varargs and ignored logger result, with no lookup, descriptor
dereference, registration mutation, lock or new error/resource behavior.

The new Rust module reuses the exact existing Ddebug ABI and accepted raw flag
read idiom. It exports the original global callback name, preserving the existing
Rust foreign declaration/caller unchanged. The original C body remains verbatim
in the opposite selector branch. Its one debug record remains one C data record
with identical source function/logical line/null fmt/default flags, and the
successor logical source line is restored. All earlier BODY/cumulative packets
remain frozen; Root alone integrates canonical/shared source and accepts artifacts.

The HOST fixture uses the actual original C function and genuine debug macro.
A test-only C assembly link-name declaration routes the oracle symbol away from
the Rust export while keeping its C identifier/body/__func__ unchanged. No machine
instruction assembly or production C callback is added. The two genuine records
must match exact lexical metadata. ABI10 checks C Ddebug layout/int/unsigned-long/
callback widths and record count against reused Rust. The200 C/Rust pairs use
flags0/1/2/128/255, five signed-int TID boundaries and eight unsigned-long address
boundaries. An independent exact format/function-text/argument/count oracle and
both full-record snapshots must agree. All descriptor values remain scalar;
no address is dereferenced. All printing is mocked, with one final HOST result
line only. No actual registration/thread lookup/syscall/MM/IKC/hardware/lock runs.

The actual parent BODY12 followup authorizes ordinary HOST checks under existing
standing/aggregate limits. The worker-owned record honestly carries that authority
and inherited <=4-command/one-obvious-fixture-correction bound. CPU6/jobs1/AS2GiB/
CPU60s/wall90s, actual reviewed guardian/account/tightcap checks and exact saved
source/header/tool bindings apply before every command. The reused runner
retains full argv/raw streams/status/PID birth/positive wait4/group/stream closure/
CPU/wall/RSS evidence. Semantic or second failure stops. No actual Root, Docker,
native, guest, locks, network, subagents, shared writes or new framework are
introduced. Prior evidence/dirty work/exclusions/scratch21/permanent27:4 and the
same06:00Z/credit/control identity remain preserved. Source/HOST supplies no new
default/native/file closure, and actual linked registry389 proof remains open.
