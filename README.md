# git-rekt

A new git subcommand, `git rekt`, that **irreversibly destroys the local git
repository you run it in**. For laughs, for pranks on your own machines, for
that one repo you swore you'd never look at again.

> ⚠️ **This is a joke tool that does real, permanent damage.** There is no undo.
> It nukes the reflog and overwrites the object store with random bytes. Point
> it only at repositories you are happy to lose. Your working-tree *files* are
> left alone — only the git history/plumbing is destroyed.

It does **not** touch remotes, does **not** phone home, and is loud about
everything it does. It only ever affects the repo in the current directory, and
it asks for explicit confirmation first.

## What it does

Run in order (all by default), each step best-effort:

| step       | effect |
|------------|--------|
| `scramble` | Rewrites every commit message to random garbage (real history, clown wig). |
| `branches` | Renames all branches to nonsense. |
| `recovery` | Expires the reflog, clears stashes, deletes `logs/`, `ORIG_HEAD`, etc. — kills the safety nets. |
| `loop`     | Points `HEAD` into a self-referential symbolic-ref cycle so `checkout`/`switch`/`status` hard-fail. |
| `index`    | Overwrites the staging index with random bytes. |
| `objects`  | **The kill shot:** overwrites every loose object and packfile with random bytes. git can no longer read a single object. |

Afterwards, essentially every git command returns `fatal:`.

## Install

`git` discovers any executable named `git-rekt` on your `PATH` and exposes it as
`git rekt`. Installing this package creates exactly that executable — including
a `git-rekt.exe` shim on Windows — so the one install works on Linux, macOS and
Windows.

**Recommended — [pipx](https://pipx.pypa.io) (isolated, global):**

```sh
pipx install git+https://github.com/kammt/git-rekt.git
# or from a local checkout:
pipx install .
```

**With pip:**

```sh
pip install --user .
# make sure the user scripts dir is on PATH:
#   Linux/macOS: ~/.local/bin
#   Windows:     %APPDATA%\Python\Scripts
```

Then, from inside any repo:

```sh
git rekt --list      # show the chaos steps, change nothing
git rekt --dry-run   # show what would happen, change nothing
git rekt             # ask for confirmation, then destroy
```

No install needed to try it safely: `python3 -m git_rekt --dry-run`.

## Usage

```
git rekt [-y|--yes] [-n|--dry-run] [--only STEP ...] [--list]

  -n, --dry-run   show what would happen; harm nothing
  --only STEP     run only this step (repeatable); default runs all
  --list          list the chaos steps and exit
  -y, --yes       skip both confirmation prompts (for the brave / scripts)
```

By default you must answer `y` **and** type the repository's directory name to
proceed. `--yes` bypasses both — use with care.

## Requirements

- Python 3.8+
- the `git` binary on `PATH`

## License

See [LICENSE](LICENSE). Provided as-is, with no warranty. If you `git rekt` a
repository you cared about, that is a `you` problem, as the tool's name,
confirmation prompt, and this entire README tried to warn you.
