# Sentence and surface patterns

Tiers: **S** acts on one sighting. **M** acts when it recurs or when other tells are nearby. **W** is weak alone and counts only in clusters. Every fix keeps the underlying fact. Scanner key in `code` where slopscan detects it.

## A. Staging instead of stating (strongest)

**A1. Contrast with no opponent: not X but Y (S)** `not_x_but_y`
Forms: "It's not X, it's Y"; "not just/only/merely X but Y"; "This isn't about X. It's about Y."; "less X than Y"; "not because X but because Y"; a clipped tail (", no guessing").
The negative half names something nobody claimed, so the positive half sounds bigger. State Y. Keep the contrast only when X is a belief the reader actually holds, or when both halves carry information. A doctrinal "full inerrancy rather than limited inerrancy" names a real rival position, so it stays.
> It's not just a scheduling tool; it's a new way to run a clinic. → The tool runs the front desk's whole schedule.

**A2. Closers and kickers (S)** `paragraph_kickers`, `short_paragraph_endings`, `summary_closer` (info)
A last line that restates, moralizes, or tells the reader how to feel: "That's the real lesson." / "And that changes everything." / "This shows how careful the church was." Length doesn't excuse it. "So I can trust all of it, even what I find hard to accept." runs 13 words and makes the same move; `summary_closer` flags paragraph-final sentences that open with So, That's why, This is why, In the end, Ultimately, and the like. Cut it and end on the last concrete sentence. If the paragraph needs closure, close with a consequence or next step taken from the source. Fixing `short_paragraph_endings` means cutting the kicker, not lengthening every sentence: keep the short sentences that state a point (B1).

**A3. Sayings that sound deep (S)**
"At its core", "the real question is", "what truly matters", "X is the currency of Y", "X becomes a mirror". Replace the aphorism with the specific claim, or delete it.

**A4. Staged run-up (S)** `signposting`
"Here's the thing", "Let's dive in", "It's worth noting that", "Importantly,", "The key point is", "In this essay I will". Delete the run-up and start with the point.

**A5. Arguing with no one (M)**
"To be clear", "I'm not saying", "Some might think… but", "A tempting approach would be". Cut the defense unless a real objection is named and answered.

**A6. Self-answered questions and colon reveals (S)** `self_answered_question`, `colon_reveal`, `colon_heavy`
"The result? Chaos." / "The best part: it learns." Write the plain sentence. Use colons for lists, labels, and quotations. Current models use about four times as many colons in running prose as the human samples (5.6 vs 1.4 per 1,000 words).

**A7. Interpretive metadiscourse (M)**
Telling the reader what to notice ("This distinction matters", "As you can see", "In other words" when nothing was unclear). Delete it, or replace it with the fact that makes the point.

## B. Rhythm and shape by rule

**B1. The sentence ceiling (M)** `sentence_ceiling`
No sentence goes past ~30 words. In our calibration, 90% of human samples had at least one sentence of 35+ words in 450 words, the human median longest sentence was 49 words, and the current-Claude median was 33. Human writers let connected thoughts run ("…, and so…", "…, which…", "; …"). Fix by joining two related short sentences in a few places, aiming for a handful of 35–45-word sentences per page. Don't add short punchy sentences for rhythm (pure "burstiness" advice pushes the wrong way for current models). Don't overshoot either: blind judges marked rewrites that chained whole paragraphs into long sentences as heavy and said they buried the point.
The floor is the mirror image `sentence_floor` (scored in essay and reflection; info elsewhere): almost no sentence of 8 words or fewer. Full-length expository texts in the Brown corpus have a median of 10.5% such sentences, and only 10% fall under 3%. A rewrite lands there when it joins sentences to break the ceiling and also cuts every short paragraph ending (one short sentence in 48, in a doctrinal statement we reviewed). Leave a few plain short sentences where a point stands on its own.

**B2. Reflexive threes (M)** `triad_habit`
Three adjectives, three clauses, three examples, three paragraphs of evidence. Check each item. Merge or drop the filler item; let some lists run to two or four. Keep a three-item list when the content really has three items (Law, Prophets, Psalms).

