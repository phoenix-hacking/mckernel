from pathlib import Path
import os
base=Path('/home/holden/mckernel-work/host-preparation/settid-current-production-link-preparation-20261021-1/owned-fork-pin-successor-1/coupled-current-pin-correction-1/full-image-attempt-1')
assert not os.path.lexists(base)
base.mkdir(mode=0o700)
for name in ('owner-work','owner-evidence'):(base/name).mkdir(mode=0o700)
