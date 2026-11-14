"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only validator caller; verified loader and operation admission still required.
"""
import os
import signal
import compositor


def run():
    if os.geteuid()!=1000:raise ValueError('ordinary validator UID required')
    channel=int(os.environ['MCKERNEL_CUSTODY_FD'])
    journal=int(os.environ['MCKERNEL_PIDFD_CUSTODY_JOURNAL_FD'])
    nonce=os.environ['MCKERNEL_PIDFD_CUSTODY_NONCE']
    operation=compositor.OperationCustody(journal,nonce)  # held before session constructor
    try:
        return compositor.prepare_from_inherited_channel(channel,operation)
    except BaseException:
        if operation.state=='UNKNOWN_RETAINED':
            # Preserve the actual unverified FD and caller record. The external
            # operation owner/watchdog must assess and retire this process; no
            # native or child ownership conclusion follows from this pause.
            while True:signal.pause()
        raise


if __name__=='__main__':raise RuntimeError('SOURCE ONLY: actual operation admission and verified loader absent')
