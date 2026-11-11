"""Text normalisation helpers shared by normalize, link, layers and the tests."""

from __future__ import annotations

import hashlib
import re
import unicodedata

DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>]+", re.IGNORECASE)
_TRAILING_PUNCT = ".,;:)]}"
_DOI_PREFIXES = ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/", "doi:")


def norm_text(s: str | None) -> str:
    """Lowercase ASCII letters/digits separated by single spaces; accents stripped."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def tokens(s: str | None) -> list[str]:
    return norm_text(s).split()


def norm_doi(doi: str | None) -> str | None:
    """Lowercase bare DOI (no resolver prefix, no trailing punctuation); None if not a DOI."""
    if not doi:
        return None
    d = str(doi).strip().lower()
    for prefix in _DOI_PREFIXES:
        if d.startswith(prefix):
            d = d[len(prefix):]
    d = d.strip().rstrip(_TRAILING_PUNCT)
    return d if DOI_RE.fullmatch(d) else None


def extract_doi(text: str | None) -> str | None:
    m = DOI_RE.search(text or "")
    return norm_doi(m.group(0)) if m else None


def pub_id(title: str | None, year: int | None, citation: str | None) -> str:
    """Stable id when the source has none: sha1(normalised title | year | normalised citation)."""
    key = f"{norm_text(title)}|{'' if year is None else int(year)}|{norm_text(citation)}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def text_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


_IT_WORDS = frozenset("""il lo la i gli le un uno una di del dello della dei degli delle da dal dalla dai nel nella nei nelle
sul sulla sui sulle per con tra fra che non sono come anche più dei tra alla alle allo agli al ai ed della e è o ma
se si sua suo loro questo questa questi queste tra sulla studio analisi tra verso nella nell""".split())
_EN_WORDS = frozenset("""the of and in on for with from to by an is are was were be as at or its their this that these those
between into through using use via under over towards toward within without not can has have which who when where
study analysis approach based new""".split())
_IT_ACCENTS = re.compile(r"[àèìòù]")


def detect_lang(text: str | None) -> str | None:
    """'it' | 'en' | None (undecided). Stopword vote on normalised tokens; needs a clear margin.
    Deliberately dependency-free; short titles without function words stay undecided (the caller falls back to the
    language declared in the open data)."""
    if not text:
        return None
    toks = norm_text(text).split()
    it = sum(t in _IT_WORDS for t in toks) + (2 if _IT_ACCENTS.search(str(text).lower()) else 0)
    en = sum(t in _EN_WORDS for t in toks)
    if it >= en + 1 and it > 0:
        return "it"
    if en >= it + 1 and en > 0:
        return "en"
    return None


_DECLARED_LANG = {"inglese": "en", "italiano": "it"}


def text_lang(title: str | None, abstract: str | None, declared: str | None) -> str:
    """Language group of the text that is embedded: 'it' | 'en' | 'other'. Detected on title + abstract; when undecided,
    the language declared in the open data (only if it names exactly one of italiano/inglese); else 'other'."""
    s = lambda x: x if isinstance(x, str) else ""  # noqa: E731  (pandas NA / None -> "")
    d = detect_lang(f"{s(title)}. {s(abstract)}")
    if d:
        return d
    return _DECLARED_LANG.get(s(declared).strip().lower(), "other")
