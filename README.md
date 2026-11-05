# git-rekt

A new git subcommand, `git rekt`, that **irreversibly destroys the git
repository you run it in — and force-wipes the history off any remotes it
tracks**. For laughs, for pranks on your own machines, for that one repo you
swore you'd never look at again.

> ⚠️ **This is a joke tool that does real, permanent damage.** There is no undo.
> It nukes the reflog, overwrites the object store with random bytes, and then
> shuffles and renames your working-tree files into gibberish. As its very
> first act it also **force-pushes an empty history over any remote branches
> this repo tracks** — so the destruction is not even confined to your machine.
> Point it only at repositories (and remotes) you are happy to lose.

It is loud about everything it does. Apart from the force-push over its own
tracked remotes, it only affects the repo in the current directory, and it asks
for explicit confirmation first.

## What it does

Every step always runs, in this order, each one best-effort:

| step       | effect |
|------------|--------|
| `remote`   | **First, off-machine:** for every branch that tracks a remote, force-pushes a single empty commit over the remote branch, removing all of its commits from the remote. |
| `scramble` | Rewrites every commit message to random garbage (real history, clown wig). |
| `branches` | Renames all branches to nonsense. |
| `recovery` | Expires the reflog, clears stashes, deletes `logs/`, `ORIG_HEAD`, etc. — kills the safety nets. |
| `loop`     | Points `HEAD` into a self-referential symbolic-ref cycle so `checkout`/`switch`/`status` hard-fail. |
| `index`    | Overwrites the staging index with random bytes. |
| `objects`  | **The kill shot:** overwrites every loose object and packfile with random bytes. git can no longer read a single object. |
| `files`    | **The encore:** re-orders the lines within every working-tree file at random, then renames every file and directory to a random string (`.git/` excepted). |

Afterwards, essentially every git command returns `fatal:`, and the working
tree is a pile of gibberish-named files full of shuffled lines.

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
git rekt --dry-run   # show what would happen, change nothing
git rekt             # ask for confirmation, then destroy
```

No install needed to try it safely: `python3 -m git_rekt --dry-run`.

## Usage

```
git rekt [-y|--yes] [-n|--dry-run]

  -n, --dry-run   show what would happen; harm nothing
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
