# McKernel TXT mailbox

The phone interface is a pair of files on the `codex/mckernel-control-mailbox`
branch of `phoenix-hacking/mckernel`. The workstation reads your instructions;
its replies use a separate path so they cannot overwrite your input.

| File | Purpose |
| --- | --- |
| [mailbox.txt](https://github.com/phoenix-hacking/mckernel/blob/codex/mckernel-control-mailbox/mailbox.txt) | Your current instruction, written as ordinary UTF-8 text. |
| [mailbox-reply.txt](https://github.com/phoenix-hacking/mckernel/blob/codex/mckernel-control-mailbox/mailbox-reply.txt) | The latest acknowledgement, blocker or result. |
| [status.txt](https://github.com/phoenix-hacking/mckernel/blob/codex/mckernel-control-mailbox/status.txt) | The existing M14/M15 progress and agent-status report. |

## Send instructions from a phone

1. Open `mailbox.txt` on the control branch, choose **Edit**, and replace its
   contents with the instruction you want the computer to receive. No command
   prefix, JSON or message envelope is required.
2. Commit the change to that branch using your `phoenix-hacking` GitHub account.
3. After the new reader is adopted on the workstation, it checks every ten
   minutes. It reads the file at the exact commit that last changed it and queues
   that observed revision once.
4. Read `mailbox-reply.txt` for acknowledgement and subsequent output. `RECEIVED`
   means durable queueing; `RECEIVED BY CONTROLLER` means controller acceptance.
   Neither claims that the requested work has finished.

The **whole file** is the current instruction. Avoid retaining old commands that
you do not want included again. Unchanged content is not repeatedly submitted.
If you commit several changes between polls, only the latest revision observed
by the poller is submitted; this is not a promise to execute every intermediate
edit. A blank file is inactive, and clearing it does not cancel work already
queued. Git preserves prior file versions.

The reader verifies the configured numeric owner, commit signature and exact
blob contents. GitHub's signed web edits are supported. A foreign or unsigned
commit, binary content, invalid UTF-8, or a Git LFS pointer is reported as a file
input error. These checks do not disable the existing PR-comment mailbox.

## Capacity and notifications

There is no application-imposed limit on instruction length, multipart count,
retained mailbox history or total comments scanned. The old 8 KiB instruction,
2 MiB mailbox-state and 1,000-comment limits are removed. Comment polling uses
durable cursors and resumes across polls instead of loading a fixed first page
range forever. Status snapshots show recent receipt metadata and accurate total
counts; full history remains in the durable mailbox state.

This is not infinite storage. GitHub permits browser uploads up to 25 MiB and
blocks ordinary repository files larger than 100 MiB. API timeouts, disk space,
memory, rate limits and the controller/model's accepted context still matter.
Large historical logs are usually better kept as referenced files, with a clear
current instruction in `mailbox.txt`. Provider limits are documented in
[GitHub's large-file guidance](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

Notification comments contain the supplied message, with the existing mention
and HTML escaping. Repeated introductory text, reply instructions, footer and
push-triggered setup announcements are removed. A hidden event marker retains
deduplication. GitHub may still add its own email headers and unsubscribe links;
repository code cannot remove GitHub's email wrapper. Very long notifications
use multiple transport parts. GitHub documents email behavior in
[notification settings](https://docs.github.com/en/subscriptions-and-notifications/get-started/configuring-notifications).

## Existing comment interface

PR [#3](https://github.com/phoenix-hacking/mckernel/pull/3) continues to accept the
existing `/mckernel-instruct` and `/mckernel-resume` forms. For a large local text
file, use:

```sh
python3 -B scripts/send_os_goal_message.py --message-file /path/instruction.txt
```

The sender verifies the configured account and mailbox, splits exact UTF-8 text
into transport-sized comments, and deduplicates already posted parts. The
receiver queues a multipart instruction only after all parts arrive and its
complete SHA-256 matches. An uncertain post stops the sender; rerunning explicitly
rescans receipts before sending missing parts. Reusing the same file deduplicates
the same logical message. Conflicting historical parts require review, not blind
replay. Malformed manual assemblies remain recorded; a fresh complete corrected
assembly can be received without deleting history.

## Workstation adoption and recovery

Root must adopt the reviewed source and `scripts/os_goal_mailbox.json` through
the normal workstation update path. Creating the files on GitHub alone does not
activate the reader. Preserve existing mailbox state, queue records and delivery
receipts. Do not replace a running controller or reset its saved identity to
install this interface. Ordinary TXT instructions do not activate a paused goal
or release an actual account, service, ownership or resource hold.

The notification workflow executes from `codex/local-native-staging-repair` after
adoption; its workflow file must also continue to exist on the repository's
default branch for GitHub dispatch discovery. The file reader and reply publisher
use the control branch. Mailbox data commits use `[skip ci]`; code changes retain
their normal checks and the dedicated offline mailbox suite.

Replies use compare-and-swap writes. Uncertain writes back off and read remote
state before another attempt. A delayed acceptance acknowledgement preserves a
result written since the previous mailbox mirror. Email delivery continues if
the reply-file write fails. Poll timestamps, source revisions, receipt states and
errors remain observable without copying full message bodies into heartbeats.
