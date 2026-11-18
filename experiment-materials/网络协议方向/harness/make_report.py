"""把累积的报告源文件（Markdown 子集）转成 Word。每轮出一个新文件，旧的不覆盖。

用法：python make_report.py ..\\报告源\\网络协议方向.md ..\\报告\\网络协议方向_第1轮.docx

支持的写法：
  # / ## / ###        标题
  空行分段；**粗体**；`代码`
  | a | b |            表格（第二行 |---| 是表头分隔）
  ![图注](相对路径.png)  图片（相对报告源文件），图注放在图下；行尾加 {宽=12} 可把图宽改成 12 厘米（默认 15.5）
  > 怎么读：...          灰底说明框（用来写“怎么读这个公式/这个机制”）
  - 列表项
"""
import re, sys
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

FONT = '微软雅黑'


def set_font(run, size=None, bold=None, color=None, mono=False):
    f = 'Consolas' if mono else FONT
    run.font.name = f
    run._element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
    if size: run.font.size = Pt(size)
    if bold is not None: run.bold = bold
    if color: run.font.color.rgb = RGBColor.from_string(color)


def add_inline(p, text, size=10.5):
    for part in re.split(r'(\*\*[^*]+\*\*|`[^`]+`)', text):
        if not part: continue
        if part.startswith('**'):
            set_font(p.add_run(part[2:-2]), size, bold=True)
        elif part.startswith('`'):
            set_font(p.add_run(part[1:-1]), size, mono=True, color='9C2A00')
        else:
            set_font(p.add_run(part), size)


def shade(p, fill='EEF2F7'):
    pPr = p._p.get_or_add_pPr(); s = OxmlElement('w:shd')
    s.set(qn('w:val'), 'clear'); s.set(qn('w:color'), 'auto'); s.set(qn('w:fill'), fill); pPr.append(s)


def table(doc, rows):
    cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows]
    hdr, body = cells[0], [r for r in cells[2:]]
    t = doc.add_table(rows=1 + len(body), cols=len(hdr)); t.style = 'Table Grid'
    for i, row in enumerate([hdr] + body):
        for j in range(len(hdr)):
            c = t.cell(i, j); c.text = ''
            add_inline(c.paragraphs[0], row[j] if j < len(row) else '', 9)
            c.paragraphs[0].paragraph_format.keep_with_next = i < len(body)  # 整张表留在同一页
            if i == 0:
                for r in c.paragraphs[0].runs: r.bold = True
                tcPr = c._tc.get_or_add_tcPr(); s = OxmlElement('w:shd')
                s.set(qn('w:val'), 'clear'); s.set(qn('w:fill'), 'DCE6F1'); tcPr.append(s)
    for r in t.rows:
        r._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
    doc.add_paragraph()


def build(src, out):
    src = Path(src); lines = src.read_text(encoding='utf8').splitlines()
    doc = Document()
    sec = doc.sections[0]; sec.left_margin = sec.right_margin = Cm(2.2)
    st = doc.styles['Normal']; st.font.name = FONT; st.element.rPr.rFonts.set(qn('w:eastAsia'), FONT); st.font.size = Pt(10.5)
    i = 0; para = []; last_cap = None
    def flush():
        nonlocal para
        if para:
            p = doc.add_paragraph(); add_inline(p, ''.join(para)); p.paragraph_format.space_after = Pt(6)
        para = []
    while i < len(lines):
        l = lines[i]
        if not l.strip():
            flush(); i += 1; continue
        m = re.match(r'^(#{1,3}) (.*)', l)
        if m:
            flush(); lvl = len(m.group(1))
            h = doc.add_heading(level=lvl - 1 if lvl > 1 else 0) if lvl == 1 else doc.add_heading(level=lvl - 1)
            set_font(h.add_run(m.group(2)), {1: 20, 2: 15, 3: 12.5}[lvl], bold=True, color='1F3864')
            i += 1; continue
        if l.startswith('|'):
            flush(); rows = []
            if doc.paragraphs and doc.paragraphs[-1]._p is not last_cap and len(doc.paragraphs[-1].text) <= 80: doc.paragraphs[-1].paragraph_format.keep_with_next = True  # 引出表格的一句和表留在同一页；图注不算，否则图和整张表要挤进同一页
            while i < len(lines) and lines[i].startswith('|'): rows.append(lines[i]); i += 1
            table(doc, rows); continue
        m = re.match(r'^!\[(.*)\]\((.*?)\)(?:\{宽=([\d.]+)\})?\s*$', l)
        if m:
            flush(); img = (src.parent / m.group(2)).resolve()
            if img.exists():
                doc.add_picture(str(img), width=Cm(float(m.group(3) or 15.5))); doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                doc.paragraphs[-1].paragraph_format.keep_with_next = True  # 图和图注留在同一页
            else:
                add_inline(doc.add_paragraph(), f'（缺图：{m.group(2)}）')
            cap = doc.add_paragraph(); add_inline(cap, m.group(1), 9); cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            last_cap = cap._p
            nxt = next((x for x in lines[i + 1:] if x.strip()), '')
            cap.paragraph_format.keep_with_next = nxt.startswith('>')  # 公式和“怎么读”留在同一页
            i += 1; continue
        if l.startswith('>'):
            flush(); buf = []
            while i < len(lines) and lines[i].startswith('>'): buf.append(lines[i][1:].strip()); i += 1
            p = doc.add_paragraph(); add_inline(p, ' '.join(buf), 10); shade(p)
            p.paragraph_format.left_indent = Cm(0.4); continue
        if re.match(r'^\s*[-*] ', l):
            flush(); p = doc.add_paragraph(style='List Bullet'); add_inline(p, re.sub(r'^\s*[-*] ', '', l)); i += 1; continue
        para.append(l.strip()); i += 1
    flush()
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    if Path(out).exists(): sys.exit(f'{out} 已存在：每轮用新文件名，不覆盖旧报告')
    doc.save(out); print('写好', out)


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2])
