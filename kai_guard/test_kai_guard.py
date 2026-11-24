#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KaiGuard v1.3.0 tests. Run: python -m unittest -v   (stdlib only, no pytest needed)."""
import json
import random
import threading
import time
import unicodedata
import unittest

from kai_guard import (Action, AntiBullshitLoop, DEFAULT_MESSAGES, KaiBoundary, Policy, STATE_SCHEMA,
                       StaleDecisionError, StateError, __version__, normalize, similarity)

Q = "Dlaczego KFC to KFC?"
STAGES = [Action.ANSWER, Action.ANSWER, Action.REPHRASE, Action.REPHRASE,
          Action.CLARIFY, Action.CLARIFY, Action.CLARIFY, Action.STOP_LOOP]


def ask(g, text=Q, *, delivered=True, **kw):
    d = g.decide(text, **kw)
    g.commit(d, delivered=delivered)
    return d


class TestPolicy(unittest.TestCase):
    def test_default_valid(self):
        Policy()

    def test_validation(self):
        bad = [dict(rephrase_at=5, clarify_at=4), dict(rephrase_at=1), dict(stop_at=2),
               dict(similarity_threshold=0.0), dict(similarity_threshold=1.5), dict(similarity_threshold=True),
               dict(similarity_method="semantic"), dict(min_normalized_chars=0), dict(max_input_chars=0),
               dict(history_limit=0), dict(stop_at=True), dict(exempt_phrases={"ok"}),
               dict(polarity_tokens=frozenset({1})), dict(messages={"no_such_reason": "x"}),
               dict(messages={"input_too_long": 5})]
        for kw in bad:
            with self.assertRaises(ValueError, msg=str(kw)):
                Policy(**kw)

    def test_history_limit_is_independent_of_stop_at(self):
        # alpha v1.2 rejected history_limit=5 although history no longer affects decisions
        Policy(history_limit=5)

    def test_policy_roundtrip(self):
        p = Policy(stop_at=9, messages={"input_too_long": "Too long."})
        self.assertEqual(Policy.from_dict(json.loads(json.dumps(p.to_dict()))), p)


class TestNormalize(unittest.TestCase):
    def test_cases(self):
        self.assertEqual(normalize("  ŻÓŁĆ!!! "), "żółć")
        self.assertEqual(normalize("Hello, World!"), "hello world")
        self.assertEqual(normalize("   "), "")
        self.assertEqual(normalize("żółć"), normalize(unicodedata.normalize("NFD", "żółć")))

    def test_static_alias_kept(self):
        self.assertEqual(AntiBullshitLoop.normalize("A!"), "a")


