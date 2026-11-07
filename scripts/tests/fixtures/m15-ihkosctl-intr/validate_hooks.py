"""Narrow nm-global binding check for the corrected actual CLI C objects."""
import re

def validate(output):
 symbols={}
 for line in output.splitlines():
  fields=line.split()
  if len(fields) not in (2,3):raise ValueError('Unexpected nm row: '+line)
  symbols[fields[-1].split('@')[0]]=fields[-2]
 undefined={name for name,kind in symbols.items() if kind in ('U','w','v')}
 required={'observation_open','observation_ioctl','observation_close'}
 if not required<=undefined:raise ValueError('Missing actual CLI hook imports: '+repr(required-undefined))
 forbidden={name for name in undefined if re.fullmatch(r'(?:open(?:64|at|at64)?|__open.*|ioctl|__ioctl.*|close|__close.*)',name)}
 if forbidden:raise ValueError('Real device-capable CLI imports remain: '+repr(forbidden))
 if symbols.get('observed_main')!='T':raise ValueError('Actual main export is not defined')
 return {'required_undefined':sorted(required),'forbidden_undefined':[],'actual_main_export':'T'}
