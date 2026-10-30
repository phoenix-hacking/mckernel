"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Notifications are advisory; bounded fresh main-loop reads confirm quota identity.
"""
import ast
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time

RESET = 1793774133
AUTH_START = 1793251609.1432834
WEEK_SECONDS = 604800
ORIGINAL_BOOT_END = 1571574.6959790066
ORIGINAL_MONOTONIC_END = 1556236.568932019


class WeeklyWindowChanged(ValueError):
    pass


def weekly_row(limits, reset_at=RESET):
    if (type(reset_at) is not int or reset_at != RESET or not isinstance(limits, dict)
            or limits.get('limitId') != 'codex'):
        raise ValueError('authorized codex weekly limits required')
    rows=[]
    for name in ('primary','secondary'):
        row=limits.get(name)
        if isinstance(row,dict) and row.get('windowDurationMins') == 10080:
            rows.append((name,row))
    if len(rows)!=1:
        raise ValueError('one unambiguous weekly usage row required')
    name,row=rows[0];used=row.get('usedPercent');reset=row.get('resetsAt')
    if (type(row.get('windowDurationMins')) is not int or type(used) not in (int,float)
            or not math.isfinite(used) or not 0<=used<=100):
        raise ValueError('finite weekly usage required')
    # A valid 100% usage notification remains decisive even if reset metadata
    # itself is malformed; it cannot authorize further included inference.
    if type(reset) is not int and used<100:
        raise ValueError('reported weekly reset metadata required for confirmation')
    same_period=(type(reset) is int and reset-WEEK_SECONDS<=AUTH_START<reset)
    return dict(slot=name,usedPercent=used,windowDurationMins=10080,resetsAt=reset,
                canonicalResetsAt=RESET,authorizationStart=AUTH_START,sameAuthorizedPeriod=same_period)


def install(module,reset_at=RESET):
    if reset_at!=RESET:
        raise ValueError('immutable weekly authority differs')
    original_arguments=module.arguments
    def included_arguments(argv=None):
        args=original_arguments(argv)
        if args.credit_budget is not None or args.credit_run_id is not None:
            raise ValueError('weekly-only invocation forbids prepaid credit flags')
        return args
    module.arguments=included_arguments
    original_record=module.Campaign.record_rate_limits
    def observe(campaign,limits,source):
        at=datetime.now(timezone.utc).isoformat()
        observation=dict(at=at,source=source,limits=limits,worker_pid=campaign.state.get('worker_pid'),
                         worker_start=campaign.state.get('worker_start'),thread_id=campaign.state.get('thread_id'))
        # Existing protocol.jsonl retains notification envelopes. This adjacent
        # append-only log also retains every raw direct read and advisory payload.
        directory=getattr(campaign,'log_dir',None)
        if directory is not None:
            with (Path(directory)/'weekly-quota-observations.jsonl').open('a',encoding='utf-8') as stream:
                stream.write(json.dumps(observation,sort_keys=True,allow_nan=True)+'\n');stream.flush()
        campaign.save(weekly_last_raw_observation=observation)
        return observation
    def reject(campaign,limits,reason,detail):
        if campaign.stop_reason:
            return
        at=datetime.now(timezone.utc).isoformat()
        saved=dict(last_rate_limits=limits,weekly_usage_error=detail,
                   weekly_usage_observation_at=at,weekly_confirmation_pending=False)
        if 'weekly_first_confirmed_rejection' not in campaign.state:
            saved['weekly_first_confirmed_rejection']=dict(at=at,limits=limits,reason=reason,
                detail=detail,worker_pid=campaign.state.get('worker_pid'),
                worker_start=campaign.state.get('worker_start'),thread_id=campaign.state.get('thread_id'))
        if 'weekly_usage_failure_limits' not in campaign.state:
            saved.update(weekly_usage_failure_limits=limits,weekly_usage_failure_observed_at=at,
                weekly_usage_failure_reason=reason,weekly_usage_failure_worker_pid=campaign.state.get('worker_pid'),
                weekly_usage_failure_worker_start=campaign.state.get('worker_start'),
                weekly_usage_failure_thread_id=campaign.state.get('thread_id'))
        campaign.save(**saved);campaign.stop_reason=reason;campaign.stop_now=True
    def pending(campaign,limits,detail):
        generation=campaign.state.get('weekly_confirmation_generation',0)+1
        saved=dict(weekly_confirmation_pending=True,weekly_confirmation_generation=generation,
                   weekly_last_advisory_mismatch_limits=limits,weekly_last_advisory_mismatch_reason=detail)
        if 'weekly_first_advisory_mismatch_limits' not in campaign.state:
            saved.update(weekly_first_advisory_mismatch_limits=limits,
                         weekly_first_advisory_mismatch_at=datetime.now(timezone.utc).isoformat())
        campaign.save(**saved)
    def check_end(campaign):
        actual_boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        if campaign.state.get('weekly_effective_boot_id',actual_boot)!=actual_boot:
            reject(campaign,None,'weekly_usage_unknown','confirmed quota clock belongs to another boot')
            return
        end=min(RESET,campaign.state.get('weekly_effective_end',RESET))
        if (time.time()>=end
                or time.clock_gettime(time.CLOCK_BOOTTIME)>=campaign.state.get('weekly_effective_boot_end',float('inf'))
                or time.monotonic()>=campaign.state.get('weekly_effective_monotonic_end',float('inf'))):
            reject(campaign,campaign.state.get('last_rate_limits'),'weekly_window_changed',
                   'original or earlier confirmed weekly ceiling reached')
    module.Campaign.check_weekly_end=check_end
    def record(campaign,limits,*,notification=False):
        if (campaign.credit_guard is not None or campaign.args.credit_budget is not None
                or campaign.args.credit_run_id is not None):
            raise ValueError('weekly-only worker cannot have a prepaid credit guard')
        observe(campaign,limits,'notification' if notification else 'fresh_read')
        # A 100% notification during an RPC is sticky; its later response cannot
        # clear the stop or replace its first actual rejection evidence.
        if campaign.stop_reason:
            original_record(campaign,limits,notification=notification)
            return
        if (isinstance(limits,dict) and limits.get('limitId')=='codex'
                and limits.get('spendControlReached') is True):
            campaign.save(billing_hold=dict(source='codex_quota_observation',spendControlReached=True))
            reject(campaign,limits,'billing_hold','account spend control reached')
            return
        check_end(campaign)
        if campaign.stop_reason:
            return
        try:
            row=weekly_row(limits,reset_at)
        except ValueError as error:
            if notification:
                pending(campaign,limits,str(error));return
            reject(campaign,limits,'weekly_usage_unknown',str(error));return
        if row['usedPercent']>=100:
            reject(campaign,limits,'weekly_usage_exhausted','confirmed or notified weekly usage100%')
            return
        if notification:
            last=campaign.state.get('weekly_confirmed_usage') or {}
            campaign.save(weekly_advisory_usage=row)
            if (not row['sameAuthorizedPeriod'] or row['resetsAt']!=last.get('resetsAt')
                    or row['usedPercent']<last.get('usedPercent',0)):
                pending(campaign,limits,'advisory metadata/usage differs; require fresh main-loop read')
            return
        if not row['sameAuthorizedPeriod']:
            reject(campaign,limits,'weekly_window_changed','fresh weekly interval excludes original authorization start')
            return
        # Corrected counters within this same authorized period are reporting,
        # never a new allowance or a reason to pause. Preserve highwater only.
        end=min(RESET,campaign.state.get('weekly_effective_end',RESET),row['resetsAt'])
        # Sample the monotonic clocks before wall time so scheduling delay only
        # makes this bound earlier. A later wall rollback cannot restore time.
        mono=time.monotonic();boot=time.clock_gettime(time.CLOCK_BOOTTIME);wall=time.time()
        left=max(0,end-wall)
        boot_end=min(campaign.state.get('weekly_effective_boot_end',float('inf')),boot+left,
                     ORIGINAL_BOOT_END+(end-RESET))
        mono_end=min(campaign.state.get('weekly_effective_monotonic_end',float('inf')),mono+left,
                     ORIGINAL_MONOTONIC_END+(end-RESET))
        high=max(campaign.state.get('weekly_confirmed_highwater',0),row['usedPercent'])
        request=getattr(campaign,'_weekly_request_generation',campaign.state.get('weekly_confirmation_generation',0))
        saved=dict(weekly_confirmed_usage=row,weekly_usage=row,weekly_confirmed_highwater=high,
                   weekly_effective_end=end,weekly_usage_error=None,
                   weekly_effective_boot_end=boot_end,weekly_effective_monotonic_end=mono_end,
                   weekly_effective_boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                   weekly_usage_observation_at=datetime.now(timezone.utc).isoformat(),
                   weekly_usage_worker_pid=campaign.state.get('worker_pid'),
                   weekly_usage_worker_start=campaign.state.get('worker_start'),
                   weekly_usage_thread_id=campaign.state.get('thread_id'))
        if request==campaign.state.get('weekly_confirmation_generation',0):
            saved['weekly_confirmation_pending']=False
        campaign.save(**saved)
        check_end(campaign)
        if not campaign.stop_reason:
            original_record(campaign,limits,notification=False)
    module.Campaign.record_rate_limits=record
    def refresh(campaign):
        if campaign.stop_reason:
            return
        campaign._weekly_request_generation=campaign.state.get('weekly_confirmation_generation',0)
        try:
            result=campaign.rpc.call('account/rateLimits/read',{},timeout=20)
            campaign.record_rate_limits(result.get('rateLimits'))
        except Exception as error:
            reject(campaign,None,'weekly_usage_unknown','bounded quota confirmation failed: '+type(error).__name__)
        finally:
            campaign._weekly_next_confirmation=time.monotonic()+5
    module.Campaign.refresh_weekly_usage=refresh
    def confirm_pending(campaign):
        check_end(campaign)
        if (not campaign.stop_reason and campaign.state.get('weekly_confirmation_pending')
                and time.monotonic()>=getattr(campaign,'_weekly_next_confirmation',0)):
            campaign.refresh_weekly_usage()
    module.Campaign.confirm_pending_weekly_usage=confirm_pending
    path=Path('/home/holden/mckernel/scripts/run_os_goal.py')
    tree=ast.parse(path.read_bytes(),filename=str(path))
    classes=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Campaign']
    begins=[n for n in classes[0].body if isinstance(n,ast.FunctionDef) and n.name=='begin']
    startup_reads=0
    for node in ast.walk(begins[0]):
        if (isinstance(node,ast.Expr) and isinstance(node.value,ast.Call)
                and ast.unparse(node.value).startswith("self.record_rate_limits(self.rpc.call('account/rateLimits/read'")):
            node.value=ast.parse('self.refresh_weekly_usage()',mode='eval').body;startup_reads+=1
    if len(begins)!=1 or startup_reads!=1:
        raise ValueError('one exact startup weekly usage-read seam required')
    scope=module.__dict__;prior=scope.get('begin');had='begin' in scope
    exec(compile(ast.fix_missing_locations(ast.Module(body=begins,type_ignores=[])),str(path),'exec'),scope)
    module.Campaign.begin=scope['begin']
    if had:scope['begin']=prior
    else:del scope['begin']
    # Poll in the real normal loop, never inside an event/RPC callback. Keep its
    # existing 30-second included-only cadence and stop/control handling.
    methods=[n for n in classes[0].body if isinstance(n,ast.FunctionDef) and n.name=='run']
    if len(methods)!=1:
        raise ValueError('canonical campaign loop interface differs')
    loops=[node for node in ast.walk(methods[0]) if isinstance(node,ast.While)
           and any(isinstance(child,ast.Expr) and ast.unparse(child)=='self.deliver_instruction()' for child in node.body)]
    if len(loops)!=1:
        raise ValueError('one canonical main-loop confirmation seam required')
    loop=loops[0]
    index=next(i for i,node in enumerate(loop.body) if isinstance(node,ast.Expr) and ast.unparse(node)=='self.deliver_instruction()')
    loop.body[index:index]=ast.parse('self.confirm_pending_weekly_usage()\nif self.stop_now:\n continue').body
    count=0
    for node in ast.walk(methods[0]):
        if (isinstance(node,ast.If) and ast.unparse(node.test)=='self.credit_guard is not None'
                and node.body and isinstance(node.body[0],ast.Expr)
                and ast.unparse(node.body[0])=='self.refresh_credit_budget()'):
            node.test=ast.Constant(value=True)
            node.body=ast.parse('self.refresh_weekly_usage()\nif self.stop_now:\n continue').body
            node.orelse=[];count+=1
    if count!=1:
        raise ValueError('one exact periodic usage-read seam required')
    scope=module.__dict__
    prior=scope.get('run');had='run' in scope
    exec(compile(ast.fix_missing_locations(ast.Module(body=methods,type_ignores=[])),str(path),'exec'),scope)
    module.Campaign.run=scope['run']
    if had:scope['run']=prior
    else:del scope['run']
