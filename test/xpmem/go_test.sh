#!/usr/bin/bash

USELTP=0
USEOSTEST=0

XPMEM_DIR=${XPMEM_DIR:-$HOME/usr}
XPMEM_BUILD_DIR=${XPMEM_BUILD_DIR:-$HOME/xpmem}
XPMEM_RUN_UPSTREAM=${XPMEM_RUN_UPSTREAM:-1}
XPMEM_UPSTREAM_TIMEOUT=${XPMEM_UPSTREAM_TIMEOUT:-120}
XPMEM_MODULE="${XPMEM_DIR}/lib/modules/$(uname -r)/xpmem.ko"
xpmem_loaded_by_test=0

. ../common.sh
export MCEXEC
set -e

cleanup_xpmem() {
	if [ "$xpmem_loaded_by_test" -eq 1 ]; then
		sudo rmmod xpmem || true
	fi
}
trap cleanup_xpmem EXIT

if [ ! -f "${XPMEM_MODULE}" ]; then
	echo "xpmem.ko not found: ${XPMEM_MODULE}" >&2
	exit 77
fi
if [ ! -d "${XPMEM_BUILD_DIR}/test" ]; then
	echo "XPMEM userspace tests not found: ${XPMEM_BUILD_DIR}/test" >&2
	exit 77
fi

if ! lsmod | awk '$1 == "xpmem" { found = 1 } END { exit found ? 0 : 1 }'; then
	sudo insmod "${XPMEM_MODULE}"
	xpmem_loaded_by_test=1
fi
sudo chmod og+rw /dev/xpmem

echo "*** XPMEM_TESTSUITE start *******************************"
cwd=`pwd`
if [ "${XPMEM_RUN_UPSTREAM}" -eq 1 ]; then
	cd "${XPMEM_BUILD_DIR}/test"
	timeout "${XPMEM_UPSTREAM_TIMEOUT}" "${cwd}/mc_run.sh"
	cd "${cwd}"
else
	echo "SKIP: upstream XPMEM test suite disabled by XPMEM_RUN_UPSTREAM=0"
fi

# xpmem basic test
"${MCEXEC}" ./XTP_001
"${MCEXEC}" ./XTP_002
"${MCEXEC}" ./XTP_003
"${MCEXEC}" ./XTP_004
"${MCEXEC}" ./XTP_005
"${MCEXEC}" ./XTP_006
sleep 3
"${MCEXEC}" ./XTP_007

"${MCEXEC}" ./XTP_901
"${MCEXEC}" ./XTP_902
"${MCEXEC}" ./XTP_903
"${MCEXEC}" ./XTP_904
"${MCEXEC}" ./XTP_905

cleanup_xpmem
xpmem_loaded_by_test=0
