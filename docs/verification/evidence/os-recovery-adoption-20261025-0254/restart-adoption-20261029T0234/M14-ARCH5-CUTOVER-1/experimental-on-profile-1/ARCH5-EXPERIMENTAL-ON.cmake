# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Explicit ARCH5 portion of USER004446 combined experimental compiler profile.
# Compositor merges generic23 selectors separately; this file changes no generic owner.
# Root supplies this cache input to the single combined candidate's genuine producer.
set(MCKERNEL_ARCH5_CUTOVER_CANDIDATE ON CACHE BOOL "ARCH5 selected in experimental full cutover" FORCE)
# ABI probes compile separately and MUST NOT enter the production/full link.
set(MCKERNEL_ARCH5_ABI_WITNESS OFF CACHE BOOL "Exclude qualification probes from full link" FORCE)
