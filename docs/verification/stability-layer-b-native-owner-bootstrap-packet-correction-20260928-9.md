# Layer-B native-owner bootstrap packet correction 9

Status: \`DRAFT_PENDING_INDEPENDENT_REVIEW\`. This additive correction preserves
packet 8 and addresses its \`FAIL_BOOTSTRAP_PACKET\` review. The dispatcher must
bind the exact failure record
\`docs/verification/stability-layer-b-native-owner-bootstrap-packet-review-failure-20260928-8.json\`
(and its recorded SHA256) before review; absence or mismatch is a stop condition.
Packet 8 remains immutable and is bound here by SHA256
\`3f8f363fe5e7086b027e7814ce98c7b715f3978981ff1e71b2234f0108bf0ec9\`.
This correction does not release compilation, owner execution, tests,
native/guest execution, or any production/language gate.

## Six corrected findings and fixed scope

1. \`-D_GNU_SOURCE\` is removed from every command. The source's own
definition remains the only feature selection.
2. The service command starts with \`/usr/bin/env -i\` and an explicit,
finite allowlist. No inherited credential, locale, loader, compiler-path,
include-path, or shell variable is available. \`--working-directory\` is
explicit.
3. \`RemainAfterExit=yes\` retains an exited unit long enough to capture
\`LoadState\`, \`ActiveState\`, \`SubState\`, \`Result\`, \`ExecMainCode\`,
\`ExecMainStatus\`, \`InvocationID\`, \`ControlGroup\`, and timestamps. Only
after capture does the dispatcher stop, reset-failed, and reconcile cleanup.
4. Every submission/show/stop/kill operation is wrapped in an absolute
\`/usr/bin/timeout\` deadline. The deadline starts before submission. An
uncertain submission is reconciled against the same unique unit and is never
re-submitted.
5. Artifact inspection is static \`readelf\`/\`objdump\` only. The prior
\`ldd\` and \`LD_TRACE_LOADED_OBJECTS\` commands are removed.
6. The compile produces a finite, checked consumed-input manifest. \`-MD/-MF\`
records source and system headers, \`-Wl,-Map\` records startup/support/libc/
pthread/linker inputs, and \`-v\` records the actual search/driver paths.
The dispatcher resolves each manifest path, records mode/owner/size/SHA256,
and fails on missing, unexpected, duplicate, outside-allowlist, or changed
inputs.

The corrected fresh output root is
\`/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-9\`;
it must be absent before admission. Packet 8's root
\`...stability-layer-b-native-owner-bootstrap-20260928-8\` is retained as
failure evidence and is never reused or overwritten.

## Exact service-side environment and compile command

After independent \`PASS_BOOTSTRAP_PACKET_CORRECTION\`, create mode-0700
\`home\`, \`tmp\`, and \`logs\` below the correction root and run exactly this
unit payload. Paths are absolute; the service-side environment is installed
inside the unit, not inherited from the dispatcher:

\`\`\`text
/usr/bin/env -i LC_ALL=C LANG=C HOME=/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-9/home TMPDIR=/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-9/tmp PATH=/usr/bin:/bin /usr/bin/prlimit --core=0 --cpu=55 --nofile=256:256 --fsize=67108864:67108864 --as=536870912:536870912 -- /usr/bin/gcc -std=c11 -O2 -Wall -Wextra -Werror -fno-pie -no-pie -pthread -MD -MF /home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-9/layer_b_native_owner_v1.d -Wl,-Map,/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-9/layer_b_native_owner_v1.map /home/holden/mckernel/scripts/tests/layer_b_native_owner_v1.c -o /home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-9/layer_b_native_owner_v1
\`\`\`

There is no shell, response file, source discovery, make/configure, import,
test, second translation unit, root, container, mount, network, sudo,
credential, or owner execution. The unit command must be submitted as:

\`\`\`text
/usr/bin/timeout --signal=TERM --kill-after=1s 10s /usr/bin/systemd-run --user --unit=layer-b-native-owner-bootstrap-20260928-9-<UTCNONCE> --service-type=exec --working-directory=/home/holden/mckernel --property=RemainAfterExit=yes --property=KillMode=control-group --property=RuntimeMaxSec=60s --property=TimeoutStopSec=5s --property=SendSIGKILL=yes --property=StandardOutput=file:/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-9/logs/unit.stdout --property=StandardError=file:/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-9/logs/unit.stderr -- /usr/bin/env -i LC_ALL=C LANG=C HOME=/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-9/home TMPDIR=/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-9/tmp PATH=/usr/bin:/bin /usr/bin/prlimit --core=0 --cpu=55 --nofile=256:256 --fsize=67108864:67108864 --as=536870912:536870912 -- /usr/bin/gcc -std=c11 -O2 -Wall -Wextra -Werror -fno-pie -no-pie -pthread -MD -MF /home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-9/layer_b_native_owner_v1.d -Wl,-Map,/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-9/layer_b_native_owner_v1.map /home/holden/mckernel/scripts/tests/layer_b_native_owner_v1.c -o /home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-9/layer_b_native_owner_v1
\`\`\`

The nonce is generated once, recorded, validated as
\`[A-Za-z0-9-]+\`, and never reused. The unit is only a process owner and
lifecycle boundary. The host is systemd 245.4 with a hybrid hierarchy;
\`MemoryMax\`, \`TasksMax\`, \`IPAddressDeny\`, and other aggregate cgroup
properties are not claimed or used as enforcement.

## Submission, observation, and cleanup protocol

Set the overall deadline before the first \`systemd-run\` byte is written.
Wrap each operation below with a fresh absolute timeout no longer than the
remaining deadline:

- submit the exact command above, using the unique unit name;
- poll \`/usr/bin/timeout 5s /usr/bin/systemctl --user show UNIT
  -p LoadState -p ActiveState -p SubState -p Result -p ExecMainCode
  -p ExecMainStatus -p InvocationID -p ControlGroup -p MainPID
  -p ExecMainStartTimestamp -p ExecMainExitTimestamp\`;
- if the overall deadline expires while active, run
  \`/usr/bin/timeout 10s /usr/bin/systemctl --user stop UNIT\`, then, only if
  still active, \`/usr/bin/timeout 10s /usr/bin/systemctl --user --signal=SIGKILL --kill-who=all kill UNIT\`;
- after the unit is inactive/exited and all fields are captured, run
  \`/usr/bin/timeout 10s /usr/bin/systemctl --user reset-failed UNIT\`.

The show protocol accepts only a matching unit name and records every response.
On timeout, submission error, lost response, or ambiguous result, reconcile
the same unit with \`show\`; do not submit another unit. Capture
\`journalctl --user -u UNIT --no-pager -o cat\`, all command statuses, and
raw stdout/stderr. Before terminal classification require
\`ActiveState=inactive\`, no process in the recorded \`ControlGroup\`, and no
matching unit/process identity. Preserve the unit and root on any ambiguity.

## Finite consumed-input manifest

The source hash must remain
\`2c157335e88b2088c56fc40fd6c0d966dc653ea68b4726e51feb1d4b4e62eafc\` and
the static-test hash must remain
\`427f6133497ce0706fce39d9e52051542821bc6deab29d27322733c927efd63d\`.
Before admission, record the pinned GCC/cc1/collect2/as/ld, GCC include
directory, architecture and \`/usr/include\` headers, start files, libc,
pthread and linker inputs. During the compile, parse only the generated
\`layer_b_native_owner_v1.d\`, linker map, and \`-v\` stream. Normalize paths,
deduplicate them, reject paths outside the reviewed system-input roots or the
exact source/output roots, and write a sorted manifest with path, type, mode,
owner, size, and SHA256. The required classes are:

- the exact source and all actually consumed \`/usr/include\` and architecture
  headers;
- GCC \`cc1\`, \`collect2\`, built-in headers, assembler, linker, startup and
  support objects;
- actual libc/pthread and linker-script inputs shown by the map/driver output.

Missing dependency reports, unresolved paths, changed hashes, unexpected
classes, or a manifest that cannot be reproduced from these command outputs
is a first failure. No alternate library or compiler search path may be
silently accepted. A failed compile retains all partial reports and output.

## Static artifact inspection and evidence

Only after successful compile status, inspect without invoking the artifact:

\`\`\`text
/usr/bin/readelf -h -l -S -d -n /home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-9/layer_b_native_owner_v1
/usr/bin/objdump -p /home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-9/layer_b_native_owner_v1
\`\`\`

Do not execute the output, pass it to a shell, invoke \`ldd\`, use
\`LD_TRACE_LOADED_OBJECTS\`, or run any owner test. Capture hashes, ELF output,
dependency manifest, unit identity/status, environment evidence, limits,
timestamps, free space, repository pre/post status, complete tree manifest,
and zero residual process observations. On the first failure, write
\`failure.json\`, preserve the root and all logs, archive without deletion, and
do not retry. This packet remains review-only and grants no acceptance credit.

