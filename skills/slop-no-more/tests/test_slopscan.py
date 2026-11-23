"""Run: python3 -m unittest discover -s tests   (from the skill directory)"""
import os, re, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import slopscan as S

SLOP = """In today's fast-paced world, it's important to note that collaboration plays a crucial role in success.
It's not just a tool; it's a testament to our unwavering commitment to excellence.

Additionally, the platform seamlessly integrates with your workflow, highlighting the importance of innovation.
The result? Productivity, creativity, and growth. That's the real lesson.

In conclusion, the future looks bright. I hope this helps!"""

PLAIN = """We moved the standup to Tuesdays because half the team was out on Mondays, and the Monday meetings kept
turning into a recap of the weekend's pager alerts, which nobody needed twice. Dana will send the agenda the night before.
If you can't make it, put your update in the doc; I read it before lunch."""


class ScanTests(unittest.TestCase):
    def test_slop_scores_high(self):
        r = S.scan(SLOP)
        self.assertGreater(r["index"], 16)
        for key in ("chatbot_residue", "stock_phrases", "not_x_but_y", "ing_rider", "self_answered_question", "ai_vocabulary"):
            self.assertIn(key, r["findings"], key)

    def test_plain_scores_low(self):
        r = S.scan(PLAIN)
        self.assertLess(r["index"], 5)

    def test_proper_noun_not_vocab(self):
        r = S.scan("The Old Testament and the New Testament were read together. " * 3)
        self.assertNotIn("ai_vocabulary", r["findings"])

    def test_label_and_verse_colons_ignored(self):
        t = "Key Scripture: Heb. 1:1-2: God has spoken.\nJohn 1:18: Christ makes the Father known.\n" * 6
        self.assertNotIn("colon_heavy", S.scan(t)["findings"])


class GenreTests(unittest.TestCase):
    def test_aliases(self):
        self.assertEqual(S.scan(PLAIN, genre="email")["info"]["genre"], "professional")
        self.assertEqual(S.scan(PLAIN, genre="essay")["info"]["genre"], "general")
        self.assertEqual(S.scan(PLAIN, genre="post")["info"]["genre"], "casual")

    def test_info_gating_is_per_genre(self):
        saved = S.INFO_IN
        try:
            S.INFO_IN = {"not_x_but_y": {"academic"}}
            self.assertEqual(S.scan(SLOP, genre="academic")["findings"]["not_x_but_y"]["weight"], 0.0)
            self.assertGreater(S.scan(SLOP, genre="general")["findings"]["not_x_but_y"]["weight"], 0.0)
        finally:
            S.INFO_IN = saved

    def test_tuned_cut_overrides_percentile(self):
        t = "We met at noon: the plan changed. Then: a new list. Later: more notes. The end came: quietly. " * 4
        never = {"general": {"colon_k": {"p90": 0.0, "cut": 1000.0, "cut_q": "p95"}}}
        always = {"general": {"colon_k": {"p90": 1000.0, "cut": 0.0, "cut_q": "p75"}}}
        self.assertNotIn("colon_heavy", S.scan(t, genre="general", bands=never)["findings"])
        self.assertIn("colon_heavy", S.scan(t, genre="general", bands=always)["findings"])

    def test_profile_reported(self):
        prof = S.scan(PLAIN)["info"]["profile"]
        for key in ("sent_max", "short8", "colon_k", "triads_k", "ing_k"):
            self.assertIn(key, prof)


class DiffTests(unittest.TestCase):
    ORIG = "Athanasius's Festal Letter 39 (AD 367) confirmed the list. John 17:17: God's word is truth. Paul wrote \"the sun rose\" in kanōn."

    def test_identical_has_no_missing(self):
        d = S.diff(self.ORIG, self.ORIG)
        self.assertEqual(d["missing_locked"], [])
        self.assertEqual(d["new_locked"], [])

    def test_detects_lost_ref_name_and_invention(self):
        new = "Athanasios's Festal Letter 39 (AD 367) confirmed the list in 2019. God's word is truth. Paul wrote \"the sun rose\" in kanōn."
        d = S.diff(self.ORIG, new)
        self.assertIn("ref:John 17:17", d["missing_locked"])
        self.assertIn("name:Athanasius", d["missing_locked"])
        self.assertIn("num:2019", d["new_locked"])

    def test_sentence_position_does_not_matter(self):
        new = "The list was confirmed by Athanasius's Festal Letter 39 (AD 367). God's word is truth (John 17:17). In kanōn Paul wrote \"the sun rose\"."
        self.assertEqual(S.diff(self.ORIG, new)["missing_locked"], [])

    def test_rising_findings_are_listed(self):
        before = "We moved the standup to Tuesday. Dana sends the agenda."
        after = before + " The plan is clear, concise, and complete. The notes are short, sharp, and simple. The room is quiet, cold, and clean."
        rising = {r["finding"]: (r["before"], r["after"]) for r in S.diff(before, after)["rising"]}
        self.assertIn("triad_habit", rising)
        self.assertEqual(rising["triad_habit"][0], 0)
        self.assertEqual(S.diff(before, before)["rising"], [])


