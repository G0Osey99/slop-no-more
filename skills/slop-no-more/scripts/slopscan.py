#!/usr/bin/env python3
"""slopscan: deterministic scanner for AI-writing patterns, plus a meaning-lock diff.

Standard library only. It measures surface and sentence-level patterns that
human editors and published studies associate with LLM prose. It does NOT
estimate the probability that a text was written by AI; a clean scan means the
measured patterns sit inside the range seen in human writing, nothing more.

Usage:
  slopscan.py scan FILE [--genre auto|academic|professional|general|casual|reflection|fiction] [--json] [--top N]
  slopscan.py diff ORIGINAL REWRITE [--genre ...] [--json]
  slopscan.py outline FILE          # first and last sentence of every paragraph (outline test, endings)

Genre aliases: essay = general, email = professional, post = casual. Each genre has its own human
bands and its own set of scored checks (data/human_bands.json; INFO_IN below).

FILE may be "-" for stdin. Plain text or Markdown. Blank lines separate paragraphs;
a block whose lines each end a sentence (Word exports) is read one paragraph per line.
"""
import json
import math
import os
import re
import statistics
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
LEX_PATH = os.path.join(HERE, "..", "data", "lexicon.json")

# Index bands from the calibration-v2 tune split (benchmark/calibration_v2: ~450-word samples, 1,340 texts,
# human pre-2022 vs 2025-2026 GPT, Gemini, Claude, DeepSeek and others, six genres): human p75 2.3,
# human p90 6.7, AI median 16.3. Held-out AUC 0.92 overall (fiction 0.80, the other genres 0.92-1.00).
# The index is a count of patterns, not a probability of AI authorship.
BANDS = [(2.5, "typical human range"), (7.0, "upper human range"), (16.0, "moderate"), (float("inf"), "heavy")]

GENRES = ("academic", "professional", "general", "casual", "reflection", "fiction")
GENRE_ALIAS = {"essay": "general", "email": "professional", "post": "casual"}

# Checks reported as [info] (weight 0) in the genres listed. A check scores in a genre only if, on
# held-out texts of that genre, AI fires it at least 2x as often as human text, at least 5 points
# more often, and on no more than 10% of human texts (calibration v2, references/evidence.md).
INFO_IN = {k: set(GENRES) for k in (
    "alliteration", "fiction_ai_vocabulary", "fiction_stock_phrases", "moralizing_cues", "narrow_punctuation",
    "noun_rider", "over_chained", "rather_than_cluster", "same_length_runs", "stacked_hedges", "stance_labels",
    "summary_closer", "vague_attribution",
)}
INFO_IN["abstract_noun_of"] = {"academic"}
INFO_IN["ai_vocabulary"] = {"academic", "general"}
INFO_IN["bold_label_lists"] = {"reflection", "fiction"}
INFO_IN["chatbot_residue"] = {"academic", "professional", "casual", "reflection", "fiction"}
INFO_IN["colon_reveal"] = {"academic", "professional", "general", "casual"}
INFO_IN["common_ai_words_cluster"] = {"academic", "general", "fiction"}
INFO_IN["connective_openers"] = {"professional", "general", "casual", "reflection", "fiction"}
INFO_IN["copula_avoidance"] = {"casual", "fiction"}
INFO_IN["dash_density"] = {"casual"}
INFO_IN["decorative_bold"] = {"fiction"}
INFO_IN["dramatic_fragments"] = {"academic", "professional", "casual", "reflection", "fiction"}
INFO_IN["emoji"] = {"academic", "reflection", "fiction"}
INFO_IN["flat_sentence_rhythm"] = {"academic", "fiction"}
INFO_IN["ing_heavy"] = {"fiction"}
INFO_IN["ing_rider"] = {"fiction"}
INFO_IN["not_x_but_y"] = {"academic"}
INFO_IN["paired_modifiers"] = {"professional", "fiction"}
INFO_IN["paragraph_kickers"] = {"academic", "general", "casual", "reflection", "fiction"}
INFO_IN["recap_ending"] = {"academic", "professional", "casual", "reflection", "fiction"}
INFO_IN["repeated_opener"] = {"academic", "general", "casual", "reflection", "fiction"}
INFO_IN["self_answered_question"] = {"academic", "professional", "general", "casual", "fiction"}
INFO_IN["sentence_ceiling"] = {"professional", "general", "reflection", "fiction"}
INFO_IN["sentence_floor"] = {"academic", "professional", "casual", "fiction"}
INFO_IN["short_even_paragraphs"] = {"reflection", "fiction"}
INFO_IN["short_paragraph_endings"] = {"academic", "professional", "casual", "reflection", "fiction"}
INFO_IN["signposting"] = {"academic", "professional", "reflection", "fiction"}
INFO_IN["stock_phrases"] = {"academic"}
INFO_IN["templated_frames"] = {"academic", "professional", "general", "casual", "reflection"}
INFO_IN["title_case_headings"] = {"professional"}
INFO_IN["uniform_paragraphs"] = {"academic", "fiction"}

ABBREV = r"(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|vs|etc|e\.g|i\.e|cf|al|Gen|Ex|Lev|Num|Deut|Josh|Judg|Sam|Kgs|Chr|Neh|Esth|Ps|Prov|Eccl|Isa|Jer|Lam|Ezek|Dan|Hos|Obad|Mic|Nah|Hab|Zeph|Hag|Zech|Mal|Matt|Mk|Lk|Jn|Rom|Cor|Gal|Eph|Phil|Col|Thess|Tim|Tit|Philem|Heb|Jas|Pet|Rev|No|Vol|pp|p|Fig|Eq|ch|Inc|Co|Ltd|Corp|U\.S|a\.m|p\.m|approx|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"


