from pathlib import Path
import hashlib
source = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-REMAINING23-C-1/postimage/kernel/rust')
policy = (source / 'syscall_policy.rs').read_text()
start = policy.index('unsafe extern "C" fn f06_ptrace_report_signal_kill(')
brace = policy.index('{', start)
depth = 1
i = brace + 1
while depth:
    if policy[i] == '{': depth += 1
    elif policy[i] == '}': depth -= 1
    i += 1
adapter = policy[start:i]
bridge = (source / 'syscall_ptrace_detach_kill.rs').read_bytes()
Path('bridge.rs').write_bytes(bridge)
Path('adapter.rs').write_text(adapter + '\n')
for p in (source / 'syscall_policy.rs', source / 'syscall_ptrace_detach_kill.rs', Path('bridge.rs'), Path('adapter.rs')):
    print(hashlib.sha256(p.read_bytes()).hexdigest(), p)
