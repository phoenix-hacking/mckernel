Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The IHK source commit is preserved in this exact verified bundle because the upstream
remote did not provide noninteractive push authentication. No retry or URL change was
made. This is a source checkpoint; the new producer, install and native joins remain open.

From the McKernel repository, after initializing IHK at the recorded base, restore with:

```sh
git -C ihk fetch ../docs/verification/evidence/m15-canonical-source-producer-integration-20261024-1/IHK-SOURCE-COMMITS.bundle HEAD
git -C ihk checkout 0d62995c788bb8fa1e9bf32b8e6f93b6f1da2a6d
```

The bundle includes the preceding local control-plane correction as its necessary parent.
Main source selectors and mcps are part of the matching main checkpoint.
