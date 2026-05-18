#!/bin/sh
if [ -f "$HOME/.mck_test_config" ]; then
	. "$HOME/.mck_test_config"
fi
MCK_DIR="${MCK_DIR:-/opt/mckernel-rust}"
BIN="${BIN:-$MCK_DIR/bin}"
LTPBIN="${LTPBIN:-${LTP:-$HOME/ltp}/testcases/bin}"
MCEXEC="${MCEXEC:-$BIN/mcexec}"
export PATH="$LTPBIN:$PATH"

if [ ! -x "$MCEXEC" ]; then
	echo "no mcexec found: $MCEXEC" >&2
	exit 1
fi
if [ ! -d "$LTPBIN" ]; then
	echo "no LTP testcases bin found: $LTPBIN" >&2
	exit 77
fi

while read i;do
if $MCEXEC $LTPBIN/$i > $i.log; then
	echo $i: OK
else
	echo $i: NG
fi
done << EOF
clone01
clone03
clone04
clone06
clone07
fork01
fork02
fork03
fork04
fork07
fork08
fork09
fork10
fork11
execve01
execve02
execve03
wait02
wait401
wait402
waitid01
waitid02
waitpid01
waitpid02
waitpid03
waitpid04
waitpid05
waitpid07
waitpid08
waitpid09
waitpid12
waitpid13
ptrace01
ptrace02
ptrace05
EOF
