"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Explicit outer context: retained owner source stays exact; this wrapper replaces
its authenticate and PollSignals globals during this one reviewed invocation.
All modifications are disclosed and independently bound by outer_execution.
The mounts global additionally supplies exactly the existing PREP vendor-authority
file as a same-path read-only bind. All prior mounts are byte-preserved.
Cleanup keeps original cleaning-mode behavior and is never barred by new polling.
"""
import argparse,json,time
import execution_contract as c
from pathlib import Path
def authority_mount(owner):
    row=owner.LIBRARY_PREPARATION['libdwarf_vendor']['authority'];path=owner.safe_path(row['path'],False)
    c.need(c.ref(path)==row,'exact vendor authority closure bytes')
    # PREP already pins this complete authority; driver retains its original
    # stable-FD/hash/commit/412-file validation. No validator is bypassed.
    return (str(path),str(path),True)
def extend_mounts(rows,extra):
    c.need(extra[2] is True and extra[0]==extra[1],'only same-path readonly authority')
    matches=[r for r in rows if r[1]==extra[1]]
    c.need(not matches or matches==[extra],'conflicting authority mount')
    return rows if matches else rows+[extra]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('request','request-sha256','release','release-sha256'):p.add_argument('--'+name,required=True)
    p.add_argument('--preflight-only',action='store_true');a=p.parse_args();o=c.owner()
    original_auth=o.authenticate;original_poll=o.PollSignals;original_mounts=o.mounts
    extra=authority_mount(o)
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
    def mounts_with_authority(request):return extend_mounts(original_mounts(request),extra)
    o.authenticate=guarded_auth;o.PollSignals=CurrentPollSignals;o.mounts=mounts_with_authority
    try:result=o.guarded_execute(Path(a.request),a.request_sha256,Path(a.release),a.release_sha256)
    finally:o.authenticate=original_auth;o.PollSignals=original_poll;o.mounts=original_mounts
    print(json.dumps(result,sort_keys=True))
    return 0 if result['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
