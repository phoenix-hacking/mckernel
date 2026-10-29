"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure weekly source-binding predicates only. No controller/account/guard/proc reads.
"""
import math

IDENTITY=dict(limit_id='codex',window_duration_mins=10080,resets_at=1793774133)
ROOT='01a18582-1fc6-77b1-bfb6-15c86483f579'
BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'

def need(ok,why):
 if not ok:raise ValueError(why)

def triplet(values):
 need(type(values)in(list,tuple)and len(values)==3 and all(type(v)in(int,float)and math.isfinite(v)and v>0 for v in values),'positive finite epoch/MONOTONIC/BOOTTIME triplet')
 return list(values)

def caps(value):
 need(value['boot_id']==BOOT,'same actual boot')
 return triplet([value['deadline'],value['monotonic_deadline'],value['boot_deadline']])

def validate_authorization(auth,window):
 need(auth['status']=='EXPLICIT_WEEKLY_ONLY_WINDOW_AUTHORIZED_SOURCE_PREPARATION_NOT_RUNTIME_ARM' and auth['root_thread']==ROOT,'actual current Root weekly source authorization')
 need(auth['weekly_limit_identity']==window['weekly_limit_identity']==IDENTITY,'same weekly allowance/reset; no renewed allowance')
 need(auth['stop_at_weekly_used_percent']==window['stop_at_weekly_used_percent']==100,'stop at exhaustion')
 need(auth['prepaid_credit_fallback']is False and window['allow_prepaid_fallback']is False and window['billing_mode']=='included_only','included-only with no prepaid transition')
 need(auth['automatic_credit_purchase']is window['automatic_credit_purchase']is False and auth['api_key_billing']is window['api_key_billing']is False,'no purchases/API billing')
 need(window['status']=='ACTUAL_AUTHORIZED_LAUNCH_WINDOW' and window['boot_id']==BOOT and window['native_release']is False and auth['native_release']is False,'window metadata grants no native authority')
 need(auth['deadline_epoch']==window['deadline_epoch']==IDENTITY['resets_at'],'weekly reset is finite upper bound')
 triplet([window['deadline_epoch'],window['monotonic_deadline'],window['boot_deadline']])
 return IDENTITY.copy()

def minimum_caps(auth,window,earliest,actual_armed_caps):
 """The new envelope replaces old06UTC; each new envelope source may tighten it."""
 validate_authorization(auth,window)
 need(actual_armed_caps is not None,'actual new weekly armed cap projection required; no historical receipt')
 rows=[caps(auth['caps']),[window['deadline_epoch'],window['monotonic_deadline'],window['boot_deadline']],caps(earliest['caps']),caps(actual_armed_caps)]
 return [min(row[i]for row in rows)for i in range(3)]

def observer_pins(old,shared_guard,guardian,limits):
 """Mechanical DATA delta only; caller authenticates/reviews supplied BYTE refs."""
 import copy
 need(shared_guard is not None and guardian is not None,'actual reviewed weekly source refs required')
 result=copy.deepcopy(old)
 result.update(shared_guard=shared_guard,guardian=guardian,limits=triplet(limits))
 need(set(result)==set(old),'same observer INPUTS schema')
 for key in old:
  if key not in ('shared_guard','guardian','limits'):need(result[key]==old[key],'unchanged historical observer pin '+key)
 return result
