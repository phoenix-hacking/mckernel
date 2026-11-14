"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
AST override only: load into exact h990 helper namespace; do not execute as a legacy driver.
Only the Popen cwd keyword differs from the accepted owned_capture body.
"""
def owned_capture(command,path,wall_seconds,limits,started_reader=process_start):
 """Fixed ordinary child; errors always retire/join before stream FD reads.

 No signal is sent after reap. Unexpected descendants make this fixed-command
 envelope fail closed even if termination succeeds; their independent reaping
 is not invented. The caller's direct child remains unreaped while signalling.
 """
 global stopping
 process=None;birth=None;rc=None;direct=False;error=None;retirement_error=None;timed=False;unexpected=[];begin=time.monotonic()
 outfd=os.open(path/'stdout',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:errfd=os.open(path/'stderr',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 except BaseException:os.close(outfd);raise
 with os.fdopen(outfd,'wb') as out,os.fdopen(errfd,'wb') as err:
  try:
   # A stop cannot interrupt fork->Popen ownership assignment. The child must
   # restore the old mask before exec so ordinary TERM remains effective.
   previous=signal.pthread_sigmask(signal.SIG_BLOCK,STOP_SIGNALS)
   try:
    def child_limits():
     signal.pthread_sigmask(signal.SIG_SETMASK,previous);limits()
    process=subprocess.Popen(command['argv'],cwd=command.get('cwd'),stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,preexec_fn=child_limits)
   finally:signal.pthread_sigmask(signal.SIG_SETMASK,previous)
   birth=started_reader(process.pid)
   write(path/'started.json',dict(pid=process.pid,start=birth))
   if not wait_terminal(process,wall_seconds):raise subprocess.TimeoutExpired(command['argv'],wall_seconds)
  except BaseException as exc:
   error=type(exc).__name__+': '+str(exc);timed=isinstance(exc,subprocess.TimeoutExpired)
  finally:
   if process is not None:
    # Suppress asynchronous re-entry throughout bounded retirement and direct
    # wait. A pending stop is observed after ownership is safely resolved.
    previous=signal.pthread_sigmask(signal.SIG_BLOCK,STOP_SIGNALS)
    if error is not None:stopping=True;signal.setitimer(signal.ITIMER_REAL,0)
    anchored=False
    try:
     terminal_unreaped(process);anchored=True
     group=members(process.pid);unexpected=[pid for pid in group if pid!=process.pid]
     if unexpected and error is None:error='unexpected fixed-command group members'
     if error is not None:
      try:os.killpg(process.pid,signal.SIGTERM)
      except ProcessLookupError:pass
      ended=wait_terminal(process,2)
      # While the creator is unreaped its numeric group cannot be reused.
      # Kill any still-present group before reaping; never signal it later.
      group=members(process.pid)
      if not ended or any(pid!=process.pid for pid in group):
       try:os.killpg(process.pid,signal.SIGKILL)
       except ProcessLookupError:pass
       need(wait_terminal(process,2),'owned creator did not terminate after KILL')
    except BaseException as exc:
     retirement_error=type(exc).__name__+': '+str(exc)
     # Only an unreaped known creator permits this group signal. Census
     # uncertainty does not grant authority over a reaped/reused PGID.
     if anchored:
      try:os.killpg(process.pid,signal.SIGKILL)
      except ProcessLookupError:pass
      except BaseException as kill_error:retirement_error+='; KILL '+repr(kill_error)
    finally:
     try:
      rc=process.wait(timeout=2);direct=True
      write(path/'direct-wait.json',dict(pid=process.pid,start=birth,returncode=rc,direct_child_joined=True))
     except BaseException as exc:retirement_error=(retirement_error or '')+'; direct wait '+repr(exc)
     finally:signal.pthread_sigmask(signal.SIG_SETMASK,previous)
  absent=False;remaining=[]
  if process is not None and direct:
   try:remaining=members(process.pid);absent=not remaining
   except BaseException as exc:retirement_error=(retirement_error or '')+'; final census '+repr(exc)
  # No process action follows direct wait; no potentially reused PGID is signalled.
  joined=dict(pid=process.pid if process else None,start=birth,returncode=rc,direct_child_joined=direct,group_absent=absent,remaining_group_members=remaining,unexpected_group_members=unexpected,timed_out=timed,error=error,retirement_error=retirement_error,seconds=time.monotonic()-begin)
  write(path/'direct-join.json',joined)
 # FD hashing happens only after direct join has been persisted and files closed.
 joined['closed_streams']=True
 joined['captures']={name:hashed(path/name,32<<20) for name in ('stdout','stderr')}
 return joined
