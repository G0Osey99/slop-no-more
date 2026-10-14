# Evidence behind the rules

Load when the user asks why a rule exists or when a rule seems to conflict with the text. Figures are corpus-level. None of them is a per-text threshold or a probability of AI authorship.

## 1. Our first calibration (v1.0-v1.4 bands; superseded by §1d)
- **Human:** Brown corpus, 500 samples across 15 genres (1961 American English, about 450 words each).
- **AI:** 500 StoryScope stories (5 models × 100 prompts, about 450-word excerpts) plus 21 expository texts written by Claude Opus, Sonnet, and Haiku from plain prompts.
- **Index AUC:** 0.88 overall, 0.86 fiction, 0.80 expository. Human median 4.4, human p90 about 10, AI median 14.8. These are in-sample numbers, the human baseline is from 1961, and the expository AI set is small, so read them as a direction, not a guarantee.
- **What separated current-Claude expository prose from human prose** (AUC, or medians human vs AI):
  - Longest sentence: 49 vs 33 words. Share of sentences 35+ words: 13% vs 0% (AUC 0.11–0.15, so lower in AI).
  - Colons in running prose: 1.4 vs 5.6 per 1,000 words (AUC 0.81).
  - Semicolons, parentheses, and dashes combined: 8.5 vs 0 per 1,000 (AI uses almost none).
  - Mean paragraph length: 92 vs 60 words. Average length of a paragraph's last sentence: 24 vs 18.5 words.
  - Three-item lists: 0 vs 2.6 per 1,000 (AUC 0.66). -ing words: 22 vs 31 per 1,000 (AUC 0.72). Type/token ratio over 300 words: 0.58 vs 0.63 (AUC 0.72).
  - Did **not** separate: the classic AI-vocabulary list (current Claude avoids it), dash density, overall sentence-length variance (CV), stock connectives, hedges.
- **Phrases that fire more on human text than AI and were removed from the stock list:** "in order to", "not only… but also", "on the other hand", "the importance of", "we must", "let us".

## 1b. ZeroGPT experiments (2026-10-08, see `benchmark/zerogpt/RESULTS.md`)
- Human controls: 1961 theology essays scored 0% and 0%. The 1978 Chicago Statement (human, formal doctrine) scored 17%.
- Skills that edit minimally (Humanizer, Sepia, no-ai-slop, SlopMonster, slop-no-more v1.0–1.1) stayed within a few points of the original, or went above it. College essay: original 82%; these arms scored 77–91%.
- Controlled test on a reflection paper (baseline 89%): word-level re-voice only 87%, sentence-boundary reshaping only 81%, **both together 44%**. A humanize-text version scored 35%. Removing just its "…right?" tag and one padded aside raised it to 77%, and blind judges ranked that version last.
- Small edits of equal quality can move a score by about 7 points either way, so tuning past one pass is chasing noise.
- `slopscan.py diff` reports **RETAINED** (prose sentences kept nearly verbatim). It tracks these scores: arms that kept 60–90% of sentences scored high, and rewrites that kept 30% or less scored low.

## 1c. Checks added in v1.4 (2026-10-08)
A v1.3 rewrite of the doctrinal statement scanned at 4.65 ("typical human range"), and a review still found seven misses. Before any new check got weight, we measured how often it fires on the calibration set above (450-word samples) and on the full-length Brown texts (about 2,000 words each). None of the five separated human from AI text, so all five report as `[info]` with no weight. The index is unchanged on all 1,021 calibration samples (AUC 0.889 overall, 0.868 fiction, 0.793 expository).

| Check | Human expository (450 w / full) | AI expository (21) | Human fiction (450 w / full) | AI fiction (500) |
|---|---|---|---|---|
| `stance_labels` | 0% / 0% | 0% | 0% / 0% | 0% |
| `sentence_floor` | 9.4% / 9.9% | 0% | 22.2% / 11.1% | 13.0% |
| `noun_rider` | 0% / 0% | 0% | 0% / 0% | 1.6% |
| `summary_closer` | 2.1% / 9.9% | 0% | 2.4% / 7.9% | 0.6% |
| `vague_attribution` | 0.5% / 1.9% | 0% | not run on fiction | not run |