**B3. Paired modifiers (W)** `paired_modifiers` (scored in academic, essay, post, and reflection; info elsewhere)
"free and gracious", "complete and final", "clear and compelling". Keep the one that carries meaning. A theological or legal doublet that is a term of art stays.

**B4. Recycled frames (M)** `templated_frames`, `repeated_opener`
The same sentence frame across sections ("This experience taught me…" in every paragraph). If the frame is filler, cut it or fold the point into the sentence. If it is a stance marker or rubric phrase ("I hold firmly that…", "I hold … provisionally"), keep the words and vary their position instead: "The most debated question here is whether general revelation can save, and I hold firmly that it cannot." Rotating synonyms ("My firm answer is…", "I am equally firm…") reads as synonym cycling (C10), and blind judges flagged exactly that. Stance labels cycle the same way, one per section: "I'm convinced", "I firmly believe", "my settled view", "I'm just as confident", "I'm just as sure". `stance_labels` (info) counts them and flags a repeated relative frame (just as, equally, with the same + sure, confident, firm, certain, convinced). Use a relative-strength label at most once and carry the rest of the strength in the claim.

**B5. Parallel construction everywhere (M)**
Balanced clauses, mirrored sentences, "X does A. Y does B. Z does C." In StoryScope, frequent parallel or list-like structures appeared in 99% of AI stories and 70% of human ones. Break one in two: subordinate one clause, merge two sentences, or reorder.

**B6. One register, held (M)**
Every word sits at the same elevated level, with no plain words, idioms, or concrete nouns. People code-switch (56% of human stories vs 19% of AI). Swap a few Latinate words for plain ones (*use* for *utilize*, *show* for *demonstrate*, *help* for *facilitate*) and keep the technical terms the venue needs.

**B7. Even paragraphs (W)** `uniform_paragraphs`, `short_even_paragraphs`
Every paragraph three sentences long and about the same size. Merge two paragraphs, or let one run longer where the argument is densest.

**B8. Stock connectives (W)** `connective_openers`
"Additionally," "Furthermore," "Moreover," "Ultimately," "Overall," at sentence starts. Usually the sentence works without them; "and", "but", "so", "also" mid-sentence read more natural.

**B9. -ing and noun-phrase riders (S)** `ing_rider`, `ing_heavy`, `noun_rider` (info)
", highlighting the importance of…", ", underscoring…", ", reflecting a broader…", ", ensuring…". The rider asserts significance with no support behind it. Keep the fact and drop the rider, or make it a sentence that says exactly what follows from what.
The noun-phrase cousin does it with an appositive: ", evidence of…", ", evidence that…", ", a sign that…", ", proof that…", ", a testament to…", ", a reminder that…", ", a reflection of…". End on the evidence, or state the claim plainly in its own clause.
> Hebrews, James, and 2 Peter took longer to win wide acceptance, evidence of how careful the church was. → The church was careful with Hebrews, James, and 2 Peter, which took longer to win wide acceptance.

**B10. Stacked hedges (W)** `stacked_hedges`
"could potentially perhaps". Use one hedge where doubt is real and none elsewhere.

**B11. Dramatic fragments (M)** `dramatic_fragments`
"No warning. No plan. Just silence." Merge into one sentence that makes the claim.

**B12. Sound patterning (W)** `alliteration` (info)
Alliterative triplets and cadenced phrasing ("perfect, polished, purposeful"). Alliteration was prominent in 98% of AI stories vs 79% of human ones, and prose rhythm was more marked in AI. Break the chime when it calls attention to itself.

## C. Inflation and borrowed weight

**C1. AI vocabulary (M)** `ai_vocabulary`
delve, tapestry, testament, underscore, showcase, intricate, meticulous, pivotal, multifaceted, realm, beacon, paramount, embark, unwavering, interplay, seamless, holistic, transformative, foster, harness, elevate, leverage, robust (figurative), landscape (figurative), navigate (figurative), resonate, profound, crucial, vibrant, nuanced. Prefer the plain word. Technical uses stay ("robust standard errors", the theological sense of "illumination").

