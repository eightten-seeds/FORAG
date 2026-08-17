import re

from bs4 import BeautifulSoup, Tag

from .models import CleanDocument, RawDocument


_NOISE_RE = re.compile(
    r"cookie|onetrust|consent|privacy|newsletter|subscribe|country|region|search|"
    r"(?:site|global)[-_ ]?nav|breadcrumb",
    re.IGNORECASE,
)
_BLOCK_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote", "dt", "dd"}


def _is_noise(node: Tag) -> bool:
    if not node.attrs:
        return False
    attrs = " ".join(str(node.get(attr, "")) for attr in ("id", "class", "aria-label", "role"))
    return bool(_NOISE_RE.search(attrs))


def _main_container(soup: BeautifulSoup) -> Tag:
    for selector in ("main", "article", '[role="main"]'):
        node = soup.select_one(selector)
        if node:
            return node
    return soup.body or soup


def _text_lines(container: Tag) -> list[str]:
    lines: list[str] = []
    candidates = list(container.find_all(_BLOCK_TAGS))
    for node in container.find_all(["div", "section"]):
        attrs = " ".join(str(node.get(attr, "")) for attr in ("id", "class", "role")) if node.attrs else ""
        parent_attrs = " ".join(str(parent.get("class", "")) for parent in node.parents if isinstance(parent, Tag) and parent.attrs)
        if re.search(r"warning|caution|important|note|faq|accordion", attrs + " " + parent_attrs, re.I):
            candidates.append(node)
    for node in candidates:
        if any(parent.name in {"script", "style", "noscript", "svg"} for parent in node.parents):
            continue
        text = " ".join(node.stripped_strings)
        if not text:
            continue
        if node.name.startswith("h"):
            parent_text = " ".join(str(parent.get("class", "")) for parent in node.parents if isinstance(parent, Tag) and parent.attrs)
            if any(parent.name == "a" for parent in node.parents) or re.search(r"product|recommend|related|newsletter", parent_text, re.I):
                continue
        if node.name in {"div", "section"} and any(line.removeprefix("- ") == text for line in lines):
            continue
        if node.name.startswith("h"):
            level = int(node.name[1])
            line = f"{'#' * level} {text}"
        elif node.name == "li":
            line = f"- {text}"
        else:
            line = text
        if not lines or line != lines[-1]:
            lines.append(line)
    return lines


def _is_heading(line: str) -> bool:
    return bool(re.match(r"^#{1,6}\s+\S", line))


def clean_document(document: RawDocument) -> CleanDocument:
    if not re.search(r"<\s*(html|body|main|article|h[1-6]|p|ul|ol)\b", document.raw_content, re.I):
        lines = []
        for raw_line in document.raw_content.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            line = re.sub(r"[ \t]+", " ", raw_line).strip()
            if line and not re.match(r"^(?:cookie(?: policy| notice)?|privacy policy|terms of use)$", line, re.I):
                if not lines or line != lines[-1]:
                    lines.append(line)
        return CleanDocument(
            document_id=document.document_id, source_id=document.source_id,
            source_title=document.source_title, source_url=document.source_url,
            brand=document.brand, language=document.language,
            sections=[line for line in lines if _is_heading(line) or re.match(r"^(?:warning|caution|note)\s*:", line, re.I)],
            clean_content="\n".join(lines), content_hash=document.content_hash,
        )
    soup = BeautifulSoup(document.raw_content, "html.parser")
    for node in soup.find_all(["script", "style", "noscript", "svg", "header", "nav", "footer", "aside", "form"]):
        node.decompose()
    for node in list(soup.find_all(True)):
        if _is_noise(node):
            node.decompose()

    lines = _text_lines(_main_container(soup))
    clean_content = "\n".join(lines)
    return CleanDocument(
        document_id=document.document_id,
        source_id=document.source_id,
        source_title=document.source_title,
        source_url=document.source_url,
        brand=document.brand,
        language=document.language,
        sections=[line for line in lines if _is_heading(line)],
        clean_content=clean_content,
        content_hash=document.content_hash,
    )


def clean_documents(documents: list[RawDocument]) -> list[CleanDocument]:
    return [clean_document(document) for document in documents]