- **`sentence_floor` threshold:** the human p10 for the share of sentences of 8 words or fewer, on full-length Brown texts: 3.0% expository, 20.6% fiction (medians 10.5% and 34.4%). At 450 words the expository p10 is 0%, because one sample in ten has no short sentence at all, so the shorter cut can't set a floor. The check needs 20+ sentences. Plain-prompted Claude is not short of short sentences (median 20.8%); the floor catches a rewrite that joined and trimmed too much.
- **`stance_labels` and `vague_attribution`** fired on none of the 21 plain-prompted AI texts, but did fire on the AI-written doctrinal statement in `benchmark/inputs` and on its rewrites by the benchmark arms (all ten for `stance_labels`, eight of ten for `vague_attribution`). Neither reference set has much first-person academic argument, so the data can't say how often a student writes this way. They stay in the report as prompts to check.
- **Paragraphs from Word.** slopscan now reads a block whose lines each end a sentence as one paragraph per line. No calibration sample changed (they use blank lines). The v1.3 rewrite went from 4.65 to 6.65 because its Discussion paragraphs are now measured one by one, and their closing sentences average 18.7 words (human p25 19.4).

## 1d. Calibration v2 (2026-10-08): bigger corpus, weights from held-out data
Files, sources, and scripts: `benchmark/calibration_v2/` (README, `manifest.csv`, `results/`). The bands in `data/human_bands.json` and the per-genre weights in `slopscan.py` (`INFO_IN`) come from here.

- **Corpus:** 1,921 samples of about 450 words in six genres. **Human, all written before 2022:** MICUSP upper-level student papers and PERSUADE 2.0 grade 6-12 essays (academic), r/changemyview (essay), Enron sent mail (email), r/tifu and blogger.com posts (post), Reddit r/offmychest and r/confession plus MICUSP response papers (reflection), WritingPrompts and MICUSP creative writing (fiction). **AI:** responses to real user requests from LMArena (Apr-Oct 2025: o3, GPT-4.1, GPT-4o, GPT-5, Gemini 2.5 Pro and Flash, Claude Opus 4 and Sonnet 4, DeepSeek R1 and V3, Grok, Kimi, Qwen, Mistral), WildChat GPT conversations (Sep 2024-Jul 2025) to top up academic, post, and reflection, and StoryScope fiction (GPT-5.4, Gemini 3 Flash, Claude Sonnet 4.6, DeepSeek V3.2, Kimi K2.5). Chat wrappers ("Sure, here's…", "Let me know if…") were stripped from AI texts, as a user pasting the piece would. Markdown was kept.
- **Split:** 70% tune, 30% held-out, by source group (a student, a prompt, a mailbox, a blog, a debate thread), fixed before any scan. Bands and cuts came from the tune split only. Weights came from the held-out split only.
- **Rule:** a check scores in a genre only if, on held-out texts of that genre, AI fires it at least 2x as often as human text, at least 5 points more often, and on at most 10% of human texts. Otherwise it is `[info]` there. Genres map to scanner genres as academic → `academic`, essay → `general`, email → `professional`, post → `casual`, reflection → `reflection`, fiction → `fiction`.

| Genre | Human (tune / held-out) | AI (tune / held-out) | Held-out AUC v1.4.0 | Held-out AUC v1.5 |
|---|---|---|---|---|
| all | 729 / 319 | 611 / 262 | 0.885 | 0.919 |
| academic | 175 / 75 | 114 / 49 | 0.928 | 0.936 |
| essay | 105 / 45 | 105 / 45 | 0.959 | 0.959 |
| email | 101 / 49 | 105 / 45 | 0.824 | 0.917 |
| post | 105 / 45 | 105 / 45 | 0.979 | 0.996 |
| reflection | 103 / 45 | 42 / 18 | 0.981 | 0.989 |
| fiction | 140 / 60 | 140 / 60 | 0.702 | 0.804 |

New bands with v1.4.0 weights score 0.889 overall, so almost all of the gain comes from the weights. The index cutoffs were reset from the tune split: human p75 2.3 (typical human range below 2.5), human p90 6.7 (upper human range below 7), AI median 16.3 (heavy from 16).

