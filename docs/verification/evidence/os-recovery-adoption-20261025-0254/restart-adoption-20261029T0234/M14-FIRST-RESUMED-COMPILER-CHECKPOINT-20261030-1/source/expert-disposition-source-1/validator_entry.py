"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only validator; immutable loader and operation admission required.
"""
import os
import signal
import compositor
import validator_consumer


def _consume_prepared(plan,operation):
    """Retain the actual plan through consumption; close only terminal success."""
    complete=False
    try:
        plan.revalidate()
        result=validator_consumer.consume(plan)
        if type(result) is not validator_consumer.SourceCollection:
            raise RuntimeError('collector data result unavailable')
        plan.revalidate()
        if plan.session.closed:raise RuntimeError('session closed before terminal completion')
        plan.session.close(operation)
        complete=True
        return result
    finally:
        if not complete:
            # Registration precedes publication; even publication/close errors
            # cannot discard the plan or its process-owned descriptors.
            operation.retain_session_unknown(plan.session,plan)


def emit_stdout(result,operation,stream,nonce):
    """Emit the single diagnostic record; retain ownership on uncertain output."""
    try:
        raw=validator_consumer.stdout_record(result,nonce)
        written=stream.write(raw)
        if written!=len(raw):raise RuntimeError('short diagnostic data output')
        stream.flush()
    except BaseException:
        operation.retain_session_unknown(operation.session,operation.plan)
        raise


def run():
    if os.geteuid()!=1000:raise ValueError('ordinary validator UID required')
    channel=int(os.environ['MCKERNEL_CUSTODY_FD'])
    journal=int(os.environ['MCKERNEL_PIDFD_CUSTODY_JOURNAL_FD'])
    nonce=os.environ['MCKERNEL_PIDFD_CUSTODY_NONCE']
    operation=compositor.OperationCustody(journal,nonce)
    try:
        plan=compositor.prepare_from_inherited_channel(channel,operation)
        result=_consume_prepared(plan,operation)
        return result,operation
    except BaseException:
        if operation.session is not None and operation.state!='UNKNOWN_RETAINED':
            operation.retain_session_unknown(operation.session,operation.plan)
        if operation.state=='UNKNOWN_RETAINED':
            # External operation owner/watchdog retains and manages this process.
            while True:signal.pause()
        raise


if __name__=='__main__':raise RuntimeError('SOURCE ONLY: actual operation admission and verified loader absent')
