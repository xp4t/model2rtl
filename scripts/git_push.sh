#!/usr/bin/env bash
#
# model2rtl -- commit the remaining work, tag it, and push to origin.
#
#   ./scripts/git_push.sh --dry-run   # print every git command, run none
#   ./scripts/git_push.sh             # commit, tag, and PUSH to GitHub
#
# ---------------------------------------------------------------------------
# THIS SCRIPT PUSHES TO A PUBLIC REMOTE.
#
#   origin  https://github.com/xp4t/model2rtl.git
#
# Once pushed, the history and every file in it are public and may be cached
# or mirrored even if you delete them afterwards. Run --dry-run first and read
# what it says it will send.
# ---------------------------------------------------------------------------
#
# CURRENT STATE, as measured when this script was written:
#
#   * main is already in sync with origin/main (cb4dc66); the six stage
#     commits are pushed.
#   * The tags stage2-refresh, stage3, stage4 and stage5 exist LOCALLY but
#     were never pushed -- `git ls-remote --tags origin` is empty.
#   * The model2rtl CLI / compiler generalization is still uncommitted.
#
# So this script does three things: commits the CLI work, creates the missing
# release tags, and pushes commits and tags together.
#
# It never force-pushes and never rewrites history. If the remote has moved on,
# it stops and tells you to pull rather than clobbering someone else's work.

set -euo pipefail

DRY_RUN=0
SKIP_TESTS=0
for arg in "$@"; do
    case "$arg" in
        --dry-run)    DRY_RUN=1 ;;
        --skip-tests) SKIP_TESTS=1 ;;
        *) echo "unknown option: $arg" >&2
           echo "usage: $0 [--dry-run] [--skip-tests]" >&2; exit 1 ;;
    esac
done

run() {
    if [ "$DRY_RUN" = "1" ]; then
        printf '  '; printf '%q ' "$@"; printf '\n'
    else
        "$@"
    fi
}
say() { printf '\n== %s ==\n' "$*"; }

# ---------------------------------------------------------------------------
say "0/5  preconditions"
# ---------------------------------------------------------------------------
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
    echo "not inside a git work tree" >&2; exit 1; }
cd "$(git rev-parse --show-toplevel)"

BRANCH=$(git rev-parse --abbrev-ref HEAD)
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "<none>")
[ "$REMOTE_URL" = "<none>" ] && { echo "no 'origin' remote configured" >&2; exit 1; }

echo "repo:   $(pwd)"
echo "branch: $BRANCH"
echo "remote: $REMOTE_URL"
[ "$DRY_RUN" = "1" ] && echo "MODE:   dry run, nothing is committed or pushed"

# the fabric is the one artifact that must never move
EXPECT_FABRIC=7757362642b37fd0044bb7b323467116998caee69bad091d8454fc6010691e1c
ACTUAL_FABRIC=$(sha256sum rtl/mnist_mlp_fabric.v | cut -d' ' -f1)
[ "$ACTUAL_FABRIC" = "$EXPECT_FABRIC" ] || {
    echo "REFUSING TO PUSH: rtl/mnist_mlp_fabric.v is not the frozen file." >&2
    echo "  expected $EXPECT_FABRIC" >&2
    echo "  found    $ACTUAL_FABRIC" >&2
    exit 1; }
echo "fabric: frozen and verified"

[ -f .gitignore ] || {
    echo "REFUSING TO PUSH: .gitignore is missing. Without it a 1.3 GB .venv/" >&2
    echo "and ~190 MB of regenerable build output become pushable." >&2
    exit 1; }

# a .venv or bytecode reaching the index means .gitignore is not doing its job
LEAKED=$(git ls-files | grep -E '(^\.venv/|__pycache__/|\.pyc$)' || true)
[ -n "$LEAKED" ] && {
    echo "REFUSING TO PUSH: these are tracked but should be ignored:" >&2
    printf '%s\n' "$LEAKED" | head -10 >&2; exit 1; }
echo "index:  no virtualenv or bytecode tracked"

# ---------------------------------------------------------------------------
say "1/5  the full test suite must pass before anything is published"
# ---------------------------------------------------------------------------
if [ "$SKIP_TESTS" = "1" ]; then
    echo "  SKIPPED by --skip-tests. You are publishing untested work."
elif [ "$DRY_RUN" = "1" ]; then
    echo "  (dry run: would run 'pytest tests -q')"
else
    PY=.venv/bin/python
    [ -x "$PY" ] || PY=python3
    if ! "$PY" -m pytest tests -q; then
        echo "REFUSING TO PUSH: tests failed." >&2
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
say "2/5  commit the model2rtl CLI / compiler work"
# ---------------------------------------------------------------------------
if [ -n "$(git status --porcelain)" ] || [ "$DRY_RUN" = "1" ]; then
    run git add \
        src/model2rtl/cli.py \
        src/model2rtl/compile.py \
        src/model2rtl/genmodel.py \
        src/model2rtl/ingest.py \
        src/model2rtl/quantize.py \
        src/model2rtl/qat_general.py \
        tests/test_cli_compile.py \
        scripts/render_readme.py \
        scripts/git_push.sh \
        pyproject.toml \
        README.md \
        .gitattributes
    run git commit -m "feat(cli): compile any two-layer MLP to RTL from the command line

    model2rtl --model my_model.h5 --output ./rtlout

