"""Functional owned-harness exception read only; no security testing.
No inferior calls, writes, breakpoints, locals enumeration or memory scans.
CPython3.9 debug-info typed fields only; compact ASCII strings required.
"""
import gdb,json,shlex
MAX_TEXT=4096
MAX_INTERPRETERS=4
MAX_THREADS=16
MAX_FRAMES=128

def need(value,message):
 if not value:raise gdb.GdbError(message)

def pointer_type(name):return gdb.lookup_type(name).pointer()
def read_ascii(obj):
 need(int(obj)!=0,'null unicode pointer')
 value=obj.cast(pointer_type('PyASCIIObject')).dereference()
 expected=int(gdb.parse_and_eval('&PyUnicode_Type'))
 need(int(value['ob_base']['ob_type'])==expected,'expected exact Unicode type')
 state=value['state'];size=int(value['length'])
 need(int(state['compact'])==1 and int(state['ascii'])==1 and int(state['ready'])==1 and int(state['kind'])==1,'unsupported Unicode layout')
 need(0<=size<=MAX_TEXT,'ASCII length bound')
 raw=bytes(gdb.selected_inferior().read_memory(int(obj)+gdb.lookup_type('PyASCIIObject').sizeof,size))
 return raw.decode('ascii','strict')

def tuple_items(obj):
 value=obj.cast(pointer_type('PyTupleObject')).dereference()
 need(int(value['ob_base']['ob_base']['ob_type'])==int(gdb.parse_and_eval('&PyTuple_Type')),'expected exact tuple type')
 size=int(value['ob_base']['ob_size']);need(0<=size<=128,'tuple size bound')
 return value['ob_item'].address.cast(pointer_type('PyObject').pointer()),size

def read_exception(error,expected_type):
 need(int(error)!=0,'null error local')
 base=error.cast(pointer_type('PyBaseExceptionObject')).dereference()
 type_name=base['ob_base']['ob_type'].dereference()['tp_name']
 # tp_name is type metadata, not another local; bounded NUL-terminated read.
 name=type_name.string(length=len(expected_type)+1).split('\0',1)[0]
 need(name==expected_type,'exception type differs')
 args,count=tuple_items(base['args']);need(count==1,'exception must have one argument')
 return read_ascii(args[0])

class ReadRecoverError(gdb.Command):
 def __init__(self):super().__init__('read-exact-recover-error',gdb.COMMAND_DATA)
 def invoke(self,argument,from_tty):
  words=shlex.split(argument);need(len(words)==2,'usage: read-exact-recover-error exact_filename expected_exception_type')
  filename,expected_type=words
  need(filename.startswith('/') and len(filename)<=MAX_TEXT and expected_type in ('Refusal','RuntimeError'),'exact target arguments')
  interp=gdb.parse_and_eval('_PyRuntime.interpreters.head');seen_interps=set();seen_threads=set();matches=[];frames=0
  while int(interp):
   need(len(seen_interps)<MAX_INTERPRETERS and int(interp) not in seen_interps,'interpreter bound/cycle');seen_interps.add(int(interp))
   state=interp.dereference()['tstate_head']
   while int(state):
    need(len(seen_threads)<MAX_THREADS and int(state) not in seen_threads,'thread bound/cycle');seen_threads.add(int(state))
    frame=state.dereference()['frame'];seen_frames=set()
    while int(frame):
     need(len(seen_frames)<MAX_FRAMES and int(frame) not in seen_frames,'frame bound/cycle');seen_frames.add(int(frame));frames+=1
     value=frame.dereference();code=value['f_code'].dereference()
     if read_ascii(code['co_name'])=='recover' and read_ascii(code['co_filename'])==filename:
      names,count=tuple_items(code['co_varnames']);need(count==int(code['co_nlocals']),'local metadata count')
      indexes=[i for i in range(count) if read_ascii(names[i])=='error'];need(len(indexes)==1,'unique error local metadata')
      # Only this one local value is dereferenced. No f_locals/global dump.
      local=value['f_localsplus'].address.cast(pointer_type('PyObject').pointer())[indexes[0]]
      matches.append(read_exception(local,expected_type))
     frame=value['f_back']
    state=state.dereference()['next']
   interp=interp.dereference()['next']
  need(len(matches)==1,'must find exactly one matching recover frame')
  gdb.write(json.dumps(dict(status='PASS_EXACT_RECOVER_ERROR_READ',co_filename=filename,co_name='recover',local='error',exception_type=expected_type,error_argument=matches[0],interpreters=len(seen_interps),threads=len(seen_threads),frames_visited=frames),sort_keys=True)+'\n')
ReadRecoverError()
