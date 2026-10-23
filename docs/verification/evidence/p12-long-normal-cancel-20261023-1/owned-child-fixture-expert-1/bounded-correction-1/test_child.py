"""Functional OS only; no security testing. Disposable fixture child, never the live owner."""
import json,os,signal,sys,time
received=0
# A handler may run before the interrupted READY write returns. Raw pipe writes
# avoid Python BufferedWriter reentrancy; each exact record is below PIPE_BUF.
ready=b'TESTONLY_CHILD_READY\n'
response=(json.dumps(dict(received_SIGTERM=1,nonce=sys.argv[1]))+'\n').encode()
def term(n,f):
 global received
 received+=1
 if received!=1:raise SystemExit(98)
 if os.write(1,response)!=len(response):raise SystemExit(97)
 raise SystemExit(42)
signal.signal(signal.SIGTERM,term)
if os.write(1,ready)!=len(ready):raise SystemExit(96)
time.sleep(30)
raise SystemExit(99)
