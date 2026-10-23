-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: docker.io-app
Binary: docker.io, docker-doc
Architecture: any all
Version: 26.1.3-0ubuntu1~20.04.1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Homepage: https://mobyproject.org/
Standards-Version: 4.6.2
Vcs-Browser: https://github.com/canonical/docker.io-app
Vcs-Git: https://github.com/canonical/docker.io-app.git
Testsuite: autopkgtest
Testsuite-Triggers: dctrl-tools, debian-archive-keyring, debootstrap, snapd
Build-Depends: bash-completion, ca-certificates, cmake, debconf (>= 0.5), debhelper-compat (= 12), dh-apparmor, dh-exec, dh-golang, git, golang-1.22-go, libapparmor-dev, libbtrfs-dev | btrfs-progs (<< 4.16.1~), libdevmapper-dev (>= 2:1.02.68~), libltdl-dev, libseccomp-dev, libsystemd-dev (>= 209~), pkg-config, po-debconf, procps, tzdata
Package-List:
 docker-doc deb doc optional arch=all
 docker.io deb admin optional arch=any
Checksums-Sha1:
 f71422f36d2361e03f10e66e0e482837a947c35c 24273474 docker.io-app_26.1.3.orig.tar.gz
 49c2ecb03b4c30cca0c77438c0946f0e9932cee8 98532 docker.io-app_26.1.3-0ubuntu1~20.04.1.debian.tar.xz
Checksums-Sha256:
 ad4d3cdd2a364c1ddb3f72d341a7c294ed29b1f982cfd784bee0444e52dd8cb4 24273474 docker.io-app_26.1.3.orig.tar.gz
 ed40ee4d7060dfccabf630f1ef129058d485f088877f523a181d5a24d1fc0ee3 98532 docker.io-app_26.1.3-0ubuntu1~20.04.1.debian.tar.xz
Files:
 50b20c9804bfd204af65691f324d6eb4 24273474 docker.io-app_26.1.3.orig.tar.gz
 eaac4d4307741f3066128bdb400edca2 98532 docker.io-app_26.1.3-0ubuntu1~20.04.1.debian.tar.xz

-----BEGIN PGP SIGNATURE-----

iQJQBAEBCgA6FiEEQ5iE5oYqQpwpDfY7AzxMonYCSDQFAmcZZ10cHGF0aG9zLnJp
YmVpcm9AY2Fub25pY2FsLmNvbQAKCRADPEyidgJINNIBD/4mjAX9vwZUxtHxPJG/
A6FnmM6440g+i5U9bbd/cPnpv5gu3NHIm7bjtgXeEBNRT5uR6VfH0AR3tAL1SdwB
SKDVBT4ZDpQ1P55J/5UbjvHKjgbSaQyn+mIiH4cz2+rDfdTpFCBdI0ybQzuLV633
/Xe92S4t9qN/EdECU1QJ3z0K4HGP9HG8tozXPnx3z5jfXEsbWA7dTEFleMpsl8Vb
Vep5iy3k67rK+tA3nPMBMr9n/tkd+oIe6SCNQXGVntj3MLXMGeCGyfGND+9xEZXC
qc77gtuK/ZOFGc9Lor6LW6wQtBV5p3Sc3guQRO/fYXfuRZUfHEX6L0ORwxWYz05D
cjzcSJQ9zYbLgELf4zpIxoHofgSVBDRMjEkkEgz+NyH7SIjz1vSYeJwW9Vq3WFcF
GBYahkRPUt5lyarDtu/ogLXSgSiFFOHVUh3ea06xLbJ51vjnJUf5pmRx7jMH9rXT
yxtfAaAPm+nbRcIhhz57S/rkQ95uGGRbVm8VlgfUCmo9jYwDTZAOJo5Wx2j1gG7L
urs8XlQBdtlpd7Z2VnXz3RWE3QJFtnyX6T+k0jqqyS3RmbUwmb3ndv63YoGA8hLN
c9v5PaYLkJENTuLqnar+SUmkiLZQXANsYs8GsfEA85G4Wa8XOfVFOmwjz6xEbJHk
doaWb+TkriW+GJlGNTemF26p5g==
=oUfz
-----END PGP SIGNATURE-----
