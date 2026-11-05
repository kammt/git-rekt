"""
git-rekt  --  get your repository rekt.

A deliberately destructive joke tool. It takes the git repository you run it
in and turns it into modern art: scrambled history, looping refs, corrupted
objects. When it is done, `git` just fails. There is no undo.

Everything here operates on the repository in the current directory (and, as
its opening act, force-pushes an empty history over any remote branches that
repository is configured to track). It is loud about what it is doing, asks
for explicit confirmation first, and does not phone home or try to hide. It is
a prank you point at your own foot.

Cross-platform: pure Python + the `git` binary. Works on Linux, macOS, Windows.
"""

import argparse
import os
import random
import shutil
import string
import subprocess
import sys

# ---------------------------------------------------------------------------
# cosmetics
# ---------------------------------------------------------------------------

SKULL = r"""
          ____________
         /            \
        /   R E K T    \
       |   .--.  .--.   |
       |  (    )(    )  |
        \     /\/\     /
         \   |....|   /
          \__|::::|__/
             |::::|
             '----'
"""

WORDS = [
    "yeet", "borked", "oops", "void", "chaos", "goblin", "spaghetti", "cursed",
    "doom", "blorp", "kaboom", "nope", "undefined", "segfault", "potato",
    "quantum", "banana", "gremlin", "entropy", "glitch", "wibble", "frobnicate",
]


def c(code, text):
    """Wrap text in an ANSI color unless output is not a TTY."""
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"


red = lambda s: c("1;31", s)
yellow = lambda s: c("1;33", s)
green = lambda s: c("1;32", s)
dim = lambda s: c("2", s)


# ---------------------------------------------------------------------------
# git helpers
# ---------------------------------------------------------------------------

