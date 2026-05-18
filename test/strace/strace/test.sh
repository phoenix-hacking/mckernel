#!/bin/sh
if [ -z "${MCEXEC:-}" ]; then
	if [ -f "$HOME/.mck_test_config" ]; then
		. "$HOME/.mck_test_config"
	fi
	MCK_DIR="${MCK_DIR:-/opt/mckernel-rust}"
	BIN="${BIN:-$MCK_DIR/bin}"
	MCEXEC="$BIN/mcexec"
fi
export MCEXEC
./test1.sh
./test2.sh
