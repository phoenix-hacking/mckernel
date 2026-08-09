#!/bin/sh

if [ "${LOCAL_ONLY:-0}" = 1 ]; then
	USELTP=0
else
	USELTP=1
fi
USEOSTEST=0

: "${BOOTPARAM:=-m 1G@0,1G@0,1G@0,1G@0,1G@0,1G@0,1G@0,1G@0,1G@0,1G@0,1G@0,1G@0,1G@0,1G@0,1G@0,1G@0 -O}"

. ../../common.sh

issue="1324"
tid=01

for tno in 01 02 03
do
	tname=`printf "C${issue}T%02d" ${tid}`
	echo "*** ${tname} start *******************************"
	${MCEXEC} ./C1324T${tno}

	if [ $? -eq 0 ]; then
		echo "*** ${tname} PASSED ******************************"
	else
		echo "*** ${tname} FAILED ******************************"
	fi
	let tid++
	echo ""
done

if [ "${LOCAL_ONLY:-0}" = 1 ]; then
	echo "*** C${issue} LTP fork cases skipped: LOCAL_ONLY=1"
	exit 0
fi

for tp in fork14 fork01 fork02 fork03 fork04 fork05 fork06 fork07 fork08 fork09 fork10 fork11
do
	tname=`printf "C${issue}T%02d" ${tid}`
	echo "*** ${tname} start *******************************"
	sudo $MCEXEC $LTPBIN/$tp 2>&1 | tee $tp.txt
	ok=`grep PASS $tp.txt | wc -l`
	ng=`grep FAIL $tp.txt | wc -l`
	if [ $ng = 0 ]; then
		echo "*** ${tname} PASSED ($ok)"
	else
		echo "*** ${tname} FAILED (ok=$ok ng=%ng)"
	fi
	let tid++
	echo ""
done