**Fire rates on held-out texts (human / AI):**
- **Score in all six genres:** `triad_habit` (2-9% / 13-60%), `colon_heavy` (4-9% / 22-80%), `high_word_variety` (3-8% / 20-73%).
- **AI vocabulary** fires on 32% of student papers (84% of AI) and 13% of changemyview posts (76% of AI), so `ai_vocabulary` is `[info]` for academic and essay. It scores elsewhere (2-10% human vs 37-87% AI). `stock_phrases` (17% / 33%) and `not_x_but_y` (17% / 26%) also fail in academic prose only.
- **Dashes** now score in academic, essay, email, and reflection (2-7% / 29-56%) but not in posts, where 11% of human posts are dash-heavy.
- **Checks added in v1.4:** `sentence_floor` scores in essay and reflection (0% / 22% in both); in student papers it fires on 25% of human samples and 20% of AI ones. `paired_modifiers` scores in academic, essay, post, and reflection (0-5% / 6-16%). `stance_labels` fired on no held-out text at all. `noun_rider`, `summary_closer`, and `vague_attribution` never reached 5 points of separation. All four stay `[info]` everywhere.
- **Fail everywhere, now `[info]`:** `same_length_runs` (human 11-35%), `alliteration` (human 16-28%, often above AI), `moralizing_cues`, `narrow_punctuation`, `over_chained` (a rewrite guard; AI almost never over-chains), `rather_than_cluster`, `stacked_hedges`, and the two fiction lists (`fiction_ai_vocabulary` 22% / 80%, `fiction_stock_phrases` 13% / 58%; human rates too high).
- **Rhythm and structure tells mostly fail:** `repeated_opener`, `paragraph_kickers`, `self_answered_question`, and `dramatic_fragments` fire as often on human posts, reflections, and stories as on AI ones (human 11-45% in those genres). `flat_sentence_rhythm` and `uniform_paragraphs` separate strongly in academic prose (AI 45% and 59%) but human student papers hit them too (13% and 11%).
- **Formatting** (`title_case_headings`, `bold_label_lists`, `decorative_bold`) scores in most genres because chat models write Markdown and these human sources don't. It says nothing about the prose itself.
- **`chatbot_residue`** stays scored only in essay. The corpus strips chat wrappers, and "let me know if" or "feel free to" appear in 12% of the Enron e-mails.

122 check-and-genre weights changed: 10 promotions and 112 demotions. The full list, with each pair's held-out rates, is `benchmark/calibration_v2/results/weight_changes.md`. Many demotions are 0% / 0%: the check never fired in that genre, so there is no evidence for weight, not evidence against it.

**Limits.** Non-fiction AI text comes from 2025 models; only the fiction set is from 2026. Gemini is thin in posts (8 texts) and reflections (5). Held-out reflection has only 18 AI texts, so one text is 5.6 points. Weights were chosen on the held-out split, so v1.5's held-out AUC is optimistic; the tune split gives 0.913. Each human genre stands in for real use: Reddit confessions for reflections, changemyview for essays, and Enron for e-mail. BAWE and Hippocorpus were left out because they need a signed agreement. At about 450 words one human sample in ten has no short sentence at all, so `sentence_floor` keeps v1.4's floor (3% expository, 20.6% fiction, from full-length Brown texts) wherever the tuned floor came out as 0. None of this is a detector score.

## 1e. Step 7: from fresh-eyes review to meaning check (2026-10-09)
Reports: `benchmark/HELDOUT.md` (branch `heldout-bench`) and `benchmark/review_ablation/REVIEW_ABLATION.md` (branch `review-ablation`). Judges in both were Claude Opus, Claude Sonnet, Gemma 3 27B, and Mistral Small 3.2 24B, blind, with every packet judged under every label rotation.