**C2. Stock phrases (S)** `stock_phrases`
"plays a crucial role", "a testament to", "in today's fast-paced world", "it's important to note", "shed light on", "a deeper understanding", "the future looks bright". State the fact.

**C3. Inflated significance (S)**
"marks a pivotal moment", "left an indelible mark", "a significant milestone", "reflects a broader trend". Keep the event and drop the significance claim unless the source supports it.

**C4. Copula avoidance (M)** `copula_avoidance`
"serves as", "stands as", "functions as", "boasts", "features". Write *is* or *has*.

**C5. Vague association (M)**
"associated with", "linked to", "in connection with". Name the relationship if the source gives it; otherwise leave the wording as it is rather than guessing.

**C6. Borrowed authority (S)** `vague_attribution` (info)
"Experts agree", "studies show", "many believe", and in academic papers "Some theologians argue…", "Some critics take…". Name the source if the text has one. Otherwise flag it as `[TODO: source]` and ask the user who it is; in a paper the unnamed view is usually the position being answered, so keep the claim. Never invent a citation or a name.

**C7. Sales register (S)**
"nestled", "boasts", "vibrant", "rich history", "breathtaking", "commitment to excellence". Say what the thing is.

**C8. Abstract-noun wrappers (M)** `abstract_noun_of`
"a sense of", "the weight of", "a mix of", "the beauty of", "the power of". Name the concrete thing, or cut the wrapper.

**C9. Nominalizations (W)**
"made a decision", "the implementation of", "provides clarification". Use the verb (*decided*, *implemented*, *clarifies*).

**C10. Synonym cycling (M)** `high_word_variety`
"The agent… the assistant… the tool…" all for one referent. Repeat the right word. Generated text shows higher lexical variety than human text on our calibration set (type/token 0.63 vs 0.58).

## D. Format and leftovers

**D1. Chatbot residue (S)** `chatbot_residue`: "I hope this helps", "Certainly!", "Let me know if…", "Here's a revised version". Delete.
**D2. Knowledge-limit hedges (S)**: "as of my last update", "while details are limited". State what the source shows or cut the sentence.
**D3. Decorative formatting (M)** `bold_label_lists`, `decorative_bold`, `emoji`, `title_case_headings`: bold labels on every bullet, emoji headers, Title Case headings, rules between every section. Use prose where items aren't really separate, sentence-case headings, and bold only for warnings.
**D4. Heading echo (M)**: the first sentence restates the heading. Cut it.
**D5. Writing about the document (M)**: "This essay will explore…", "the table below shows…". Cut it unless the reader needs the map.
**D6. Wrong reader (M)**: in a reply, re-explaining what the recipient already knows. Lead with the decision.

## E. Punctuation

- **Dashes.** Judge by rate, never ban them. Some model releases write 9–11 per 1,000 words, while human editorial prose averages about 3, and current Claude essays in our sample used none. Cut dash clusters and let a dash stay where it is the best mark. If the author's own sample uses dashes, match its rate.
- **Narrow repertoire** `narrow_punctuation`. A 300+ word piece with no semicolon, parenthesis, or dash fits the current-model profile (human median about 8.5 per 1,000 words). Use them only where they fit.
- **Curly vs straight quotes.** Not a tell: word processors curl quotes automatically. Match the venue.

## Whitelist: do not "fix"

| Leave alone | Why |
|---|---|
| Formal register in a formal venue | Matching the register beats forced casualness |
| Required headings, labels, rubric phrases, citation formats | Convention, not slop |
| Terms of art (inerrancy, plenary, illumination, robust SE, due process) | Precision outranks plainness |
| A real list of three, a single "moreover", one dash, one em-dash-free page | One hit means nothing; only clusters count |
| Quoted material, Scripture text, dialogue | Load-bearing; never regularize |
| The author's verified habits from their own samples | Edit toward them |
| Clean grammar and spelling | Planting errors is a gimmick, and graders notice |
| Plain, ordinary sentences | Slack is human. Don't polish every line into distinctiveness |
