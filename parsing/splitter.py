from __future__ import annotations
import io
import os
import re


class DocumentSplitter:
    BOUNDARY_PATTERNS = [
        re.compile(r"page\s*1\s*of\s*\d+", re.IGNORECASE),
        re.compile(r"^(invoice|receipt|contract|agreement|certificate|letter|memo|report)\b", re.IGNORECASE | re.MULTILINE),
        re.compile(r"^\s*date\s*:\s*\d", re.IGNORECASE | re.MULTILINE),
    ]

    def split(self, file_bytes: bytes, filename: str) -> list[dict]:
        ext = os.path.splitext(filename)[1].lower()
        if ext != ".pdf":
            return [{"bytes": file_bytes, "filename": filename, "page_range": "all"}]

        try:
            import fitz
        except ImportError:
            try:
                import pymupdf as fitz
            except ImportError:
                return [{"bytes": file_bytes, "filename": filename, "page_range": "all"}]

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        if doc.page_count <= 1:
            doc.close()
            return [{"bytes": file_bytes, "filename": filename, "page_range": "1"}]

        boundaries = [0]
        for page_idx in range(1, doc.page_count):
            page = doc[page_idx]
            text = page.get_text("text")[:500]
            if self._is_boundary(text):
                boundaries.append(page_idx)

        if len(boundaries) <= 1:
            doc.close()
            return [{"bytes": file_bytes, "filename": filename, "page_range": f"1-{doc.page_count}"}]

        sub_docs = []
        for i, start in enumerate(boundaries):
            end = boundaries[i + 1] if i + 1 < len(boundaries) else doc.page_count
            sub = fitz.open()
            sub.insert_pdf(doc, from_page=start, to_page=end - 1)
            buf = io.BytesIO()
            sub.save(buf)
            sub.close()

            base = os.path.splitext(filename)[0]
            sub_docs.append({
                "bytes": buf.getvalue(),
                "filename": f"{base}_part{i + 1}.pdf",
                "page_range": f"{start + 1}-{end}",
            })

        doc.close()
        return sub_docs

    def _is_boundary(self, text: str) -> bool:
        for pattern in self.BOUNDARY_PATTERNS:
            if pattern.search(text):
                return True
        return False
