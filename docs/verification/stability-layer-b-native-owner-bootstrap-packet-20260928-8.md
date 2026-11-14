# Layer-B native-owner bootstrap packet 8

Status: \`DRAFT_PENDING_INDEPENDENT_REVIEW\`. This packet is a conditional,
compiler-only admission description. It does not release compilation, owner
execution, tests, native/guest execution, or any production/language gate.
The source review permitting preparation is
\`docs/verification/stability-layer-b-native-owner-source-review-20260928-7.json\`.
That review binds source SHA256
\`2c157335e88b2088c56fc40fd6c0d966dc653ea68b4726e51feb1d4b4e62eafc\` and
static-test SHA256
\`427f6133497ce0706fce39d9e52051542821bc6deab29d27322733c927efd63d\`.

## Scope and immutable inputs

The sole source input is
\`/home/holden/mckernel/scripts/tests/layer_b_native_owner_v1.c\`. The only
permitted output is the fresh, disposable, absolute root
\`/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-8\`.
The dispatcher must verify that this root does not exist, that its parent
exists, that the source hash still equals the value above, and that repository
status is recorded before creating it. A hash mismatch, existing root, changed
source, or unexpected repository change is a first failure: retain diagnostics
and stop. No source, test, packet, released catalog, or production file may
be edited.

The candidate is a native x86-64 LP64 translation unit. The exact future
compiler command, executed only after an independent \`PASS_BOOTSTRAP_PACKET\`,
is the following direct source/output invocation (the \`prlimit\` wrapper only
sets inherited per-process limits):

\`\`\`text
/usr/bin/prlimit --core=0 --cpu=55 --nofile=256:256 --fsize=67108864:67108864 --as=536870912:536870912 -- /usr/bin/gcc -std=c11 -D_GNU_SOURCE -O2 -Wall -Wextra -Werror -fno-pie -no-pie -pthread /home/holden/mckernel/scripts/tests/layer_b_native_owner_v1.c -o /home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-8/layer_b_native_owner_v1
\`\`\`

There is no shell interpolation, source discovery, response file, \`make\`,
\`configure\`, compiler test, link test, import, or second translation unit.
The output is an unexecuted artifact. \`--cpu=55\` is a per-process CPU limit;
wall-clock enforcement is supplied by the unit and an independent observation
deadline below. These are per-process bounds, not aggregate campaign caps.

## Pinned host toolchain and environment

The dispatcher records SHA256, mode, owner, size, and resolved path for every
item below before admission. These are read-only observations, not permission
to substitute a different tool:

| role | exact path | observed SHA256 |
|---|---|---|
| compiler driver | \`/usr/bin/gcc\` (resolves to \`x86_64-linux-gnu-gcc-9\`) | \`6cb2d84ccd9fd3485d4e47ba032e626be65692601c38fad46866a6b565f3100f\` |
| cc1 | \`/usr/lib/gcc/x86_64-linux-gnu/9/cc1\` | \`c09275e2d3f811e23d255eac415bfedd9e68ba8b5cf4b261d2fce136b5e8fc99\` |
| collect2 | \`/usr/lib/gcc/x86_64-linux-gnu/9/collect2\` | \`5228dbf1e15d16694059023d16e7f13f201ea0d76a82e8837c6483dc21d66682\` |
| assembler | \`/usr/bin/as\` | \`8d45684bbd6420e3e97907257c510f199bb6c5f9b02ea8ee0a590c1a8b662ead\` |
| linker | \`/usr/bin/ld\` | \`476b24d5cc1fef54f80412d06e7430b2dcf4e2b6f1525ee17e6eaaf16b28a00f\` |
| compiler headers | \`/usr/lib/gcc/x86_64-linux-gnu/9/include\` | record complete manifest at run time |
| start files | \`/usr/lib/x86_64-linux-gnu/{crt1.o,crti.o,crtn.o}\` | record each hash at run time |
| libc linker script | \`/usr/lib/x86_64-linux-gnu/libc.so\` | \`641105852be34f26444a269e7e78000c625eec5a6384112a6ab294e6dd64ab92\` |
| system libc | \`/lib/x86_64-linux-gnu/libc.so.6\` | record hash at run time |

Expected packages are GCC \`9.4.0-1ubuntu1~20.04.2\`, binutils
\`2.34-6ubuntu1.11\`, and libc6/libc6-dev \`2.31-0ubuntu9.18\`; versions and
resolved paths are captured rather than trusted from package metadata. The
execution environment is exactly \`LC_ALL=C\`, \`LANG=C\`,
\`HOME=<root>/home\`, \`TMPDIR=<root>/tmp\`, \`PATH=/usr/bin:/bin\`,
\`GCC_EXEC_PREFIX\` unset, \`COMPILER_PATH\` unset, \`LIBRARY_PATH\` unset,
\`C_INCLUDE_PATH\` unset, \`CPLUS_INCLUDE_PATH\` unset, \`CPATH\` unset, and
\`MAKEFLAGS\` unset. Create private mode-0700 \`home\`, \`tmp\`, and \`logs\`
under the output root; no network, credentials, user shell startup, container,
mount, sudo, or root operation is allowed.

## Transient systemd owner and lifecycle

Host facts are systemd \`245.4\`, user manager active, and hybrid cgroup mode.
The transient user unit is only a process owner and lifecycle boundary; it is
**not** evidence that \`MemoryMax\`, \`TasksMax\`, \`IPAddressDeny\`, or any
other aggregate cgroup limit is enforced. Do not add those properties or claim
their enforcement. The unit name is unique, includes this packet id and a
fresh UTC nonce, and must never be reused:

\`\`\`text
/usr/bin/systemd-run --user --unit=layer-b-native-owner-bootstrap-20260928-8-<UTCNONCE> --service-type=exec --property=KillMode=control-group --property=RuntimeMaxSec=60s --property=TimeoutStopSec=5s --property=SendSIGKILL=yes --property=StandardOutput=file:/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-8/logs/unit.stdout --property=StandardError=file:/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-8/logs/unit.stderr -- /usr/bin/prlimit --core=0 --cpu=55 --nofile=256:256 --fsize=67108864:67108864 --as=536870912:536870912 -- /usr/bin/gcc -std=c11 -D_GNU_SOURCE -O2 -Wall -Wextra -Werror -fno-pie -no-pie -pthread /home/holden/mckernel/scripts/tests/layer_b_native_owner_v1.c -o /home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-8/layer_b_native_owner_v1
\`\`\`

\`<UTCNONCE>\` is generated once from the dispatcher's cryptographic nonce
source, validated as \`[A-Za-z0-9-]+\`, and recorded before start. Do not use
\`--wait\`, \`--pty\`, \`--shell\`, \`--collect\`, or a shell command.
Immediately after the start response, poll \`systemctl --user show <unit>\` and
retain \`InvocationID\`, \`ControlGroup\`, \`MainPID\`, \`ActiveState\`,
\`SubState\`, \`ExecMainCode\`, \`ExecMainStatus\`,
\`ExecMainStartTimestamp\`, and \`ExecMainExitTimestamp\` in a timestamped log.
Poll at most 50 ms per observation until inactive or 60 seconds. On timeout,
issue \`systemctl --user stop <unit>\`, wait no more than five seconds, then
\`systemctl --user kill <unit> KILL\` if still active, and reconcile exact unit
state and process identities. Never kill by numeric PID outside the unit.

Store the start command, all \`show\` output, stop/kill output, unit journal
(\`journalctl --user -u <unit> --no-pager -o cat\`), and final status under
\`logs\`. The unit must be inactive, its control-group process listing empty,
and its start request status reconciled before terminal classification. Any
ambiguity, inaccessible user manager, residual process, or unexpected unit
transition is a failure; preserve the root and do not retry.

## Artifact inspection and evidence

After successful compile status only, and without invoking the artifact, capture
its SHA256, mode, size, and complete output-tree manifest. Inspect the ELF using
only non-executing tools:

\`\`\`text
/usr/bin/readelf -h -l -S -d -n <root>/layer_b_native_owner_v1
/usr/bin/objdump -p <root>/layer_b_native_owner_v1
env LD_TRACE_LOADED_OBJECTS=1 /usr/bin/ldd <root>/layer_b_native_owner_v1
\`\`\`

The last command requests loader dependency tracing only; never run the output as
a program, pass it to a shell, use \`system()\`, or perform an owner test.
Record stdout, stderr, exit status, tool hashes, and the explicit fact that no
application entry point was executed. Retain \`readelf\`/\`objdump\` output even
if dependency inspection fails. No result from this packet is application,
production, language, or whole-OS acceptance evidence.

## First-failure and cleanup contract

Capture dispatcher pre/post repository status, free space, exact argv, env
allowlist/unset list, source/tool/input hashes, unit identity, all raw streams,
limits, timestamps, status, process/control-group observations, and complete
output manifest. On the first unexpected failure, stop the affected lane, write
\`failure.json\` without deleting output, archive the root losslessly, and
preserve all unit identities and logs. Do not retry or overwrite a unit.
After terminal reconciliation, remove only the unit (never source or evidence)
and verify no matching process or unit remains. A later reviewer, not this
packet, decides whether any follow-up is permitted.

This packet is ready for independent review only. It intentionally makes no
compilation or execution claim.

