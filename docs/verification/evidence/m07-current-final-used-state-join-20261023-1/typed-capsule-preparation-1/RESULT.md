Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Prepared exact existing overlay CLI and pending manifest for accepted fdf4661f app/f4054bf9 collector, unchanged SDK5/image10972/launcherdca025. No compilation is needed. Only init and apps/app change; final guest executable modes remain0755 and expected membership62.

The manifest deliberately has NULL output identities until exclusive staging completes. Capture transformer stdout as overlay-manifest.json, fill two staging descriptors from actual bytes/stat, and exercise accepted typed load_manifest against the complete artifact. No new wrapper or oracle.

Proposed one-job CPU0/512MiB/CPU30/wall120+6 requires root scheduler grant. No transformer, compiler, host ISA probe, root, Docker or guest ran. No acceptance or capacity claim.
