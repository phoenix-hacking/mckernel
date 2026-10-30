# Current owned install metadata diagnostic review

Functional McKernel OS/apps and Rust/assembly migration only; no security
testing. The companion JSON is a conditional review for exactly the frozen
metadata source and profile, not evidence of execution or physical retirement.

The source targets only the three specified PID/birth/UID/parent identities,
reads proc identity, children, task, wchan and selected FD/fdinfo metadata,
and lstats the two exact nonce paths. It redacts unlisted FD target names and
does not read environment, credentials, process memory or file contents. PID
identity is rechecked after observation; the specified root Python must have no
children at its check. Missing or changing data fails the observation and
cannot establish absence or release. This is a point-in-time diagnostic.

The profile runs sudo -A, CPU6, 64 MiB address-space, five CPU seconds, 128 FDs,
one MiB output-file limit and GNU timeout 10 seconds plus two seconds escalation.
The exact profile literal matches the reviewed source. Timeout signals only its
own new process group under the reviewed tool model; no existing operation
process is signaled by the diagnostic source.

Before execution Root must recheck actual controls/usage, target identities and
empty root-child tree and confirm the existing operation reservation still has
room for the timeout and diagnostic Python as the two temporary operation jobs.
The sudo frontend/monitor and other host-control overhead must fit the existing
reserved share; the 64 MiB is charged inside the same four-GiB operation
reservation. Preserve the native four jobs, 12 GiB native, V2 UNKNOWN 2 GiB,
scratch21, mutex27:4, original UNKNOWN custody, nonce and captures. Root owns
the exclusive output and positive diagnostic join. Any unexpected process,
failed observation, timeout or uncertain join stays UNKNOWN; no retry or
cleanup is implied.
