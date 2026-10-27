Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Qualify the accepted strict235 result at F05 verify/from-user/to-user scope only.
The matching cohort is image2ed7ef68, SMP887dc356 and mcctrl57546af5. Independent
case/postjoin reviewa4620f18 accepts exact235B stdout/exit0, genuine caller join
and all30 owner commands reaped. Nonce2005b0dd is consumed; no replay.

The already-established routes now have a real accepted native consumer:

- Successful exec copies argv/envp through flatten_strings_from_user,
  getlong_user/copy_from_user and strlen_user/strcpy_from_user, reaching F05
  verify_process_vm through x86_user_verify_bridge.
- Native wait4 copies child status through syscall_copy_to_user_bridge and F05
  copy_to_user; the frozen payload checks child exits37/42 and subsequent ECHILD.

Preserve the actual parentACK: PID256/token3/errno0/abandoned1 is accepted by the
frozen close path. Do not replace it with abandoned0 or infer unobserved child
retirement-zero records.

Full M14-05-05 and F05 whole-file closure remain OPEN. Direct read_process_vm,
write_process_vm, patch_process_vm and partial-fault/fixup behavior are not proved
by this case. There is no already-supported frozen consumer for those uncovered
branches established in the retained F05 worklist, application catalog or known
core/235 runner bindings. Ptrace peek/poke production routes reach read/patch,
but a production route alone is not a frozen payload/oracle/native-runner binding.

This is an exact runtime-consumer/evidence gap under the existing obligation,
not another qualification quota. Root can record the newly qualified native
scope while retaining full-subgoal/file flags open. No runtime, grant, canonical
worklist, Git, port, framework or oracle change was made.
