"""Functional OS/Rust only; no security testing. Future ordinary observation timing only."""
def remaining_from_birth(start_ticks, ticks_per_second, boot_now, target_seconds):
    if ticks_per_second <= 0 or start_ticks < 0 or target_seconds < 0:
        raise ValueError("invalid birth-clock geometry")
    age = boot_now - start_ticks / ticks_per_second
    if age < -1.0 / ticks_per_second:
        raise ValueError("future process birth")
    return max(0.0, target_seconds - age)
