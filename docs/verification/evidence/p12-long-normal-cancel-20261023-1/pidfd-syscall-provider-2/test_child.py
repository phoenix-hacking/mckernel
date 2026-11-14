"""Functional OS only; no security testing. Disposable fixture child, never the live owner."""
import json,signal,sys,time
received=0
def term(n,f):
 global received
 received+=1
 print(json.dumps(dict(received_SIGTERM=received,nonce=sys.argv[1])),flush=True)
 raise SystemExit(42)
signal.signal(signal.SIGTERM,term)
print('TESTONLY_CHILD_READY',flush=True)
time.sleep(30)
raise SystemExit(99)