HERE = os.path.dirname(__file__)
# Synthetic position paper (academic, Position / Discussion) with the patterns the v1.4 checks look for:
# cycled stance labels with one relative label, no short sentences, a noun rider, a summary closer,
# two unnamed sources, and application endings. Its Discussion puts one paragraph per line, as Word exports do.
FIXTURE = os.path.join(HERE, "fixtures", "parking_position_synthetic.txt")
# The real v1.3 rewrite that prompted the v1.4 checks. Kept out of the dist zip; its tests skip when it's absent.
LOCAL = os.path.join(HERE, "local", "doctrinal_rewrite_v1_3.txt")


class V14Fixture:
    """Checks a text the v1.4 checks must fire on. Subclasses set the path and the expected details."""
    PATH = RELATIVE = RIDER = CLOSER = APPLICATION = ""
    PARAS, PARA_AT, TAGS = 0, (0, ""), {}

    @classmethod
    def setUpClass(cls):
        with open(cls.PATH, encoding="utf-8") as fh:
            cls.text = fh.read()
        cls.findings = S.scan(cls.text, genre="academic")["findings"]

    def test_fixture_fires_new_checks(self):
        for key in ("stance_labels", "sentence_floor", "noun_rider", "summary_closer", "vague_attribution"):
            self.assertIn(key, self.findings, key)

    def test_fixture_details(self):
        self.assertTrue(any("(relative)" in e and self.RELATIVE in e for e in self.findings["stance_labels"]["examples"]))
        self.assertTrue(any(self.RIDER in e for e in self.findings["noun_rider"]["examples"]))
        self.assertTrue(any(e.startswith(self.CLOSER) for e in self.findings["summary_closer"]["examples"]))
        self.assertEqual(self.findings["vague_attribution"]["count"], 2)

    def test_word_export_paragraphs_split_per_line(self):
        # the Discussion blocks put one paragraph per line with no blank line between them
        paras = S.prose_paragraphs(S.normalize(self.text))
        self.assertEqual(len(paras), self.PARAS)
        self.assertTrue(paras[self.PARA_AT[0]].startswith(self.PARA_AT[1]))

    def test_outline_endings(self):
        rows = S.outline(self.text)
        self.assertIn(self.APPLICATION, [r["last"] for r in rows])
        for start, tag in self.TAGS.items():
            self.assertIn(tag, next(r["tags"] for r in rows if r["last"].startswith(start)), start)


class V14FixtureTests(V14Fixture, unittest.TestCase):
    PATH = FIXTURE
    RELATIVE, RIDER, CLOSER = "just as confident", "evidence of how much", "So I can support both changes"
    APPLICATION = "If the council asks residents to give up free parking, I want to be able to show them exactly where the money goes."
    PARAS, PARA_AT = 7, (5, "My view on the revenue question is more provisional")
    TAGS = {"So I can support": "summary closer", "Downtown lots rebuilt": "rider",
            "If the council asks": "application?", "As a future planner": "application?"}


@unittest.skipUnless(os.path.exists(LOCAL), "local only: tests/local/doctrinal_rewrite_v1_3.txt is not shipped")
class V14LocalTests(V14Fixture, unittest.TestCase):
    PATH = LOCAL
    RELATIVE, RIDER, CLOSER = "just as confident", "evidence of how careful", "So I can trust all of it"
    APPLICATION = "If these 66 books are God's complete and final Word, I want to build my life on them and help others do the same."
    PARAS, PARA_AT = 16, (10, "A high view of Scripture ought to produce obedience")
    TAGS = {"So I can trust all of it": "summary closer", "Hebrews, James, and": "rider", "If these 66 books": "application?"}