Turns the staged MNIST demonstration into an actual compiler. A trained Keras
model goes in, portable Verilog comes out, for any two-layer dense network
rather than only the 784-32-10 one this project was built around.

The generalization is ADDITIVE. golden.py, contract.py, fabric.py,
verilog_emit.py and param_verilog.py are frozen -- their hashes are recorded in
four stage reports -- so nothing there was edited. genmodel.py reimplements the
integer arithmetic for an arbitrary topology and proves it reproduces the
frozen oracle exactly: 0 mismatches over 16,000 hidden values, 5,000 logits and
500 predictions. Compiling the frozen MNIST parameters regenerates
mnist_mlp_fabric.v and mnist_mlp_params_portable.v byte for byte, so no
verified result moved.

New pieces:
  ingest.py       Keras .h5/.keras and float .npz; rejects convolution,
                  pooling, normalisation, recurrence, wrong activations and
                  layer counts, quoting the layers it actually found
  quantize.py     post-training quantization; picks the requantisation shift
                  AND the input scale by measurement on calibration data
                  rather than assuming, and says so when it cannot
  qat_general.py  quantization-aware fine-tuning, seeded from the PTQ solution
  compile.py      emits the RTL and asserts weight independence on every run
  cli.py          the model2rtl entry point

Measured on real downloaded models: a Keras spam MLP (57-32-1) and a
Fashion-MNIST 784-64-10 both compile, elaborate under Icarus and Yosys, and the
Fashion design simulates with 0 logit differences against its integer model
over 300 held-out images. Post-training quantization cost 0.3 points there;
--quantize qat gained 3.0 over the float baseline. Three-layer MLPs and
convolutional models are refused with a specific message, which is the point:
compiling them anyway would produce hardware that computes a different network.

Also found and routed around a latent defect in the frozen
param_verilog.emit_portable: it widens the layer-2 bias by calling
bias_bus_word() without passing its own cfg, so it silently uses the default
MNIST bus width for every topology. Invisible for 784-32-10, wrong for anything
else. The MNIST path still uses the frozen verified emitter; other shapes use a
correct one in compile.py. The frozen file is untouched and the defect is
documented where the workaround lives.

README rewritten as a beginner entry point: install, a copy-pasteable quick
start, the port handshake with a working testbench, supported-model rules with
real rejection messages, and an explicit list of what this is NOT. Its code
blocks are extracted and executed as part of checking this commit.

429 tests passing. All 25 frozen artifacts byte-identical.

Adds .gitattributes. GitHub was reporting this repo as 62.6% SourcePawn,
because Linguist maps .sp to SourcePawn and OpenROM writes its SPICE netlists
with that extension -- 23.8 MB of them. build/ is 98.4% of the repository by
bytes and is entirely tool output, so it is marked linguist-generated along
with the .sp, .log, .lef and .hex artifacts. rtl/ stays counted as Verilog on
purpose: it is generated, but it is the deliverable. The language bar becomes
roughly 71% Python, 29% Verilog, which is what was actually written."
else
    echo "  nothing to commit"
fi

# ---------------------------------------------------------------------------
say "3/5  create the tags that were never made"
# ---------------------------------------------------------------------------
run git tag -f stage6 -m "Stage 6: final report, consolidation, project complete"
run git tag -f v1.0 -m "model2rtl 1.0 -- quantized MLP to portable RTL, verified through synthesis"
run git tag -f v1.1 -m "model2rtl 1.1 -- command-line compiler for any two-layer MLP"

# ---------------------------------------------------------------------------
say "4/5  what will be sent"
# ---------------------------------------------------------------------------
if [ "$DRY_RUN" = "0" ]; then
    git fetch origin "$BRANCH" --quiet || true
fi
AHEAD=$(git rev-list --count "origin/$BRANCH..HEAD" 2>/dev/null || echo "?")
BEHIND=$(git rev-list --count "HEAD..origin/$BRANCH" 2>/dev/null || echo "?")
echo "  commits to push : $AHEAD"
echo "  commits behind  : $BEHIND"
if [ "$BEHIND" != "0" ] && [ "$BEHIND" != "?" ]; then
    echo "REFUSING TO PUSH: origin/$BRANCH has $BEHIND commit(s) you do not have." >&2
    echo "Run 'git pull --rebase origin $BRANCH', re-run the tests, then retry." >&2
    echo "This script will not force-push over someone else's work." >&2
    exit 1
fi
echo "  tags to push    : $(git tag | tr '\n' ' ')"
if [ "$AHEAD" != "0" ] && [ "$AHEAD" != "?" ]; then
    echo "  files in those commits:"
    git diff --stat "origin/$BRANCH..HEAD" -- | tail -20 | sed 's/^/    /'
fi

# ---------------------------------------------------------------------------
say "5/5  push"
# ---------------------------------------------------------------------------
if [ "$DRY_RUN" = "1" ]; then
    echo "  git push origin $BRANCH"
    echo "  git push origin --tags"
    echo
    echo "dry run complete. Nothing was committed, tagged or pushed."
    exit 0
fi

run git push origin "$BRANCH"
run git push origin --tags

echo
echo "pushed to $REMOTE_URL"
git log --oneline -3 | cat
echo
echo "remote tags now:"
git ls-remote --tags origin | sed 's/^/  /' | head -10
