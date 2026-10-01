# Fixed-path Time Machine service

This fork includes a machine-specific service that reconciles generated development directories with Time Machine's fixed-path exclusions.

## Why it exists

The standard `tmutil addexclusion PATH` mechanism stores a sticky extended attribute. Time Machine discovers those attributes through Spotlight. An exclusion can therefore appear effective through `tmutil isexcluded` while being absent from a backup's exclusion manifest.

The fixed service uses `tmutil addexclusion -p`. Fixed exclusions are stored in Time Machine's `SkipPaths`, do not depend on Spotlight, and apply again when a directory is recreated at the same path.

## Policy

[`config/raine.json`](../config/raine.json) defines the machine policy:

- scan `~/code` and `~/work/epicgames`;
- exclude complete directories ending in `__worktrees`;
- detect generated directories from project sentinel files;
- explicitly cover `~/node_modules` and `~/mdwatch/target`.

The service resolves symlinks before registering them. This makes repositories using the mbx target cache exclude the actual cache location. Resolved outputs are accepted only beneath the explicitly configured `~/Library/Caches/mbx/targets` root.

## Installation

Run:

```console
scripts/install-fixed
```

The installer asks for administrator authentication because fixed exclusions require root. It installs:

- `/usr/local/libexec/asimov-fixed`, owned by root;
- `/usr/local/libexec/asimov-launcher`, a dedicated ad-hoc-signed executable;
- `/Library/Application Support/Asimov/config.json`, owned by root;
- `/Library/LaunchDaemons/com.raine.asimov.fixed.plist`;
- `~/Library/LaunchAgents/com.raine.asimov.health.plist`.

It disables the previous `com.raine.asimov` sticky-exclusion agent and starts both jobs.

Grant Full Disk Access to `/usr/local/libexec/asimov-launcher` in System Settings under **Privacy & Security → Full Disk Access**, then kick the daemon:

```console
sudo launchctl kickstart -k system/com.raine.asimov.fixed
```

The launcher remains the responsible executable while it waits for the reconciler child process. This avoids granting broad access to `/usr/bin/python3` or a shell interpreter. The service reports a missing authorization as a failed reconciliation rather than recording success.

## Operation

The root daemon runs at login/startup and at minutes 0, 15, 30, and 45. Every run:

1. scans every configured root;
2. fails if a root is missing or unreadable;
3. validates that discovered paths are under configured roots;
4. preserves previously managed fixed paths so recreated directories remain excluded;
5. adds missing fixed exclusions;
6. rereads Time Machine preferences to verify the write;
7. checks a backup manifest created after reconciliation when available;
8. atomically publishes status under `/var/db/asimov`.

The user health agent checks status every 15 minutes and displays a notification when reconciliation is missing, stale, or failed. An unchanged failure is notified at most once per day; a changed failure is reported immediately.

## Commands

```console
/usr/local/libexec/asimov-fixed discover
/usr/local/libexec/asimov-fixed doctor
/usr/local/libexec/asimov-fixed verify
```

`doctor` verifies service freshness. `verify` compares the managed set with the newest available backup exclusion manifest. A `pending` verification means no backup has started since the latest reconciliation; it is not a configuration failure.

## Security properties

The daemon code and configuration are root-owned. It never executes project files or package-manager commands. Before changing Time Machine preferences, it rejects paths outside configured roots and unrecognized generated-directory names. Existing exclusions not owned by this service are preserved.

Managed exclusions are not removed automatically. This avoids losing protection after an incomplete scan or temporarily absent project. Cleanup should be an explicit reviewed operation.