def git(args, cwd, capture=True, input_bytes=None):
    """Run a git command. Never raises; returns CompletedProcess."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        input=input_bytes,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def git_text(args, cwd):
    """Run git and return decoded stdout stripped, or '' on failure."""
    proc = git(args, cwd)
    if proc.returncode != 0:
        return ""
    return proc.stdout.decode("utf-8", "replace").strip()


def random_name():
    return "{}-{}-{}".format(
        random.choice(WORDS),
        random.choice(WORDS),
        "".join(random.choices(string.hexdigits.lower(), k=6)),
    )


def random_message():
    kind = random.random()
    if kind < 0.34:
        # a fake sha-ish blob
        return "".join(random.choices("0123456789abcdef", k=40))
    if kind < 0.67:
        # word salad
        return " ".join(random.choices(WORDS, k=random.randint(3, 9)))
    # line noise
    pool = string.ascii_letters + string.digits + " !@#$%^&*()"
    return "".join(random.choices(pool, k=random.randint(12, 64)))


# ---------------------------------------------------------------------------
# chaos modules -- each is best-effort and swallows its own errors so the
# carnage always continues to the finale.
# ---------------------------------------------------------------------------

def wipe_remotes(cwd, gitdir):
    """Opening act: force-push an empty history over every tracked remote.

    For each local branch that has a configured upstream, build a parentless
    commit pointing at the empty tree and force-push it onto the remote
    branch. Every commit that lived on that remote branch is removed -- the
    branch survives, holding a single empty commit and nothing else.

    Best-effort: branches without an upstream are skipped, and any push that
    fails (no network, no write access, protected branch) is noted and the
    carnage moves on.
    """
    fmt = "%(refname:short)\t%(upstream:remotename)\t%(upstream:short)"
    listing = git_text(["for-each-ref", "--format=" + fmt, "refs/heads"], cwd)
    if not listing:
        print(dim("    (no local branches)"))
        return 0

    # the canonical empty tree; written so commit-tree can reference it
    empty_tree = git(["mktree"], cwd, input_bytes=b"").stdout.decode().strip()
    if not empty_tree:
        print(red("    could not create empty tree; skipping remote wipe"))
        return 0

    pushed = 0
    seen_remote = False
    for line in listing.split("\n"):
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        branch, remote, upstream = (p.strip() for p in parts)
        if not remote or not upstream:
            continue  # this branch tracks no remote -- leave it
        seen_remote = True
        remote_branch = (
            upstream[len(remote) + 1:]
            if upstream.startswith(remote + "/")
            else branch
        )
        commit = git(
            ["commit-tree", empty_tree, "-m", random_message()], cwd
        ).stdout.decode().strip()
        if not commit:
            continue
        refspec = "{}:refs/heads/{}".format(commit, remote_branch)
        res = git(["push", "--force", remote, refspec], cwd)
        if res.returncode == 0:
            pushed += 1
            print(green(f"    force-pushed empty history over {remote}/{remote_branch}"))
        else:
            tail = res.stderr.decode("utf-8", "replace").strip().splitlines()
            print(dim(f"    could not push {remote}/{remote_branch}: {tail[-1] if tail else 'failed'}"))
    if not seen_remote:
        print(dim("    (no branch tracks a remote)"))
    print(green(f"    nuked history on {pushed} remote branch(es)"))
    return pushed


def scramble_messages(cwd, gitdir):
    """Rewrite every commit's message to garbage, in place, via plumbing.

    Processes commits parents-first so parent hashes can be remapped, then
    repoints every ref at the rewritten tip. Trees/blobs are untouched, so
    `git log` shows your real history wearing a clown wig -- right up until
    the object store gets shredded later.
    """
    order = git_text(["rev-list", "--all", "--topo-order", "--reverse"], cwd)
    if not order:
        print(dim("    (no commits to scramble)"))
        return 0
    commits = order.split("\n")
    mapping = {}
    for sha in commits:
        raw = git(["cat-file", "commit", sha], cwd).stdout
        if not raw:
            continue
        header, sep, message = raw.partition(b"\n\n")
        if not sep:
            continue
        new_lines = []
        for line in header.split(b"\n"):
            if line.startswith(b"parent "):
                old_parent = line[7:].decode().strip()
                new_lines.append(b"parent " + mapping.get(old_parent, old_parent).encode())
            else:
                new_lines.append(line)
        new_commit = b"\n".join(new_lines) + b"\n\n" + random_message().encode() + b"\n"
        written = git(
            ["hash-object", "-w", "-t", "commit", "--stdin"],
            cwd,
            input_bytes=new_commit,
        )
        new_sha = written.stdout.decode().strip()
        if new_sha:
            mapping[sha] = new_sha

    # repoint refs at the rewritten commits
    refs = git_text(["for-each-ref", "--format=%(refname)"], cwd)
    repointed = 0
    for ref in refs.split("\n"):
        ref = ref.strip()
        if not ref:
            continue
        old = git_text(["rev-parse", ref], cwd)
        if old in mapping:
            if git(["update-ref", ref, mapping[old]], cwd).returncode == 0:
                repointed += 1
    print(green(f"    scrambled {len(mapping)} commit message(s), repointed {repointed} ref(s)"))
    return len(mapping)


def garble_branches(cwd, gitdir):
    """Rename every branch (and retag every tag) to nonsense."""
    renamed = 0
    branches = git_text(["branch", "--format=%(refname:short)"], cwd)
    for b in branches.split("\n"):
        b = b.strip()
        if not b:
            continue
        if git(["branch", "-m", b, random_name()], cwd).returncode == 0:
            renamed += 1
    print(green(f"    renamed {renamed} branch(es) to gibberish"))
    return renamed


def symref_loop(cwd, gitdir):
    """Point HEAD into a self-referential symbolic-ref cycle.

    git caps symbolic-ref resolution depth, so instead of an *infinite* loop
    you get a hard 'too many levels of symbolic references' failure on nearly
    every checkout/switch/status. Same outcome: git refuses to work.
    """
    loop_ref = os.path.join(gitdir, "refs", "heads")
    try:
        os.makedirs(loop_ref, exist_ok=True)
        # HEAD -> refs/heads/rekt-loop -> refs/heads/rekt-loop (itself)
        with open(os.path.join(gitdir, "HEAD"), "w", newline="\n") as fh:
            fh.write("ref: refs/heads/rekt-loop\n")
        with open(os.path.join(loop_ref, "rekt-loop"), "w", newline="\n") as fh:
            fh.write("ref: refs/heads/rekt-loop\n")
        print(green("    HEAD now chases its own tail (symref cycle)"))
        return True
    except OSError as exc:
        print(red(f"    symref loop failed: {exc}"))
        return False


def nuke_recovery(cwd, gitdir):
    """Destroy the safety nets: reflog, logs, stash, ORIG_HEAD, gc the rest."""
    git(["reflog", "expire", "--expire=now", "--all"], cwd)
    git(["stash", "clear"], cwd)
    git(["gc", "--prune=now", "--quiet"], cwd)
    shutil.rmtree(os.path.join(gitdir, "logs"), ignore_errors=True)
    for name in ("ORIG_HEAD", "MERGE_HEAD", "FETCH_HEAD", "CHERRY_PICK_HEAD"):
        try:
            os.remove(os.path.join(gitdir, name))
        except OSError:
            pass
    print(green("    reflog, stash and recovery handles obliterated"))


def corrupt_index(cwd, gitdir):
    """Replace the index with random bytes."""
    idx = os.path.join(gitdir, "index")
    try:
        with open(idx, "wb") as fh:
            fh.write(os.urandom(random.randint(32, 128)))
        print(green("    index replaced with static"))
    except OSError:
        pass  # a repo with no index is already plenty broken


def corrupt_objects(cwd, gitdir):
    """The finale: overwrite every loose object and packfile with garbage.

    After this, git cannot read a single object. Fatal and irreversible.
    """
    objects = os.path.join(gitdir, "objects")
    hit = 0
    for root, _dirs, files in os.walk(objects):
        # skip the 'info' dir which holds only text metadata -- nuking the
        # actual object data below is what does the real damage
        for name in files:
            path = os.path.join(root, name)
            try:
                with open(path, "wb") as fh:
                    fh.write(os.urandom(random.randint(16, 256)))
                hit += 1
            except OSError:
                pass
    print(green(f"    overwrote {hit} object/pack file(s) with random bytes"))
    return hit


def shuffle_lines(path):
    """Re-order the lines of a single file at random. Best-effort."""
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return False
    if not data:
        return False
    lines = data.split(b"\n")
    random.shuffle(lines)
    try:
        with open(path, "wb") as fh:
            fh.write(b"\n".join(lines))
        return True
    except OSError:
        return False


def shuffle_and_rename(cwd, gitdir):
    """The encore: shred the working tree too.

    Walk the working tree bottom-up, shuffle the lines inside every file, then
    rename every file and directory to a random string. The .git directory is
    skipped (its object store is already confetti). What is left is a tree of
    gibberish-named files full of scrambled lines -- the repo's *contents* are
    now noise, matching its destroyed history.
    """
    top = git_text(["rev-parse", "--show-toplevel"], cwd)
    if not top:
        print(dim("    (no working tree -- bare repo)"))
        return 0
    gitdir_abs = os.path.abspath(gitdir)
    shuffled = renamed = 0
    for root, dirs, files in os.walk(top, topdown=False):
        root_abs = os.path.abspath(root)
        # never touch anything inside the git directory itself
        if root_abs == gitdir_abs or root_abs.startswith(gitdir_abs + os.sep):
            continue
        for name in files:
            path = os.path.join(root, name)
            if shuffle_lines(path):
                shuffled += 1
            try:
                os.rename(path, os.path.join(root, random_name()))
                renamed += 1
            except OSError:
                pass
        for name in dirs:
            sub = os.path.join(root, name)
            if os.path.abspath(sub) == gitdir_abs:
                continue  # leave .git/ named .git/
            try:
                os.rename(sub, os.path.join(root, random_name()))
                renamed += 1
            except OSError:
                pass
    print(green(f"    shuffled {shuffled} file(s), renamed {renamed} path(s) to gibberish"))
    return renamed


# order matters: wipe the remote first (while refs still point at real
# commits), then the git-level rewrites (they need a working repo), then raw
# object corruption as the kill shot, and finally shred the working tree.
CHAOS = [
    ("remote", "Force-push an empty history over every tracked remote branch", wipe_remotes),
    ("scramble", "Scramble every commit message into garbage", scramble_messages),
    ("branches", "Rename all branches to gibberish", garble_branches),
    ("recovery", "Shred reflog / stash / recovery handles", nuke_recovery),
    ("loop", "Trap HEAD in a self-referential symref loop", symref_loop),
    ("index", "Corrupt the staging index", corrupt_index),
    ("objects", "Overwrite the object store with random bytes (fatal)", corrupt_objects),
    ("files", "Shuffle every file's lines and rename all paths to gibberish", shuffle_and_rename),
]


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------

def find_repo(start):
    """Return (toplevel_or_None, absolute_git_dir_or_None, is_bare)."""
    gitdir = git_text(["rev-parse", "--absolute-git-dir"], start)
    if not gitdir:
        return None, None, False
    bare = git_text(["rev-parse", "--is-bare-repository"], start) == "true"
    top = git_text(["rev-parse", "--show-toplevel"], start)
    return (top or None), gitdir, bare


def confirm(toplevel, gitdir):
    target = toplevel or gitdir
    name = os.path.basename(os.path.normpath(target))
    print(red(SKULL))
    print(red("  git-rekt is about to PERMANENTLY destroy this repository:"))
    print(yellow(f"    {target}"))
    print()
    print("  This cannot be undone. No reflog, no backup, no mercy.")
    print("  History, object store AND working-tree files are destroyed,")
    print("  and any remote branches this repo tracks get force-wiped too.")
    print()
    try:
        if input("  Proceed? [y/N] ").strip().lower() not in ("y", "yes"):
            return False
        typed = input(f'  Type the repo name "{name}" to confirm: ').strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    if typed != name:
        print(red("  Name did not match. Backing away slowly."))
        return False
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="git rekt",
        description="Irreversibly destroy the current git repository. For laughs.",
    )
    parser.add_argument(
        "-y", "--yes", action="store_true",
        help="skip the confirmation prompts (dangerous; for scripts/the brave)",
    )
    parser.add_argument(
        "-n", "--dry-run", action="store_true",
        help="show what would happen without destroying anything",
    )
    args = parser.parse_args(argv)

    toplevel, gitdir, bare = find_repo(os.getcwd())
    if not gitdir:
        print(red("fatal: not a git repository. Nothing to rekt."), file=sys.stderr)
        return 128

    if args.dry_run:
        print(yellow("DRY RUN -- no repository will be harmed.\n"))
        print(f"Target: {toplevel or gitdir}")
        if bare:
            print(dim("(bare repository)"))
        print("\nWould perform:")
        for key, desc, _ in CHAOS:
            print(f"  [{key}] {desc}")
        return 0

    if not args.yes and not confirm(toplevel, gitdir):
        print(dim("Aborted. Your repository lives to see another commit."))
        return 1

    print()
    print(red(">>> getting rekt <<<"))
    for key, desc, fn in CHAOS:
        print(yellow(f"  [{key}] {desc}"))
        try:
            fn(os.getcwd(), gitdir)
        except Exception as exc:  # noqa: BLE001 - nothing stops the carnage
            print(red(f"    step raised {exc!r} (continuing anyway)"))

    print()
    print(red("  Repository rekt. "), end="")
    print("git is now a paperweight. GG.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
