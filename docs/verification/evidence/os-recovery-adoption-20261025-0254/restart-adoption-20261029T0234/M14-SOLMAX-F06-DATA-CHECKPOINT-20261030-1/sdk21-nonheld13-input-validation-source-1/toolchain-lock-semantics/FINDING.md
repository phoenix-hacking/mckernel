# SDK13 toolchain lock semantics — source and retained receipt

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
`fd3d7a13e1b8b5d103f7e59d22f17c9e4b99cc937637decaa66749acfae6c802`
is SHA-256 of the literal complete toolchain-lock JSON file bytes. It is not a
canonical-JSON or extracted-subdocument digest. The original retained image
preparer `docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-SOURCE-CHECKPOINT-1/source31-runtime-sources/08-native_rust_exact_build_image_prepare.py`
SHA256 `45cb12e0fd58d164468badfb99a3ed922e65e06046bf38b4a50e27e18595a27b`
uses `digest(toolchain_lock)` in its receipt at line 228. The imported retained
helper `04-native_rust_exact_build_container_owner.py` SHA256
`96d17547bfc71454d54e95a705138cc9b26faa1e2cafc34105c9ed8d5a68f4d1`
implements `digest` at line 57 as SHA-256 streamed over the file opened `rb`.
The preparer also parses the file as JSON for direct-artifact package pins; this
does not change the byte-hash subject.

One direct current local-file comparison: `/home/holden/mckernel/host-kernel/rocky/toolchain-lock.json`
is 28,867 bytes and SHA256 `fd3d7a13e1b8b5d103f7e59d22f17c9e4b99cc937637decaa66749acfae6c802`.
This establishes that these current bytes match the retained digest. It does not
prove that this exact pathname was the historical preparer's original pathname.
The lock and relevant manifest remain read-only inputs, not current image proof.

`/home/holden/mckernel-exact-image-evidence-942c927b-scratch22-authority3-image1-20261017/image-receipt.json`
SHA256 `352102798e60bfcf8a72facded532430a93ba30f949a55e1d8eaf54a2f351550`
records PASS, source-free, runtime network none, retired, the above lock digest,
and image ID `sha256:41778f1f22fd68897c1209e225a9807a197ed47bf0edd17835821bb5986e50b5`.
It is a rebind and names source receipt
`/home/holden/mckernel-exact-image-evidence-c81aeaca-7/image-receipt.json`
SHA256 `824e22c0aad7494914d39adb31bb70290c59912d5326618d2ffeb5cdbb6ef845`,
which records the same image ID and lock digest. The retained rebind validator
`09-native_rust_exact_build_image_rebind.py` SHA256
`f10ab116e55a24e8db7a8157d71efdd01198ba3453a8141bc8bbf596eda6b61e`,
lines 159–190, requires the source receipt bytes, expected image, lock digest,
PASS, offline/source-free, retired and candidate identities to agree. Retained
consumer `03-native_rust_exact_mckernel_image_container_owner.py` SHA256
`e9861cf73b0328c9fe2eacb987ea179933146cbeddbc3951405d4e60e89560f4`,
lines 587–609, authenticates image receipt hash and compares its lock digest to
the request's digest. This is historical receipt validation, not a live Docker
image observation or fresh operation release.

SDK13 profile 3e6d2491 and SDK12 profile c88825ef carry this lock digest and
SDK41778 image as retained expected inputs. The prior actual conversion producer
contract fa275bbc does not itself contain a direct lock-file path; it is not a
new actual SDK13 input receipt. The current validator c7dfd75f's
`source_map.toolchain_lock = {path, sha256}` and direct file-byte equality are
therefore semantically valid; a future independently reviewed source map may
bind the matching path above without any adapter correction for this issue.
Fresh root-release source-map binding, live image/tool/daemon/resource checks,
complete compiler source closure and SDK output/ABI/native evidence remain open.
No Docker, compiler, owner, fixture, sudo or native operation was run.
