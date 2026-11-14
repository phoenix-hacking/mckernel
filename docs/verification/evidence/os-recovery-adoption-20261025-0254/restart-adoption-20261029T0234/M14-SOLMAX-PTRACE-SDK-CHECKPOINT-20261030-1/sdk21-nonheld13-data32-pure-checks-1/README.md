# Data32 bounded pure checks

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The operation used the Root ordinary grant `381afc98...`: CPU0, per-child address-space 512 MiB, CPU20 seconds, wall30 seconds (TERM plus five seconds), nofile128, file-size16 MiB and core0. Each case has its exact owner and child argv, clean environment, fresh usage/time/controller/marker pre-spawn check, started PID/birth, stdout/stderr, wait4 resource measurements and group census before reaping in its named subdirectory. Each child exited with a closed group. Test temporary paths were restricted to each owned output directory. No real compile lease, container, SDK, native operation or mounted source/nightly/Rust content read occurred.

- `validator/`: six synthetic data32 validator cases passed, exit 0.
- `snapshot/`: seven synthetic cases ran; five passed and two failed, exit 1. `test_adoption_checks_prior_hash_and_current_metadata` and profile mutation in `test_root_and_profile_identity_drift_fail` expected identity drift to reject same-size changes, but no ValueError occurred. No conclusion about cause is established; retain failures and investigate before relying on the snapshot approach. The fixture was not repeated.
- `converter/`: evidence-only output `NORMALIZED-PROPOSED.json` SHA-256 `804e9c2f82b855def239d4daba66ba8cd2c2725909a299ba6007d05d427fd94e`, canonical `prehashed_trees` SHA-256 `8de3afaa436f4329def5089395ccde59c606a4e45dc88bc67e591ff4846c0447`. It binds the reviewed map and fixed Rust157 receipt plus old source/nightly ledgers. This is proposed data and confers no live authority.

Live adoption requires resolution and independently reviewed correction of the snapshot failure, valid real owner/lease and source quiescence, supported filesystem metadata semantics, root and directory identity/membership checks and the other controls in the independent review. No runtime/native/SDK/default acceptance is claimed.