- **Held-out benchmark.** On 15 new texts (12 AI drafts from four non-Claude families, 3 human controls), v1.6.0 did not beat v1.3.2: average rank 2.24 vs 2.13, with the no-skill baseline at 1.62. v1.3.2 was ahead on 9 of 14 judged texts (sign test p = 0.42). Where v1.6.0's fresh-eyes review ran (academic, application, cover letter), it lost to v1.3.2 in 18 judge×text comparisons and won 5; where it didn't run, it won 13 and lost 6. Judges preferred v1.6.0's own pre-review draft to its final in 71% of 56 blind judgments.
- **Why.** Asked for "any meaning change against the original", the reviewer read the draft's intensifiers and stock phrases ("invaluable", "deep understanding", "underscores") as locked meaning, and the rewriter put them back. It also turned "may play a larger role" into a flat claim. Its real catches were a dropped "I am confident", a dropped detail, and a changed anecdote.
- **Ablation.** Six review designs ran on v1.6.0's eight pre-review drafts (seven AI, one human control). The meaning check alone, now step 7, was the only one both judge families preferred to the pre-review draft: 12 wins, 4 losses, and 12 ties over 28 judge×text pairs (the ties are the four texts it left unchanged; sign test p = 0.08), 7–1 with Claude judges and 5–3 with local ones. It had the best meaning score (9.26/10), made 6 edits in 8 texts, passed 8 of 9 regression cases, and left the human control alone. In 24 runs it never flagged an intensifier or stock phrase. Re-running the old step 7 went 16–12 (p = 0.57; Claude judges 12–2, local 4–10) and again restored "invaluable" and "deep understanding". A tells check that couldn't see the original added claims, and a guard that dropped fixes raising RETAINED or the index cut 11 of 58 fixes, one real catch among them.
- **Limits.** The ablation ran on a dev set: HELDOUT.md had already examined those drafts, and the regression cases came from its diagnosis. Each design ran once (the meaning check three times, with consistent findings). The change still needs a held-out check on new text.

## 1f. Mode choice: polish text that already reads as the author's (v1.7.1, 2026-10-10)
Reports: `benchmark/HELDOUT2.md` and `benchmark/REPLICATES.md`.

- **Held-out round 2 (v1.7.0).** The texts were 15 new ones: 12 AI drafts from four non-Claude model families and 3 human controls. Four blind judges (Opus, Sonnet, Gemma 3 27B, Mistral Small 3.2 24B) ranked v1.7.0 first overall: 2.29, against 2.41 for the no-skill baseline and 2.50 for v1.3.2. Its lead over v1.3.2 was within noise (8–6–1, p = 0.79).
- **Damage to the controls.** v1.7.0 also did the most damage of any version to the human controls. It fully rewrote two of the three, and all four judges called its rewrite of an MMWR discussion section worse than the original. That text's request line mentioned a detector flag, and v1.7.0's notes leaned on the Detectors section's line that the full re-voice "is what moves the score".
- **Change.** v1.7.1 chooses rewrite or polish from the text itself, weighing signs of a model's draft against signs of the author's own writing. Neither the request's wording nor the scan index decides it: four of the twelve AI drafts scan in the human range. Text that already reads as the author's own gets polish, and the user is told that detectors flag formal human prose.
- **Replicates.** v1.7.1 and v1.3.2 ran three times each, on the 15 texts plus four new human controls: a 2020 BLS report, a 2017 Library of Congress blog post, a 1917 letter, and a 1928 story opening.
  - **Mode choice.** Every v1.7.1 run polished, or left as is, all seven controls and rewrote all twelve AI drafts (57/57). Every v1.3.2 run rewrote the Coast Guard blog post.
  - **Controls.** With provenance disclosed, Sonnet judged no v1.7.1 control output worse than its original (mean severity 0.00 of 3).
  - **AI drafts.** With the three runs pooled, Sonnet ranked v1.7.1 ahead of v1.3.2 (10–2, p = 0.04). Gemma and Mistral called it even (6–4–2).
- **Run-to-run noise.** On a single text, two Sonnet-ranked runs of the same version differed by 1.78 ranks, nearly as much as two runs of different versions (1.94). Single run-against-run comparisons went 7–3, 5–6, and 7–2. RETAINED varied as much within a version as between versions, so round 2's finding that v1.7.0 keeps more of the draft (17.7% against 12.1%) was noise: v1.3.2 alone ranged from 12.1% to 18.1%.
- **Ablations not adopted.** Two variants were tested and neither was adopted.
  - Treating emphasis and confidence words as voice in step 5 won 4 of 9 texts and lowered meaning scores.
  - Letting emails, posts, and introductions reorder points went 2–2, and its reorders won 1 and lost 2.