class V14CheckTests(unittest.TestCase):
    def test_hard_wrapped_prose_not_split(self):
        self.assertEqual(len(S.prose_paragraphs(PLAIN)), 1)
        self.assertEqual(len(S.prose_paragraphs("One short line.\nAnother short line.\nA third one here.")), 1)

    def test_stance_relative_frames(self):
        two = "I'm just as confident that the second view holds. Later, I'm just as sure that the third holds too. " * 1
        self.assertIn("stance_labels", S.scan(two)["findings"])
        one = "I'm just as confident that the second view holds. The third view is plain enough from the text."
        self.assertNotIn("stance_labels", S.scan(one)["findings"])

    def test_noun_rider(self):
        lex = S.load_lex()
        self.assertTrue(S.has_noun_rider("Hebrews and James took longer to win acceptance, evidence of how careful the church was.", lex))
        self.assertTrue(S.has_noun_rider("The library stayed open all night, a sign that finals had started.", lex))
        self.assertFalse(S.has_noun_rider("However, evidence that the plan worked is thin.", lex))
        self.assertFalse(S.has_noun_rider("The court heard it as evidence of fraud.", lex))

    def test_summary_closer_only_at_paragraph_end(self):
        end = "We read the whole letter twice. The second reading took an hour. So I can trust all of it, even the parts I find hard."
        mid = "So I can trust all of it, even the parts I find hard. We read the whole letter twice. The second reading took an hour."
        self.assertIn("summary_closer", S.scan(end)["findings"])
        self.assertNotIn("summary_closer", S.scan(mid)["findings"])
        self.assertNotIn("summary_closer", S.scan("We waited. The bus never came. So far nobody has explained why.")["findings"])

    def test_vague_attribution_not_in_fiction(self):
        t = "Some theologians argue that the light of nature can save. Many people believe it too. We read Romans 1 instead."
        self.assertIn("vague_attribution", S.scan(t, genre="academic")["findings"])
        self.assertNotIn("vague_attribution", S.scan(t, genre="fiction")["findings"])
        self.assertNotIn("vague_attribution", S.scan("NLRDA studies show that flat cars load faster. We used them.", genre="academic")["findings"])

    def test_sentence_floor(self):
        long_s = "The committee met on Tuesday afternoon to review the budget for the coming year and the staffing plan. "
        self.assertIn("sentence_floor", S.scan(long_s * 24, genre="academic")["findings"])
        mixed = (long_s * 4 + "Nobody objected. ") * 6
        self.assertNotIn("sentence_floor", S.scan(mixed, genre="academic")["findings"])


class HygieneAndLockTests(unittest.TestCase):
    def test_invisible_characters_counted_and_stripped(self):
        t = "The committee re\u200bviewed the\u00a0plan.\ufeff It passed."
        r = S.scan(t)
        self.assertEqual(r["findings"]["invisible_characters"]["count"], 2)
        self.assertEqual(r["findings"]["invisible_characters"]["weight"], 0.0)
        self.assertEqual(r["info"]["odd_spaces"], {"NO-BREAK SPACE": 1})
        self.assertIn("reviewed", S.normalize(t))

    def test_legitimate_joiners_ignored(self):
        self.assertEqual(S.invisible_chars("family \U0001F468\u200d\U0001F469 and \u0645\u06cc\u200c\u062e\u0648\u0627\u0647\u0645"), {})

    def test_invisible_does_not_change_index(self):
        base = S.scan(PLAIN)["index"]
        self.assertEqual(S.scan(PLAIN.replace("standup", "stand\u200bup"))["index"], base)

    def test_protected_terms(self):
        o = "We used the Kepler survey and the Gaia catalog. The Kepler survey was small."
        n = "We used the Kepler survey and a star catalog."
        d = S.diff(o, n, protect=S.parse_terms("Kepler survey, Gaia catalog; Zeta"))
        self.assertIn("protected:Gaia catalog", d["missing_locked"])
        self.assertNotIn("protected:Kepler survey", d["missing_locked"])
        p = {x["term"]: (x["before"], x["after"]) for x in d["protected"]}
        self.assertEqual(p["Kepler survey"], (2, 1))
        self.assertEqual(p["Zeta"], (0, 0))

    def test_verbatim_runs(self):
        o = 'The budget for the survey was far too small for the work we planned. She said "one two three four five six seven eight nine".'
        n = 'We cut corners. The budget for the survey was far too small for the work. She said "one two three four five six seven eight nine".'
        runs = S.verbatim_runs(o, n)
        self.assertEqual(runs, ["The budget for the survey was far too small for the work"])
        self.assertEqual(S.verbatim_runs(o, "Nothing in common here at all, not even a little bit of it."), [])

    def test_cli_protect_arg_not_read_as_file(self):
        import io, contextlib, tempfile
        with tempfile.TemporaryDirectory() as td:
            a, b = os.path.join(td, "a.txt"), os.path.join(td, "b.txt")
            open(a, "w").write("We used the Gaia catalog for every star in the sample.")
            open(b, "w").write("Every star in the sample came from a catalog.")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                S.main(["slopscan.py", "diff", a, b, "--protect", "Gaia catalog", "--genre", "academic"])
            self.assertIn("protected:Gaia catalog", buf.getvalue())


