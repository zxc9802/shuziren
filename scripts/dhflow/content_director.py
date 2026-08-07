"""Deterministic script segmentation and priority-based semantic classification."""


import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Literal


Role = Literal[
    "hook",
    "question",
    "explanation",
    "warning",
    "contrast",
    "steps",
    "conclusion",
]
RuleMatcher = Callable[[str, bool, bool], bool]

ROLES = {
    "hook",
    "question",
    "explanation",
    "warning",
    "contrast",
    "steps",
    "conclusion",
}


class RuleKind(str, Enum):
    QUESTION_PUNCTUATION = "question_punctuation"
    WARNING_PHRASE = "warning_phrase"
    CONTRAST_PHRASE = "contrast_phrase"
    STEP_PHRASE = "step_phrase"
    FINAL_IMPERATIVE = "final_imperative"
    CONCLUSION_PHRASE = "conclusion_phrase"
    FIRST_BEAT_HOOK = "first_beat_hook"


@dataclass(frozen=True)
class SemanticRule:
    kind: RuleKind
    role: Role
    matches: RuleMatcher


_CHINESE_WARNING_PHRASES = (
    "注意",
    "警惕",
    "风险",
    "不要",
    "不能",
    "避免",
    "当心",
    "小心",
    "切勿",
    "踩坑",
    "踩的坑",
    "别急",
    "别再",
    "别忘",
)
_ENGLISH_WARNING_PHRASES = ("warning", "risk", "avoid", "beware")
_CHINESE_CONTRAST_PHRASES = ("但是", "不过", "然而", "反而", "而是")
_ENGLISH_CONTRAST_PHRASES = ("but", "however", "instead")
_CHINESE_STEP_PHRASES = (
    "第一",
    "第二",
    "第三",
    "第四",
    "首先",
    "其次",
    "最后",
    "第1",
    "第2",
    "第3",
)
_ENGLISH_STEP_PHRASES = (
    "step one",
    "step two",
    "step three",
    "first",
    "second",
    "third",
    "finally",
)
_CHINESE_CONCLUSION_PHRASES = ("现在就", "今天就", "立刻", "马上", "因此", "所以")
_CHINESE_HOOK_PHRASES = (
    "你是否",
    "你有没有",
    "想知道",
    "你想",
    "如何",
    "为什么",
    "怎么",
    "让你",
    "教你",
    "分享",
)
_FINAL_CHINESE_IMPERATIVE_PATTERNS = (
    r"^(?:请)?执行(?:这一步|步骤|任务)(?=\s|[。！？!?；;…]|$)",
    r"^完成(?:表格|任务|这一步)(?=\s|[。！？!?；;…]|$)",
    r"^使用(?:这个|该|此)(?:方法|方案|工具)(?=\s|[。！？!?；;…]|$)",
    r"^选择(?:一个|一)(?:场景|方案|选项)(?=\s|[。！？!?；;…]|$)",
    r"^点击(?:下方|这个|该)?(?:链接|按钮)(?=\s|[。！？!?；;…]|$)",
    r"^关注(?:我们|账号|公众号)(?=\s|[。！？!?；;…]|$)",
    r"^尝试(?:这个|该|此)(?:方案|方法)(?=\s|[。！？!?；;…]|$)",
    r"^记住(?:这一点|这点|这个步骤)(?=\s|[。！？!?；;…]|$)",
    r"^先找到(?:一个|一)(?:高频)?场景(?=\s|[。！？!?；;…]|$)",
)
_FINAL_ENGLISH_IMPERATIVE_PATTERNS = (
    r"^use\s+this\s+method\b",
    r"^try\s+this\s+approach\b",
    r"^choose\s+one\s+scenario\b",
    r"^click\s+the\s+link\b",
    r"^follow\s+these\s+steps\b",
    r"^remember\s+this\s+point\b",
    r"^apply\s+this\s+method\b",
    r"^complete\s+the\s+table\b",
    r"^execute\s+this\s+step\b",
    r"^start\s+with\s+one\s+scenario\b",
    r"^subscribe\s+now\b",
)
_TERMINATORS = frozenset("。！？!?；;.…")
_CLOSING_QUOTES_AND_BRACKETS = frozenset("”’）】》〉」』)]}")
_SEMANTIC_PUNCTUATION = "。！？!?；;.…，、：:\"'“”‘’()（）[]【】{}《》〈〉「」『』"


