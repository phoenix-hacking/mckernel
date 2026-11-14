"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure M14 finite-cutoff source binding, without any process/control action.
"""
import math

def positive_triplet(value):
    if type(value) is not list or len(value)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) or x<=0 for x in value):
        raise ValueError('three finite positive UTC/MONO/BOOT cutoffs required')
    return value

def validate_monotone_cutoffs(old,new):
    positive_triplet(old);positive_triplet(new)
    if any(after>before for before,after in zip(old,new)):
        raise ValueError('cutoff extension refused')
    return new

def bind_cutoffs(old,armed,bootstrap):
    caps=armed['earliest_control_caps']
    actual=positive_triplet([caps['deadline_epoch'],caps['monotonic_deadline'],caps['boot_deadline']])
    initial=positive_triplet([bootstrap['deadline'],bootstrap['watcher_cutoff_lower'],bootstrap['boot_deadline']])
    positive_triplet(old)
    validate_monotone_cutoffs(old,actual)
    validate_monotone_cutoffs(old,initial)
    if old[0]!=1793253600 or actual[0]!=1793253600 or initial[0]!=1793253600:
        raise ValueError('same original UTC deadline required')
    if bootstrap['boot_id']!='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb':
        raise ValueError('same original boot required')
    watcher=armed['actors']['watcher']
    if (bootstrap['watcher_pid'],bootstrap['watcher_start'])!=(watcher['pid'],watcher['start']):
        raise ValueError('actual initial watcher identity required')
    return validate_monotone_cutoffs(old,[min(a,b,c) for a,b,c in zip(old,actual,initial)])