def load_bands():
    path = os.path.join(HERE, "..", "data", "human_bands.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except OSError:
        return {}


def load_lex():
    with open(LEX_PATH, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------- text utils

def normalize(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    return text


def strip_markup(text):
    """Remove code blocks, inline code, URLs, and markdown emphasis for prose stats."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\*\*|__", "", text)
    return text


def paragraphs(text):
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out = []
    for p in paras:
        lines = [l for l in p.split("\n") if l.strip()]
        # One paragraph per line when every prose line ends a sentence and is paragraph-sized on its
        # own (single-newline paragraphs, as in text copied from Word). Hard-wrapped prose breaks
        # mid-sentence, and one-sentence-per-line Markdown has short one-sentence lines.
        prose_lines = [l for l in lines if not (is_heading(l) or is_list_item(l))]
        per_line = len(prose_lines) >= 2 and all(
            re.search(r"[.!?][\"')\]]*\s*$", l) and (len(sentences(l)) >= 2 or len(words_of(l)) >= 25) for l in prose_lines)
        # treat short label/heading lines as their own blocks
        buf = []
        for l in lines:
            if is_heading(l) or is_list_item(l):
                if buf:
                    out.append(" ".join(buf)); buf = []
                out.append(l.strip())
            elif per_line:
                out.append(l.strip())
            else:
                buf.append(l.strip())
        if buf:
            out.append(" ".join(buf))
    return out


def is_heading(line):
    s = line.strip()
    if s.startswith("#"):
        return True
    words = s.split()
    return 0 < len(words) <= 10 and not re.search(r"[.!?:]$", s) and s[:1].isupper() and not s.endswith(",")


REF_LINE = re.compile(r"^\s*(?:[A-Z][a-z]+(?: [A-Z][a-z]+)?:\s*)?(?:[1-3] )?[A-Z][a-z]{1,9}\.? \d+(?::\d+(?:[-–]\d+)?)?:")


def is_list_item(line):
    """Bullets, numbered items, and reference-gloss lines ("John 1:18: ...") are not running prose."""
    return bool(re.match(r"\s*(?:[-*•]|\d+[.)])\s+", line)) or bool(REF_LINE.match(line))


def prose_paragraphs(text):
    """Paragraphs that are running prose (>= 2 sentences or >= 25 words)."""
    out = []
    for p in paragraphs(text):
        if is_heading(p) or is_list_item(p):
            continue
        if len(words_of(p)) >= 25 or len(sentences(p)) >= 2:
            out.append(p)
    return out


def sentences(text):
    t = re.sub(r"\s+", " ", text.strip())
    if not t:
        return []
    # protect abbreviations and verse refs like "Heb. 1:1"
    t = re.sub(r"\b(" + ABBREV + r")\.", lambda m: m.group(1) + "․", t)
    t = re.sub(r"\b([A-Z])\.(?=\s?[A-Z]\.)", lambda m: m.group(1) + "․", t)  # initials
    parts = re.split(r"(?<=[.!?])[\"')\]]?\s+(?=[\"'(\[]?[A-Z0-9])", t)
    return [p.replace("․", ".").strip() for p in parts if p.strip()]


def words_of(text):
    return re.findall(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*", text)


def find_phrases(low, phrases):
    hits = []
    for ph in phrases:
        pat = r"(?<![a-z])" + re.escape(ph) + r"(?![a-z])"
        n = len(re.findall(pat, low))
        if n:
            hits.append((ph, n))
    return hits


def snippet(s, n=110):
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


# ---------------------------------------------------------------- detectors

NOT_BUT = [
    r"\b(?:not|n't)\s+(?:just|only|merely|simply)\b[^.!?]{0,90}?\b(?:but|it's|it is|they're|we're|but also)\b",
    r"\b(?:is|was|are|were)(?:n't| not)\s+(?:about|a|an|the)\b[^.;!?]{0,60}?[,;—–-]\s*(?:it's|it is|it was|but|they're|this is)\b",
    r"\bnot because\b[^.;!?]{0,80}\bbut because\b",
    r"\bless (?:about|a|an)\b[^.;!?]{0,50}\b(?:than|and more)\b",
]
SPLIT_NOT = re.compile(r"^(?:it|this|that|they|he|she|the \w+)(?:'s| is| was| are| were)?\s*(?:n't|not)\b|^(?:it|this|that)(?: is| was)n't\b", re.I)
SPLIT_POS = re.compile(r"^(?:it|this|that|they|he|she)(?:'s| is| was| are| were)\b", re.I)
COLON_REVEAL = re.compile(r"^(?:The|Here's|Here is|One|My|Our|And the|But the|What|This)\b[^:.!?]{0,45}:\s+[a-z]")
COPULA = re.compile(r"\b(?:serves?|served|serving|stands?|stood|functions?|acts?|operates?)\s+as\s+(?:a|an|the|both)\b|\bboasts?\b", re.I)
SIGNPOST = re.compile(
    r"\b(?:it(?:'s| is) (?:worth|important|crucial|essential|vital) (?:noting|to note|mentioning|to remember|to understand|to recognize)"
    r"|(?:notably|importantly|interestingly|crucially|essentially|simply put|put simply),"
    r"|in other words,|to put it (?:simply|another way)|the key (?:point|takeaway|insight|lesson|difference|question) (?:is|here)"
    r"|let(?:'s| us) (?:explore|dive|break|take a (?:closer )?look|unpack|examine|consider)"
    r"|as (?:we've|we have|I've|I have) (?:seen|discussed|noted|mentioned)|as mentioned (?:earlier|above|before)"
    r"|in this (?:essay|paper|post|article|section|piece|reflection|letter)"
    r"|this (?:essay|paper|post|article|reflection) (?:will|explores|examines|argues|discusses|aims))\b",
    re.I,
)
QA_PAIR = re.compile(r"(?:^|\s)([A-Z][^.?!]{0,70}\?)\s+([A-Z][^.?!]{0,60}[.!])")
# stance labels: "I'm convinced", "I firmly believe", "my settled view", "my view ... is more provisional"
STANCE = re.compile(
    r"\bI(?:'m| am)\s+(?:(?:fully|completely|absolutely|quite|very|firmly|deeply|thoroughly|now|still|also|just as|equally|every bit as|less|more)\s+)?(?:convinced|persuaded|certain|sure|confident)\b"
    r"|\bI\s+(?:firmly|strongly|truly|deeply|wholeheartedly|fully|confidently)\s+(?:believe|hold|affirm|maintain|reject|agree|think)\b"
    r"|\bI\s+hold\b[^.!?;]{0,40}?\b(?:firmly|strongly|confidently|provisionally|tentatively|loosely)\b"
    r"|\bmy\s+(?:settled|firm|firmest|considered|strong|tentative|provisional|working)\s+(?:view|conviction|position|answer|belief|judgment|conclusion)\b"
    r"|\bmy\s+(?:view|position|answer|belief|conviction)\b[^.!?;]{0,60}?\bis\s+(?:more\s+|less\s+|much\s+)?(?:provisional|tentative|settled|firm|firmer)\b"
    r"|\bI\s+(?:remain|stay|am still)\s+(?:convinced|unconvinced|persuaded|unpersuaded|confident)\b", re.I)
# relative-strength frames that point back at an earlier label: "I'm just as sure", "I am equally firm"
STANCE_REL = re.compile(
    r"\b(?:I|I'm|I am|I've|we|we're|we are)\b[^.!?;]{0,40}?\b(?:just as|equally|every bit as|no less)\s+(?:sure|confident|firm|firmly|certain|convinced|strongly|persuaded|committed)\b"
    r"|\bwith (?:the same|equal)\s+(?:confidence|certainty|conviction|firmness|assurance)\b", re.I)
# paragraph-final summary closers of any length: "So I can trust all of it...", "That's why..."
SUMMARY_OPENER = re.compile(
    r"^(?:So,? (?:I|I'm|we|you|it|it's|this|that|that's|the|in|all|there|my|our)\b|And so\b|(?:That's|That is|This is|Which is) (?:why|how)\b|In the end\b|Ultimately\b"
    r"|In short\b|In sum\b|All (?:of )?this\b|In other words\b|Put simply\b|Simply put\b|At the end of the day\b"
    r"|The (?:point|lesson|upshot|takeaway|bottom line) is\b|(?:This|That) (?:means|shows|proves)\b)", re.I)
# unnamed authorities: "Some theologians argue", "Many people believe", "Studies show"
VAGUE_SOURCE = re.compile(
    r"\b(?<!too )(?<!how )(?:some|many|most|several|certain)\s+(?:theologians|scholars|critics|experts|people|researchers|commentators|historians|observers"
    r"|analysts|writers|thinkers|authors|philosophers|economists|scientists|educators)\s+(?:(?:also|even|still|now|today|often|would|might|may|have|will|do)\s+)?"
    r"(?:argue|argued|say|said|claim|claimed|believe|believed|think|thought|take|took|hold|held|suggest|suggested|contend|contended|maintain|maintained"
    r"|insist|insisted|agree|agreed|assert|asserted|assume|assumed|feel|felt|reject|rejected|object|objected|warn|warned|teach|taught)\b"
    r"|(?:^|(?<=[,;:(] )|\b(?:that|and|but|as|because|since|while|though|although)\s+)(?:experts|studies|research)\s+(?:agree|show|shows|suggest|suggests|have shown|has shown)\b", re.I)
# application or maxim cue in a paragraph's last sentence (outline hint only, not scored)
APPLICATION = re.compile(
    r"\b(?:I|I'm|my|me|we|we're|our|us|you|your)\b[^.!?]*?\b(?:should|ought to|must|need to|have to|want to)\b"
    r"|\b(?:should|ought to|must|need to|have to|want to)\b[^.!?]*?\b(?:I|my|me|we|our|us|you|your)\b", re.I)
ADJ_SUFFIX = re.compile(r"(?:ous|ive|ful|ible|able|ic|ical|ent|ant|est|less|ary|ory|ish)$")
NOMINAL = re.compile(r"\b[a-z]{4,}(?:tion|tions|sion|sions|ment|ments|ness|ity|ities|ance|ence)\b")
CONTRACTION = re.compile(r"\b[A-Za-z]+(?:n't|'re|'ve|'ll|'d|'m)\b|\b(?:it|that|there|here|what|who|he|she|let)'s\b", re.I)
DASH = re.compile(r"—|–|(?<=\w) -- (?=\w)|(?<=\w)--(?=\w)| - (?=[a-z])")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✅]")
FUNCTION_WORDS = set("a an the of to and or but in on at by for with from as is are was were be been being it its this that these those i me my we our you your he him his she her they them their not no so if then than too very can will would should could may might must do does did have has had".split())


def noun_rider_re(lex):
    """', evidence of how…', ', a sign that…', ', a testament to…': a trailing noun phrase that asserts significance."""
    return re.compile(r",\s+(?:(?:a|an|one more|yet another|further)\s+)?(?:(?:clear|powerful|striking|vivid|telling|fitting|lasting|living|sure|quiet|small|stark)\s+)?"
                      r"(?:" + "|".join(re.escape(n) for n in lex.get("noun_riders", [])) + r")\s+(?:of|that|to)\b", re.I)


RIDER_SKIP = {"however", "fact", "indeed", "course", "turn", "short", "sum", "addition", "contrast", "effect", "words",
              "is", "was", "are", "were", "be", "been", "became", "becomes", "remains", "remained", "seems", "seemed"}


def has_noun_rider(sent, lex):
    """True when the rider closes a clause ('…wide acceptance, evidence of how…'), not after an opener ('However, evidence…')."""
    for m in noun_rider_re(lex).finditer(sent):
        before = words_of(sent[: m.start()])
        if len(before) >= 4 and before[-1].lower() not in RIDER_SKIP:
            return True
    return False


def ending_tags(sent, lex):
    """Hints for the outline's endings list: summary closer, significance rider, application or maxim."""
    tags = []
    if SUMMARY_OPENER.match(sent):
        tags.append("summary closer")
    if has_noun_rider(sent, lex) or re.search(r",\s+(?:thereby\s+|thus\s+)?(?:" + "|".join(re.escape(r) for r in lex["ing_riders"]) + r")\b", sent, re.I):
        tags.append("rider")
    if APPLICATION.search(sent):
        tags.append("application?")
    return tags


def detect_triads(sent):
    """Count lists of exactly three short items: 'X, Y, and Z'."""
    n3 = nother = 0
    for m in re.finditer(r"((?:[\w'-]+(?: [\w'-]+){0,4}, ){2,})(?:and|or) [\w'-]+", sent):
        items = m.group(1).count(", ") + 1
        if items == 3:
            n3 += 1
        else:
            nother += 1
    return n3, nother


def detect_doublets(sent, adjset):
    out = []
    for m in re.finditer(r"\b(?:(?:most|more|so|both|very)\s+)?([a-z]+)\s+and\s+(?:(?:most|more|so|very)\s+)?([a-z]+)\b", sent):
        a, b = m.group(1), m.group(2)
        if a == b or a in FUNCTION_WORDS or b in FUNCTION_WORDS:
            continue
        ia = a in adjset or (len(a) > 5 and ADJ_SUFFIX.search(a))
        ib = b in adjset or (len(b) > 5 and ADJ_SUFFIX.search(b))
        if ia and ib:
            out.append(m.group(0))
    return out


def alliteration_runs(words):
    """Windows of 4 consecutive content words where >=3 share an initial consonant."""
    content = [w.lower() for w in words if w.lower() not in FUNCTION_WORDS and len(w) > 2 and w[0].isalpha()]
    hits = 0
    i = 0
    while i + 4 <= len(content):
        win = content[i : i + 4]
        initials = Counter(w[0] for w in win if w[0] not in "aeiou")
        if initials and initials.most_common(1)[0][1] >= 3:
            hits += 1
            i += 4
        else:
            i += 1
    return hits


def flat_runs(lengths, tol=0.25, minlen=3):
    """Runs of >= minlen adjacent sentences whose lengths stay within +-tol of the run mean (or 3 words)."""
    runs = []
    start = 0
    for i in range(1, len(lengths) + 1):
        seg = lengths[start:i]
        mean = sum(seg) / len(seg)
        ok = all(abs(x - mean) <= max(3, tol * mean) for x in seg)
        if not ok:
            if i - 1 - start >= minlen:
                runs.append((start, i - 1))
            start = i - 1
    if len(lengths) - start >= minlen:
        runs.append((start, len(lengths)))
    return runs


def guess_genre(text, low):
    if re.search(r"\b(?:said|whispered|asked)\b", low) and low.count('"') >= 6:
        return "fiction"
    if re.search(r"(?:^|\n)\s*(?:dear |hi |hello |hey )|(?:^|\n)\s*(?:sincerely|best regards|regards|best|thanks|cheers),?\s*(?:\n|$)", text.lower()):
        return "professional"
    if re.search(r"\b(?:et al\.|\(\d{4}\)|participants|findings|literature|scripture|theolog|hypothes|survey)\b", low):
        return "academic"
    return "general"


def scan(text, genre="auto", top=8, bands=None):
    lex = load_lex()
    text = normalize(text)
    prose = strip_markup(text)
    low = re.sub(r"\s+", " ", prose.lower())
    words = words_of(prose)
    nw = max(len(words), 1)
    k = 1000.0 / nw
    if genre == "auto":
        genre = guess_genre(text, low)
    genre = GENRE_ALIAS.get(genre, genre)
    wgenre = genre if genre in GENRES else "general"  # genre used for bands and weights

    paras = prose_paragraphs(prose)
    sents = [s for p in paras for s in sentences(p)]
    slen = [len(words_of(s)) for s in sents]
    plens = [len(words_of(p)) for p in paras]
    allb = load_bands() if bands is None else bands
    bands = allb.get(wgenre) or allb.get("fiction" if genre == "fiction" else "expository", {})

    def band(metric, q, default):
        return bands.get(metric, {}).get(q, default)

    def cut(metric, q, default):
        """Threshold for a profile check: the tuned cut when the bands carry one, else percentile q."""
        b = bands.get(metric, {})
        return (b["cut"], b.get("cut_q", "cut")) if "cut" in b else (b.get(q, default), q)

    F = {}  # findings: key -> dict(count, weight, examples, layer, note)

    def add(key, layer, count, weight, examples=None, note=""):
        if count:
            if wgenre in INFO_IN.get(key, ()):
                weight = 0.0
            F[key] = dict(layer=layer, count=count, weight=weight, examples=(examples or [])[:top], note=note)

    # --- residue & stock phrases & vocabulary
    res = find_phrases(low, lex["residue"])
    add("chatbot_residue", "surface", sum(n for _, n in res), 6.0, [p for p, _ in res], "Chat wrapper text left in the piece. Delete.")
    stock = find_phrases(low, lex["stock_phrases"])
    add("stock_phrases", "surface", sum(n for _, n in stock), 2.0, [f"{p} x{n}" if n > 1 else p for p, n in sorted(stock, key=lambda x: -x[1])])
    proper = set()
    for s_ in sentences(prose):
        for w_ in words_of(s_)[1:]:
            if w_[:1].isupper():
                proper.add(w_)
    wa = Counter(w.lower() for w in words if w.lower() in set(lex["words_a"]) and w not in proper)
    add("ai_vocabulary", "surface", sum(wa.values()), 1.5, [f"{w} x{n}" if n > 1 else w for w, n in wa.most_common()])
    wb = Counter(w.lower() for w in words if w.lower() in set(lex["words_b"]))
    if sum(wb.values()) * k > 6:  # only counts as a cluster
        add("common_ai_words_cluster", "surface", sum(wb.values()), 0.5, [f"{w} x{n}" if n > 1 else w for w, n in wb.most_common()], "Weak alone; counts only as a cluster.")
    if genre == "fiction":
        fp = find_phrases(low, lex["fiction_phrases"])
        add("fiction_stock_phrases", "surface", sum(n for _, n in fp), 1.5, [f"{p} x{n}" if n > 1 else p for p, n in sorted(fp, key=lambda x: -x[1])])
        fw = Counter(w.lower() for w in words if w.lower() in set(lex["fiction_words"]))
        add("fiction_ai_vocabulary", "surface", sum(fw.values()), 0.6, [f"{w} x{n}" if n > 1 else w for w, n in fw.most_common()])
    ab = re.findall(r"\b(?:a|the)\s+(?:" + "|".join(lex["abstract_of"]) + r")\s+of\b", low)
    add("abstract_noun_of", "sentence", len(ab), 1.0, [m for m, _ in Counter(ab).most_common()], "'a sense of', 'the weight of': name the concrete thing or cut the wrapper.")

    # --- sentence-level patterns
    nb = []
    for s in sents:
        for pat in NOT_BUT:
            m = re.search(pat, s, re.I)
            if m:
                nb.append(snippet(s)); break
    for a, b in zip(sents, sents[1:]):
        if SPLIT_NOT.search(a) and SPLIT_POS.search(b) and len(words_of(b)) <= 18:
            nb.append(snippet(a + " " + b, 140))
    add("not_x_but_y", "sentence", len(nb), 3.0, nb, "Contrast against a claim nobody made. State the positive point.")

    rather = [snippet(s) for s in sents if re.search(r"\brather than\b|\binstead of\b", s, re.I)]
    if len(rather) * k > 4:
        add("rather_than_cluster", "sentence", len(rather), 0.8, rather, "Weak; legitimate when both halves carry information.")

    riders = []
    rider_re = re.compile(r",\s+(?:thereby\s+|thus\s+)?(?:" + "|".join(re.escape(r) for r in lex["ing_riders"]) + r")\b", re.I)
    for s in sents:
        if rider_re.search(s):
            riders.append(snippet(s))
    add("ing_rider", "sentence", len(riders), 2.5, riders, "Trailing -ing clause that claims significance. Keep the fact, drop the rider.")

    nrid = [snippet(s) for s in sents if has_noun_rider(s, lex)]
    add("noun_rider", "sentence", len(nrid), 1.0, nrid, "', evidence of…', ', a sign that…': the appositive cousin of the -ing rider. End on the evidence, or state the claim plainly in its own clause.")

    if genre != "fiction":
        vague = [snippet(s) for s in sents if VAGUE_SOURCE.search(s)]
        add("vague_attribution", "sentence", len(vague), 1.0, vague, "Unnamed source ('some theologians argue'). Use the name the source gives; otherwise ask the user. Never invent one.")

    cop = [snippet(s) for s in sents if COPULA.search(s)]
    add("copula_avoidance", "sentence", len(cop), 1.5, cop, "'serves as', 'stands as', 'boasts': use is/has.")

    sp = [snippet(s) for s in sents if SIGNPOST.search(s)]
    add("signposting", "sentence", len(sp), 2.0, sp, "Tells the reader what to notice instead of saying it.")

    cr = [snippet(s) for s in sents if COLON_REVEAL.search(s)]
    add("colon_reveal", "sentence", len(cr), 2.0, cr)

    qa = [snippet(m.group(0)) for m in QA_PAIR.finditer(" ".join(sents)) if len(words_of(m.group(1))) <= 12]
    add("self_answered_question", "sentence", len(qa), 2.0, qa)

    hed = []
    hedge_re = re.compile(r"\b(?:" + "|".join(re.escape(h) for h in lex["hedges"]) + r")\b", re.I)
    for s in sents:
        if len(hedge_re.findall(s)) >= 3:
            hed.append(snippet(s))
    add("stacked_hedges", "sentence", len(hed), 1.5, hed)

    t3 = tother = 0
    tri_ex = []
    for s in sents:
        a, b = detect_triads(s)
        t3 += a; tother += b
        if a:
            tri_ex.append(snippet(s))
    tcut, tq = cut("triads_k", "p90", 4.2)
    if t3 >= 2 and t3 * k > tcut:
        add("triad_habit", "sentence", t3, 1.5, tri_ex, f"{t3} three-item lists vs {tother} other-length lists ({t3 * k:.1f}/1k; human {tq} {tcut:.1f}).")

    dbl = []
    adjset = set(lex["adjectives"])
    for s in sents:
        dbl += detect_doublets(s.lower(), adjset)
    if len(dbl) * k > 2.5:
        add("paired_modifiers", "sentence", len(dbl), 1.0, [d for d, _ in Counter(dbl).most_common()], "'free and gracious', 'complete and final'. Keep the one that carries meaning; common in formal human prose too.")

    tr_re = re.compile(r"^(?:" + "|".join(re.escape(t) for t in lex["transitions"]) + r")\b,?", re.I)
    trs = [tr_re.match(s).group(0).rstrip(",") for s in sents if tr_re.match(s)]
    if sents and len(trs) / len(sents) > 0.18 and len(trs) >= 3:
        add("connective_openers", "sentence", len(trs), 1.0, [f"{w} x{n}" if n > 1 else w for w, n in Counter(t.lower() for t in trs).most_common()], f"{len(trs)}/{len(sents)} sentences open with a stock connective.")

    mor = find_phrases(low, lex["moral_cues"])
    add("moralizing_cues", "structure", sum(n for _, n in mor), 1.0, [f"{p} x{n}" if n > 1 else p for p, n in mor], "Thematic commentary / lesson statements (StoryScope: AI 76% vs human 51%).")

    # dashes
    nd = len(DASH.findall(prose))
    dcut, dq = cut("dash_k", "p50", band("semi_paren_dash_k", "p50", 7.0))
    if nd and nd * k > dcut and nd * k > 3.0:
        add("dash_density", "surface", nd, 0.8, [f"{nd * k:.1f} per 1,000 words (human {dq} {dcut:.1f})"], "Weak alone, and only in clusters. Never strip every dash: a text with no dashes, semicolons, or parentheses is its own tell.")

    # fragments in a row
    frag = []
    for a, b in zip(sents, sents[1:]):
        if len(words_of(a)) <= 4 and len(words_of(b)) <= 4 and not re.search(r"\d", a + b):
            frag.append(snippet(a + " " + b))
    add("dramatic_fragments", "sentence", len(frag), 0.4 if genre == "fiction" else 1.0, frag)

    # --- rhythm
    rhythm = {}
    if len(slen) >= 6:
        mean = statistics.mean(slen)
        sd = statistics.pstdev(slen)
        cv = sd / mean if mean else 0
        runs = flat_runs(slen)
        in_runs = sum(e - s for s, e in runs)
        rhythm = dict(sentences=len(slen), mean=round(mean, 1), sd=round(sd, 1), cv=round(cv, 2),
                      short_share=round(sum(x <= 8 for x in slen) / len(slen), 2),
                      long_share=round(sum(x >= 30 for x in slen) / len(slen), 2),
                      flat_run_share=round(in_runs / len(slen), 2), longest_flat_run=max([e - s for s, e in runs] or [0]))
        if cv < 0.30 and len(slen) >= 8:
            add("flat_sentence_rhythm", "rhythm", 1, 1.5, [f"length CV {cv:.2f} (human median ~0.49)"], "Sentence lengths are very even.")
        if in_runs / len(slen) > 0.5 and len(slen) >= 8:
            ex = [snippet(" | ".join(str(slen[i]) for i in range(s, e)), 60) for s, e in runs[:3]]
            add("same_length_runs", "rhythm", len(runs), 1.0, ex, f"{in_runs}/{len(slen)} sentences sit in runs of similar length.")
        smax = max(slen)
        ccut, cq = cut("sent_max", "p10", 35)
        if len(slen) >= 12 and smax < ccut:
            add("sentence_ceiling", "rhythm", 1, 2.5 if genre != "fiction" else 1.0, [f"longest sentence {smax} words (human {cq} {ccut:.0f} in ~450 words)"],
                "No long, loose sentences. Join two related sentences in a few places; don't chain whole paragraphs.")
        # floor: short-sentence share below the human low cut
        nshort = sum(x <= 8 for x in slen)
        floor, fq = cut("short8", "p10", 0.206 if genre == "fiction" else 0.03)
        if len(slen) >= 20 and nshort / len(slen) < floor:
            add("sentence_floor", "rhythm", 1, 1.0, [f"{nshort} of {len(slen)} sentences ({nshort / len(slen):.0%}) are 8 words or fewer (human {fq} {floor:.0%})"],
                "No short sentences. Let one or two points stand alone in a plain short sentence; don't chop whole paragraphs.")
        long35 = sum(x >= 35 for x in slen) / len(slen)
        ocut, oq = cut("long35", "p90", 0.375)
        if len(slen) >= 10 and long35 > ocut + (0.05 if "cut" not in bands.get("long35", {}) else 0):
            add("over_chained", "rhythm", 1, 1.5, [f"{long35:.0%} of sentences are 35+ words (human {oq} {ocut:.0%})"],
                "Over-correction: too many long chained sentences. Split where a sentence carries two points.")

    # openers / templated frames (line-start labels like "Statement:" are format, not prose)
    sents = [re.sub(r"^(?:[A-Z][\w'-]*(?: [\w'-]+){0,2}):\s+", "", x) for x in sents]
    if len(sents) >= 8:
        first = Counter(words_of(s)[0].lower() for s in sents if words_of(s))
        w, n = first.most_common(1)[0]
        if n / len(sents) > 0.3 and w not in ("the",):
            add("repeated_opener", "sentence", n, 1.0, [f"'{w}' opens {n}/{len(sents)} sentences"])
        tri = Counter(" ".join(words_of(s)[:3]).lower() for s in sents if len(words_of(s)) >= 3)
        frames = [(f, n) for f, n in tri.items() if n >= 3]
        mid = Counter()
        stance = Counter()
        for s in sents:
            raw = words_of(s)
            for i in range(1, len(raw) - 2):
                tri3 = raw[i : i + 3]
                if any(x[:1].isupper() and x != "I" for x in tri3):
                    continue
                mid[" ".join(tri3).lower()] += 1
            for i in range(len(raw) - 1):
                if raw[i][:1].isupper() or raw[i + 1][:1].isupper():
                    continue
                a_, b_ = raw[i].lower(), raw[i + 1].lower()
                if (a_.endswith("ly") or b_.endswith("ly")) and not ({a_, b_} & FUNCTION_WORDS) and len(a_) > 2 and len(b_) > 2:
                    stance[a_ + " " + b_] += 1
        seen = {f for f, _ in frames}
        frames += [(f, n) for f, n in mid.items() if n >= 4 and f not in seen and not set(f.split()) <= FUNCTION_WORDS]
        frames += [(f, n) for f, n in stance.items() if n >= 3 and not any(f in g for g, _ in frames)]
        if frames:
            add("templated_frames", "structure", sum(n for _, n in frames), 0.5, [f"'{f}' x{n}" for f, n in sorted(frames, key=lambda x: -x[1])], "Same sentence frame recycled. Check whether the venue requires it before changing.")

    # stance labels cycled across sections ("I'm convinced", "my settled view", "I'm just as sure")
    lab = []
    nrel = 0
    for s in sents:
        rel = STANCE_REL.search(s)
        m = rel or STANCE.search(s)
        if m:
            nrel += bool(rel)
            lab.append(f"{m.group(0)}" + ("  (relative)" if rel else "") + f"  <- {snippet(s, 70)}")
    if nrel >= 2 or len(lab) >= 3:
        add("stance_labels", "structure", len(lab), 1.0, lab,
            f"{len(lab)} stance labels, {nrel} relative ('just as sure', 'equally firm'). Use a relative label at most once and carry strength in the claim itself.")

    # paragraph shape
    pstats = {}
    plens = [len(words_of(p)) for p in paras]
    if len(plens) >= 4:
        pm = statistics.mean(plens)
        pcv = statistics.pstdev(plens) / pm if pm else 0
        pstats = dict(paragraphs=len(plens), mean_words=round(pm), cv=round(pcv, 2))
        if pcv < 0.25:
            add("uniform_paragraphs", "structure", 1, 0.5, [f"paragraph length CV {pcv:.2f}"], "Every paragraph about the same size.")
    kick = []
    mor_re = re.compile(r"\b(?:matter|matters|mattered|truly|real|lesson|reminder|remind|means|meaning|everything|nothing|always|never|power|beauty|why|what it|that's|this is|and that|which is|all the difference)\b", re.I)
    for p in paras:
        ss = sentences(p)
        if len(ss) >= 3:
            last = ss[-1]
            if len(words_of(last)) <= 14 and mor_re.search(last):
                kick.append(snippet(last))
    if kick:
        add("paragraph_kickers", "structure", len(kick), 1.0, kick, "Short closing line that restates or moralizes. End on the last concrete point.")
    closers = []
    for p in paras:
        ss = sentences(p)
        if len(ss) >= 2 and SUMMARY_OPENER.match(ss[-1]) and snippet(ss[-1]) not in kick:
            closers.append(snippet(ss[-1]))
    add("summary_closer", "structure", len(closers), 1.0, closers, "The paragraph ends on 'So…', 'That's why…', 'Ultimately…'. A long kicker is still a kicker. End on the last concrete point.")
    if paras:
        lastp = paras[-1].lower()
        if re.match(r"(?:in conclusion|in summary|to sum up|ultimately|overall|in the end|at the end of the day|as (?:i|we) (?:look|move) (?:forward|ahead)|looking ahead|moving forward)", lastp):
            add("recap_ending", "structure", 1, 2.5, [snippet(paras[-1])])

    # profile checks against human bands (Brown corpus, ~450-word samples)
    body_colons = 0
    for line in prose.split("\n"):
        q = re.sub(r"\b\d+:\d+(?:[-\u2013]\d+)?:?", "", line)          # verse/time refs and the label colon after them
        q = re.sub(r"^\s*(?:[A-Z][\w'.-]*(?: [\w'.-]+){0,3}):", "", q)  # line-start labels ("Statement:", "Key Scripture:")
        q = re.sub(r"^\s*(?:[1-3] )?[A-Z][a-z]{1,9}\.? \d+:", "", q)
        body_colons += q.count(":")
    colon_k = body_colons * k
    kcut, kq = cut("colon_k", "p90", 4.4)
    if body_colons >= 2 and colon_k > kcut:
        add("colon_heavy", "sentence", body_colons, 1.5, [f"{colon_k:.1f} colons per 1k words in running prose (human {kq} {kcut:.1f})"], "Colons used to stage reveals or set up lists.")
    spd = prose.count(";") + prose.count("(") + nd
    if genre != "fiction" and nw >= 300 and spd == 0:
        add("narrow_punctuation", "sentence", 1, 1.0, ["no semicolons, parentheses, or dashes"], "Human prose (median ~8.5/1k) mixes these in; use them where they fit, never by quota.")
    if len(plens) >= 5:
        pm_ = statistics.mean(plens)
        pcv_ = statistics.pstdev(plens) / pm_ if pm_ else 0
        if pm_ < cut("para_mean", "p25", 60)[0] and pcv_ < 0.4 and genre != "fiction":
            add("short_even_paragraphs", "structure", 1, 1.0, [f"mean paragraph {pm_:.0f} words, CV {pcv_:.2f}"], "Many short, similar paragraphs.")
    lasts = [len(words_of(sentences(p)[-1])) for p in paras if len(sentences(p)) >= 3]
    if len(lasts) >= 4 and statistics.mean(lasts) < cut("last_sent_mean", "p25", 19)[0]:
        add("short_paragraph_endings", "structure", len(lasts), 1.0, [f"paragraphs end on {statistics.mean(lasts):.0f}-word sentences on average (human median {band('last_sent_mean', 'p50', 24):.0f})"], "Paragraphs close on a short line.")
    ttr = len({w.lower() for w in words[:300]}) / max(1, min(300, nw))
    vcut, vq = cut("ttr300", "p90", 0.633)
    if nw >= 300 and ttr > vcut:
        add("high_word_variety", "surface", 1, 0.8, [f"type/token over first 300 words {ttr:.2f} (human {vq} {vcut:.2f})"], "Possible synonym cycling: repeat the right word instead of rotating near-synonyms.")
    ingk = sum(w.lower().endswith("ing") and len(w) > 5 for w in words) * k
    icut, iq = cut("ing_k", "p90", 36)
    if ingk > icut:
        add("ing_heavy", "sentence", 1, 0.8, [f"{ingk:.0f} -ing words per 1k (human {iq} {icut:.0f})"])

    # formatting
    md_bold = len(re.findall(r"\*\*[^*]+\*\*", text))
    bold_labels = len(re.findall(r"^\s*(?:[-*•]|\d+[.)])\s+\*\*[^*]+:?\*\*:?", text, re.M))
    emojis = len(EMOJI.findall(text))
    title_heads = [l.strip() for l in text.split("\n") if l.strip().startswith("#") and len(l.split()) >= 4
                   and sum(w[:1].isupper() for w in l.lstrip("# ").split() if len(w) > 3) >= 0.8 * max(1, len([w for w in l.lstrip("# ").split() if len(w) > 3]))]
    add("bold_label_lists", "format", bold_labels, 1.5, [], "Every bullet has a bold label and colon.")
    if md_bold * k > 8 and not bold_labels:
        add("decorative_bold", "format", md_bold, 0.8)
    add("emoji", "format", emojis, 1.5)
    add("title_case_headings", "format", len(title_heads), 0.5, title_heads)

    allit = alliteration_runs(words)
    if allit * k > 8:
        add("alliteration", "sentence", allit, 1.0, [], "Sound-patterned phrasing (StoryScope: alliteration prominent in 98% of AI vs 79% of human stories).")

    # --- informational metrics (no score)
    info = dict(words=len(words), genre=genre,
                contractions_per_1k=round(len(CONTRACTION.findall(prose)) * k, 1),
                nominalizations_per_100=round(len(NOMINAL.findall(low)) * 100 / nw, 1),
                dashes_per_1k=round(nd * k, 1),
                triads=t3, other_lists=tother,
                rhythm=rhythm, paragraphs=pstats,
                # the measures the human bands describe (data/human_bands.json)
                profile=dict(sent_max=max(slen) if slen else None,
                             long35=round(sum(x >= 35 for x in slen) / len(slen), 3) if slen else None,
                             short8=round(sum(x <= 8 for x in slen) / len(slen), 3) if slen else None,
                             para_mean=round(statistics.mean(plens), 1) if plens else None,
                             colon_k=round(colon_k, 2), semi_paren_dash_k=round(spd * k, 2), dash_k=round(nd * k, 2),
                             ing_k=round(ingk, 2), ttr300=round(ttr, 3) if nw >= 300 else None, triads_k=round(t3 * k, 2),
                             last_sent_mean=round(statistics.mean(lasts), 1) if lasts else None))

    # --- index: density-weighted for countable tells, flat weight for habit/profile flags
    FLAT = {"flat_sentence_rhythm", "sentence_ceiling", "uniform_paragraphs", "recap_ending", "narrow_punctuation", "short_even_paragraphs",
            "short_paragraph_endings", "high_word_variety", "ing_heavy", "colon_heavy", "triad_habit", "templated_frames", "repeated_opener",
            "common_ai_words_cluster", "connective_openers", "rather_than_cluster", "dash_density", "title_case_headings"}
    score = 0.0
    for key, f in F.items():
        if key in FLAT:
            score += f["weight"] * (1.0 if f["count"] <= 1 else min(2.0, math.log2(1 + f["count"]) / 1.6))
        else:
            score += f["weight"] * min(f["count"] * k, 12.0)
    label = next(lbl for lim, lbl in BANDS if score < lim)
    return dict(index=round(score, 2), band=label, info=info, findings=F)


# ---------------------------------------------------------------- diff (meaning lock)

STARTERS = set("""the a an this that these those it its in on at as if when while because since though although but and or so
yet for nor some many most each every all no not what how why where who which there here he she they we i you my our your his her
their one two three first second third finally also even then now today however therefore thus still such after before during until
both either neither more less other another any much few several only just perhaps maybe yes let do does did is are was were be
can could should would will may might must""".split())


def lock_items(text):
    """Items that must survive a rewrite: refs, numbers, quotes, non-ASCII terms, names, URLs/code."""
    t = normalize(text)
    items = set()
    for m in re.finditer(r"\b(?:[1-3]\s)?[A-Z][a-z]{1,9}\.?\s\d{1,3}(?::\d{1,3}(?:[-\u2013]\d{1,3})?)?(?:[-\u2013]\d{1,3})?\b", t):
        items.add(("ref", re.sub(r"\s+", " ", m.group(0).replace("\u2013", "-"))))
    body = re.sub(r"(?m)^\s*(?:[-*\u2022]\s+)?(?:\d+[.)]|[A-Za-z][.)])\s+", "", t)  # list markers
    body = re.sub(r"\*\*|__", "", body)
    for m in re.finditer(r"\b\d[\d,.:%/-]*\b", body):
        items.add(("num", m.group(0).rstrip(".,")))
    for m in re.finditer(r'"([^"]{3,120})"', t):
        items.add(("quote", m.group(1)))
    for m in re.finditer(r"\b[a-z]*[\u00c0-\u024f\u0370-\u03ff][\w\u00c0-\u024f\u0370-\u03ff]*\b", t):
        items.add(("term", m.group(0)))
    chunks = []
    for line in body.split("\n"):
        line = re.sub(r"^\s*(?:[-*\u2022>#]+\s*)+", "", line)
        chunks += sentences(line)
    mid_caps = set()
    for s in chunks:
        for w in re.findall(r"[A-Za-z][\w-]*", s)[1:]:
            if w[0].isupper():
                mid_caps.add(w)
    for s in chunks:
        ws = re.findall(r"[A-Za-z][\w-]*", s)
        for i, w in enumerate(ws):
            if not w[0].isupper() or w.lower() in STARTERS or len(w) < 2:
                continue
            if i == 0:
                # sentence-initial: a name only if it is capitalized mid-sentence elsewhere,
                # possessive, or followed by another capitalized word ("Festal Letter")
                nxt = ws[1] if len(ws) > 1 else ""
                if not (w in mid_caps or re.match(re.escape(w) + r"'s\b", s) or (nxt[:1].isupper() and nxt.lower() not in STARTERS)):
                    continue
            items.add(("name", w))
    for m in re.finditer(r"https?://\S+|[\w.+-]+@[\w-]+\.[\w.]+|`[^`]+`", t):
        items.add(("code", m.group(0)))
    return items


def _present(item, text):
    kind, val = item
    if kind == "name":
        return re.search(r"\b" + re.escape(val) + r"\b", text) is not None
    if kind == "num":
        return re.search(r"(?<![\d])" + re.escape(val) + r"(?![\d])", text) is not None
    return re.sub(r"\s+", " ", val) in re.sub(r"\s+", " ", text)


def diff(orig, new, genre="auto"):
    to, tn = normalize(orig), normalize(new)
    missing = sorted(f"{k}:{v}" for k, v in lock_items(orig) if not _present((k, v), tn))
    added = sorted(f"{k}:{v}" for k, v in lock_items(new) if not _present((k, v), to))
    wa, wb = words_of(normalize(orig)), words_of(normalize(new))
    ca = {w.lower() for w in wa if w.lower() not in FUNCTION_WORDS}
    cb = {w.lower() for w in wb if w.lower() not in FUNCTION_WORDS}
    s0, s1 = scan(orig, genre=genre), scan(new, genre=genre)
    f0 = {k: v["count"] for k, v in s0["findings"].items()}
    f1 = {k: v["count"] for k, v in s1["findings"].items()}

    def shape(t):
        t = normalize(t)
        return dict(paragraphs=len([p for p in re.split(r"\n\s*\n", t) if p.strip()]),
                    list_items=len(re.findall(r"(?m)^\s*(?:[-*\u2022]|\d+[.)])\s+", t)),
                    questions=t.count("?"))
    sh0, sh1 = shape(orig), shape(new)

    def bigrams(x):
        w = [t.lower() for t in words_of(x)]
        return set(zip(w, w[1:]))
    s_orig = [x for p in prose_paragraphs(normalize(orig)) for x in sentences(p) if len(words_of(x)) >= 6]
    s_new = [bigrams(x) for p in prose_paragraphs(normalize(new)) for x in sentences(p)]
    kept = 0
    for x in s_orig:
        b0 = bigrams(x)
        if b0 and any(len(b0 & b1) / len(b0) >= 0.7 for b1 in s_new):
            kept += 1
    retained = dict(kept=kept, total=len(s_orig))
    return dict(
        retained=retained,
        structure=dict(before=sh0, after=sh1),
        length=dict(before=len(wa), after=len(wb), change_pct=round(100.0 * (len(wb) - len(wa)) / max(1, len(wa)), 1)),
        content_word_overlap=round(len(ca & cb) / max(1, len(ca | cb)), 2),
        missing_locked=missing, new_locked=added,
        index=dict(before=s0["index"], after=s1["index"], band_before=s0["band"], band_after=s1["band"]),
        findings_before=f0, findings_after=f1,
        rising=[dict(finding=k, before=f0.get(k, 0), after=f1[k], info=s1["findings"][k]["weight"] == 0)
                for k in sorted(f1) if f1[k] > f0.get(k, 0)],
        rhythm_before=s0["info"]["rhythm"], rhythm_after=s1["info"]["rhythm"],
    )


# ---------------------------------------------------------------- output

def print_scan(r):
    i = r["info"]
    print(f"SLOPSCAN  index {r['index']}  ({r['band']})   words {i['words']}  genre {i['genre']}")
    rh = i.get("rhythm") or {}
    if rh:
        print(f"  rhythm: {rh['sentences']} sentences, mean {rh['mean']} words, CV {rh['cv']}, short<=8 {rh['short_share']:.0%}, long>=30 {rh['long_share']:.0%}, in flat runs {rh['flat_run_share']:.0%}")
    print(f"  per 1k words: contractions {i['contractions_per_1k']}, dashes {i['dashes_per_1k']}; nominalizations/100w {i['nominalizations_per_100']}; lists of three {i['triads']} vs other {i['other_lists']}")
    if not r["findings"]:
        print("  no findings")
        return
    order = {"structure": 0, "rhythm": 1, "sentence": 2, "surface": 3, "format": 4}
    for key, f in sorted(r["findings"].items(), key=lambda kv: (kv[1]["weight"] == 0, order[kv[1]["layer"]], -kv[1]["weight"] * kv[1]["count"])):
        tag = "info" if f["weight"] == 0 else f["layer"]
        print(f"\n  [{tag}] {key}  x{f['count']}" + (f"  - {f['note']}" if f["note"] else ""))
        for ex in f["examples"]:
            print(f"      - {ex}")


def print_diff(d):
    L = d["length"]
    print(f"LENGTH  {L['before']} -> {L['after']} words ({L['change_pct']:+}%)   content-word overlap {d['content_word_overlap']}")
    print(f"INDEX   {d['index']['before']} ({d['index']['band_before']}) -> {d['index']['after']} ({d['index']['band_after']})")
    rb, ra = d["rhythm_before"], d["rhythm_after"]
    if rb and ra:
        print(f"RHYTHM  CV {rb['cv']} -> {ra['cv']}   flat-run share {rb['flat_run_share']} -> {ra['flat_run_share']}")
    rt = d["retained"]
    if rt["total"]:
        print(f"RETAINED {rt['kept']}/{rt['total']} prose sentences kept near-verbatim ({100 * rt['kept'] // rt['total']}%)")
    print("MEANING LOCK")
    if d["missing_locked"]:
        print("  MISSING from rewrite (verify nothing was lost):")
        for x in d["missing_locked"]:
            print("    - " + x)
    else:
        print("  all locked items from the original are present")
    if d["new_locked"]:
        print("  NEW in rewrite (verify each is supported by the source or the user):")
        for x in d["new_locked"]:
            print("    + " + x)
    sb, sa = d["structure"]["before"], d["structure"]["after"]
    print(f"SHAPE   paragraphs {sb['paragraphs']} -> {sa['paragraphs']}   list items {sb['list_items']} -> {sa['list_items']}   questions {sb['questions']} -> {sa['questions']}")
    if sa["list_items"] < sb["list_items"]:
        print("  ! list items were removed or folded into prose: keep real lists unless the list itself was the tell")
    if sa["questions"] < sb["questions"]:
        print("  ! a question was dropped: closing questions and calls to action are content")
    if sb["paragraphs"] >= 3 and abs(sa["paragraphs"] - sb["paragraphs"]) > max(1, sb["paragraphs"] // 4):
        print("  ! paragraph count changed a lot: keep the author's paragraphing unless a break was the tell")
    keys = sorted(set(d["findings_before"]) | set(d["findings_after"]))
    if keys:
        print("FINDINGS  before -> after")
        for k in keys:
            print(f"  {k:28s} {d['findings_before'].get(k, 0):>3} -> {d['findings_after'].get(k, 0)}")
    for r in d["rising"]:
        print(f"  ! RISING {r['finding']} {r['before']} -> {r['after']}" + (" (info)" if r["info"] else "")
              + ": the rewrite made this worse. Fix it, or say in the notes why it stays.")


def outline(text):
    """First and last sentence of every prose paragraph, with hint tags on the last."""
    lex = load_lex()
    out = []
    for p in prose_paragraphs(normalize(text)):
        ss = sentences(p) or [p]
        out.append(dict(first=ss[0], last=ss[-1], sentences=len(ss), tags=ending_tags(ss[-1], lex)))
    return out


def print_outline(rows):
    print("OPENINGS  (outline test: if these read as a clean, evenly paced summary, the structure is machine-shaped)")
    for i, r in enumerate(rows, 1):
        print(f"{i:>2}. {snippet(r['first'], 160)}")
    print("\nENDINGS  (last sentence of each paragraph: sections should not all close on a lesson, maxim, or application)")
    for i, r in enumerate(rows, 1):
        print(f"{i:>2}. {snippet(r['last'], 160)}" + (f"   [{', '.join(r['tags'])}]" if r["tags"] else ""))
    n = sum(bool(r["tags"]) for r in rows)
    if n:
        print(f"\n  {n} of {len(rows)} endings carry a summary, rider, or application cue (hints, not verdicts).")


def read(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__); return 0
    cmd = argv[1]
    as_json = "--json" in argv
    genre = "auto"
    top = 8
    if "--genre" in argv:
        genre = argv[argv.index("--genre") + 1]
    if "--top" in argv:
        top = int(argv[argv.index("--top") + 1])
    args = [a for a in argv[2:] if not a.startswith("--") and a not in (genre, str(top))]
    if cmd == "scan":
        r = scan(read(args[0]), genre=genre, top=top)
        print(json.dumps(r, indent=1)) if as_json else print_scan(r)
    elif cmd == "diff":
        d = diff(read(args[0]), read(args[1]), genre=genre)
        print(json.dumps(d, indent=1)) if as_json else print_diff(d)
    elif cmd == "outline":
        o = outline(read(args[0]))
        print(json.dumps(o, indent=1)) if as_json else print_outline(o)
    else:
        print(__doc__); return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
