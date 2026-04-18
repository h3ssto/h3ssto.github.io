#!/usr/bin/env python3
"""
Build index.html from template.html + contents.toml + BibTeX files.

Requirements:
    pip install -r requirements.txt

Usage:
    python build.py
"""

import tomllib

import re
import urllib.request
import markdown
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.customization import convert_to_unicode
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

_bib_writer = BibTexWriter()
_bib_writer.indent = "  "


# -- Author matching -----------------------------------------------------------


def _norm(s: str) -> str:
    """Normalise a BibTeX string for fuzzy author comparison.
    Handles ß, {\\ss}, \\ss{}, \\ss in any order before stripping braces.
    """
    s = s.replace(r"{\ss}", "ss").replace(r"\ss{}", "ss").replace(r"\ss", "ss")
    s = s.replace("ß", "ss")
    return s.lower().replace("{", "").replace("}", "")


def is_target(author: str, last: str, first: str) -> bool:
    a = _norm(author)
    return _norm(last) in a and first.lower() in a


# -- Author parsing & formatting -----------------------------------------------


def split_authors(raw: str) -> list[str]:
    """Split a BibTeX author field on ' and ', normalise to 'First Last'."""
    authors = []
    for part in re.split(r"\s+and\s+", raw, flags=re.IGNORECASE):
        part = part.strip()
        if "," in part:
            last, first = part.split(",", 1)
            part = f"{first.strip()} {last.strip()}"
        authors.append(part)
    return authors


def format_authors(authors: list[str], last: str, first: str) -> str:
    """Return an HTML author string with the target author in <strong>."""
    MAX_SHOWN = 6
    parts = []
    for a in authors[:MAX_SHOWN]:
        if is_target(a, last, first):
            parts.append(f"<strong>{a}</strong>")
        else:
            parts.append(f'<span class="pub-coauthor">{a}</span>')
    if len(authors) > MAX_SHOWN:
        parts.append('<span class="pub-coauthor">et al.</span>')
    return ", ".join(parts)


# -- Venue abbreviation expansion ----------------------------------------------

_ABBREVS = [
    (r"\bProc\.\s+of\b", "Proceedings of"),
    (r"\bProc\.", "Proceedings"),
    (r"\bConf\.", "Conference"),
    (r"\bInt(?:'?l)?\.?", "International"),
    (r"\bSymp\.", "Symposium"),
    (r"\bAnn\.", "Annual"),
    (r"\bWkshp\.", "Workshop"),
    (r"\bWksp\.", "Workshop"),
    (r"\bJ\.", "Journal"),
    (r"\bTrans\.", "Transactions"),
    (r"\bEng\.", "Engineering"),
    (r"\bSci\.", "Science"),
    (r"\bComput\.", "Computing"),
    (r"\bVol\.", "Volume"),
    (r"\bNo\.", "Number"),
]
_ABBREV_RE = [(re.compile(pat), repl) for pat, repl in _ABBREVS]


def expand_venue(venue: str) -> str:
    venue = venue.replace("\\ ", " ")  # LaTeX non-breaking space
    for pattern, replacement in _ABBREV_RE:
        venue = pattern.sub(replacement, venue)
    return venue


# -- BibTeX loading & filtering ------------------------------------------------


def load_bib(*paths: Path) -> bibtexparser.bibdatabase.BibDatabase:
    """Concatenate bib files and parse (resolves @String entries)."""
    parser = BibTexParser(common_strings=True)
    parser.customization = convert_to_unicode
    combined = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in paths)
    return bibtexparser.loads(combined, parser=parser)


def entry_bib_text(entry: dict) -> str:
    """Serialise a single BibTeX entry as a plain string."""
    db = bibtexparser.bibdatabase.BibDatabase()
    db.entries = [entry]
    return bibtexparser.dumps(db, _bib_writer).strip()


def entry_venue(entry: dict) -> str:
    return (
        entry.get("journal")
        or entry.get("booktitle")
        or entry.get("series")
        or entry.get("school")
        or entry.get("institution")
        or ""
    )


