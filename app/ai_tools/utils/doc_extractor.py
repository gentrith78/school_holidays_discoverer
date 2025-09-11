# docx_extractor.py
from __future__ import annotations
from typing import List
from docx import Document

def _clean(s: str) -> str:
    return " ".join((s or "").split())

def docx_to_text(path: str) -> str:
    """
    Extract readable TEXT from a .docx file using only python-docx.
    - Preserves paragraph order
    - Converts tables to simple TSV-like blocks
    - Flattens whitespace
    """
    doc = Document(path)
    chunks: List[str] = []

    # Paragraphs
    for p in doc.paragraphs:
        txt = p.text.strip()
        if txt:
            chunks.append(_clean(txt))

    # Tables (append after paragraphs; if you prefer inline order, iterate doc.element.body)
    for tbl in doc.tables:
        for row in tbl.rows:
            row_vals = [cell.text.replace("\n", " ").strip() for cell in row.cells]
            if any(v for v in row_vals):
                chunks.append("\t".join(_clean(v) for v in row_vals))

    return "\n".join(chunks).strip()


def docx_to_markdown(path: str) -> str:
    """
    Extract a LIGHT Markdown from a .docx:
    - Headings (Heading 1..6) -> # .. ######
    - Bulleted/numbered lists -> -, 1.
    - Tables -> Markdown tables
    - Falls back to plain paragraphs
    """
    doc = Document(path)
    lines: List[str] = []

    # Helper: detect heading level by style name
    def heading_marks(style_name: str) -> str | None:
        if not style_name:
            return None
        s = style_name.lower()
        for lvl in range(1, 7):
            if f"heading {lvl}" in s:
                return "#" * lvl
        return None

    # Helper: detect list (numbered/bulleted)
    def is_list_paragraph(p) -> str | None:
        # python-docx doesn't expose list info directly, use numPr presence
        pPr = getattr(p._p, "pPr", None)
        if pPr is not None and getattr(pPr, "numPr", None) is not None:
            # crude detection: numbered vs bullet not easily accessible; render as '-'
            return "-"
        # fallback on style name hints
        name = (p.style.name or "").lower() if p.style else ""
        if "list" in name or "bullet" in name or "number" in name:
            return "-"
        return None

    # Walk document in body order (paragraphs and tables interleaved)
    for block in doc.element.body.iterchildren():
        tag = block.tag.rsplit("}", 1)[-1]
        if tag == "p":
            p = block
            # rebuild a docx paragraph proxy to re-use python-docx helpers
            # (cheap: locate matching paragraph by text index)
            # Instead, do a light extraction from runs:
            text = "".join([node.text or "" for node in p.iter() if node.tag.rsplit("}",1)[-1] == "t"]).strip()
            if not text:
                continue
            # Find the style via mapping: search in doc.paragraphs sequentially (safe & simple)
            # (We’re OK with a simpler approach here.)
            # Use a heuristic heading detection by text style name from the closest paragraph with same text
            style_name = None
            for para in doc.paragraphs:
                if para.text.strip() == text:
                    style_name = para.style.name if para.style else None
                    break

            # Heading?
            marks = heading_marks(style_name or "")
            if marks:
                lines.append(f"{marks} {_clean(text)}")
                continue

            # List?
            bullet = None
            if style_name:
                dummy = type("Dummy", (), {})()
                dummy._p = p  # hack to reuse is_list_paragraph
                dummy.style = type("S", (), {"name": style_name})()
                bullet = is_list_paragraph(dummy)
            else:
                dummy = type("Dummy", (), {})()
                dummy._p = p
                dummy.style = type("S", (), {"name": ""})()
                bullet = is_list_paragraph(dummy)

            if bullet:
                lines.append(f"{bullet} {_clean(text)}")
            else:
                lines.append(_clean(text))

        elif tag == "tbl":
            # Convert table to Markdown
            tbl = None
            # match the python-docx table by text content
            table_texts = []
            for row in block.iterchildren():
                if row.tag.rsplit("}", 1)[-1] != "tr":
                    continue
                row_vals = []
                for cell in row.iterchildren():
                    if cell.tag.rsplit("}", 1)[-1] != "tc":
                        continue
                    cell_text = " ".join([t.text or "" for t in cell.iter() if t.tag.rsplit("}",1)[-1] == "t"]).strip()
                    row_vals.append(_clean(cell_text))
                table_texts.append(row_vals)

            # Render as Markdown
            if table_texts:
                # header (use first row as header if it looks header-ish; otherwise generic)
                header = table_texts[0]
                if not any(header):
                    header = [f"Col {i+1}" for i in range(len(header))]
                lines.append("| " + " | ".join(header) + " |")
                lines.append("| " + " | ".join(["---"] * len(header)) + " |")
                for row in table_texts[1:]:
                    lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines).strip()