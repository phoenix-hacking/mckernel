import os
from pathlib import Path
import stat

root = Path(os.environ['INITRAMFS_ROOT'])
destination = Path(os.environ['RUNTIME_EVIDENCE']) / 'initramfs.list'
records = []
for path in sorted(root.rglob('*')):
    name = '/' + str(path.relative_to(root))
    if any(character.isspace() for character in str(path)):
        raise SystemExit('Unsupported whitespace in initramfs path')
    metadata = path.lstat()
    mode = format(stat.S_IMODE(metadata.st_mode), 'o')
    if stat.S_ISDIR(metadata.st_mode):
        records.append('dir {} {} 0 0'.format(name, mode))
    elif stat.S_ISREG(metadata.st_mode):
        records.append('file {} {} {} 0 0'.format(name, path, mode))
    else:
        raise SystemExit('Unexpected initramfs entry type: ' + name)
# Linux gen_init_cpio writes these nodes into the archive; no host or container
# device node is created, and no elevated container capability is needed.
records.extend(['nod /dev/console 600 0 0 c 5 1', 'nod /dev/null 666 0 0 c 1 3'])
destination.write_text('\n'.join(records) + '\n')
print('Initramfs manifest entries:', len(records))
