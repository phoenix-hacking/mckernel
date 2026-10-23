Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Verdict: ACCEPT_CORRECTED_SOURCE_FOR_ONE_COMPILE_ONLY_QUALIFICATION. This is
source acceptance, not Docker/build admission, physical acceptance or lease release.
The prepared request still has compile_only_release=null. This review executed
no tests, Docker, compiler, root operation, guest or P12 lifecycle action.

Scope was the six requested private compile-only files. The preserved offline
image driver's command construction was read only to verify jobs1 and offline
compile/link behavior. No P12 executable helper was edited or substituted.

Findings by severity:

- HIGH, corrected before this verdict: compile_image_owner.py originally defined
  main() without invoking it. Both proposed direct Python commands silently
  exited0. The current EOF invokes SystemExit(main()). The added real-script
  fixture executes the actual entrypoint with NULL admission and requires a
  nonzero exit, the exact release-reference error, no stdout and no path effects.
  I inspected its source and the retained fixture stderr:19 tests pass in0.367s.
  The reported outer CPU0 job elapsed0.601072256s. I did not rerun the fixture.
- No remaining source-level launch blocker found in the reviewed concurrency,
  Docker lifecycle, source binding or normal exact-CID release paths.
- Recovery limit, explicitly retained rather than treated as a launch blocker:
  exceptions after lease acquisition but before create leave a retained lease,
  retired=false and no CID. The finite release action requires retired=true and
  a valid CID; it cannot clear that class of failure. Such a case requires
  separately reviewed root reconciliation. Do not claim ordinary accepted-CID
  release covers every terminal failure or retry it automatically.

Why the proposed split is admissible at source level:

- Fixed compile profile is CPU6/1CPU/4GiB, MemorySwap=Memory, pids128, jobs1.
  P12 remains CPU2-5/4CPU/12GiB, MemorySwap=Memory, pids512. Controller allowance
  is an explicit root fact. No native/heavy record is acquired or released.
- Root-owned sealed release binds owner/helper/profile hashes and the canonical
  request core; root admission also binds that core, boot and <=120s boottime
  age. Both root and fresh local MemAvailable must be >=24GiB. Root must accept
  actual dual capacity, CPU6 retirement, P12 sole-native ownership, unchanged
  native cgroups and disjoint P12/compile writable roots.
- Immediately before create and start the owner inspects the exact P12 CID,
  checks its name/owner/config/HostConfig hashes and all reserved resource caps.
  Its only P12 Docker operation is inspect. Source, manifest, derivative,
  materialization, image, driver, toolchain closures and source identities stay
  bound through the inherited full validation and revalidation.
- The sole writable bind is the private HOST owner-work root at/work. Source,
  toolcache, driver and manifests are read-only; rootfs is read-only,/tmp is
  bounded256MiB, and network is none. Effective command, user, mount set,
  resources and isolation are inspected after create. The preserved driver
  builds only the selected offline artifacts with jobs1; no native activation.
- An exclusive HOST lease exists before Docker effects. Create returns a full
  CID; inspection authenticates CID/name/image/owner/operation before lifecycle
  operations. Ambiguous create uses the fixed exact-owned name only to discover
  a CID. Cleanup reinspects that CID, records terminal state/logs, then removes
  by CID and checks absence by CID/name/owner. Any unproved Docker client
  retirement is sticky and prevents removal/retirement claims. Exceptions retain
  the lease and failure evidence; compiler success never clears native ownership.
- Ordinary lease release requires separate sealed root physical acceptance of
  the exact receipt and lease, owner/controller join and all client retirement,
  then rechecks own-container absence and exact lease bytes/device/inode. It
  does not target P12 or release native/global ownership.

Required before an actual launch:

1. Root must supply fresh actual CPU6 consumer retirement, actual P12 identity/
   effective config and RW roots, dual disk capacity/headroom, controller budget,
   same-boot <=120s facts and MemAvailable>=24GiB. The root facts and release must
   bind this exact owner/helper/profile/request core and this independent review.
2. Produce/review the finalized request with its sealed release reference; run
   full pure request validation on those exact bytes. The current prepared NULL
   request is deliberately nonexecutable. Confirm the inherited full source and
   toolchain validation fits the120s fact lifetime; refresh admission through a
   newly bound release if required, never bypass the age check.
3. Review exact operation captures before one Docker qualification. Prove actual
   create/inspect limits, HOST-only output, jobs1 build completion or recorded
   failure, exact compiler CID cleanup, all client joins and P12 configuration/
   ownership unchanged. The fixture's fake Docker is not this runtime proof.
4. Keep the HOST lease until root independently joins the outer owner/controller
   and clients, accepts exact container absence and publishes physical acceptance.
   Only then use the finite ordinary accepted-CID release. No native guest or
   mutation qualification is authorized by this review.

Reviewed source bindings:

- owner:8cd5a1948fc973461e15c17cdea604932b723f839f00646ec7df35c31647d555
- helper:8ffc9a09e2f2e9e9c9cc09af559d707bf6c4b989fc4f9d3ad51fe88a8e5b6083
- profile:9b78e4ec49f163a333a3fd7e9cf0dc6b05dbdc097a0b785c20cf741aaa6e23fa
- prepared request:92bcb96713c498bf2397bb24c3473a2ffbeb61f45dfa423a6ae8b99f4a4ffe4f
- request core:1a93ac79346055cff43e18afa9b4f358cc9ff9f9328976d37c724b28b020ab2c
- fixture:eee51f34f08d7e2003fb3d4128608b5106021c6f84d8b70dc64f94a0931f5260
- reviewed operation-plan version:29da1a242434527973b701eeb84b66196f7a0c4b4ce1e6a4ac42a2fa4afa01a8

Operation-plan bookkeeping may acquire the already-preserved fixture-result
reference and this review reference without changing the accepted executable
source or the still-required root admission/release boundary.