def group_by_year(pubs: list[dict], limit: int = 5) -> list[dict]:
    """
    Group a year-sorted publication list into per-year buckets.
    Publications beyond *limit* (counting from most recent) are flagged overflow=True.
    Returns [{'year': int, 'pubs': [...]}, ...] descending by year.
    """
    from collections import defaultdict

    by_year: dict[int, list] = defaultdict(list)
    for pub in pubs:
        by_year[pub["year"]].append(pub)

    count = 0
    groups = []
    for year in sorted(by_year.keys(), reverse=True):
        year_pubs = []
        for pub in by_year[year]:
            pub = dict(pub, overflow=(count >= limit))
            count += 1
            year_pubs.append(pub)
        groups.append({"year": year, "pubs": year_pubs})
    return groups


_ACM_BADGES = {
    "available": "https://www.acm.org/binaries/content/gallery/acm/publications/replication-badges/artifacts_available_dl.jpg",
    "functional": "https://www.acm.org/binaries/content/gallery/acm/publications/replication-badges/artifacts_evaluated_functional_dl.jpg",
    "reusable": "https://www.acm.org/binaries/content/gallery/acm/publications/replication-badges/artifacts_evaluated_reusable_dl.jpg",
}


def resolve_badge(badge: str) -> str:
    """Return a badge image URL from a shorthand key or pass through a full URL."""
    return _ACM_BADGES.get(badge, badge)


def parse_publications(
    db: bibtexparser.bibdatabase.BibDatabase,
    last: str,
    first: str,
    starred: set[str] | None = None,
    artifacts: dict[str, dict] | None = None,
) -> dict:
    """
    Return grouped publication data:
        first_author        - list of year-groups (see group_by_year)
        coauthor            - list of year-groups
        first_author_total  - int
        coauthor_total      - int
    """
    starred = starred or set()
    artifacts = artifacts or {}

    first_author: list[dict] = []
    coauthor: list[dict] = []

    for entry in db.entries:
        if entry.get("ENTRYTYPE", "").lower() in ("mastersthesis", "masterthesis"):
            continue

        raw = entry.get("author", "").strip()
        if not raw:
            continue

        authors = split_authors(raw)

        if not any(is_target(a, last, first) for a in authors):
            continue

        pub = {
            "title": entry.get("title", "").strip("{}"),
            "authors_html": format_authors(authors, last, first),
            "venue": expand_venue(entry_venue(entry).strip("{}")),
            "year": int(entry.get("year", 0) or 0),
            "doi": entry.get("doi", "").strip() or None,
            "entry_type": entry.get("ENTRYTYPE", "misc"),
            "bib_key": entry.get("ID", "ref"),
            "bib_text": entry_bib_text(entry),
            "starred": entry.get("ID", "") in starred,
            "artifact_url": artifacts.get(entry.get("ID", ""), {}).get("url"),
            "artifact_badge_urls": [
                resolve_badge(b.strip())
                for b in artifacts.get(entry.get("ID", ""), {})
                .get("badge", "")
                .split(",")
                if b.strip()
            ],
            "award_url": (
                ("awards/" + artifacts[entry.get("ID", "")]["award"])
                if artifacts.get(entry.get("ID", ""), {}).get("award")
                else None
            ),
        }

        if is_target(authors[0], last, first):
            first_author.append(pub)
        else:
            coauthor.append(pub)

    first_author.sort(key=lambda p: p["year"], reverse=True)
    coauthor.sort(key=lambda p: p["year"], reverse=True)

    return {
        "first_author": group_by_year(first_author),
        "coauthor": group_by_year(coauthor),
        "first_author_total": len(first_author),
        "coauthor_total": len(coauthor),
    }


# -- Thesis parsing -----------------------------------------------------------


def format_thesis_author(raw: str) -> str:
    """'Last, First' → 'First Last'."""
    raw = raw.strip()
    if "," in raw:
        last, first = raw.split(",", 1)
        return f"{first.strip()} {last.strip()}"
    return raw


