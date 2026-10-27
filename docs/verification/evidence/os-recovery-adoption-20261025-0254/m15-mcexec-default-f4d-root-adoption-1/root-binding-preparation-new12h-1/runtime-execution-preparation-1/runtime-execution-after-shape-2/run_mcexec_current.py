"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Explicit outer context: retained owner source stays exact; this wrapper replaces
its authenticate and PollSignals globals during this one reviewed invocation.
All modifications are disclosed and independently bound by outer_execution.
Cleanup keeps original cleaning-mode behavior and is never barred by new polling.
"""
import argparse,json,time
import execution_contract as c
from pathlib import Path
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('request','request-sha256','release','release-sha256'):p.add_argument('--'+name,required=True)
    p.add_argument('--preflight-only',action='store_true');a=p.parse_args();o=c.owner()
    original_auth=o.authenticate;original_poll=o.PollSignals
    request,release=c.authenticate_outer(a.request,a.request_sha256,a.release,a.release_sha256)
    if a.preflight_only:
        print(json.dumps(dict(status='PASS_OUTER_AUTHENTICATION_ONLY',execution_authority=False)));return
    def guarded_auth(*args):
        # Avoid recursion while both retained and outer source authentication run.
        o.authenticate=original_auth
        try:return c.authenticate_outer(*args)
        finally:o.authenticate=guarded_auth
    class CurrentPollSignals(original_poll):
        def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.last_campaign=0
        def check(self):
            if not self.cleaning and time.monotonic()-self.last_campaign>=1:
                c.campaign();self.last_campaign=time.monotonic()
            return super().check()
    o.authenticate=guarded_auth;o.PollSignals=CurrentPollSignals
    try:result=o.guarded_execute(Path(a.request),a.request_sha256,Path(a.release),a.release_sha256)
    finally:o.authenticate=original_auth;o.PollSignals=original_poll
    print(json.dumps(result,sort_keys=True))
    return 0 if result['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
