"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
PRIVATE CANDIDATE ONLY: function definition; does nothing unless explicitly called.
For exact reviewed in-process recovery on Python3.8 only. No owner methods,
ownership flags, signals, ACK, filesystem writes or historical exit-code repair.
Root must independently review/bind the live intervention and current identity.
"""
def install_missing_waitstatus_converter(os_module, version_info):
    if tuple(version_info[:2]) != (3, 8):
        raise RuntimeError("expected affected Python3.8")
    if getattr(os_module, "__name__", None) != "os":
        raise RuntimeError("expected live os module")
    if hasattr(os_module, "waitstatus_to_exitcode"):
        raise RuntimeError("converter already exists; do not replace")
    # Capture only the existing POSIX status decoders; no owner object is held.
    exited = os_module.WIFEXITED
    exit_status = os_module.WEXITSTATUS
    signaled = os_module.WIFSIGNALED
    term_signal = os_module.WTERMSIG
    def waitstatus_to_exitcode(status):
        if exited(status):
            return exit_status(status)
        if signaled(status):
            return -term_signal(status)
        raise ValueError("wait status does not describe an exited or signaled process")
    os_module.waitstatus_to_exitcode = waitstatus_to_exitcode
    return {"compatibility_converter_installed": True,
            "owner_flags_changed": 0, "owner_methods_invoked": 0,
            "historical_statuses_reconstructed": False}
