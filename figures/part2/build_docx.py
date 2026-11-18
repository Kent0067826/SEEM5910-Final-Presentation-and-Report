"""把 第二部分_网络建模与主要优化.md 导出成排好中文字体的 Word。

运行（仓库根目录）：python3 figures/part2/build_docx.py
需要 pandoc 和 python-docx。
"""
import subprocess
import tempfile
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "第二部分_网络建模与主要优化.md"
OUT = ROOT / "第二部分_网络建模与主要优化.docx"

CN_BODY = "宋体"
CN_HEAD = "黑体"
LATIN = "Times New Roman"


def set_fonts(style, latin, east, size=None, bold=None, color=None):
    style.font.name = latin
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for k in ("w:ascii", "w:hAnsi", "w:cs"):
        rfonts.set(qn(k), latin)
    rfonts.set(qn("w:eastAsia"), east)
    for k in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rfonts.get(qn(k)) is not None:
            del rfonts.attrib[qn(k)]
    if size:
        style.font.size = Pt(size)
    if bold is not None:
        style.font.bold = bold
    if color is not None:
        style.font.color.rgb = color


def make_reference(path):
    subprocess.run(["pandoc", "-o", str(path), "--print-default-data-file", "reference.docx"],
                          check=True)
    doc = Document(path)
    by_name = {s.name.lower(): s for s in doc.styles}

    class _St:
        def __iter__(self):
            return iter(by_name.values())

        def __getitem__(self, k):
            return by_name[k.lower()]

    st = _St()
    for name in ("Normal", "Body Text", "First Paragraph", "Compact", "Block Text", "Image Caption",
                 "Table Caption", "Caption"):
        if name .lower() in by_name:
            set_fonts(st[name], LATIN, CN_BODY, 11 if name != "Compact" else 10)
    for name, size in (("Title", 20), ("Heading 1", 18), ("Heading 2", 15), ("Heading 3", 13)):
        if name .lower() in by_name:
            set_fonts(st[name], LATIN, CN_HEAD, size, True, RGBColor(0x1F, 0x29, 0x33))
    for name in ("Body Text", "First Paragraph"):
        if name .lower() in by_name:
            pf = st[name].paragraph_format
            pf.line_spacing = 1.4
            pf.space_after = Pt(6)
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    for side in ("left_margin", "right_margin"):
        setattr(sec, side, Cm(2.2))
    sec.top_margin = sec.bottom_margin = Cm(2.2)
    doc.save(path)


def border_tables(doc):
    for table in doc.tables:
        tblPr = table._tbl.tblPr
        borders = OxmlElement("w:tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            el = OxmlElement(f"w:{edge}")
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), "4")
            el.set(qn("w:color"), "A8B3C1")
            borders.append(el)
        tblPr.append(borders)
        for i, row in enumerate(table.rows):
            for cell in row.cells:
                if i == 0:
                    shd = OxmlElement("w:shd")
                    shd.set(qn("w:val"), "clear")
                    shd.set(qn("w:fill"), "EEF2F7")
                    cell._tc.get_or_add_tcPr().append(shd)
                for p in cell.paragraphs:
                    for r in p.runs:
                        r.font.size = Pt(9.5)
                        if i == 0:
                            r.font.bold = True


def fit_images(doc, max_cm=16.5):
    for shape in doc.inline_shapes:
        if shape.width > Cm(max_cm):
            ratio = Cm(max_cm) / shape.width
            shape.width = Cm(max_cm)
            shape.height = int(shape.height * ratio)
    for p in doc.paragraphs:
        if p._p.xpath(".//pic:pic"):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER


def main():
    with tempfile.TemporaryDirectory() as td:
        ref = Path(td) / "ref.docx"
        make_reference(ref)
        subprocess.run(["pandoc", "-f", "markdown-implicit_figures", str(SRC), "-o", str(OUT), "--resource-path", str(ROOT),
                        "--reference-doc", str(ref)], check=True, cwd=ROOT)
    doc = Document(OUT)
    border_tables(doc)
    fit_images(doc)
    doc.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
