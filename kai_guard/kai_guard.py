#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KaiGuard v1.3.0: AntiBullshitLoop + KaiBoundary.

Deterministic, local, provider-independent conversation-loop and boundary policy.
No emotion/intent diagnosis, no API calls, no telemetry. Python >= 3.10, stdlib only.

CONTRACT (the part earlier versions got wrong)
    decision = guard.decide(text, topic=...)         # pure: does not change state
    reply    = <model output, or decision.message>   # what the USER will actually see
    delivered = <True only if that reply reached the user>
    guard.commit(decision, delivered=delivered)      # exactly once per decision

    `delivered` means "the user received a response" (a substantive answer OR a guard
    message such as CLARIFY / STOP_LOOP). A failed delivery (outage, timeout) never
    counts as a repetition, so users are not punished for provider failures.
    Refusals and invalid inputs carry no ticket; commit() on them is a no-op.
"""
from __future__ import annotations

import difflib
import re
import threading
import unicodedata
from types import MappingProxyType
from collections import Counter, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Mapping, Optional

__version__ = "1.3.0"
STATE_SCHEMA = "kai_guard.state.v1"

__all__ = [
    "Action", "Decision", "HistoryEntry", "Policy", "AntiBullshitLoop", "KaiBoundary",
    "StaleDecisionError", "StateError", "normalize", "similarity",
    "DEFAULT_EXEMPT_PHRASES", "DEFAULT_POLARITY_TOKENS", "DEFAULT_MESSAGES",
    "STATE_SCHEMA", "__version__",
]


class Action(str, Enum):
    ANSWER = "answer"
    REPHRASE = "rephrase"
    CLARIFY = "clarify"
    STOP_LOOP = "stop_loop"
    REFUSE = "refuse"


class StaleDecisionError(RuntimeError):
    """commit() was called with a decision that is no longer current (double commit,
    interleaved turns, or a decision from another guard)."""


class StateError(ValueError):
    """A persisted state snapshot is malformed or inconsistent."""


# --------------------------------------------------------------------------- defaults

# Short continuation/confirmation messages are not "the same question asked again".
DEFAULT_EXEMPT_PHRASES = frozenset({
    "ok", "okay", "tak", "nie", "y", "n", "yes", "no", "dalej", "kontynuuj", "więcej",
    "next", "continue", "more", "dzięki", "thanks",
})

# Tokens whose presence/absence flips the meaning of a question. If two texts differ in
# how many of these they contain, they are NOT treated as repeats of each other.
DEFAULT_POLARITY_TOKENS = frozenset({
    "nie", "not", "no", "never", "nigdy", "bez", "without", "brak", "non",
})

DEFAULT_MESSAGES: Mapping[str, str] = MappingProxyType({
    "normal_or_new_information": "",
    "exempt_phrase": "",
    "input_too_long": "Podziel wiadomość na krótsze części.",
    "empty_or_too_short": "Napisz, o co chcesz zapytać.",
    "repetition_rephrase": "Spróbuję wyjaśnić to inaczej.",
    "repetition_without_progress": "Co dokładnie pozostaje niejasne? Mogę wyjaśnić inny aspekt lub podać przykład.",
    "repeated_answered_question": (
        "Odpowiedziałem już na to pytanie kilka razy. Nie będę powtarzał tej samej odpowiedzi. "
        "Jeśli masz nowe informacje lub chcesz zapytać o coś innego — śmiało."
    ),
    "trusted_policy_prohibition": "Nie wykonam tego żądania.",
    "untrusted_instruction_attempt": "Nie wykonam instrukcji, która próbuje zmienić zasady lub zadanie systemu.",
})


# --------------------------------------------------------------------------- validation

def _req_str(name: str, v: Any) -> str:
    if not isinstance(v, str):
        raise TypeError(f"{name} must be str, got {type(v).__name__}")
    return v


def _req_bool(name: str, v: Any) -> bool:
    if not isinstance(v, bool):          # "false" / 0 / None must not silently pass as flags
        raise TypeError(f"{name} must be bool, got {type(v).__name__}")
    return v


def _req_topic(v: Any) -> Optional[str]:
    if v is not None and not isinstance(v, str):
        raise TypeError(f"topic must be str or None, got {type(v).__name__}")
    return v


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


# --------------------------------------------------------------------------- text & similarity

def normalize(text: str) -> str:
    """NFKC + casefold, keep letters/digits/whitespace, collapse whitespace."""
    text = unicodedata.normalize("NFKC", text).casefold()
    text = "".join(c if (c.isalnum() or c.isspace()) else " " for c in text)
    return " ".join(text.split())


_DIGIT_RUNS = re.compile(r"\d+")
_MAX_TOKENS = 400        # SequenceMatcher is only run on <= this many items per side
_MAX_CHARS = 1200


def _bag_overlap(a: Counter, b: Counter, denom: int) -> float:
    return sum((a & b).values()) / denom if denom else 0.0


def similarity(a: str, b: str, *, method: str = "tokens",
               polarity_tokens: frozenset = DEFAULT_POLARITY_TOKENS) -> float:
    """Symmetric similarity of two NORMALIZED strings in [0, 1]; deterministic.

    Hard guards (similarity 0.0, whatever the surface resemblance):
      * different digit sequences ("10 sztuk" vs "20 sztuk");
      * different number of polarity tokens ("jest bezpieczne" vs "nie jest bezpieczne").
    method="tokens": order-aware ratio over word lists (conservative; default).
    method="chars":  order-aware ratio over characters (looser; for scripts without spaces).
    Long inputs are compared on head+tail samples AND a full bag-of-items overlap; the
    lower of the two wins, so cost stays bounded and template-wrapped texts do not match.
    """
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    if _DIGIT_RUNS.findall(a) != _DIGIT_RUNS.findall(b):
        return 0.0
    ta, tb = a.split(), b.split()
    if polarity_tokens and (sum(t in polarity_tokens for t in ta) != sum(t in polarity_tokens for t in tb)):
        return 0.0
    x, y, cap = (ta, tb, _MAX_TOKENS) if method == "tokens" else (a, b, _MAX_CHARS)
    truncated = len(x) > cap or len(y) > cap
    bag_ratio = 1.0
    if truncated:
        if method == "tokens":
            bag_ratio = _bag_overlap(Counter(ta), Counter(tb), max(len(ta), len(tb)))
        else:
            bag_ratio = _bag_overlap(Counter(zip(a, a[1:])), Counter(zip(b, b[1:])), max(len(a), len(b)) - 1)
        h = cap // 2
        x, y = x[:h] + x[-h:], y[:h] + y[-h:]
    x, y = sorted((x, y))                       # canonical order => symmetric by construction
    ratio = difflib.SequenceMatcher(None, x, y, autojunk=False).ratio()
    return min(ratio, bag_ratio)


# --------------------------------------------------------------------------- data classes

@dataclass(frozen=True)
class Policy:
    history_limit: int = 60
    rephrase_at: int = 3
    clarify_at: int = 5
    stop_at: int = 8
    similarity_threshold: float = 0.86
    similarity_method: str = "tokens"            # "tokens" | "chars"
    max_input_chars: int = 12000
    min_normalized_chars: int = 1
    exempt_phrases: frozenset = DEFAULT_EXEMPT_PHRASES
    polarity_tokens: frozenset = DEFAULT_POLARITY_TOKENS
    messages: Optional[Mapping[str, str]] = None   # override texts by `reason`

    def __post_init__(self):
        for n in ("history_limit", "rephrase_at", "clarify_at", "stop_at",
                  "max_input_chars", "min_normalized_chars"):
            if not _is_int(getattr(self, n)):
                raise ValueError(f"{n} must be an int")
        if not (1 < self.rephrase_at < self.clarify_at < self.stop_at):
            raise ValueError("thresholds must increase and rephrase_at > 1")
        if isinstance(self.similarity_threshold, bool) or not isinstance(self.similarity_threshold, (int, float)) \
                or not (0.0 < self.similarity_threshold <= 1.0):
            raise ValueError("invalid similarity threshold")
        if self.similarity_method not in ("tokens", "chars"):
            raise ValueError("similarity_method must be 'tokens' or 'chars'")
        if self.history_limit < 1 or self.max_input_chars < 1 or self.min_normalized_chars < 1:
            raise ValueError("invalid limits")
        for n in ("exempt_phrases", "polarity_tokens"):
            v = getattr(self, n)
            if not isinstance(v, frozenset) or not all(isinstance(s, str) for s in v):
                raise ValueError(f"{n} must be a frozenset of str")
        if self.messages is not None:
            bad = set(self.messages) - set(DEFAULT_MESSAGES)
            if bad or not all(isinstance(v, str) for v in self.messages.values()):
                raise ValueError(f"messages: unknown reasons {sorted(bad)} or non-str values")

    def message_for(self, reason: str) -> str:
        if self.messages and reason in self.messages:
            return self.messages[reason]
        return DEFAULT_MESSAGES[reason]

    def to_dict(self) -> dict:
        return {
            "history_limit": self.history_limit, "rephrase_at": self.rephrase_at,
            "clarify_at": self.clarify_at, "stop_at": self.stop_at,
            "similarity_threshold": self.similarity_threshold, "similarity_method": self.similarity_method,
            "max_input_chars": self.max_input_chars, "min_normalized_chars": self.min_normalized_chars,
            "exempt_phrases": sorted(self.exempt_phrases), "polarity_tokens": sorted(self.polarity_tokens),
            "messages": dict(self.messages) if self.messages else None,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Policy":
        known = set(cls.__dataclass_fields__)
        if not isinstance(data, Mapping) or set(data) - known:
            raise StateError("policy: unexpected or missing structure")
        kw = dict(data)
        for n in ("exempt_phrases", "polarity_tokens"):
            if n in kw:
                if not isinstance(kw[n], (list, tuple)):
                    raise StateError(f"policy.{n} must be a list")
                kw[n] = frozenset(kw[n])
        try:
            return cls(**kw)
        except (ValueError, TypeError) as exc:
            raise StateError(f"policy invalid: {exc}") from exc


@dataclass(frozen=True)
class _Ticket:
    owner: object
    epoch: int
    norm: str
    topic: Optional[str]
    chain: bool
    exempt: bool


@dataclass(frozen=True)
class Decision:
    action: Action
    reason: str
    repetition_count: int = 0
    message: str = ""
    signals: tuple[str, ...] = ()
    ticket: Optional[_Ticket] = field(default=None, repr=False, compare=False)

    @property
    def should_record(self) -> bool:
        """True iff this decision must be passed to commit()."""
        return self.ticket is not None


@dataclass(frozen=True)
class HistoryEntry:
    """Audit trail without user content: only topic, action and delivery outcome."""
    topic: Optional[str]
    action: str
    delivered: bool


# --------------------------------------------------------------------------- loop

class AntiBullshitLoop:
    """Counts how many times the same question was asked after a delivered response.

    * A turn is "in chain" if it has the same topic as the chain's ANCHOR (the first
      question of the chain) and is similar to that anchor. Comparing with the anchor,
      not the previous turn, stops slow drift from chaining unrelated questions.
    * topic=None is one ordinary default topic: callers that never pass topics still get
      loop detection.
    * Only delivered responses advance the streak; failed deliveries never do.
    * A new topic, a dissimilar question or `new_information=True` starts a new chain.
    * Exempt phrases ("dalej", "ok", ...) are transparent: they never change the chain.
    """

    def __init__(self, policy: Optional[Policy] = None):
        self.policy = policy or Policy()
        self._lock = threading.RLock()
        self._token = object()
        self._exempt = frozenset(normalize(p) for p in self.policy.exempt_phrases)
        self._history: Deque[HistoryEntry] = deque(maxlen=self.policy.history_limit)
        self._streak = 0
        self._anchor: Optional[str] = None
        self._topic: Optional[str] = None
        self._epoch = 0

    # compat helpers
    normalize = staticmethod(normalize)

    def similarity(self, a: str, b: str) -> float:
        return similarity(a, b, method=self.policy.similarity_method,
                          polarity_tokens=self.policy.polarity_tokens)

    @property
    def streak(self) -> int:
        return self._streak

    @property
    def last_topic(self) -> Optional[str]:
        return self._topic

    def history(self) -> tuple:
        with self._lock:
            return tuple(self._history)

    # ---- decide (pure) ---------------------------------------------------------
    def _plain(self, action: Action, reason: str, **kw) -> Decision:
        return Decision(action, reason, message=self.policy.message_for(reason), **kw)

    def assess(self, text: str, *, topic: Optional[str] = None, new_information: bool = False) -> Decision:
        _req_str("text", text); _req_topic(topic); _req_bool("new_information", new_information)
        p = self.policy
        if len(text) > p.max_input_chars:
            return self._plain(Action.CLARIFY, "input_too_long")
        norm = normalize(text)
        if len(norm) < p.min_normalized_chars:
            return self._plain(Action.CLARIFY, "empty_or_too_short")
        with self._lock:
            if norm in self._exempt:
                t = _Ticket(self._token, self._epoch, norm, topic, chain=False, exempt=True)
                return self._plain(Action.ANSWER, "exempt_phrase", ticket=t)
            in_chain = (not new_information and self._anchor is not None and topic == self._topic
                        and self.similarity(norm, self._anchor) >= p.similarity_threshold)
            count = self._streak + 1 if in_chain else 1
            t = _Ticket(self._token, self._epoch, norm, topic, chain=in_chain, exempt=False)
        if count >= p.stop_at:
            return self._plain(Action.STOP_LOOP, "repeated_answered_question", repetition_count=count,
                               signals=("high_repetition", "no_new_information"), ticket=t)
        if count >= p.clarify_at:
            return self._plain(Action.CLARIFY, "repetition_without_progress", repetition_count=count,
                               signals=("repetition",), ticket=t)
        if count >= p.rephrase_at:
            return self._plain(Action.REPHRASE, "repetition_rephrase", repetition_count=count,
                               signals=("repetition",), ticket=t)
        return self._plain(Action.ANSWER, "normal_or_new_information", repetition_count=count, ticket=t)

    # ---- commit (the only mutator besides reset/from_dict) -----------------------
    def commit(self, decision: Decision, *, delivered: bool) -> bool:
        """Apply the outcome of one decision. Returns False for tickets-less decisions."""
        _req_bool("delivered", delivered)
        t = decision.ticket
        if t is None:
            return False
        with self._lock:
            if t.owner is not self._token:
                raise StaleDecisionError("decision belongs to another guard")
            if t.epoch != self._epoch:
                raise StaleDecisionError("decision is stale: already committed or another turn intervened")
            if t.exempt:
                pass
            elif t.chain:
                if delivered:
                    self._streak += 1
            else:
                self._anchor, self._topic = t.norm, t.topic
                self._streak = 1 if delivered else 0
            self._history.append(HistoryEntry(t.topic, decision.action.value, delivered))
            self._epoch += 1
        return True

    def record(self, text: str, *, answered: bool, topic: Optional[str] = None,
               new_information: bool = False) -> bool:
        """DEPRECATED compatibility wrapper (decide+commit in one call).

        `answered` is read as "delivered". For backward compatibility, guard-originated
        messages (CLARIFY / STOP_LOOP) count as delivered even if the caller passes False,
        because old docs told callers to record them as answered=False.
        """
        _req_bool("answered", answered)
        d = self.assess(text, topic=topic, new_information=new_information)
        return self.commit(d, delivered=answered or d.action in (Action.CLARIFY, Action.STOP_LOOP))

    # ---- state -------------------------------------------------------------------
    def reset(self) -> None:
        with self._lock:
            self._history.clear()
            self._streak = 0
            self._anchor = None
            self._topic = None
            self._epoch += 1                       # invalidates outstanding decisions

    def get_state(self) -> dict:
        with self._lock:
            return {"version": __version__, "streak": self._streak, "answered_once": self._streak > 0,
                    "last_topic": self._topic, "has_anchor": self._anchor is not None,
                    "history_len": len(self._history), "epoch": self._epoch,
                    "policy": self.policy.to_dict()}

    def to_dict(self, *, include_content: bool = False) -> dict:
        """JSON-serialisable snapshot.

        By default NO user content is written: the chain is dropped and, after restore, the
        loop simply starts a fresh chain (fails safe: nobody is penalised).
        include_content=True also stores the normalized anchor text and streak; treat that
        snapshot as sensitive and integrity-protect it (e.g. HMAC) if it crosses a trust boundary.
        """
        with self._lock:
            chain = None
            if include_content and self._anchor is not None:
                chain = {"anchor": self._anchor, "streak": self._streak, "topic": self._topic}
            return {"schema": STATE_SCHEMA, "version": __version__, "policy": self.policy.to_dict(),
                    "chain": chain,
                    "history": [{"topic": h.topic, "action": h.action, "delivered": h.delivered}
                                for h in self._history]}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], *, policy: Optional[Policy] = None) -> "AntiBullshitLoop":
        """Validate and restore. Raises StateError on anything malformed."""
        if not isinstance(data, Mapping) or data.get("schema") != STATE_SCHEMA:
            raise StateError("unknown or missing state schema")
        loop = cls(policy or Policy.from_dict(data.get("policy") or {}))
        p = loop.policy
        chain = data.get("chain")
        if chain is not None:
            if not isinstance(chain, Mapping) or set(chain) != {"anchor", "streak", "topic"}:
                raise StateError("chain: bad structure")
            a, s, tp = chain["anchor"], chain["streak"], chain["topic"]
            if not isinstance(a, str) or not a or len(a) > p.max_input_chars or a != normalize(a):
                raise StateError("chain.anchor must be a non-empty normalized string")
            if not _is_int(s) or not (0 <= s <= 1_000_000):
                raise StateError("chain.streak out of range")
            if tp is not None and not isinstance(tp, str):
                raise StateError("chain.topic must be str or None")
            loop._anchor, loop._streak, loop._topic = a, s, tp
        hist = data.get("history", [])
        if not isinstance(hist, list) or len(hist) > p.history_limit:
            raise StateError("history: bad structure or too long")
        valid_actions = {a.value for a in Action}
        for h in hist:
            if (not isinstance(h, Mapping) or set(h) != {"topic", "action", "delivered"}
                    or h["action"] not in valid_actions or not isinstance(h["delivered"], bool)
                    or (h["topic"] is not None and not isinstance(h["topic"], str))):
                raise StateError("history entry malformed")
            loop._history.append(HistoryEntry(h["topic"], h["action"], h["delivered"]))
        return loop


# --------------------------------------------------------------------------- boundary

class KaiBoundary:
    """Boundary policy, not a safety classifier.

    `prohibited` and `injection_detected` come from a TRUSTED caller (application policy or
    an external detector); they are never inferred from user text, and must be real bools.
    """

    def __init__(self, loop: Optional[AntiBullshitLoop] = None, policy: Optional[Policy] = None):
        self.loop = loop or AntiBullshitLoop(policy)

    def decide(self, text: str, *, topic: Optional[str] = None, new_information: bool = False,
               prohibited: bool = False, injection_detected: bool = False) -> Decision:
        _req_bool("prohibited", prohibited); _req_bool("injection_detected", injection_detected)
        _req_str("text", text); _req_topic(topic); _req_bool("new_information", new_information)
        pol = self.loop.policy
        if prohibited:
            return Decision(Action.REFUSE, "trusted_policy_prohibition",
                            message=pol.message_for("trusted_policy_prohibition"))
        if injection_detected:
            return Decision(Action.REFUSE, "untrusted_instruction_attempt",
                            message=pol.message_for("untrusted_instruction_attempt"))
        return self.loop.assess(text, topic=topic, new_information=new_information)

    def commit(self, decision: Decision, *, delivered: bool) -> bool:
        return self.loop.commit(decision, delivered=delivered)

    def record(self, text: str, *, answered: bool, topic: Optional[str] = None,
               new_information: bool = False) -> bool:
        """DEPRECATED: use commit(). Does not know about refusals; see AntiBullshitLoop.record."""
        return self.loop.record(text, answered=answered, topic=topic, new_information=new_information)

    def reset(self) -> None:
        self.loop.reset()

    def get_state(self) -> dict:
        return self.loop.get_state()

    def history(self) -> tuple:
        return self.loop.history()

    def to_dict(self, *, include_content: bool = False) -> dict:
        return self.loop.to_dict(include_content=include_content)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], *, policy: Optional[Policy] = None) -> "KaiBoundary":
        return cls(loop=AntiBullshitLoop.from_dict(data, policy=policy))
