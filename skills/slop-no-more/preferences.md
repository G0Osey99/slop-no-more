---
ban:                  # any of: semicolon, dash, colon, parenthesis, exclamation (comma-separated)
max_sentence_words:   # a number, or leave blank for no cap
contractions:         # yes, no, or blank to follow the genre
words_per_page:       # for --pages estimates; blank means 275 (12 pt, double-spaced)
---

# Writing preferences

Standing preferences for every piece this skill writes or rewrites. Fill in the front matter above and
add notes below. They override the skill's own style advice (for example, a banned semicolon means no
semicolon joins and no "widen the punctuation" move). An instruction in the current request overrides
this file.

In Claude Code you can keep a personal copy at `~/.claude/slop-no-more/preferences.md` instead; it is
read after this one and wins where the two differ.

`scripts/slopscan.py` reads the front matter and reports any banned punctuation or over-long sentence
in the text it scans. "Dash" means em dashes, en dashes between words, and spaced or doubled hyphens;
hyphenated words and number ranges are fine. Quotations, parenthetical citations, URLs, and verse
references are never counted.

## Notes

(Free text: word choice, tone, things to avoid, formatting habits. Write each as a plain rule.)
