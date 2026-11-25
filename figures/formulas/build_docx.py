"""Build SEEM5910_公式讲解_v1.docx from 公式讲解_源稿.md with pandoc (Chinese fonts set in a reference doc)."""
import pathlib, re, shutil, subprocess, tempfile, zipfile
here = pathlib.Path(__file__).resolve().parent
root = here.parents[1]
out = root / "SEEM5910_公式讲解_v1.docx"
tmp = pathlib.Path(tempfile.mkdtemp())
ref = tmp / "ref.docx"
subprocess.run(["pandoc", "-o", str(ref), "--print-default-data-file", "reference.docx"], check=True)
# set East Asian font for every style
z = zipfile.ZipFile(ref); files = {n: z.read(n) for n in z.namelist()}; z.close()
st = files["word/styles.xml"].decode()
st = re.sub(r'<w:rFonts [^>]*/>', '<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="Microsoft YaHei" w:cs="Calibri"/>', st)
st = st.replace('<w:rPrDefault><w:rPr>', '<w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="Microsoft YaHei" w:cs="Calibri"/><w:lang w:eastAsia="zh-CN"/>', 1) if 'w:eastAsia="Microsoft YaHei"' not in st.split('</w:docDefaults>')[0] else st
files["word/styles.xml"] = st.encode()
with zipfile.ZipFile(ref, "w", zipfile.ZIP_DEFLATED) as z:
    for n, b in files.items(): z.writestr(n, b)
subprocess.run(["pandoc", str(here / "公式讲解_源稿.md"), "-o", str(out), "--reference-doc", str(ref),
                ], check=True)
shutil.rmtree(tmp)
print(out)
