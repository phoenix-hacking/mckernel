"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare private accounting candidate only; execution remains deliberately blocked.
"""
from pathlib import Path
import difflib
D=Path(__file__).resolve().parent
S=D.parent.parent/'p12-coupled-resource-review-20261023-1/source/long_transport.py'
a=S.read_text()
b=a.replace("DOCKER_LOG_BYTES = 96 * 2**20\n", "DOCKER_LOG_BYTES = 96 * 2**20\n# Separate direct-file capture storage; no claim that post-join32MiB hashing limits writes.\nEXTERNAL_CAPTURE = dict(command_count=1, stream_slots=2, retained_copies=1,\n                        stream_file_bytes=384 * 2**20)\nEXTERNAL_CAPTURE_BYTES = (EXTERNAL_CAPTURE['command_count'] * EXTERNAL_CAPTURE['stream_slots'] *\n                          EXTERNAL_CAPTURE['retained_copies'] * EXTERNAL_CAPTURE['stream_file_bytes'])\n# No final wrapper/argv/path/copy binding exists in this private cohort.\nEXTERNAL_CAPTURE_BINDING = None\n")
b=b.replace("metadata_bytes=32 * 2**20, logical_growth_bytes=(7 * 384 + 512 + 32 + 96) * 2**20)", "metadata_bytes=32 * 2**20, external_capture=EXTERNAL_CAPTURE,\n                 external_capture_bytes=EXTERNAL_CAPTURE_BYTES,\n                 logical_growth_bytes=(7 * 384 + 512 + 32 + 96) * 2**20 + EXTERNAL_CAPTURE_BYTES)")
b=b.replace("    output_parent(parent)\n    readonly_input(path, parent)", "    need(EXTERNAL_CAPTURE_BINDING is not None,\n         'final external capture wrapper/argv/paths/copy count not bound; execution blocked')\n    output_parent(parent)\n    readonly_input(path, parent)")
assert a!=b and 'execution blocked' in b
(D/'long_transport.accounting-proposal.py').write_text(b)
(D/'accounting-proposal.diff').write_text(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile=str(S),tofile='private/long_transport.py')))
