# stack-test-stacks

A project to facilitate testing the [stack](https://github.com/bozemanpass/stack) tool.

This project defines a set of stacks and components thereof that are used in various tests in the [stack](https://github.com/bozemanpass/stack) project.

Nothing here is meant to be useful on its own. Each stack, container and compose
file is a *fixture*: it exists because some test in the `stack` repo needs a
concrete thing to deploy, and it is shaped so that the test can observe whether
the tool did the right thing. Changing a fixture will usually break an assertion
somewhere in `stack`, so treat the two repos as a pair.

## Layout

```
stack-files/
  stacks/      one directory per stack (stack.yml, optional stack.lock, README, deploy hooks)
  compose/     the compose files the stacks reference as "pods"
  containers/  Containerfile + build.sh (+ run.sh) for the images built from this repo
  config/      external config fixtures mounted into deployments
```

A stack's `pods:` entry names a compose file in `stack-files/compose` without
the `composefile-` prefix or the `.yml` suffix -- pod `test-database` is
`compose/composefile-test-database.yml`. Container names likewise resolve by
convention: `bozemanpass/test-container` is built from
`containers/bozemanpass-test-container`, which is why most `containers:` entries
need no explicit `ref:` or path.

## Stacks

| Stack | Pod(s) | What it is for |
| --- | --- | --- |
| `test-stack` | `test` | The general-purpose smoke-test stack. Deploy/start/stop/logs, config and environment variable plumbing, volumes, external stacks, deploy hooks, and the deprecated `repos:` path. |
| `test-database-stack` | `test-database` | Postgres plus a client container. Covers stack-declared secrets, service-to-service networking, and portless services. |
| `test-backup-stack` | `test-backup` | Backup and restore: volume backup, the `backup-exclude` annotation, and `backup-command` dumps. |
| `test-s3-stack` | `test-s3` | A local S3-compatible object store, mixed into other deployments that need somewhere to put a backup repository. |
| `test-static-content-stack` | `test-static-content` | The `static-content` wrapper: a source repo turned into a served site, with a checked-in `stack.lock`. |
| `test-static-content-subdir-stack` | `test-static-content-subdir` | The same wrapper serving only a subdirectory (`content-root: pages`) of the source repo. |

### `test-stack`

The workhorse. `stack.yml` is named `test` (deliberately not matching its
directory) and keeps one entry under the deprecated `repos:` key --
`stack-test-project@test-branch` -- so the "throw in an extra repo" path,
including `@branch` handling, stays exercised until that feature goes away.
`stack validate` warning about it here is expected, not a defect.

Its compose file mounts three volumes (`/data`, `/data2`, and a read-only
`/config`) and passes five `STACK_TEST_PARAM_*` variables, some with `FAILED`
defaults so a test can tell "the value arrived" from "the value did not".
`stack-files/config/external-test/external-test.env` is the external config
fixture that gets mounted at `/config`.

`deploy/commands.py` holds the deploy hooks. They exist to be observed rather
than to do anything: `init()` adds `test-variable-1` to the generated spec, and
`create()` writes a known string into a known file in the deployment directory.
Both leave a side effect a shell test asserts on -- keep the strings in step
with the assertions in `bozemanpass/stack`.

### `test-database-stack`

Postgres 16 (`test-database-container`) plus a psql client
(`test-database-client`). `POSTGRES_PASSWORD` is declared under `secrets:` in
`stack.yml`, so it is generated at deploy time and injected into both
containers; it appears in no file in this repo.

The database publishes no ports on purpose -- the only things that reach it are
the client, which is part of the stack, and `manage exec` -- which makes this
the fixture that catches a deployer emitting no Service at all for a portless
service. The client waits for the database, creates `test_table_1` if it is not
already there, and logs distinct lines for "test data already exists" versus
"test data does not exist"; the test harness reads those lines, so it can tell a
fresh deployment from one restored or restarted onto existing data.

### `test-backup-stack` and `test-s3-stack`

`test-backup-stack` keeps two volumes: `app-data` is backed up normally, and
`app-data2` carries `# @stack backup-exclude` and must not appear in a backup --
on Kubernetes that becomes a `k8up.io/backup=false` annotation on the PVC, a
different mechanism from the Docker target's, which is why the fixture lives in
the application stack and runs against both targets. A `backup-command`
annotation `cat`s a payload file so its stdout is captured as a snapshot of its
own, standing in for a real database dump. `test-database-stack` is the same
idea done properly: the data directory is excluded and `pg_dump` output *is* the
backup.

`test-s3-stack` (SeaweedFS, Apache-2.0) is mixed into the backup test on the
Docker target to give restic somewhere to write its repository; on a real
cluster the test points at a real object store and does not mix it in. It
configures an S3 identity via an entrypoint wrapper because current SeaweedFS
images reject signed writes without one, and it excludes its own volume from
backup -- backing a repository up into itself is not useful.

### The static-content stacks

These two do not build a container from this repo at all. They point at
`github.com/bozemanpass/stack-test-static-content` and apply the
`static-content` wrapper, which turns a repo of files into a served site. The
subdir variant adds `content-root: pages` to serve only part of the source repo.
`test-static-content-stack` is the one with a committed `stack.lock`, and the
one CI publishes, so it is also the fixture for lock pinning and image
publishing.

## Containers

Images built from this repo are tagged `:stack` locally. Each directory under
`stack-files/containers` holds a `Containerfile` and a `build.sh` that sources
`build-base.sh` from `$STACK_CONTAINER_BASE_DIR` -- the interface `stack build`
expects.

- **`bozemanpass/test-container`** -- Ubuntu + nginx. Its `run.sh` reports
  whether `/data` and `/data2` are mounted and whether each is fresh or has been
  seen before (it drops an `exists` file with a timestamp), echoes any
  `STACK_TEST_PARAM_*` it was given, dumps anything under `/config`, then runs
  nginx in the foreground to stay alive. Everything it prints is there for a
  test to grep. Used by `test-stack` and `test-backup-stack`.
- **`bozemanpass/test-database-container`** -- `postgres:16-bullseye`,
  unmodified apart from `EXPOSE 5432`.
- **`bozemanpass/test-database-client`** -- Ubuntu + `postgresql-client`, with
  the wait/create/report logic described above. It requires
  `POSTGRES_PASSWORD` to be injected and fails loudly if it is not, rather than
  falling back to a default and looking like a slow-starting database.

## CI

Two GitHub Actions workflows, both in `.github/workflows`. Both install the
`stack` binary from the latest release and log in to `ghcr.io` with the
built-in `GITHUB_TOKEN`.

### `publish-images.yml` -- Publish Container Images

Runs on every push to `main`, and on demand via **workflow_dispatch**. It runs
`stack prepare --publish-images --image-registry ghcr.io` for
`test-static-content-stack`, so the images that stack pins are built and pushed
to GHCR identified by this repo's commit hash. Only clean, committed,
fully-pinned state publishes; anything else builds as an unpublishable
`stackdev-` image.

### `update-locks.yml` -- Update Locks

Manual (**workflow_dispatch**) only, with an optional `stack` input to limit the
run to one stack directory; the scheduled trigger is present but commented out.
It is serialized by a `update-locks` concurrency group.

For each stack it deletes `stack.lock` and re-runs `stack prepare`, which
regenerates the pins at current upstream state -- wrapper commits, source-repo
commits, external image digests -- and validates them by building. **This is the
only sanctioned way locks change: delete and regenerate, never hand-edit.** If
nothing moved, the job stops there. Otherwise it commits the new locks as
`github-actions[bot]`, publishes the stacks named in `PUBLISH_STACKS` (the same
set as `publish-images.yml`), and pushes.

Publishing happens inline, *before* the push, because a push made with the
default `GITHUB_TOKEN` does not trigger other workflows -- so `publish-images.yml`
would never fire for the lock commit.