- **Held-out round 3** (`benchmark/HELDOUT3.md`). One v1.7.1 run on 16 new texts: ten AI drafts from four non-Claude model families, five of them scanning in the human range, and six new human controls; half of each group were sent with a detector line. It rewrote all ten drafts and returned all six controls unchanged (16/16). In a blind comparison with the original drafts, Opus and Sonnet preferred every revision, in both label orders (40/40), and rated the two versions 9–10 of 10 for saying the same thing.
- **Limits.**
  - The fix was written with round 2's texts in view; the replicate round's four new controls and round 3's sixteen texts are the out-of-sample tests.
  - Round 3 was a single run with no comparison arm, and seven of its ten AI drafts are emails or fiction.
  - v1.7.0 was not rerun.

## 2. StoryScope (fiction; Russell et al., 2026, arXiv:2604.03136)
Recomputed from the released feature file (61,575 stories; human vs pooled AI; every row points the same way for all five models):

| Feature | Human | AI |
|---|---|---|
| Frequent parallel or list-like sentence structures | 70% | 99% |
| Loose multi-clause chains | 76% | 55% |
| Consistently elevated or literary register | 11% | 40% |
| Mixed register with code-switching | 56% | 19% |
| Extended conceit present | 40% | 83% |
| Recurring metaphorical motif | 69% | 96% |
| Earnest or lyrical tone | 40% | 71% |
| Ironic or wry tone | 36% | 13% |
| Prominent alliteration | 79% | 98% |
| Narrator thematic commentary | 51% | 76% |
| Thematic explicitness and moralizing (1–5) | 3.28 | 3.94 |
| Explicit named references to texts or authors | 46% | 24% |
| Pop-culture or brand names | 40% | 13% |
| Allusion used as moral signposting | 26% | 46% |
| Embodied emotion as the dominant mode | 39% | 81% |
| Explicit emotion labels | 29% | 8% |
| Required external knowledge (0–2) | 0.70 | 0.54 |

Headline results: narrative-only features reach 93.2% macro-F1; after LAMP-style surface edits, 93.9%. Style-only features reach 85.8%.

## 3. Other studies these rules lean on (cited via Sepia's research ledger and the other skills)
- **Muñoz-Ortiz et al. 2024:** sentences of 41+ tokens are 12.0% of human news sentences vs 5.5% for a 2023 model. This supports the sentence-ceiling rule.
- **Reinhart et al., PNAS 2025:** instruction-tuned models overuse present participles and nominalizations and favor a dense, noun-heavy style. This supports the -ing and nominalization rules.
- **LAMP (Chakrabarty et al., CHI 2025):** professional editors' fixes to AI prose split roughly 74% replace, 18% delete, 8% insert. The most common fixes are awkward word choice, poor sentence structure, redundant exposition, and cliché. This supports "cut more than you add".
- **Shan et al. 2026:** AI *editing* of human text dilutes content words (lexical density d = −3.10). This supports the deletion and reversion tests and the length guard.
- **QUDsim (COLM 2025):** models reuse the same question sequence across stories, and comparison or verification moves are very rare (about 0.2–0.3% vs 19% for consequence moves).
- **Russell et al., ACL 2025:** people who use ChatGPT often are accurate detectors, and paraphrasing leaves position-level tells visible, sometimes more so.
- **Freeburg 2026:** em dashes per 1,000 words are 10.6 (GPT-4.1), 9.1 (Claude Opus 4.6), 1.4 (GPT-5.4), and 0 (Llama 3) against a human mean of 3.2. Dash rate depends on the model release, so it is never a universal rule.
- **Wikipedia "Signs of AI writing"** (WikiProject AI Cleanup), as distilled in blader/humanizer: source for most of the surface catalog.

## 4. Why not target detectors
- Detectors disagree with each other and change between versions. ZeroGPT in particular has a record of false positives on well-known human texts.
- AI text rewritten by AI (light polish) is often still flagged, and human text lightly polished by AI often gets flagged too.
- Translation chains and paraphrase loops (humanize-text's approach) move detector scores but cause terminology and citation drift, which is fatal for academic and technical writing.
- Readers' standards are stable. Text that a careful reader takes as the author's own is the goal that survives detector updates.