class TestSimilarity(unittest.TestCase):
    def test_basics(self):
        self.assertEqual(similarity("a b", "a b"), 1.0)
        self.assertEqual(similarity("", "a"), 0.0)
        self.assertEqual(similarity("a", ""), 0.0)

    def test_symmetric_and_bounded_randomised(self):
        rng = random.Random(5)
        vocab = "kfc nie jest to dlaczego 10 20 panierka sos".split()
        for method in ("tokens", "chars"):
            for _ in range(300):
                a = " ".join(rng.choice(vocab) for _ in range(rng.randint(1, 12)))
                b = " ".join(rng.choice(vocab) for _ in range(rng.randint(1, 12)))
                s1, s2 = similarity(a, b, method=method), similarity(b, a, method=method)
                self.assertEqual(s1, s2)
                self.assertTrue(0.0 <= s1 <= 1.0)

    def test_digit_guard(self):
        for a, b in [("ile kosztuje 10 sztuk", "ile kosztuje 20 sztuk"),
                     ("oblicz 17 razy 23 plus 8", "oblicz 19 razy 23 plus 8")]:
            for method in ("tokens", "chars"):
                self.assertEqual(similarity(a, b, method=method), 0.0)   # alpha v1.2 chars: 0.95 / 0.96

    def test_polarity_guard(self):
        self.assertEqual(similarity("czy mozna to jesc", "czy nie mozna to jesc"), 0.0)
        self.assertEqual(similarity("czy mozna to jesc", "czy nie mozna to jesc", method="chars"), 0.0)
        self.assertGreater(similarity("czy mozna to jesc", "czy nie mozna to jesc", polarity_tokens=frozenset()), 0.5)

    def test_documented_tradeoff_tokens_misses_paraphrase_chars_catches(self):
        a, b = "dlaczego kfc to kfc", "dlaczego kfc jest kfc"
        self.assertLess(similarity(a, b, method="tokens"), 0.86)       # conservative: false negative
        self.assertGreaterEqual(similarity(a, b, method="chars"), 0.86)

    def test_filler_words_still_detected(self):
        self.assertGreaterEqual(similarity("dlaczego kfc to kfc", "hej dlaczego kfc to kfc"), 0.86)

    def test_different_questions_low(self):
        self.assertLess(similarity("dlaczego kfc", "jakie sa skladniki panierki"), 0.5)

    def test_near_duplicate_of_medium_length_text_is_detected(self):
        # difflib autojunk (default) dropped ~13% of such near-duplicates (alpha v1.2: 0.44 vs 0.97)
        rng = random.Random(7)
        vocab = "dlaczego kfc skrot panierka kurczak sos frytki restauracja historia nazwa marka pytanie".split()
        misses = 0
        for words in range(30, 200, 7):
            for _ in range(5):
                toks = [rng.choice(vocab) for _ in range(words)]
                alt = list(toks); alt[len(alt) // 2] = "zmiana"
                for method in ("tokens", "chars"):
                    if similarity(" ".join(toks), " ".join(alt), method=method) < 0.86:
                        misses += 1
        self.assertEqual(misses, 0)

    def test_template_wrapped_different_bodies_are_not_similar(self):
        head = " ".join(f"zasada{chr(97 + i % 26)}{chr(97 + i // 26)}" for i in range(200))
        tail = " ".join(f"podsumowanie{chr(97 + i % 26)}{chr(97 + i // 26)}" for i in range(200))
        rng = random.Random(3)
        mid_a = " ".join(rng.choice(["alfa", "beta", "gamma", "delta", "sigma", "omega"]) for _ in range(1000))
        mid_b = " ".join(rng.choice(["kot", "pies", "mysz", "ptak", "ryba", "lis"]) for _ in range(1000))
        a, b = f"{head} {mid_a} {tail}", f"{head} {mid_b} {tail}"
        # the sampled head+tail alone would be identical (ratio 1.0): only the bag-overlap guard separates them
        self.assertLess(similarity(a, b), 0.86)
        self.assertLess(similarity(a, b, method="chars"), 0.86)

    def test_adversarial_long_inputs_are_fast(self):
        a = " ".join(["a", "b"] * 3000)[:12000]
        b = " ".join(["b", "a"] * 3000)[:12000]
        c = "x" * 12000
        d = "x" * 11999 + "y"
        t = time.perf_counter()
        for method in ("tokens", "chars"):
            similarity(a, b, method=method); similarity(c, d, method=method); similarity(a, a[::-1], method=method)
        self.assertLess(time.perf_counter() - t, 2.0)


class TestStages(unittest.TestCase):
    def test_full_sequence_with_topic(self):
        g = KaiBoundary()
        self.assertEqual([ask(g, topic="kfc").action for _ in STAGES], STAGES)

    def test_full_sequence_without_topic(self):
        # alpha v1.1/v1.2 silently disabled loop detection when topic was omitted
        g = KaiBoundary()
        self.assertEqual([ask(g).action for _ in STAGES], STAGES)

    def test_stop_loop_persists(self):
        g = KaiBoundary()
        for _ in range(8):
            ask(g)
        for _ in range(3):
            self.assertEqual(ask(g).action, Action.STOP_LOOP)

    def test_repetition_count_matches_position(self):
        g = KaiBoundary()
        self.assertEqual([ask(g).repetition_count for _ in range(8)], list(range(1, 9)))

    def test_decide_is_pure(self):
        g = KaiBoundary()
        before = g.get_state()
        for _ in range(5):
            g.decide(Q)
        self.assertEqual(g.get_state(), before)


class TestDelivery(unittest.TestCase):
    def test_outage_after_one_answer_does_not_penalise(self):
        # alpha v1.0/v1.2: 1 answer + 8 failed deliveries => STOP_LOOP "I already answered"
        g = KaiBoundary()
        ask(g, delivered=True)
        self.assertEqual({ask(g, delivered=False).action for _ in range(10)}, {Action.ANSWER})
        self.assertEqual(g.get_state()["streak"], 1)

    def test_failed_guard_message_keeps_the_stage(self):
        g = KaiBoundary()
        for _ in range(4):
            ask(g)
        self.assertEqual(ask(g, delivered=False).action, Action.CLARIFY)    # user never saw it
        self.assertEqual(ask(g, delivered=True).action, Action.CLARIFY)     # same stage again
        self.assertEqual(ask(g, delivered=True).action, Action.CLARIFY)

    def test_unanswered_first_turns_do_not_count(self):
        g = KaiBoundary()
        for _ in range(10):
            ask(g, "KFC?", delivered=False, topic="kfc")
        self.assertEqual(g.decide("KFC?", topic="kfc").action, Action.ANSWER)
        self.assertEqual(g.get_state()["streak"], 0)

    def test_streak_never_advances_on_failed_delivery(self):
        rng = random.Random(11)
        g = KaiBoundary()
        for _ in range(200):
            before = g.get_state()["streak"]
            d = ask(g, delivered=(ok := rng.random() < 0.5))
            after = g.get_state()["streak"]
            self.assertTrue(after == before or ok)

    def test_legacy_record_with_old_readme_flow_reaches_stop(self):
        # old README: ANSWER/REPHRASE -> answered=True, everything else -> answered=False
        g = KaiBoundary()
        seen = []
        for _ in range(10):
            d = g.decide(Q, topic="kfc")
            seen.append(d.action)
            g.record(Q, answered=d.action in (Action.ANSWER, Action.REPHRASE), topic="kfc")
        self.assertIn(Action.STOP_LOOP, seen)

    def test_legacy_record_failed_model_calls_still_not_penalised(self):
        g = KaiBoundary()
        g.record(Q, answered=True)
        for _ in range(10):
            g.record(Q, answered=False)
        self.assertEqual(g.decide(Q).action, Action.ANSWER)


class TestChains(unittest.TestCase):
    def test_new_information_resets(self):
        g = KaiBoundary()
        for _ in range(4):
            ask(g, topic="kfc")
        self.assertEqual(ask(g, "A jaka jest historia zmiany nazwy?", topic="kfc", new_information=True).action, Action.ANSWER)
        self.assertEqual(g.get_state()["streak"], 1)

    def test_topic_switch_resets(self):
        g = KaiBoundary()
        for _ in range(6):
            ask(g, "KFC?", topic="kfc")
        self.assertEqual(ask(g, "KFC?", topic="physics").action, Action.ANSWER)

    def test_different_question_same_topic_not_a_loop(self):
        g = KaiBoundary()
        for _ in range(5):
            ask(g, "Dlaczego KFC to skrót?", topic="kfc")
        self.assertEqual(ask(g, "Jakie są składniki panierki?", topic="kfc").action, Action.ANSWER)

    def test_ten_different_numeric_questions_are_not_a_loop(self):
        g = KaiBoundary()
        acts = {ask(g, f"Ile kosztuje {i}0 sztuk?", topic="c").action for i in range(1, 11)}
        self.assertEqual(acts, {Action.ANSWER})        # alpha v1.2 chars: STOP_LOOP at the 8th

    def test_polarity_flip_is_not_a_repeat(self):
        g = KaiBoundary()
        for _ in range(4):
            ask(g, "Czy to jest bezpieczne dla dzieci?")
        self.assertEqual(ask(g, "Czy to nie jest bezpieczne dla dzieci?").action, Action.ANSWER)

    def test_slow_drift_does_not_chain_unrelated_questions(self):
        base = ("opisz dokladnie jak dziala silnik spalinowy w samochodzie osobowym oraz jakie ma zalety "
                "wady i zastosowania w praktyce codziennej").split()
        repl = "alfa beta gamma delta sigma omega kappa lambda theta zeta iota eta".split()
        chain, cur = [" ".join(base)], list(base)
        for k, w in enumerate(repl):
            cur[k] = w
            chain.append(" ".join(cur))                      # one token changes per step
        for method in ("tokens", "chars"):
            L = AntiBullshitLoop(policy=Policy(similarity_method=method))
            consecutive = [L.similarity(normalize(a), normalize(b)) for a, b in zip(chain, chain[1:])]
            self.assertTrue(all(c >= 0.86 for c in consecutive), (method, min(consecutive)))   # previous-turn rule WOULD chain
            self.assertLess(L.similarity(normalize(chain[0]), normalize(chain[-1])), 0.86)      # but first vs last differ
            g = KaiBoundary(policy=Policy(similarity_method=method))
            decisions = [ask(g, q, topic="x") for q in chain]
            self.assertNotIn(Action.STOP_LOOP, [d.action for d in decisions], method)
            self.assertLess(max(d.repetition_count for d in decisions), 8, method)

    def test_exempt_phrases_are_transparent(self):
        g = KaiBoundary()
        self.assertEqual({ask(g, "dalej").action for _ in range(10)}, {Action.ANSWER})   # 'dalej' x10
        ask(g, Q); ask(g, "Dalej."); d = ask(g, Q)
        self.assertEqual(d.repetition_count, 2)          # 'dalej' neither reset nor advanced the chain

    def test_short_legitimate_messages_are_answered(self):
        g = KaiBoundary()
        for t in ("y", "n", "7", "好", "Q?"):
            self.assertEqual(g.decide(t).action, Action.ANSWER, t)      # alpha v1.1/v1.2: CLARIFY

    def test_symbol_only_input_is_clarified_and_not_recorded(self):
        g = KaiBoundary()
        d = g.decide("?!?")
        self.assertEqual((d.action, d.reason, d.should_record), (Action.CLARIFY, "empty_or_too_short", False))
        self.assertFalse(g.commit(d, delivered=True))
        self.assertEqual(g.get_state()["history_len"], 0)

    def test_too_long_input(self):
        g = KaiBoundary()
        d = g.decide("a" * 12001)
        self.assertEqual((d.action, d.reason, d.should_record), (Action.CLARIFY, "input_too_long", False))
        self.assertFalse(g.commit(d, delivered=True))


class TestTicketContract(unittest.TestCase):
    def test_double_commit_rejected(self):
        g = KaiBoundary()
        d = g.decide(Q)
        g.commit(d, delivered=True)
        with self.assertRaises(StaleDecisionError):
            g.commit(d, delivered=True)

    def test_interleaved_decisions_rejected(self):
        g = KaiBoundary()
        d1, d2 = g.decide(Q), g.decide(Q)
        g.commit(d1, delivered=True)
        with self.assertRaises(StaleDecisionError):
            g.commit(d2, delivered=True)

    def test_foreign_decision_rejected(self):
        a, b = KaiBoundary(), KaiBoundary()
        with self.assertRaises(StaleDecisionError):
            b.commit(a.decide(Q), delivered=True)

    def test_reset_invalidates_outstanding_decisions(self):
        g = KaiBoundary()
        d = g.decide(Q)
        g.reset()
        with self.assertRaises(StaleDecisionError):
            g.commit(d, delivered=True)

    def test_refusal_has_no_ticket_and_does_not_touch_state(self):
        g = KaiBoundary()
        d = g.decide("abc", prohibited=True)
        self.assertEqual((d.action, d.should_record), (Action.REFUSE, False))
        self.assertFalse(g.commit(d, delivered=True))
        self.assertEqual(g.get_state()["history_len"], 0)

    def test_decision_repr_and_equality_do_not_expose_user_text(self):
        g = KaiBoundary()
        d = g.decide("sekretne dane osobowe 123")
        self.assertNotIn("sekretne", repr(d))
        self.assertEqual(KaiBoundary().decide("zupelnie inny tekst"), KaiBoundary().decide("inny tekst tez"))

    def test_concurrent_commits_of_one_decision_exactly_one_wins(self):
        g = KaiBoundary()
        d = g.decide(Q)
        results, barrier = [], threading.Barrier(8)

        def worker():
            barrier.wait()
            try:
                g.commit(d, delivered=True); results.append("ok")
            except StaleDecisionError:
                results.append("stale")

        ts = [threading.Thread(target=worker) for _ in range(8)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual((results.count("ok"), results.count("stale")), (1, 7))
        self.assertEqual(g.get_state()["streak"], 1)


class TestBoundary(unittest.TestCase):
    def test_profanity_is_not_prohibited(self):
        self.assertEqual(KaiBoundary().decide("Kurwa, wyjaśnij fizykę").action, Action.ANSWER)

    def test_trusted_flags(self):
        self.assertEqual(KaiBoundary().decide("abc", prohibited=True).action, Action.REFUSE)
        d = KaiBoundary().decide("abc", injection_detected=True)
        self.assertEqual((d.action, d.reason), (Action.REFUSE, "untrusted_instruction_attempt"))
        self.assertEqual(KaiBoundary().decide("abc", prohibited=True, injection_detected=True).reason,
                         "trusted_policy_prohibition")

    def test_flags_must_be_real_bools(self):
        g = KaiBoundary()
        for kw in ({"prohibited": "false"}, {"prohibited": 0}, {"injection_detected": "no"},
                   {"new_information": 1}):
            with self.assertRaises(TypeError, msg=str(kw)):
                g.decide("abc", **kw)

    def test_bad_types(self):
        g = KaiBoundary()
        for args, kw in [((None,), {}), ((b"x",), {}), (("a",), {"topic": 5})]:
            with self.assertRaises(TypeError):
                g.decide(*args, **kw)
        with self.assertRaises(TypeError):
            g.commit(g.decide("abc"), delivered="yes")

    def test_message_overrides_by_reason(self):
        g = KaiBoundary(policy=Policy(messages={"input_too_long": "Please shorten your message."}))
        self.assertEqual(g.decide("a" * 12001).message, "Please shorten your message.")
        self.assertEqual(g.decide(" ").message, DEFAULT_MESSAGES["empty_or_too_short"])

    def test_every_reason_has_a_default_message_key(self):
        g = KaiBoundary()
        for _ in range(9):
            ask(g)
        for d in (g.decide("abc", prohibited=True), g.decide("abc", injection_detected=True), g.decide(Q)):
            self.assertIn(d.reason, DEFAULT_MESSAGES)
            self.assertTrue(d.message)

    def test_readme_flow_executes(self):
        g = KaiBoundary()
        model_up = lambda i: i != 2                 # provider fails on the 3rd call
        log = []
        for i in range(9):
            d = g.decide(Q, topic="kfc")
            if d.action in (Action.ANSWER, Action.REPHRASE):
                delivered = model_up(i)
            else:
                delivered = True                    # guard message always shown
            g.commit(d, delivered=delivered)
            log.append(d.action)
        self.assertIn(Action.STOP_LOOP, log)


class TestHistoryAndState(unittest.TestCase):
    def test_history_bounded_and_content_free(self):
        g = KaiBoundary(policy=Policy(history_limit=5))
        for i in range(12):
            ask(g, f"pytanie numer {i} o czyms zupelnie innym", topic="t")
        h = g.history()
        self.assertEqual(len(h), 5)
        self.assertNotIn("pytanie", repr(h))

    def test_history_records_action_topic_and_delivery_outcome(self):
        g = KaiBoundary()
        ask(g, topic="t", delivered=True)
        ask(g, topic="t", delivered=False)
        h = g.history()
        self.assertEqual([(e.topic, e.action, e.delivered) for e in h],
                         [("t", "answer", True), ("t", "answer", False)])

    def test_reset(self):
        g = KaiBoundary()
        for _ in range(5):
            ask(g, topic="t")
        g.reset()
        s = g.get_state()
        self.assertEqual((s["streak"], s["answered_once"], s["last_topic"], s["has_anchor"], s["history_len"]),
                         (0, False, None, False, 0))

    def test_state_has_no_user_content_and_has_version(self):
        g = KaiBoundary()
        ask(g, "moj sekret 42")
        s = json.dumps(g.get_state())
        self.assertNotIn("sekret", s)
        self.assertEqual(g.get_state()["version"], __version__)


class TestPersistence(unittest.TestCase):
    def test_default_snapshot_contains_no_user_content(self):
        g = KaiBoundary()
        ask(g, "Moj PESEL to 44051401458, dlaczego KFC?", topic="x")
        blob = json.dumps(g.to_dict(), ensure_ascii=False)
        self.assertNotIn("PESEL", blob)
        self.assertNotIn("44051401458", blob)

    def test_default_snapshot_restores_a_fresh_chain_nobody_is_penalised(self):
        g = KaiBoundary()
        for _ in range(7):
            ask(g)
        g2 = KaiBoundary.from_dict(json.loads(json.dumps(g.to_dict())))
        self.assertEqual(g2.decide(Q).action, Action.ANSWER)

    def test_content_snapshot_roundtrip_is_decision_equivalent(self):
        rng = random.Random(21)
        qs = ["Dlaczego niebo jest niebieskie?", "Jak działa silnik spalinowy?", "Ile waży słoń afrykański?"]
        for _ in range(40):
            g = KaiBoundary()
            for _ in range(rng.randint(0, 12)):
                ask(g, rng.choice(qs), delivered=rng.random() < 0.8, topic=rng.choice([None, "a"]))
            g2 = KaiBoundary.from_dict(json.loads(json.dumps(g.to_dict(include_content=True))))
            for _ in range(15):
                q, dl, tp = rng.choice(qs), rng.random() < 0.8, rng.choice([None, "a"])
                self.assertEqual(ask(g, q, delivered=dl, topic=tp), ask(g2, q, delivered=dl, topic=tp))

    def test_from_dict_rejects_malformed_state(self):
        g = KaiBoundary(); ask(g)
        good = g.to_dict(include_content=True)

        def mutate(fn):
            d = json.loads(json.dumps(good)); fn(d); return d

        bad = {
            "schema": mutate(lambda d: d.update(schema="other")),
            "streak<0": mutate(lambda d: d["chain"].update(streak=-1)),
            "streak huge": mutate(lambda d: d["chain"].update(streak=10**12)),
            "streak bool": mutate(lambda d: d["chain"].update(streak=True)),
            "anchor not normalized": mutate(lambda d: d["chain"].update(anchor="Not Normalized!")),
            "anchor empty": mutate(lambda d: d["chain"].update(anchor="")),
            "chain extra key": mutate(lambda d: d["chain"].update(extra=1)),
            "history action": mutate(lambda d: d.update(history=[{"topic": None, "action": "dance", "delivered": True}])),
            "history keys": mutate(lambda d: d.update(history=[{"bogus": 1}])),
            "history too long": mutate(lambda d: d.update(history=[{"topic": None, "action": "answer", "delivered": True}] * 999)),
            "policy invalid": mutate(lambda d: d["policy"].update(stop_at=2)),
            "policy unknown key": mutate(lambda d: d["policy"].update(evil=1)),
        }
        for name, data in bad.items():
            with self.assertRaises(StateError, msg=name):
                KaiBoundary.from_dict(data)
        for junk in (None, [], "x", {}):
            with self.assertRaises(StateError):
                KaiBoundary.from_dict(junk)

    def test_explicit_policy_overrides_stored_policy(self):
        g = KaiBoundary(); ask(g)
        g2 = KaiBoundary.from_dict(g.to_dict(), policy=Policy(stop_at=12))
        self.assertEqual(g2.loop.policy.stop_at, 12)
        self.assertEqual(g.to_dict()["schema"], STATE_SCHEMA)


class TestModelBased(unittest.TestCase):
    """Compare the engine with a tiny reference model on random event streams."""
    QS = ["Dlaczego niebo jest niebieskie?", "Jak działa silnik spalinowy?",
          "Ile waży słoń afrykański?", "Kto napisał Pana Tadeusza?"]
    VARIANTS = lambda q, r: [q, q.upper(), q.lower().replace("?", "??"), "  " + q + "  "][r % 4]

    @staticmethod
    def reference(events):
        anchor = topic = None
        streak, out = 0, []
        for key, tp, ni, dl in events:
            in_chain = (not ni) and anchor is not None and tp == topic and key == anchor
            count = streak + 1 if in_chain else 1
            out.append((count, "stop" if count >= 8 else "clarify" if count >= 5 else "rephrase" if count >= 3 else "answer"))
            if in_chain:
                streak += 1 if dl else 0
            else:
                anchor, topic, streak = key, tp, 1 if dl else 0
        return out

    def test_random_streams(self):
        rng = random.Random(2024)
        for _ in range(150):
            events = []
            for _ in range(rng.randint(1, 60)):
                key = rng.choice(self.QS) if rng.random() < 0.35 else events[-1][0] if events and rng.random() < 0.8 else rng.choice(self.QS)
                events.append((key, rng.choice([None, "a", "b"]), rng.random() < 0.05, rng.random() < 0.85))
            g = KaiBoundary()
            got = []
            for key, tp, ni, dl in events:
                d = g.decide(TestModelBased.VARIANTS(key, rng.randint(0, 3)), topic=tp, new_information=ni)
                got.append((d.repetition_count, {Action.STOP_LOOP: "stop", Action.CLARIFY: "clarify",
                                                 Action.REPHRASE: "rephrase", Action.ANSWER: "answer"}[d.action]))
                g.commit(d, delivered=dl)
            self.assertEqual(got, self.reference(events))

    def test_determinism(self):
        runs = []
        for _ in range(2):
            g, rng = KaiBoundary(), random.Random(9)
            runs.append([ask(g, rng.choice(self.QS), delivered=rng.random() < 0.7).action for _ in range(80)])
        self.assertEqual(runs[0], runs[1])


class TestFuzz(unittest.TestCase):
    def test_random_unicode_never_crashes(self):
        rng = random.Random(77)
        alphabets = ["abc xyz ?!.", "żółć ĄĘŚ ", "好是的 ", "\x00\ud800\udfff\u200b\u202e", "😀🙂 ", "0123456789 ", "\n\t\r "]
        g = KaiBoundary(policy=Policy(similarity_method="chars"))
        for _ in range(500):
            text = "".join(rng.choice(rng.choice(alphabets)) for _ in range(rng.randint(0, 80)))
            d = g.decide(text, topic=rng.choice([None, "a"]), new_information=rng.random() < 0.1)
            g.commit(d, delivered=rng.random() < 0.7)
        json.dumps(g.to_dict(include_content=True), ensure_ascii=False)

    def test_max_length_inputs(self):
        g = KaiBoundary()
        big = ("slowo " * 2000)[:12000]
        for _ in range(3):
            ask(g, big)
        ask(g, big[:-1] + "x")


if __name__ == "__main__":
    unittest.main(verbosity=2)