def analyze_script(text: str) -> list[dict]:
    """Split a non-empty script into lossless, semantically labelled beats."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text must be a non-empty string")

    clauses = _split_clauses(text)
    last_content_index = max(index for index, clause in enumerate(clauses) if clause.strip())
    beats = []
    for index, clause in enumerate(clauses, start=1):
        is_first = index == 1
        is_last_content = index - 1 == last_content_index
        role, keywords = _classify_clause(clause.strip(), is_first, is_last_content)
        beats.append(
            {
                "id": f"beat-{index:03d}",
                "text": clause,
                "role": role,
                "importance": _importance_for(role),
                "keywords": keywords,
            }
        )
    return beats


def _split_clauses(text: str) -> list[str]:
    clauses = []
    start = 0
    index = 0
    while index < len(text):
        if _is_clause_terminator(text, index):
            end = index + 1
            while end < len(text) and _is_clause_terminator(text, end):
                end += 1
            while end < len(text) and text[end] in _CLOSING_QUOTES_AND_BRACKETS:
                end += 1
            while end < len(text) and text[end].isspace():
                end += 1
            candidate = text[start:end]
            if _has_semantic_content(candidate):
                clauses.append(candidate)
                start = end
            index = end
            continue
        index += 1
    if start < len(text):
        tail = text[start:]
        if _has_semantic_content(tail):
            clauses.append(tail)
        elif clauses:
            clauses[-1] += tail
        else:
            raise ValueError("text must include semantic content")
    return clauses


def _is_clause_terminator(text: str, index: int) -> bool:
    if text[index] not in _TERMINATORS:
        return False
    return not (
        text[index] == "."
        and 0 < index < len(text) - 1
        and text[index - 1].isdigit()
        and text[index + 1].isdigit()
    )


def _has_semantic_content(text: str) -> bool:
    return bool(text.strip().strip(_SEMANTIC_PUNCTUATION))


def _classify_clause(text: str, is_first: bool, is_last_content: bool) -> tuple[Role, list[str]]:
    for rule in _SEMANTIC_RULES:
        if rule.matches(text, is_first, is_last_content):
            return rule.role, [rule.kind.value]
    return "explanation", []


def _matches_question(text: str, _is_first: bool, _is_last_content: bool) -> bool:
    return "?" in text or "？" in text


def _matches_warning(text: str, _is_first: bool, _is_last_content: bool) -> bool:
    return _matches_chinese_phrase(text, _CHINESE_WARNING_PHRASES) or _matches_english_phrase(
        text, _ENGLISH_WARNING_PHRASES
    )


def _matches_contrast(text: str, _is_first: bool, _is_last_content: bool) -> bool:
    return _matches_chinese_phrase(text, _CHINESE_CONTRAST_PHRASES) or _matches_english_phrase(
        text, _ENGLISH_CONTRAST_PHRASES
    )


def _matches_steps(text: str, _is_first: bool, _is_last_content: bool) -> bool:
    return _matches_chinese_phrase(text, _CHINESE_STEP_PHRASES) or _matches_english_phrase(
        text, _ENGLISH_STEP_PHRASES
    )


def _matches_final_imperative(text: str, _is_first: bool, is_last_content: bool) -> bool:
    if not is_last_content:
        return False
    return _matches_pattern(text, _FINAL_CHINESE_IMPERATIVE_PATTERNS) or _matches_pattern(
        text, _FINAL_ENGLISH_IMPERATIVE_PATTERNS, re.IGNORECASE
    )


def _matches_conclusion_phrase(text: str, _is_first: bool, is_last_content: bool) -> bool:
    return is_last_content and _matches_chinese_phrase(text, _CHINESE_CONCLUSION_PHRASES)


def _matches_first_hook(text: str, is_first: bool, _is_last_content: bool) -> bool:
    return is_first and _matches_chinese_phrase(text, _CHINESE_HOOK_PHRASES)


def _matches_chinese_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _matches_english_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    return any(
        re.search(rf"(?<![A-Za-z]){re.escape(phrase)}(?![A-Za-z])", text, re.IGNORECASE)
        is not None
        for phrase in phrases
    )


def _matches_pattern(text: str, patterns: tuple[str, ...], flags: int = 0) -> bool:
    return any(re.search(pattern, text, flags) is not None for pattern in patterns)


_SEMANTIC_RULES = (
    SemanticRule(RuleKind.QUESTION_PUNCTUATION, "question", _matches_question),
    SemanticRule(RuleKind.WARNING_PHRASE, "warning", _matches_warning),
    SemanticRule(RuleKind.CONTRAST_PHRASE, "contrast", _matches_contrast),
    SemanticRule(RuleKind.STEP_PHRASE, "steps", _matches_steps),
    SemanticRule(RuleKind.FINAL_IMPERATIVE, "conclusion", _matches_final_imperative),
    SemanticRule(RuleKind.CONCLUSION_PHRASE, "conclusion", _matches_conclusion_phrase),
    SemanticRule(RuleKind.FIRST_BEAT_HOOK, "hook", _matches_first_hook),
)


def _importance_for(role: Role) -> str:
    if role in {"hook", "warning", "conclusion"}:
        return "high"
    if role in {"question", "contrast", "steps"}:
        return "medium"
    return "normal"
