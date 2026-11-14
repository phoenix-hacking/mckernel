# Ten-minute engineering steering — prepared, not started

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The old supervisor2590193/start37928121 is absent. Selected process/timer inspection found no current campaign monitor or user timer. VELOCITY-REVIEWS ends at the2026-10-22 stopped checkpoint; its prior reviews used30-minute intervals. Existing runtime watcher/launcher recovery is separate from engineering reviews. Evidence is in EXISTING-SUPERVISION.json.

`steer_every_ten_minutes.py` reuses the existing `run_os_goal.py` queue_instruction, atomic_json and utc function bytes, extracted with AST to avoid importing launcher/server code. It queues an intelligent review request for the existing exact thread immediately on first authorized launch and at most once every600seconds thereafter. The dispatcher performs the engineering reasoning and steering. M14 and P12 both progress when resources and reviewed controls permit; the short Rust-first priority is explicitly superseded.

The supervisor reads small state and two8KiB log tails. It keeps two compact snapshots, a tiny durable journal and at most two1MiB event logs. A single retained private flock prevents duplicate instances. Any pending/sending queue backlog suppresses submission. Durable intent before queue publication makes ambiguous crash/restart refuse another submission. It stops on inactive/paused/stopped/held goal, policy error, thread change, invalid or older-than120-second real heartbeat, identity change or an unresolved earlier intent. It never resumes/restarts, retries service holds, calls a model/API, invokes root, or launches workloads. No canonical docs/state or other agents' files were changed.

Queue submission is the existing launcher API, which has no atomic compare-thread parameter. The script rechecks exact thread/goal/heartbeat/launcher identity immediately before queuing, includes the exact target identity and no-action-on-change instruction in the message, and stops if the post-submit check changes. This reduces but cannot make the existing queue primitive transactional with an external state change. A dispatcher already inside an indivisible operation may consume a reminder late; backlog suppression deliberately avoids accumulating reminders. Queuing is not proof that the review was completed.

Proposed supervisor launch, to be invoked only by the coordinator after source/fixture acceptance:

```sh
/usr/bin/taskset -c 0 /usr/bin/prlimit --as=268435456:268435456 --fsize=33554432:33554432 --nofile=128:128 --core=0:0 -- /home/holden/anaconda3/bin/python3 -I -B /home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/ten-minute-steering/steer_every_ten_minutes.py --run
```

No supervisor process has been started. Its private lock/journal remain absent until that launch; existing native/campaign locks stay untouched. If it exits on a hold/stop or uncertain submission, human/coordinator review is required; it never restarts itself.

`test_steering.py` contains meaningful temporary-campaign fixtures for paused/stopped/complete goals, checkpoint/hold/policy, real heartbeat versus updated_at, future/stale heartbeat, thread change,600-second dedup, pending/sending backlog, durable uncertain submission, existing queue API publication, bounded tails, unchanged campaign state and thread/pause changes during the final read. Fixtures invoke only the existing queue API in a temporary directory, with no live queue/process/workload. All14 fixtures passed in the single explicitly granted CPU0 job (unittest0.128s, exit0); the slot was released. TEST-RESULT.json binds the exact tested main and fixture hashes. No tested-core source change followed that run. The optional stop helper is separately prepared, not executed.

Proposed test command after root explicitly transfers the ordinary CPU0 slot:

```sh
/usr/bin/taskset -c 0 /usr/bin/timeout --signal=TERM --kill-after=6s 90s /usr/bin/prlimit --as=2147483648:2147483648 --cpu=60:60 --fsize=33554432:33554432 --nofile=256:256 --core=0:0 -- /home/holden/anaconda3/bin/python3 -I -B /home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/ten-minute-steering/test_steering.py
```

The main writes PID/start_ticks/boot_id/script_path in supervisor.json. The coordinator may stop this exact private monitor using `/home/holden/anaconda3/bin/python3 -I -B /home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/ten-minute-steering/stop_supervisor.py`. This separately prepared helper opens a pidfd, verifies boot/PID birth/UID/script, records private stop-request.json and sends TERM only to that pidfd; it never targets campaign processes. No helper execution or signal was performed. Main startup refuses a retained explicit stop request.
