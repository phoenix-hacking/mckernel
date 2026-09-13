# Application backend integration map

This is a source-only integration map for the first three reviewed startup
fixtures. It changes no runtime release, original catalog, packet or report.
The companion JSON freezes the sources read for this map. No application,
compiler, test, container or guest was executed by this review. The broader
stability, native production, Rust/assembly and qualification roadmap remains
in `stability-run-20260913.md`.

## Existing interfaces

| Component | Reusable interface | Limit on its conclusion |
| --- | --- | --- |
| Planned CLI, `scripts/application-tests/README.md:146` | `run.py --inputs ABS_BUNDLE --case CASE --attempt ABS_FRESH --profile baseline-root-1cpu --mode differential-guest` | `run.py` does not exist at this review. The README command is a future interface. |
| `runtime_contracts.py:183` | `load_runtime_bundle(path)` | Verifies strict JSON, frozen artifact identities and schema. Reload immediately before every attempt. It does not authorize execution or semantically evaluate compiler/capability proof. |
| `runtime_contracts.py:352` | `validate_case(bundle, case_id)` | Metadata PASS, FAIL or BLOCKED only; derives unchanged global/case prerequisites. Missing/blocked/unsupported capabilities, disabled review or unsupported predicates block. Nonempty `depends_on` blocks until a dependency acceptance evaluator exists. |
| `runtime_contracts.py:383` | `evaluate_case(bundle, case_id, collection_report, evidence=None)` | Independent exact-byte/JSON and raw-wait oracle only. The reserved `evidence` argument is discarded. Every result has `application_acceptance: false`. |
| `supervisor.py:174` | `run_supervised(argv, *, cwd, env, attempt_dir, timeout_seconds, cleanup_timeout_seconds, stdout_limit_bytes, stderr_limit_bytes, stdin_path=None, executable_path=None)` | Collects a Linux process and its owned descendants. It has no QEMU, native application or capability authority. COMPLETED includes ordinary nonzero exit and signal death. |
| `compile_reviewed.py:154` | Retained reviewed source, ELF, object, disassembly, emitted dependency/link map and interpreter/DSO captures | The dated packet001 compilation record proves only these exact compile outputs. It reports runtime and acceptance NOT_RUN. |
| `verification_state.py:157` and `:252` | `compile_capture(...)`, `reviewed_compilations(...)` | Existing bounded archive/dependency/ELF review logic is a useful source for a future build-evidence adapter. Its ledger result is not an execution permit. |

The supervisor preserves literal argv independently of executable path, reads
stdin from a bound regular file or `/dev/null`, closes extra descriptors, drains
both pipes, records actual raw wait status, and independently checks observed
completion against a deadline beginning before `Popen`. Its caller supplies
the container/guest resource boundaries and outer QEMU watchdog. It records the
inherited uid/gid/groups/umask; it does not set a requested identity profile.

The accepted baseline root inspected here contains no Python path. Reusing the
Python supervisor inside that guest requires a separately bound interpreter and
complete library closure, or a separately reviewed native collector with an
honest compatible evidence format. Running this Python utility in the build
container cannot supply the pinned-Linux guest reference. The existing fault
controller is specific to readiness/read16/RET injection; its frozen payload
and protocol must not be repurposed into a generic application backend.

## Packet 001 conversion

`reviewed/packet-001-v3/review.json` is an immutable fixture-review-and-compile
packet with `execution_enabled: false`, not the runtime `execution-packet`
schema. Its original pending fields remain historical. The additive independent
review and compilation records carry the later source-review and build results;
neither enables runtime. Create a new reviewed version for execution.

| Case | Literal launch contract | Frozen output |
| --- | --- | --- |
| `startup.argv-empty` | Executable `/apps/app`; argv `["app","A","","B"]`; cwd `/case/work` | Reviewed argc/argv/NULL-terminator fixture and exact independent JSON bytes |
| `startup.environment` | Executable/argv0 `/apps/startup.environment`; explicit complete environment with ALPHA and BETA and absent missing-key variable | Exact reviewed getenv observations serialized to frozen JSON |
| `startup.stdout-stderr` | Executable/argv0 `/apps/startup.stdout-stderr`; explicit environment/cwd | Each stream 4096 bytes: stdout 0..255 repeated 16 times, stderr 255..0 repeated 16 times |

The three oracle files preserve the expected byte/wait rules but do not use the
runtime `independent-oracle` schema. They have `artifact_version`, `case_version`,
`independent_source`, `unresolved_expectations` and historical
`PENDING_INDEPENDENT_REVIEW`; the strict runtime loader instead requires `kind`,
`version`, `source_sha256`, `predicates` and a supported review status. Create
new source-bound execution oracle records, preserving the original files and
their exact stdout/stderr/wait expectations. Retain a derivation mapping and
the independent review identity; never rewrite the old oracle flags in place.

Retained compiler outputs supply executable/source/oracle and loader byte
identities. Convert the review packet's integer umask 18 to the runtime profile's
explicit string `0022`; map its `environment` to `env` without adding inherited
variables. Bind `stdin: null` for `/dev/null` only in a newly reviewed execution
packet. Keep the exact source and expected bytes, with actual review
assertions/parameter status, unchanged catalog limits and compiler proof.

For the argv case the McKernel command is literal
`["/bin/mcexec","-t","1","0","app","A","","B"]`, with
PATH `/apps:/bin:/usr/bin` and no `COKERNEL_PATH`. Passing `/apps/app` as the
argument to mcexec would change payload argv0. Prove that the selected PATH
entry resolves to the same retained ELF used by Linux `execve`.

The new artifact order is:

