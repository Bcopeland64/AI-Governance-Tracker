from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


CATEGORIES = (
    "Technical Standards & Certification Bodies",
    "Intergovernmental & Policy Frameworks",
    "Frontier Safety & Technical Consensus",
    "Dedicated Policy & Regulation Trackers",
    "Legal Intelligence & Law Firm Hubs",
)


@dataclass(frozen=True)
class Source:
    name: str
    category: str
    url: str
    domain: str
    search_terms: str


SOURCES = (
    Source(
        "ISO/IEC JTC 1/SC 42 (Artificial Intelligence)",
        CATEGORIES[0],
        "https://www.iso.org/committee/6794475.html",
        "iso.org",
        '"artificial intelligence" standards',
    ),
    Source(
        "IEEE Standards Association (Global AI Ethics Initiative)",
        CATEGORIES[0],
        "https://standards.ieee.org/",
        "standards.ieee.org",
        '"AI ethics" standards initiative',
    ),
    Source(
        "OECD.AI Policy Observatory",
        CATEGORIES[1],
        "https://oecd.ai/en/",
        "oecd.ai",
        "AI policy regulation",
    ),
    Source(
        "Council of Europe (Framework Convention on AI)",
        CATEGORIES[1],
        "https://www.coe.int/en/web/artificial-intelligence/the-framework-convention-on-artificial-intelligence",
        "coe.int",
        "artificial intelligence framework convention",
    ),
    Source(
        "UNESCO Global AI Ethics Observatory",
        CATEGORIES[1],
        "https://www.unesco.org/en/artificial-intelligence/recommendation-ethics",
        "unesco.org",
        "AI ethics observatory",
    ),
    Source(
        "Global Partnership on AI (GPAI)",
        CATEGORIES[1],
        "https://gpai.ai/",
        "gpai.ai",
        "global partnership AI policy",
    ),
    Source(
        "International Network of AI Safety Institutes (AISIs)",
        CATEGORIES[2],
        "https://www.gov.uk/government/publications/international-network-of-ai-safety-institutes",
        "gov.uk",
        "international network AI safety institutes",
    ),
    Source(
        "IAPP AI Governance Dashboard & Tracker",
        CATEGORIES[3],
        "https://iapp.org/",
        "iapp.org",
        "AI governance regulation tracker",
    ),
    Source(
        "Stanford HAI AI Index & Policy Tracker",
        CATEGORIES[3],
        "https://hai.stanford.edu/ai-index",
        "hai.stanford.edu",
        "AI index policy regulation",
    ),
    Source(
        "TechieRay Global AI Regulation Tracker",
        CATEGORIES[3],
        "https://techieray.com/",
        "techieray.com",
        "global AI regulation tracker",
    ),
    Source(
        "AI Governance Directory / Tracker",
        CATEGORIES[3],
        "https://aigovernance.com/",
        "aigovernance.com",
        "AI governance tracker",
    ),
    Source(
        "White & Case (AI Watch: Global Regulatory Tracker)",
        CATEGORIES[4],
        "https://www.whitecase.com/insight-our-thinking/ai-watch-global-regulatory-tracker",
        "whitecase.com",
        "AI Watch global regulatory tracker",
    ),
    Source(
        "Covington & Burling (Covington AI Pulse)",
        CATEGORIES[4],
        "https://www.covington.com/insights/ai-pulse",
        "covington.com",
        "AI Pulse artificial intelligence regulation",
    ),
    Source(
        "Gibson Dunn AI Practice Hub",
        CATEGORIES[4],
        "https://www.gibsondunn.com/practice/artificial-intelligence/",
        "gibsondunn.com",
        "artificial intelligence regulation",
    ),
    Source(
        "Latham & Watkins AI Practice Hub",
        CATEGORIES[4],
        "https://www.lw.com/en/practices/artificial-intelligence",
        "lw.com",
        "artificial intelligence regulation",
    ),
)

SOURCES_BY_NAME = {source.name: source for source in SOURCES}


def build_feed_url(source: Source) -> str:
    query = quote_plus(f"site:{source.domain} {source.search_terms}")
    return (
        "https://news.google.com/rss/search"
        f"?q={query}&hl=en-US&gl=US&ceid=US:en"
    )


def _child_text(element: ET.Element, name: str) -> str:
    local_name = name.rsplit("}", 1)[-1]
    child = element.find(f"{{*}}{local_name}")
    return child.text.strip() if child is not None and child.text else ""


def _atom_link(element: ET.Element) -> str:
    for link in element.findall("{*}link"):
        href = link.attrib.get("href", "")
        if href and link.attrib.get("rel", "alternate") == "alternate":
            return href
    return ""


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_feed(xml_content: bytes, source_name: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_content)
    entries = root.findall(".//item") or root.findall(".//{*}entry")
    updates = []
    for entry in entries:
        title = _child_text(entry, "title")
        link = _child_text(entry, "link") or _atom_link(entry)
        if not title or not link or not link.startswith(("https://", "http://")):
            continue
        updates.append(
            {
                "title": title,
                "url": link,
                "published": _parse_date(
                    _child_text(entry, "pubDate")
                    or _child_text(entry, "published")
                    or _child_text(entry, "updated")
                ),
                "source": source_name,
            }
        )
    return updates


def fetch_source_updates(
    source: Source, timeout: int = 12
) -> tuple[list[dict[str, Any]], str | None]:
    request = Request(
        build_feed_url(source),
        headers={"User-Agent": "GlobalAIGovernanceTracker/1.0"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            updates = parse_feed(response.read(), source.name)
    except HTTPError as error:
        return [], f"HTTP {error.code}: {error.reason}"
    except (URLError, TimeoutError, OSError) as error:
        return [], f"Connection failed: {error}"
    except ET.ParseError as error:
        return [], f"Feed could not be parsed: {error}"
    return updates, None


def fetch_updates(
    source_names: tuple[str, ...],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    updates: list[dict[str, Any]] = []
    failures: dict[str, str] = {}
    sources = [SOURCES_BY_NAME[name] for name in source_names]
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(fetch_source_updates, source): source
            for source in sources
        }
        for future in as_completed(futures):
            source = futures[future]
            source_updates, error = future.result()
            updates.extend(source_updates)
            if error:
                failures[source.name] = error
    updates.sort(
        key=lambda update: update["published"] or datetime.min.replace(
            tzinfo=timezone.utc
        ),
        reverse=True,
    )
    return updates, failures
