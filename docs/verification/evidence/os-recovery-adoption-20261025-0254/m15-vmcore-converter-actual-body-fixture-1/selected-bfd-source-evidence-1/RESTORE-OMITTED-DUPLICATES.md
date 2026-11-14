# Restore omitted duplicate package data

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The two official RPMs are retained in this directory. The following duplicate
payloads may be omitted from Git; local originals remain preserved. Run these
commands from this directory only when restoring a checkout that lacks them.
These commands read package/archive data as an ordinary user. They do not install,
build, run package scripts, or authorize SDK/native execution.

First verify the retained RPMs:

```sh
sha256sum -c <<'SHA256'
fc13bb730e5ff7b22c0c26b246061980844f8fe685d234c4495b67993e70e3eb  binutils-2.41-63.el10.src.rpm
0907f95d4351afcac619be9aaf398d05389eba037ad5080c09254824e4539d84  binutils-devel-2.41-63.el10.x86_64.rpm
SHA256
```

Use the existing `bsdtar` extractor to restore the exact source tar and static
library from their RPM members, then verify both before reading further members:

```sh
mkdir -p rpm-data binary-selected binary-functions
bsdtar -xf binutils-2.41-63.el10.src.rpm -C rpm-data binutils-2.41.tar.xz
bsdtar -xf binutils-devel-2.41-63.el10.x86_64.rpm -C binary-selected ./usr/lib64/libbfd.a
sha256sum -c <<'SHA256'
ae9a5789e23459e59606e6714723f2d3ffc31c03174191ef0d015bdf06007450  rpm-data/binutils-2.41.tar.xz
2324c3f9557b3387126123659badf4cccdbbd272104aec42a21c709c31bf6d4e  binary-selected/usr/lib64/libbfd.a
SHA256
```

Restore the two omitted object members using the existing `ar` data reader:

```sh
ar p binary-selected/usr/lib64/libbfd.a opncls.o > binary-functions/opncls.o
ar p binary-selected/usr/lib64/libbfd.a section.o > binary-functions/section.o
sha256sum -c <<'SHA256'
647fd15e418e613e07035e6585120162bd2ab6d55e594822b723b20552fc2f1f  binary-functions/opncls.o
4004ae285891960ab4836afb28f8ca2a190af50d018328b6ebaa06e075383158  binary-functions/section.o
SHA256
```

Exact omitted duplicate sizes:

| Path | Bytes |
| --- | ---: |
| `rpm-data/binutils-2.41.tar.xz` | 26,765,692 |
| `binary-selected/usr/lib64/libbfd.a` | 18,504,828 |
| `binary-functions/opncls.o` | 318,120 |
| `binary-functions/section.o` | 237,288 |

These are official package payloads. The actual selected SDK `libbfd.a` hash
remains unbound; restoring these files supplies no SDK identity or native proof.
The existing `SOURCE-LIFETIME-FACTS.json` is unchanged (SHA256
`3db997f0c067ce19992d9a0ff57e352abdcecea40ddacb66b406a7aa6381b54c`).