class PrefsAndLimitsTests(unittest.TestCase):
    def prefs_file(self, td, body):
        path = os.path.join(td, "preferences.md")
        open(path, "w").write(body)
        return path

    def test_load_prefs_layering(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            a = self.prefs_file(td, "---\nban: semicolons, dashes   # comment\nmax_sentence_words:\n---\nnotes")
            b = os.path.join(td, "b.md"); open(b, "w").write("---\nban: colon\nwords_per_page: 500\n---\n")
            p = S.load_prefs([a, os.path.join(td, "missing.md"), b])
            self.assertEqual(p["ban"], {"colon"})
            self.assertEqual(p["words_per_page"], 500)
            self.assertEqual(len(p["sources"]), 2)
            self.assertEqual(S.load_prefs([a])["ban"], {"semicolon", "dash"})

    def test_shipped_template_bans_nothing(self):
        p = S.load_prefs([os.path.join(HERE, "..", "preferences.md")])
        self.assertEqual(p["ban"], set())
        self.assertEqual(p["sources"], [])

    def test_banned_punctuation_skips_allowed_spans(self):
        prefs = dict(ban={"semicolon", "dash"})
        t = ('The church recognized the canon; it did not create it. Jonah ran \u2014 and God followed (Jonah 1:3; 4:6\u201311). '
             'Pages 4-6 and a well-known idea -- grace -- matter. He said "wait; listen \u2014 now".')
        v = S.check_prefs(t, prefs)
        self.assertEqual(v["semicolon"]["count"], 1)
        self.assertEqual(v["dash"]["count"], 3)
        self.assertEqual(S.check_prefs("A well-known, long-term plan for 2019-2020 (Smith 4; Jones 7).", prefs), {})

    def test_colon_label_allowed(self):
        v = S.check_prefs("Statement: Scripture is true.\nThe reason is simple: it says so.", dict(ban={"colon"}))
        self.assertEqual(v["colon"]["count"], 1)

    def test_sentence_cap(self):
        long_s = "This sentence keeps going and going with one clause after another until it is far too long to read easily at all. "
        v = S.check_prefs(long_s + "Short one.", dict(ban=set(), max_sentence_words=15))
        self.assertEqual(v["max_sentence_words"]["count"], 1)

    def test_parse_range(self):
        self.assertEqual(S.parse_range("375"), (None, 375))
        self.assertEqual(S.parse_range("2-3"), (2, 3))
        self.assertEqual(S.parse_range("300 to 375"), (300, 375))
        with self.assertRaises(ValueError):
            S.parse_range("about three")

    def test_limits(self):
        t = "# Title\n\n" + "One two three four five. " * 20
        lim = S.check_limits(t, dict(words=(None, 90), sentences=(25, 30), pages=(None, 1)))
        st = {c["limit"]: c["status"] for c in lim["checks"]}
        self.assertEqual(lim["words"], 101)
        self.assertEqual(st, dict(words="OVER", sentences="UNDER", pages="ok"))
        self.assertEqual([c for c in lim["checks"] if c["limit"] == "words"][0]["over_by_words"], 11)

    def test_scan_and_diff_carry_prefs_and_limits(self):
        prefs = dict(ban={"semicolon", "dash"}, sources=["x"], words_per_page=275)
        r = S.scan(PLAIN, prefs=prefs, limits=dict(words=(None, 20)))
        self.assertIn("semicolon", r["prefs"]["violations"])
        self.assertEqual(r["limits"]["checks"][0]["status"], "OVER")
        d = S.diff(PLAIN, PLAIN.replace(";", "."), prefs=prefs)
        self.assertEqual(d["prefs"]["before"], {"semicolon": 1})
        self.assertEqual(d["prefs"]["violations"], {})
        self.assertIsNone(S.scan(PLAIN)["prefs"])


class SkillFileTests(unittest.TestCase):
    ROOT = os.path.join(HERE, "..")

    def test_named_files_exist(self):
        with open(os.path.join(self.ROOT, "SKILL.md"), encoding="utf-8") as fh:
            named = set(re.findall(r"`((?:prompts|scripts|references)/[\w./]+)`", fh.read()))
        self.assertIn("prompts/meaning_check.txt", named)
        for path in named:
            self.assertTrue(os.path.exists(os.path.join(self.ROOT, path)), path)

    def test_prompts_have_no_template_slots(self):
        # step 7 and cross_review.sh send these files as written, followed only by the two texts
        for name in ("meaning_check.txt", "cross_review.txt"):
            with open(os.path.join(self.ROOT, "prompts", name), encoding="utf-8") as fh:
                self.assertNotRegex(fh.read(), r"\{[A-Z_]+\}", name)


if __name__ == "__main__":
    unittest.main()
