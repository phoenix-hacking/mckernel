Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

# Persistent dispatcher model preference

The user's October30 direction makes `gpt-6.1-sol/max` the default dispatcher.
The configured fallback ranking is `gpt-6-astra`, `gpt-6.1-terra`, `gpt-6-sol`,
then `gpt-6-luna`. Prefer advertised max-capable choices before lower dispatcher
effort. This is a routing preference, not a capacity or entitlement claim.

`scripts/run_os_goal.py` supplies the shared candidate policy. An explicit
`--model` or `--effort` pins the resulting pair. Implicit defaults may select an
advertised fallback; preflight records server defaults separately from selected
thread parameters. Actual thread model, effort and full-access permissions must
match their readback. Required worker capabilities remain a separate condition.
Ordinary workers use medium, complex workers/reviewers high, and bounded auditors
low. A capacity replacement must preserve those lower worker effort levels.

The prepared controller successor uses the shared policy, removes the obsolete
three-choice parser adaptation, and keeps typed capacity eligibility, hold vetoes,
whole-model cooldown, positive retirement, finite watcher reentry and weekly-only
controls. Old frozen controllers and their stop records remain retained. No model
switch may retry a held service rejection or uncertain submission. Stop at100%
weekly usage, or earlier on an actual hold, unknown billing or inherited cutoff;
the current reset is an upper bound and prepaid fallback stays disabled.

Exact source review and validation are retained in
[the source-preparation evidence](../evidence/os-dispatcher-max-preference-20261030-1/RESULT.json).
The canonical launcher/recovery/billing tests pass172 cases, and the prepared
controller passes11 offline cases. The16-target combined-profile data parser
passes18 synthetic cases and always returns unauthenticated data with no authority.
These checks accept no kernel artifact, native run, C retirement or file goal.

At this source checkpoint the campaign is stopped on technical integration work.
M14 remains4/6 supported file goals; M15 is queued until original-scope M14
acceptance. A fresh same-Root controller envelope needs matching source/config
packets, current account/catalog/weekly/goal/turn observations, positive retired
actor/lease observations, independent review, and actual new routing, permissions,
heartbeat, guardian and monitor readbacks before being called restarted.

Physical compilation still needs the real complete scripts union, split output
and work directory identities/custody, source exclusion, pre-shadow snapshot,
effective mount evidence and operation-specific profile/owner/resource admission.
The graph parser prepares the schema; it supplies none of those physical facts.
Source preparation and independent conversion work may advance while those gates
remain open. Preserve every service hold, native owner, consumed nonce, scratch21,
artifact and evidence record. Reuse existing implementation and accepted artifacts.
