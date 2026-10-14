# Architecture and discourse

Rewording leaves these intact, which is why they matter most. StoryScope found that narrative and structural choices alone identify AI fiction at 93.2% macro-F1, and still 93.9% after the surface style was edited by professional writers. The categories below translate those findings to essays, papers, statements, and professional writing. The narrative-only rules are in `fiction.md`.

## 1. The outline test
Run `python3 scripts/slopscan.py outline FILE` and read the first sentences (OPENINGS) as a list. If they form a clean, evenly paced summary of the piece (claim, claim, claim, conclusion), the structure is machine-shaped. Human outlines have jumps, a paragraph that starts mid-thought, and an opener that only makes sense in context.
**Fix:** Start a paragraph from its evidence or example instead of its topic sentence. Let one paragraph pick up a thread from two paragraphs back. Merge two paragraphs that make one point.

## 2. One template, every section
Each section runs the same moves in the same order, for example question → firm view → argument → softer view → application to my life. Readers pick up the template by the second section.
**Fix:** Keep the content and vary the order and weight. Open one section on the objection, another on a concrete case. Give the most contested point the most room, and let an easy point take two sentences. If the assignment mandates the moves, keep all of them but don't phrase them identically.

## 3. The moral at the end (thematic over-determination)
AI explains what things mean. In StoryScope, narrator thematic commentary appeared in 76% of AI stories vs 51% of human ones, thematic explicitness and moralizing scored 3.94 vs 3.28, and endings commented on themselves in 47% vs 37%. In essays this looks like the closing line of every paragraph saying what it shows, a final paragraph restating the lesson, or "This experience taught me that…".
**Check:** the ENDINGS list from `outline` puts every paragraph's last sentence in one column. When most sections close on an application, maxim, or summary ("…if the Bible is my final authority, my decisions should show it." / "If these 66 books are God's complete and final Word, I want to build my life on them…"), the template is showing, even if each line reads fine where it sits.
**Fix:** Cut commentary the content already makes plain, and trust the reader. Where a reflection or application is required, keep it where the assignment puts it, ground it in the author's concrete situation from the source (a named church, class, job, decision), state it once, and end on that concrete detail rather than on a general lesson.

## 4. Resolution by realization
AI arcs resolve inside the head: "I came to realize", "I now understand", "it made me see". StoryScope found 47% of AI stories end in internal understanding vs 27% of human. Personal essays end on this move constantly.
**Fix:** End on what the author did, decided, or still doesn't know, as the source reports it. Leave one tension unresolved if the source leaves it unresolved. Never invent the action.

## 5. Over-explaining for a reader who knows
AI assumes the reader knows nothing: it defines common terms, re-states the prompt, and backfills context. Human texts demand more outside knowledge (StoryScope "required external knowledge" 0.70 vs 0.54) and use more in-group reference.
**Fix:** Write for the actual reader. A theology professor doesn't need "the Apocrypha" explained, and a teammate doesn't need the meeting recap. Cut definitions the venue takes for granted, and keep the ones the argument depends on.

## 6. Unnamed references
AI gestures ("some theologians", "experts", "many people", "a famous author") where people name names. Explicit named references to texts or authors appeared in 46% of human stories and 24% of AI. Pop-culture and brand names showed up in 40% of human stories and 13% of AI.
**Fix:** Bring forward the names already in the source. Never add a name, source, or quotation that isn't there. `vague_attribution` flags the common frames ("Some theologians argue", "Many people believe"). Flag gaps as `[TODO: which theologians?]` and ask the user for the name under "Needs you".

## 7. Even emphasis
Every point gets the same weight, the same length, and the same confidence. Human emphasis clusters where the writer cares or where the dispute is.
**Fix:** Expand the contested point and compress the obvious ones. One section can be a single short paragraph.

## 8. The symmetrical argument
"Some argue X. Others argue Y. Both have merit. Ultimately, Z." A balanced survey followed by a safe verdict.
**Fix:** If the author holds a view, lead with it, and answer the strongest objection specifically. Drop the straw position nobody in the venue holds.

## 9. Missing move types
Models use consequence and procedure moves (what happened → why → what followed → what it means) and almost never compare, verify, or digress (QUDsim: about 19% vs 0.2–0.3%).
**Fix:** Where the source supports it, turn one consequence paragraph into a comparison (two views, two periods, two texts) or a qualification ("that's not how Jerome saw it"). Use only material already in the source.

## 10. Openings and endings
- **Openings.** A scene-setting or throat-clearing sentence, then the thesis ("In today's world…", "Throughout history…", "As a student…"). Start with the claim, the case, or the question.
- **Endings.** A recap, an outlook ("As I continue my journey…"), or a call to action the source doesn't support. End when the content ends.
- **The middle.** Detectors and readers find AI text easiest to spot in the body, where models hold one register and pace. Put the variation there: a longer analytical paragraph, a short one, and one turn the opening didn't predict.

## 11. Tone held at one pitch
AI is earnest throughout (StoryScope: earnest or lyrical tone in 71% of AI stories vs 40% of human; irony or wryness in 13% vs 36%). Where the author and genre allow, one dry or self-aware line is human. An academic paper doesn't need jokes. It can still have one sentence that admits something ("I can defend inerrancy on an exam and still…").

## 12. Extended metaphor
AI sustains a conceit (a journey, a tapestry, a compass, a lighthouse) across a piece (extended conceit in 83% of AI stories vs 40% of human; recurring metaphorical motif in 96% vs 69%). In non-fiction, drop the running metaphor and say the literal thing. A single figure of speech is fine.
