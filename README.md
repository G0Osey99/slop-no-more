# Slop No More

A Claude skill that rewrites or reviews human-facing writing (papers, statements, application essays, cover letters, emails, posts, docs, fiction) so it reads as written by a specific person for a specific reader, without changing what it says.

## Install

**Claude Desktop / Claude.ai:** download `slop-no-more.zip` from the [latest release](../../releases/latest) and upload it under Settings → Capabilities → Skills.

**Claude Code (plugin):**

```
/plugin marketplace add G0Osey99/slop-no-more
/plugin install slop-no-more@slop-no-more
```

**Claude Code (manual):** copy `skills/slop-no-more` into `~/.claude/skills/`.

## Use

```
/slop-no-more  <paste text, or name a file>
/slop-no-more review  <text>        # findings only, no rewrite
/slop-no-more polish  <text>        # light touch
```

It also triggers on plain requests: "humanize this", "this got flagged by ZeroGPT", "does this sound like AI?".

The bundled scanner runs on its own (Python 3, standard library only):

```bash
python3 skills/slop-no-more/scripts/slopscan.py scan draft.txt --genre academic
python3 skills/slop-no-more/scripts/slopscan.py diff draft.txt draft_revised.txt
python3 skills/slop-no-more/scripts/slopscan.py outline draft.txt
python3 skills/slop-no-more/scripts/slopscan.py diff draft.txt draft_revised.txt --protect "Gaia catalog, IRB"   # lock your own terms
python3 skills/slop-no-more/scripts/slopscan.py scan essay.txt --words 300-375 --pages 2-3 --sentences 3     # hard limits
python3 skills/slop-no-more/scripts/slopscan.py overlap paper.docx reading.txt slides.txt   # source wording used without quotes
python3 skills/slop-no-more/scripts/slopscan.py profile my_old_paper.docx draft.txt          # draft vs how you actually write
```

## Preferences

`skills/slop-no-more/preferences.md` holds standing rules the skill follows on every piece: banned punctuation (`semicolon`, `dash`, `colon`, `parenthesis`, `exclamation`), an optional sentence-length cap, a contractions setting, and free-text notes on wording. It ships blank. Fill it in before zipping for Claude Desktop, or in Claude Code put your copy at `~/.claude/slop-no-more/preferences.md`. Preferences override the skill's own style advice, and the scanner reports every break.

Paths under `benchmark/` cited in `references/evidence.md` refer to the private development repo and are not included here.

## License

MIT