1. `selected-inputs`: source commit/diff and compiler proof, all three native
   modules, Linux kernel, McKernel image, unchanged launcher, compiler, fixed
   profile, and exactly the selected payload/source/loader/stdin identities.
2. `runtime-capabilities`: bind the selected-input hash, with reviewed original
   evidence for each required capability. Preserve blocked reasons until proof
   is complete; infrastructure unit tests cannot become capability proof by
   relabeling their status.
3. `execution-packet`: new version, exact catalog/input/capability hashes, one to
   three cases with reviewed source/oracle/limits and explicit release state.
4. `runtime-bundle`: artifact references to those three manifests. No hash cycle
   or self-hashing manifest is needed.

The current gate union for all three cases is `current-inputs`,
`runner-contract`, `runtime-transport-fault-injection`, and `dynamic-etexec`.
Their catalog dependencies are empty. The transport gate explicitly requires
all four actual modes: prepublication hard error, postpublication notification
error, recoverable pressure, and permanent pressure. One collected mode or the
controller/UART/parser tests cannot satisfy that gate. Dynamic ET_EXEC support
is historical until rebound and replayed for the selected current binaries.

## Missing backend evidence and schema seams

1. **Prepared root and actual isolation.** The initial selected-input schema
   hashes artifacts and records QEMU argv but has no typed prepared-root/CPIO
   mapping, guest collector/interpreter identity, container image digest,
   effective cgroup proof, boot arguments/topology observations, guest pathname
   installation map or input-reset manifest. Compiler bindings are an opaque
   hashed artifact, not parsed compilation evidence. Hashed interpreter/DSO
   lists are not independently rederived from the ELF or installed root by the
   oracle evaluator. Add a separately reviewed
   backend manifest, bound to the selected-input hash, with original source,
   executable, dependency and guest-path relations. Do not add unknown fields
   to the current strict schema. Reject unresolved or unproved relations.
2. **Guest setup.** Create and inventory `/apps`, `/case/work`, attempt parents,
   payloads and loader closure explicitly. Verify directory/link/file identity
   and actual proc/fd facilities before launch. The current fault-guest missing
   cwd failure demonstrates why a string-valued cwd is not setup evidence.
   Establish actual uid0/gid0/groups[0]/umask0022, stdin and fd setup before each
   engine. Reset and rehash case inputs between reference and McKernel runs.
3. **Launcher versus payload.** A supervisor around mcexec records mcexec's
   executable, argv and Linux wait status. `evaluate_case` expects the payload's
   executable and argv. Passing that launcher report directly fails; rewriting
   its fields as if a payload process had been collected would falsify evidence.
   Keep the original launcher report and define a distinct derived application
   observation linked to actual scheduling, OS/generation/PID/TIDs and matched
   request/return. Signal cases additionally require actual payload signal
   termination, not a launcher exit code of 128+signal. They remain outside the
   first startup slice until that evidence is implemented.
4. **Environment and streams.** The unchanged launcher can add preload/stack
   environment state, as the independent packet review records. Prove the
   actual payload environment; the startup fixture's three getenv checks do
   not prove complete environment equality. Retain every combined launcher
   stdout/stderr byte. A separately reviewed source-bound framing adapter may
   identify exact diagnostic segments, retaining offsets and original hashes;
   generic regex filtering or normalization is not permitted. Evaluate payload
   bytes against both the independent oracle and the pinned guest reference.
   `evaluate_case` takes only one collection report; differential pairing and
   distinct identities for both engines require a separate orchestrator.
5. **Normal lifetime and loss.** Fault snapshots establish their narrow selected
   read/RET contracts, not general application completion. The new backend needs
   normal retirement, owner/pager/claim conservation, actual process/thread
   inventory, application-child attribution and trace loss/coverage. The reserved
   `evidence` argument currently cannot check them. An application exit0 marker
   or matching streams cannot compensate for absent lifecycle evidence.
6. **Artifact transport and repeated attempts.** Preserve original guest paths
   and reports when importing files; retain a hashed mapping to local canonical
   paths for validation rather than overwriting originals. Bound a complete
   export tree and acknowledge only durable capture under the original deadline.
   Partial/raw evidence and the first failure remain retained. Apply same-OS
   repeats=3 and fresh-guest repeats=1 as explicit reviewed schedules, with
   separate observations and input identities; no hidden retry after a failure.

## Next implementation slice

Implement a metadata-only `run.py` preflight after this map is reviewed. It can
preserve the planned CLI, exclusively create a bounded attempt directory,
retain the bundle and an identity index, call `load_runtime_bundle` and
`validate_case`, and report which backend obligations are still missing.
Preflight must always report execution NOT_RUN and application acceptance false;
even metadata PASS must remain BLOCKED while backend/release/provenance support
is absent. Unknown profiles/modes, increased bounds, unsupported capabilities,
stale hashes, absent case IDs and existing attempt paths fail closed. Include
source-only negative test fixtures for the parent to run in the pinned container.

Do not add a callable execution backend in that slice. First review a typed
backend preparation/evidence schema and guest collector choice, then implement
the actual guest launch and observation adapters behind those checks. The
independent fault-gate work can proceed under its existing bounded authority
while catalog execution remains blocked. After all gates and a separate packet
release pass, start with one reviewed startup case, stop at its first unexpected
failure, and advance through the remaining two plus their required repeats.
The subsequent family/dependency plan and whole-OS requirements remain intact.

Validation of this document is read-only source/metadata inspection and exact
identity retention. No `run.py` skeleton was written: the initial metadata
entry point is concrete here, while its guest/provenance interfaces still need
review before they are represented as executable code.
