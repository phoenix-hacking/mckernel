# stopped-rescue-v1 source protocol

Source/mock-only packet. The blocking fixture emits `READY` and `STOP_ARMED`,
then raises `SIGSTOP`; the dedicated single-threaded rescuer records raw wait
4991, kills and reaps the leader, observes grandchild adoption, kills the
adopted child, sends `SIGTERM` then `SIGCONT` to the collector, and requires
raw waits 9/9/256 followed by `ECHILD`. Runtime and application acceptance are
separate reviewed gates and are disabled here.
