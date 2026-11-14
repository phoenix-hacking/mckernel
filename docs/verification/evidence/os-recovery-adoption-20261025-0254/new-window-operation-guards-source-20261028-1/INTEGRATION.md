Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This is a source candidate. All existing operation guards, grants and releases remain
historical, unchanged. No live guard, account capture, controller, compiler, Docker,
privileged command or nonce operation was invoked by this work.

The shared guard retains historical cumulative-account semantics by authenticating
and importing only the predecessor account module. It never calls its expired
window guard. Credit identity, ceiling, resident billing settings, positive finite
account balance, real holds, stop flags, active goal and fresh heartbeat retain
those existing checks. A Root-supplied cumulative-spent floor can only tighten
the retained floor. The new actual window is authenticated separately by bytes.

Root integration sequence:

1. Obtain independent source review of operation_window_guard.py and the exact
   consumer adapter, including the fresh read-only guardian adapter. The guardian
   adapter must validate the actual new guardian receipt, journal and live birth,
   retain all tighter actual parent clocks and return the three actual clocks.
2. Prepare fresh per-operation consumer sources under disjoint Root-owned output.
   current116 must explicitly replace the expired runner hook, capture guard pin,
   runner deadline, common clamp, worker clamp, profile and reviewer-binding data
   as one reviewed successor. Keep historical values in predecessor_cutoffs. The
   already active ready116 worker owns this concrete adapter. ready227 owns its
   separate original227 shim and cohort. Do not modify historical releases.
3. Root fills the corresponding SUCCESSOR.TEMPLATE.NOT-AUTHORITY.json in a new
   actual namespace. operation_cutoffs must be the minimum of the new immutable
   window, fresh guardian's actual clocks and any tighter new operation-specific
   restriction. Preserve the exact named predecessor clamp; extension is explicit
   operation review, never implicit launcher-time renewal. minimum_cumulative_spent
   comes from the fresh actual cumulative account observation without resetting it.
   subjects maps every reviewed consumer/source subject to its exact byte reference.
   guardian is {"source": <exact reviewed adapter byte reference>, "entrypoint":"guard"}.
   source_owners includes /root and all source owners. Other resource/runtime grants
   remain separately required; this record itself grants no execution authority.
4. Independent reviewer emits schema mckernel.independent-operation-window-review.v1,
   decision PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR, independent=true, reviewer
   equal to its actual /root/<reviewer> identity, operation equal to the operation,
   and successor equal to the complete exact Root successor JSON object. The
   reviewer must be absent from source_owners. Root/consumer authenticates this
   review and successor by exact byte reference before any clock-sensitive entry.
5. Consumer pins the shared module bytes and calls guard(operation, successor_ref,
   review_ref, expected_subjects). It returns [epoch, MONOTONIC, BOOTTIME]. For a
   retained no-argument guard()/current_cutoffs() interface, render an exact pinned
   per-operation shim; current_cutoffs returns validated operation_cutoffs, never
   the global new deadline alone. validate_operation is the cheap pure check.
6. Pass original exact producer→consumer preclock checks. Only after the actual
   independent reviewer is waiting with verified PID/birth, acquire fresh clocks.
   Preserve original120s freshness, fsync-before-final-check, once-entry, actual
   resource grants, exact fresh admissions and all Root custody/native prerequisites.

Independent review must still qualify the complete runnable source closure. This
candidate does not revive any old grant, nonce, old guardian receipt or expired
physical observer. The postnative observer owner separately supplies genuine
native lifecycle/current-free evidence; this account guard does not replace it.

The concrete no-argument adapters are current116_guard_adapter.py and
original227_guard_adapter.py. Call configure(config_ref) exactly once immediately
after import; unconfigured guard/current_cutoffs reject. The config is declared
JSON, authenticated by bytes, and contains shared_guard, successor, review and
subjects references. Both methods reauthenticate config bytes; current_cutoffs
also reauthenticates successor/review and repeats the pure operation check.
Configuration/current_cutoffs performs no live guard/account observation.

Avoid the remaining cycle by passing config_ref as independently authenticated
Root binding DATA, never embedding its hash into a source listed in successor
subjects. Root's original admission/grant/review closure pins config and stable
adapter source separately. Thread this exact data reference through nested
physical-observer loaders. Their original predicates and live guard calls remain;
each loader configures its newly imported adapter before calling guard().

Independent review identified the historical account THREAD as expired too. The
explicit successor requires actual new launcher thread
01a18111-26a7-7ef2-bbd6-e33d1c8dc803. Only the private imported predecessor module's
THREAD constant changes; its file and every remaining account/balance predicate
are unchanged. Pure regressions accept this identity and reject the old/unrelated
identities. Twelve unittest methods pass, including both no-argument adapters,
unconfigured refusal, one-time configuration and config-drift refusal.