def parse_theses(
    db: bibtexparser.bibdatabase.BibDatabase,
    starred: set[str] | None = None,
    awards: dict[str, list[str]] | None = None,
) -> list[dict]:
    """
    Return theses supervised by TH, grouped by year (desc), sorted by author
    name within each year.  'nottobepublished' suppresses the DOI link.
    """
    starred = starred or set()
    awards  = awards  or {}
    theses: list[dict] = []

    for entry in db.entries:
        tags = entry.get("typo3tags", "")
        if "SupervisorTH" not in tags:
            continue

        published = entry.get("comments", "").strip().lower() != "nottobepublished"
        doi = entry.get("doi", "").strip() if published else None

        raw_author = entry.get("author", "").strip()
        author = format_thesis_author(raw_author.split(" and ")[0])

        label = entry.get("type", "Thesis").strip() or "Thesis"

        key = entry.get("ID", "")
        theses.append({
            "author":  author,
            "title":   entry.get("title", "").strip("{}"),
            "type":    label,
            "year":    int(entry.get("year", 0) or 0),
            "doi":     doi or None,
            "starred": key in starred,
            "awards":  awards.get(key, []),
        })

    # Group by year descending, within year sort by author name
    from collections import defaultdict
    by_year: dict[int, list] = defaultdict(list)
    for t in theses:
        by_year[t["year"]].append(t)

    groups = []
    for year in sorted(by_year.keys(), reverse=True):
        groups.append({
            "year":    year,
            "theses":  sorted(by_year[year], key=lambda t: t["author"].split()[-1]),
        })
    return groups


# -- Markdown filter -----------------------------------------------------------


def md_filter(text: str) -> str:
    return markdown.markdown(text.strip(), extensions=["smarty"])


def md_inline_filter(text: str) -> str:
    """Render Markdown inline — strips the surrounding <p>...</p> wrapper."""
    html = markdown.markdown(text.strip(), extensions=["smarty"])
    return re.sub(r"^\s*<p>(.*)</p>\s*$", r"\1", html, flags=re.DOTALL)


# -- BibTeX fetch -------------------------------------------------------------

_BIB_BASE = (
    "https://raw.githubusercontent.com/TUBS-ISF/BibTags/refs/heads/main/literature/"
)
_BIB_FILES = ["MYabrv.bib", "literature.bib"]


def fetch_bib_files(root: Path) -> None:
    for name in _BIB_FILES:
        url = _BIB_BASE + name
        dest = root / name
        print(f"Fetching {url} ...")
        urllib.request.urlretrieve(url, dest)


# -- Main ----------------------------------------------------------------------


def main() -> None:
    root = Path(__file__).parent
    fetch_bib_files(root)

    with open(root / "contents.toml", "rb") as f:
        data = tomllib.load(f)

    # Derive author identity from the card section
    author_name: str = data["card"]["name"]  # e.g. "Tobias Heß"
    name_parts = author_name.split()
    author_first = name_parts[0]  # "Tobias"
    author_last = name_parts[-1]  # "Heß"

    db = load_bib(root / "MYabrv.bib", root / "literature.bib")

    pub_cfg = data.get("publications", {})
    starred = set(pub_cfg.get("starred", []))
    artifacts = {a["key"]: a for a in pub_cfg.get("artifacts", [])}
    data["publications"] = parse_publications(
        db, last=author_last, first=author_first, starred=starred, artifacts=artifacts,
    )
    theses_cfg     = data.get("theses", {})
    theses_starred = set(theses_cfg.get("starred", []))
    theses_awards  = {a["key"]: a["items"] for a in theses_cfg.get("awards", [])}
    data["theses"] = parse_theses(db, starred=theses_starred, awards=theses_awards)

    env = Environment(
        loader=FileSystemLoader(root),
        autoescape=False,
        keep_trailing_newline=True,
    )
    env.filters["md"] = md_filter
    env.filters["md_inline"] = md_inline_filter

    html = env.get_template("template.html").render(**data)
    out = root / "index.html"
    out.write_text(html, encoding="utf-8")

    fa = data["publications"]["first_author_total"]
    co = data["publications"]["coauthor_total"]
    print(f"Built {out}  ({fa} first-author, {co} co-author publications)")


if __name__ == "__main__":
    main()
