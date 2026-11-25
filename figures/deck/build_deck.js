// Build the 15-minute, 4-speaker deck (22 slides + 1 backup slide): DoorFlow. Every slide shows its own English speech (read-along panel).
// Run from the repo root:  NODE_PATH=<dir with pptxgenjs> node figures/deck/build_deck.js
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require(process.env.PPTX_SKILL + "/scripts/apply_theme.js");

const ROOT = path.resolve(__dirname, "../..");
const OUT = path.join(ROOT, process.env.DECK_OUT || "SEEM5910_演讲PPT_v52.pptx");
const IMG = JSON.parse(fs.readFileSync(path.join(__dirname, "images.json"), "utf8"));
const SCRIPT = JSON.parse(fs.readFileSync(path.join(__dirname, "script.json"), "utf8"));

const THEME = {
  name: "DoorFlow",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1B2631", lt1: "FFFFFF", dk2: "0E3A4A", lt2: "EDF2F4",
    accent1: "E39B2D", accent2: "0F6E7E", accent3: "C0392B",
    accent4: "5D6D7E", accent5: "D7E6EA", accent6: "FBEFD9",
    hlink: "0F6E7E", folHlink: "5D6D7E",
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "DoorFlow: Scheduling Robots Through Narrow Doors";
const C = pres.SchemeColor;
const W = 13.333, H = 7.5, M = 0.6;

pres.defineSlideMaster({
  title: "DARK",
  background: { color: THEME.colors.dk2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 2.0, w: 8.2, h: 1.9, fontSize: 40, bold: true, color: C.background1, valign: "top", align: "left" }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: THEME.colors.lt1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.35, w: 10.4, h: 0.85, fontSize: 30, bold: true, color: C.text2, valign: "middle", align: "left" }, text: "" } },
  ],
  slideNumber: { x: 12.35, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: C.accent4, align: "right" },
});

// ---------- helpers ----------
function fit(key, x, y, w, h, align = "center") {
  const im = IMG[key];
  const r = im.w / im.h;
  let ww = w, hh = w / r;
  if (hh > h) { hh = h; ww = h * r; }
  const xx = align === "left" ? x : x + (w - ww) / 2;
  return { path: path.join(ROOT, im.path), x: xx, y: y + (h - hh) / 2, w: ww, h: hh };
}
function addImg(slide, key, x, y, w, h, align) {
  const o = fit(key, x, y, w, h, align);
  slide.addImage({ ...o, altText: key, objectName: "img-" + key });
  return o;
}
function speakerChip(slide, n) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 11.25, y: 0.5, w: 1.5, h: 0.45, rectRadius: 0.22, fill: { color: C.accent6 }, line: { color: C.accent1, width: 1 }, objectName: "speaker-chip" });
  slide.addText(n ? "Speaker " + n : "Backup", { x: 11.25, y: 0.5, w: 1.5, h: 0.45, fontSize: 13, bold: true, color: C.text2, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "speaker-label" });
}
function numCircle(slide, x, y, label, d = 0.5, fill = C.accent1) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill, width: 0.5 }, objectName: "num-" + label });
  slide.addText(String(label), { x, y, w: d, h: d, fontSize: 16, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
}
function card(slide, x, y, w, h, fill = C.background2) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: { color: fill, width: 0.5 }, objectName: "card" });
}
function stat(slide, x, y, w, big, label, color = C.accent2, bigSize = 40) {
  slide.addText(big, { x, y, w, h: 0.8, fontSize: bigSize, bold: true, color, fontFace: THEME.headFontFace, margin: 0, isTextBox: true, valign: "bottom" });
  slide.addText(label, { x, y: y + 0.85, w, h: 0.75, fontSize: 14, color: C.text1, margin: 0, isTextBox: true, valign: "top" });
}
function caption(slide, text, x, y, w) {
  slide.addText(text, { x, y, w, h: 0.35, fontSize: 11, italic: true, color: C.accent4, margin: 0, isTextBox: true });
}
function body(slide, items, x, y, w, h, size = 16) {
  const runs = items.map((t, i) => {
    const o = { paraSpaceAfter: 8, breakLine: i < items.length - 1 };
    if (Array.isArray(t)) return t.map((r, j) => ({ text: r.text, options: { ...r.options, ...(j === 0 ? o : {}), breakLine: j === t.length - 1 && i < items.length - 1 } }));
    return [{ text: t, options: o }];
  }).flat();
  slide.addText(runs, { x, y, w, h, fontSize: size, color: C.text1, valign: "top", margin: 0, isTextBox: true });
}
function notes(slide, s) {
  return;   // v44: no speaker notes; the key formulas are in the slide text, the full script is in the Word file
  const clean = (t) => t.replace(/\*\*/g, "").replace(/[{}]/g, "");
  const hints = s.hints.map((h) => "- " + h).join("\n");
  const body = s.segs.map((g) => `${clean(g.en)}\n中：${clean(g.zh)}`).join("\n\n");
  const src = s.foot ? `\n\nWhere the numbers come from:\n${s.foot}` : "";
  slide.addNotes(`[${s.speaker ? "Speaker " + s.speaker + " · " + s.time : "Backup slide: not presented, use if asked"}]\n\n提示 / Cues:\n${hints}\n\nScript（英文一段，下面跟中文）:\n\n${body}${src}`);
}
// grey origin line at the bottom: where this slide's numbers come from (script.json "foot")
function foot(slide, s, color = C.accent4) {
  return;   // v43: no small print on the slides; the origin line stays in the speaker notes and the Word tables
  slide.addText(s.foot, { x: M, y: 6.99, w: 11.6, h: 0.44, fontSize: 8.5, color, margin: 0, isTextBox: true, valign: "top", objectName: "origin-line" });
}
function content(s) {
  section(s.speaker);
  const slide = pres.addSlide({ masterName: "CONTENT", sectionTitle: s.speaker ? "Speaker " + s.speaker : "Backup (not presented)" });
  slide.addText(s.title, { placeholder: "title" });
  speakerChip(slide, s.speaker);
  notes(slide, s);
  foot(slide, s);
  return slide;
}
const S = (n) => SCRIPT[n - 1];
const sections = new Set();
function section(n) { const t = n ? "Speaker " + n : "Backup (not presented)"; if (!sections.has(t)) { pres.addSection({ title: t }); sections.add(t); } }

// rich text: **bold** -> bold run
function md(t, color = C.text1, boldColor = C.text2) {
  return t.split(/(\*\*[^*]+\*\*)/).filter((x) => x).map((x) => x.startsWith("**")
    ? { text: x.slice(2, -2), options: { bold: true, color: boldColor } }
    : { text: x, options: { color } });
}
function para(slide, t, x, y, w, h, size = 14, color = C.text1, boldColor = C.text2, valign = "top") {
  slide.addText(md(t, color, boldColor), { x, y, w, h, fontSize: size, valign, margin: 0, isTextBox: true });
}
function bullets(slide, items, x, y, w, h, size = 14) { body(slide, items.map((t) => md(t)), x, y, w, h, size); }
// pseudocode block: "~" at the start = safety-net line (grey, italic); text after "#" = comment; keywords in orange
const KW = new Set(["every", "for", "each", "if", "and", "then", "else", "once", "where", "in"]);
function code(slide, rows, x, y, w, h, size = 12) {
  // rows: [code] or [code, comment]; comments start in one column
  const col = Math.max(...rows.filter((r) => r.length > 1).map((r) => r[0].length)) + 3;
  const runs = [];
  rows.forEach(([ln, cm], i) => {
    const grey = ln.startsWith("~");
    let t = grey ? " " + ln.slice(1) : ln;
    let com = "";
    if (cm) { t = t.padEnd(col); com = "# " + cm; }
    t = t.replace(/^ +/, (sp) => "\u00A0".repeat(sp.length));
    let parts;
    if (grey) parts = [[t, "8A97A3"]];
    else parts = t.split(/(\b[a-z]+\b)/).filter((p) => p !== "").map((p) => [p, KW.has(p) ? "F0A93B" : "E8EEF1"]);
    if (com) parts.push([com, grey ? "8A97A3" : "6FC2CE"]);
    if (!parts.length) parts.push(["\u00A0", "E8EEF1"]);
    parts.forEach(([txt, c], j) => runs.push({ text: txt, options: { color: c, italic: grey, breakLine: j === parts.length - 1 && i < rows.length - 1 } }));
  });
  slide.addText(runs, { x, y, w, h, fontSize: size, fontFace: "Consolas", valign: "top", margin: 0, isTextBox: true, lineSpacingMultiple: 1.32 });
}

// ---------- read-along text: most of each slide's speech from script.json ----------
// 【…】 = pointing cue, {…} = linking words and side remarks the speaker says from memory; both are left off the slide,
// so the slide shows only the key parts of the speech.
const cue = (t) => t.replace(/【[^】]*】\s*/g, "").replace(/\{[^}]*\}/g, " ").replace(/\s+([,.;:!?])/g, "$1").replace(/\s{2,}/g, " ").trim()
  .replace(/^(\**)([a-z])/, (m, a, b) => a + b.toUpperCase()).replace(/([.!?]\s+)(\**)([a-z])/g, (m, a, b, c) => a + b + c.toUpperCase());
// slide text = each segment's "key" (keywords taken from its own words; a list = several lines); backup slides keep the full text
const say = (s, idx) => (idx || s.segs.map((_, i) => i)).flatMap((i) => s.segs[i].key ? [].concat(s.segs[i].key) : [cue(s.segs[i].en)]).filter((p) => p);
const oneP = (a) => a;   // keyword lines stay on their own lines
const keyOf = (s, i) => [].concat(s.segs[i].key !== undefined ? s.segs[i].key : cue(s.segs[i].en));   // one segment's slide lines ([] = nothing on the slide)
function estLines(t, w, sz, em = 0.52) {   // greedy word wrap, ~0.52 em per character (conservative)
  const cpl = Math.max(8, Math.floor((w * 72 * 0.93) / (sz * em)));
  let lines = 1, cur = 0;
  t.replace(/\*\*/g, "").split(/\s+/).forEach((wd) => {
    const L = wd.length + (cur ? 1 : 0);
    if (cur + L > cpl && cur > 0) { lines += 1; cur = wd.length; } else cur += L;
  });
  return lines;
}
function fitSize(paras, w, h, max = 18, min = 11, gap = 6, em = 0.52) {
  for (let sz = max; sz >= min; sz -= 0.5) {
    const n = paras.reduce((a, p) => a + estLines(p, w, sz, em), 0);
    if ((n * sz * 1.2 + (paras.length - 1) * gap) / 72 <= h) return sz;
  }
  return min;
}
const FIT = [];   // [slide no., font size] of every read panel, printed at the end
// panel with the speech text; a thin orange bar on the left marks "read this"
function readPanel(slide, s, paras, x, y, w, h, o = {}) {
  const { max = 18, min = 11, fill = "F4F7F8", color = C.text1, bold = C.text2, valign = "top", pad = 0.2, em = 0.52, shrink = true, center = false } = o;   // em: lower it only where the render shows slack
  if (!paras.length) return 0;
  const pd = fill ? pad : 0;
  if (shrink) {   // keyword lines are short: fit the box to them instead of leaving it half empty
    const iw0 = w - 2 * pd - 0.1, sz0 = fitSize(paras, iw0, h - 2 * pd, max, min, 6, em);
    const need = (paras.reduce((a, p) => a + estLines(p, iw0, sz0, em), 0) * sz0 * 1.2 + (paras.length - 1) * 6) / 72 + 2 * pd + 0.12;
    if (need < h) { if (center) y += (h - need) / 2; h = need; }
  }
  if (fill) card(slide, x, y, w, h, fill);
  slide.addShape(pres.shapes.RECTANGLE, { x: x + (fill ? 0 : -0.2), y: y + 0.12, w: 0.06, h: h - 0.24, fill: { color: C.accent1 }, line: { color: C.accent1, width: 0 }, objectName: "read-bar" });
  const tx = x + pd + 0.1, iw = w - 2 * pd - 0.1, ih = h - 2 * pd;
  const sz = fitSize(paras, iw, ih, max, min, 6, em);
  const runs = [];
  paras.forEach((p, i) => {
    const r = md(p, color, bold);
    r[0].options.paraSpaceAfter = 6;
    r.forEach((run, j) => { run.options.breakLine = j === r.length - 1 && i < paras.length - 1; });
    runs.push(...r);
  });
  slide.addText(runs, { x: tx, y: y + pd, w: iw, h: ih, fontSize: sz, valign, margin: 0, isTextBox: true, objectName: "read-text" });
  FIT.push([s.n, sz]);
  return sz;
}
// "what we tried" table: rows [option, result, best?]; the best rows are shaded and their result in teal
function tried(slide, rows, x, y, w, h, head = "What we tried", size = 12.5, split = 0.56) {
  slide.addText(head, { x, y, w, h: 0.34, fontSize: 13, bold: true, color: C.text2, margin: 0, isTextBox: true, valign: "bottom" });
  const rh = (h - 0.42) / rows.length;
  rows.forEach(([a, b, best], i) => {
    const yy = y + 0.42 + i * rh;
    card(slide, x, yy, w, rh - 0.06, best ? C.accent6 : C.background2);
    para(slide, a, x + 0.15, yy, w * split - 0.2, rh - 0.06, size, C.text1, C.text2, "middle");
    para(slide, b, x + w * split, yy, w * (1 - split) - 0.15, rh - 0.06, size, best ? C.accent2 : C.text1, best ? C.accent2 : C.text2, "middle");
  });
}
function bigStat(slide, x, y, w, big, label, col = C.accent2, size = 34) {
  slide.addText(big, { x, y, w, h: 0.7, fontSize: size, bold: true, color: col, fontFace: THEME.headFontFace, margin: 0, isTextBox: true, valign: "bottom" });
  para(slide, label, x, y + 0.74, w, 0.7, 13);
}

// ---------- 1 title ----------
section(1);
{
  const s = S(1);
  const slide = pres.addSlide({ masterName: "DARK", sectionTitle: "Speaker 1" });
  slide.addText(s.title, { placeholder: "title" });
  slide.addText("SEEM5910 Final Presentation\nLeague of Robot Runners (LoRR) 2026 · official room map", { x: M, y: 4.0, w: 7.3, h: 0.9, fontSize: 18, color: C.accent5, margin: 0, isTextBox: true });
  readPanel(slide, s, say(s), M + 0.2, 5.0, 7.1, 1.45, { fill: null, color: C.background1, bold: C.accent1, max: 18 });
  slide.addText("15 minutes", { x: M, y: 6.45, w: 6, h: 0.4, fontSize: 14, color: C.accent1, bold: true, margin: 0, isTextBox: true });
  card(slide, 8.2, 0.75, 4.55, 6.0, C.background1);
  addImg(slide, "bg", 8.3, 0.85, 4.35, 5.8);
  notes(slide, s);
}

// ---------- 2 background ----------
{
  const s = S(2); const slide = content(s);
  addImg(slide, "bg", M, 1.3, 5.6, 5.65, "left");
  readPanel(slide, s, say(s), 6.65, 1.3, 6.1, 4.0, { max: 20, center: true });
  card(slide, 6.65, 5.5, 6.1, 1.4, C.accent6);
  [["16", "rooms\n(counted)"], ["31", "doors, most 1 cell wide (counted)"], ["200–300", "robots\n(competition)"], ["5,000", "ticks per run\n(competition)"]].forEach(([b, l], i) => {
    const x = 6.85 + i * 1.48;
    slide.addText(b, { x, y: 5.58, w: 1.42, h: 0.55, fontSize: 22, bold: true, color: C.accent2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
    slide.addText(l, { x, y: 6.15, w: 1.38, h: 0.65, fontSize: 12, color: C.text1, margin: 0, isTextBox: true, valign: "top" });
  });
}

// ---------- 3 slower ----------
{
  const s = S(3); const slide = content(s);
  card(slide, M, 1.3, 3.4, 5.62, C.accent6);
  slide.addText("127", { x: M + 0.3, y: 1.5, w: 2.8, h: 0.9, fontSize: 54, bold: true, color: C.accent2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  slide.addText("orders per 500 ticks at the start", { x: M + 0.3, y: 2.4, w: 2.9, h: 0.5, fontSize: 14, color: C.text1, margin: 0, isTextBox: true });
  slide.addText("37", { x: M + 0.3, y: 3.1, w: 2.8, h: 0.9, fontSize: 54, bold: true, color: C.accent3, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  slide.addText("at the end of the run", { x: M + 0.3, y: 4.0, w: 2.9, h: 0.5, fontSize: 14, color: C.text1, margin: 0, isTextBox: true });
  para(slide, "2024 champion's way of giving out orders · **60 runs**", M + 0.3, 4.8, 2.9, 1.6, 13);
  addImg(slide, "collapse", 4.3, 1.25, 8.45, 3.6);
  readPanel(slide, s, say(s), 4.3, 5.0, 8.45, 1.9, { max: 20, pad: 0.15, center: true });
}

// ---------- 4 jam ----------
{
  const s = S(4); const slide = content(s);
  addImg(slide, "jam", M, 1.3, 5.6, 5.65, "left");
  readPanel(slide, s, say(s), 6.65, 1.3, 6.1, 2.6, { max: 22, center: true });
  card(slide, 6.65, 4.2, 6.1, 2.7, C.accent6);   // the 97 robots are in the figure's own note, so only one number card
  slide.addText("1 week", { x: 6.95, y: 4.4, w: 5.5, h: 0.9, fontSize: 40, bold: true, color: C.accent2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  para(slide, "to build the monitor", 6.95, 5.4, 5.5, 1.2, 18);
}

// ---------- 5 prior work ----------
{
  const s = S(5); const slide = content(s);
  for (let i = 0; i < 4; i++) {   // four groups (the title already says "four groups")
    const x = M + (i % 2) * 6.15, y = 1.35 + Math.floor(i / 2) * 1.75;
    readPanel(slide, s, keyOf(s, i + 1), x, y, 5.95, 1.6, { max: 20, fill: C.background2, valign: "middle", shrink: false });
  }
  readPanel(slide, s, keyOf(s, 5), M, 5.0, 12.15, 1.9, { max: 20, fill: C.accent6, valign: "middle", shrink: false });
}

// ---------- 6 everything we tried ----------
{
  const s = S(6); const slide = content(s);
  // [text, key?] ; numbers from report section 9 (both tables)
  const cols = [
    ["Early ideas · dispatch & quotas", [
      ["Early quotas & prices: +0.53% on top of the champion"], ["Hungarian matching: −1.9%"], ["Pin broken robots: −2.3%, −4.9%"], ["4× planning compute: −1%"],
      ["Throttle after a jam is seen: −7 to −15 points on room maps", 1], ["20 small tweaks: none reliable"], ["AIMD quota: worse than fixed"],
      ["Quota = physical capacity 49: −17.2% (300 robots)", 1], ["Per-link quotas: −1.28%, −1.13%, −4.28%"], ["Quotas for missed cuts: −1.12%, −2.78%"],
      ["BBR-style cap: +0.08%"], ["Region gate: +6.8%, but picked no door"]]],
    ["Early ideas · routes & door rules", [
      ["Early backpressure, backoff, pricing: void (evaluation bug)"], ["Reroute by live occupancy: +1.18% at 1,200 ticks only"], ["Detours: +0.75% (random control +1.07%)"],
      ["Load balancing: −5.2%, −3.76%, −0.06%"], ["Segment routing: −39.2% to −55.4%"], ["Fix a deadlock between two door rules: confirm +0.11%"],
      ["Max 80 steps per side: −0.90%"], ["Step back 3 cells: −2.64%, deadlocked runs 11 → 29"], ["Self-computed global cap: −0.27%"],
      ["Yield past broken robots: one run 1,130 → 351"]]],
    ["Later · door order", [
      ["NAV reservation: +0.20%, worst −7.60%"], ["EF priority for crossers: −0.74%"], ["Token-ring early release: +0.55%, −0.50%"],
      ["802.1Qbv timetable switching: −4.98%, −6.43%", 1], ["VOQ: +1.07%, mostly from 2 maps"],
      ["TXOP, iSLIP, fast reroute, MPLS, RSVP-TE, PCE, hop-by-hop admission: skipped"]]],
    ["Later · rate & quotas", [
      ["Token bucket: −1.82%, −2.42%"], ["PFC pause on dispatch: −4.11%"], ["HTTP pipelining: +0.25%, worst −7.47%"], ["Looser global quota: −0.46%, −1.08%"],
      ["Longer execution window: −2.36%, −2.92%"], ["SWAN headroom: dev +1.69%, confirm −0.75%"], ["Quota from early measurement: −0.05%"],
      ["Auto-bandwidth quotas: never triggered"], ["CoDel, ECN, DCQCN, BwE, …: skipped"]]],
    ["Later · rerouting", [
      ["BFD + LFA detour: −2.07%"], ["FRER backup doors: −6.04%, −9.88%"], ["SWAN / B4 strict priority: −1.25%, −1.31%"], ["Fortz–Thorup weights: −0.29%"],
      ["Retarget on arrival: −1.36%"], ["oFIB, no stepping back: −64.09%", 1], ["HN-SPF link costs: −25.88%", 1], ["CSPF detour limit: −20.98%, −8.70%"],
      ["BGP damping: +0.20%, rarely triggered"], ["Two lanes in wide doors: +0.20%; one deadlock 1,114 → 700"], ["Anycast, flowlets, deflection, …: skipped"]]],
    ["Later · queues & deadlock", [
      ["Hop-by-hop credit flow: −2.74%", 1], ["RED early drop: −0.47%, −0.69%"], ["Predictive follow-up: −1.24%"], ["More door schedulers (SDN): −0.06%, −0.13%"],
      ["Turn before the door: −1.32%, −2.09%"], ["Duato escape channel: +0.02%"], ["Watchdog re-timing: +0.13%"], ["4-mechanism combo: +1.65%, mostly 1 map"],
      ["Wormhole, cut-through, cycle breaking, …: skipped"]]],
  ];
  const cw = 1.95, gap = 0.09;
  cols.forEach(([head, items], i) => {
    const x = M + i * (cw + gap);
    card(slide, x, 1.3, cw, 4.32, i < 2 ? C.accent6 : C.background2);
    slide.addText(head, { x: x + 0.1, y: 1.36, w: cw - 0.2, h: 0.42, fontSize: 10.5, bold: true, color: C.text2, margin: 0, isTextBox: true, valign: "top" });
    const runs = items.map(([txt, key], j) => ({ text: txt, options: { color: key ? C.accent3 : C.text1, bold: !!key, breakLine: j < items.length - 1, paraSpaceAfter: 3 } }));
    slide.addText(runs, { x: x + 0.1, y: 1.8, w: cw - 0.18, h: 3.78, fontSize: 8.2, valign: "top", margin: 0, isTextBox: true });
  });
  readPanel(slide, s, oneP(say(s)), M, 5.72, 12.15, 1.22, { max: 18, pad: 0.12 });
}

// ---------- 7 congestion monitor ----------
{
  const s = S(7); const slide = content(s);
  addImg(slide, "monitor", M, 1.25, 12.15, 3.85);
  caption(slide, "Panels at tick 3,000: orders finished so far · robots stuck now · door-6 crossings in the next 500 ticks. Bars: share of the run each door was jammed.", M, 5.13, 12.15);
  readPanel(slide, s, say(s), M, 5.5, 12.15, 1.42, { max: 18, pad: 0.12 });
}

// ---------- 8 model + ceiling ----------
{
  const s = S(8); const slide = content(s);
  addImg(slide, "map", M, 1.3, 7.0, 5.6);   // the formulas are written as text on the right, so no separate formula image
  readPanel(slide, s, say(s), 7.8, 1.3, 4.95, 5.65, { max: 20, center: true });
}

// ---------- 9 why only about 26 robots per 500 ticks at door 6 (breakdown of the 18.7 ticks) ----------
{
  const s = S(9); const slide = content(s);
  addImg(slide, "doorC", M, 1.25, 12.15, 2.55);
  readPanel(slide, s, say(s), M, 3.95, 12.15, 3.0, { max: 20, pad: 0.15, em: 0.46 });
}

// ---------- 10 what makes our robots different ----------
{
  const s = S(10); const slide = content(s);
  const X = [M, M + 4.05, M + 8.15], CW = [3.95, 4.0, 4.0], rh = 0.44, y0 = 1.72;
  ["Our robots", "Computer networks", "Road traffic"].forEach((h, j) =>
    slide.addText(h, { x: X[j] + 0.1, y: 1.3, w: CW[j] - 0.15, h: 0.36, fontSize: 15, bold: true, color: j ? C.text1 : C.accent3, margin: 0, isTextBox: true, valign: "bottom" }));
  const rows = [  // [our robots, networks, differs?, traffic, differs?]
    ["**Cannot be dropped**", "**Drops packets**, sends them again", 1, "Same: a car cannot vanish", 0],
    ["**Waiting takes up a cell**", "Waits in router memory, **off the line**", 1, "Same: a waiting car blocks its lane", 0],
    ["**Fixed fleet:** robots never leave the map", "A packet **leaves** once delivered", 1, "Cars **leave** at their destination", 1],
    ["**Face to face:** a one-cell door jams", "Most lines carry **both ways at once**", 1, "Most roads have **a lane each way**", 1],
    ["**May wait long,** if more orders finish", "Flows expect **a fair share**", 1, "**No car** may wait forever", 1],
    ["**One program** decides every order and move", "**Each sender** sets its own rate", 1, "**Each driver** picks a route", 1],
  ];
  rows.forEach(([a, b, db, c, dc], i) => {
    const y = y0 + i * (rh + 0.04);
    card(slide, X[0], y, CW[0], rh, C.background2);
    card(slide, X[1], y, CW[1], rh, db ? C.accent6 : "FFFFFF");
    card(slide, X[2], y, CW[2], rh, dc ? C.accent6 : "FFFFFF");
    para(slide, a, X[0] + 0.12, y, CW[0] - 0.2, rh, 13, C.text1, C.text2, "middle");
    para(slide, b, X[1] + 0.12, y, CW[1] - 0.2, rh, 13, db ? C.text1 : "8A8F98", C.text2, "middle");
    para(slide, c, X[2] + 0.12, y, CW[2] - 0.2, rh, 13, dc ? C.text1 : "8A8F98", C.text2, "middle");
  });
  caption(slide, "Shaded = different from our robots. Computer networks differ in all six rows, road traffic in four.", M, y0 + 6 * (rh + 0.04) + 0.02, 12.15);
  readPanel(slide, s, oneP(say(s)), M, 5.0, 12.15, 1.95, { max: 18, pad: 0.15 });
}

// ---------- 11 a quota for each door ----------
{
  const s = S(11); const slide = content(s);
  addImg(slide, "bdp", M, 1.3, 6.3, 5.65, "left");
  readPanel(slide, s, say(s), 7.1, 1.3, 5.65, 5.65, { max: 20, center: true });
}

// ---------- 12 door 6's quota, number by number ----------
{
  const s = S(12); const slide = content(s);
  const X = [M, M + 4.7, M + 8.45], CW = [4.6, 3.65, 3.7], y0 = 1.3, rh = 0.7;   // the table, then one line saying how the rows chain
  ["", "Into the lower-left", "Out of it"].forEach((h, j) =>
    slide.addText(h, { x: X[j] + 0.1, y: y0, w: CW[j] - 0.15, h: 0.36, fontSize: 14, bold: true, color: C.text2, margin: 0, isTextBox: true, valign: "bottom" }));
  const rows = [
    ["**Ticks per robot**, each way: door rate\n500 ÷ 18.7 ≈ 26 (slide 9) ÷ 2 = 13 per 500", "500 ticks ÷ 13 robots ≈ **38.5**", "500 ticks ÷ 13 robots ≈ **38.5**"],
    ["**Free trip** = 25 to the pickup\n+ average from every far-side cell", "to pickup 25 + to door 222 = **247**", "to pickup 25 + to door 133 = **158**"],
    ["**Slowdown** = real ÷ free trip\nmedian of 224 timed trips", "× **2.23**", "× **2.23**"],
    ["**Real trip** = slowdown × free trip", "2.23 × 247 ≈ **551**", "2.23 × 158 ≈ **352**"],
    ["**Quota** = real trip ÷ ticks per robot,\nrounded up", "551 ÷ 38.5 ≈ 14.3 → **15**", "352 ÷ 38.5 ≈ 9.2 → **10**"],
  ];
  rows.forEach((row, i) => {
    const y = y0 + 0.45 + i * (rh + 0.06);
    row.forEach((txt, j) => {
      card(slide, X[j], y, CW[j], rh, j === 0 ? C.background2 : C.accent6);
      para(slide, txt, X[j] + 0.15, y, CW[j] - 0.25, rh, j === 0 ? 14 : 16, C.text1, j ? C.accent2 : C.text2, "middle");
    });
  });
  const yEnd = y0 + 0.45 + 5 * (rh + 0.06);
  readPanel(slide, s, say(s), M, yEnd + 0.08, 12.15, 0.75, { max: 20, pad: 0.12 });
  caption(slide, "Set in advance: only the limits 15 / 10. Counted live, every round: the robots on the way. The planner prints the same values (247 / 158, 15 / 10); recompute: figures/deck/demo/door6_numbers.py", M, yEnd + 0.95, 12.15);
}

// ---------- 13 one quota per door, sized by formula: what we tried ----------
{
  const s = S(13); const slide = content(s);
  addImg(slide, "knee", M, 1.3, 6.4, 5.1, "left");
  caption(slide, "Each dot = one 500-tick period, one measured run each.", M, 6.5, 6.4);
  readPanel(slide, s, say(s), 7.2, 1.3, 5.55, 3.95, { max: 18 });   // the sizes (8, 32, formula) are in the text, so the table only compares how to count
  tried(slide, [["One quota for all robots", "+0.53%"], ["One quota **per door and direction**", "**+29.1%** ✓", 1]],
        7.2, 5.4, 5.55, 1.5, "What we tried", 13, 0.6);
}

// ---------- 14 fixed quota from averages, or adjusted live: three live alternatives rerun ----------
{
  const s = S(14); const slide = content(s);
  addImg(slide, "live", M, 1.25, 7.55, 5.72, "left");
  readPanel(slide, s, say(s), 8.3, 1.3, 4.45, 5.62, { max: 20, center: true });
}

// ---------- 15 one direction at a time (panel A) ----------
{
  const s = S(15); const slide = content(s);
  addImg(slide, "doorA", M, 1.3, 6.6, 4.95, "left");
  slide.addText("Switch: when no robot of this side is within 8 cells and the other side waits, stop letting this side in; once the door and this side's 4-cell buffer are empty, switch.", { x: M, y: 6.3, w: 6.6, h: 0.62, fontSize: 10.5, italic: true, color: C.accent4, margin: 0, isTextBox: true, valign: "top" });
  readPanel(slide, s, say(s), 7.45, 1.3, 5.3, 3.3, { max: 22, center: true });
  card(slide, 7.45, 4.8, 5.3, 2.1, C.accent6);
  slide.addText("+27.6%", { x: 7.7, y: 4.95, w: 4.8, h: 0.85, fontSize: 40, bold: true, color: C.accent2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  para(slide, "this rule alone, on **17 room-map instances**", 7.7, 5.85, 4.8, 0.9, 15);
}

// ---------- 16 when should the door switch sides (formula curve + what we tried) ----------
{
  const s = S(16); const slide = content(s);
  addImg(slide, "utilC", M, 1.25, 7.6, 3.55);
  tried(slide, [["Fixed timetable", "−5.0%, −6.4%"], ["At most 80 steps per turn", "−1.1%"], ["**Serve one side until it is empty**", "**best** ✓", 1]],
        M, 4.85, 7.6, 2.05, "What we tried for switching", 13.5);
  readPanel(slide, s, say(s), 8.45, 1.3, 4.3, 5.62, { max: 20, center: true });
}

// ---------- 17 how big should the buffer be (panel B + what we tried) ----------
{
  const s = S(17); const slide = content(s);
  addImg(slide, "doorB", M, 1.3, 12.15, 3.75);
  readPanel(slide, s, say(s), M + 1.2, 5.3, 9.75, 1.6, { max: 22, center: true });
}

// ---------- 18 pseudocode ----------
{
  const s = S(18); const slide = content(s);
  card(slide, M, 1.35, 12.15, 5.55, "16212B");
  // "~" = safety-net line (grey); text after "#" = comment
  code(slide, [
    ["every planning round:", "1 · who gets an order"],
    ["  L[d,s] ← robots holding an order that still crosses door d in direction s"],
    ["  for (robot r, order q) in order of increasing cost:"],
    ["      if L[d,s] < Q[d,s] for every door (d,s) that q crosses"],
    ["      then give q to r;  L[d,s] += 1 for those doors"],
    ["      else try r's next-cheapest order"],
    ["  where Q[d,s] = ⌈ 2.23 × T[d,s] ÷ 500 × 13 ⌉", "slowdown × free trip × robots per tick"],
    [""],
    ["every tick, inside the planner:", "2 · who moves first"],
    ["  for each door d:"],
    ["      if idle: serve the side with more robots waiting"],
    ["      if no crosser of this side within 8 cells and the other side waits: wind down"],
    ["      once the door and this side's 4-cell zone are empty: switch side"],
    ["  forbid moves into a door against its direction"],
    ["  crossers of the other side within 4 cells may only move away"],
    ["  robots held by these rules get the lowest priority"],
  ], M + 0.3, 1.6, 11.6, 5.2, 13);
}

// ---------- 19 the hardest part + demo ----------
{
  const s = S(19); const slide = content(s);
  readPanel(slide, s, say(s), M, 1.3, 5.0, 5.65, { max: 20, center: true });
  addImg(slide, "demo", 5.85, 1.3, 6.9, 4.07);
  para(slide, "One run each: no door control **609** orders · DoorFlow **1,130** orders.", 5.85, 5.5, 6.9, 1.3, 12, C.accent4, C.text2);
}

// ---------- 20 results ----------
{
  const s = S(20); const slide = content(s);
  slide.addText("+140.5%", { x: M, y: 2.2, w: 3.6, h: 1.0, fontSize: 48, bold: true, color: C.accent3, fontFace: THEME.headFontFace, margin: 0, isTextBox: true, valign: "bottom" });
  para(slide, "more orders than the official starter program", M, 3.3, 3.5, 0.8, 16);
  para(slide, "= mean of **(DoorFlow ÷ starter − 1)** over the **60** same-seed pairs", M, 4.2, 3.5, 0.9, 14);
  addImg(slide, "results", 4.3, 1.3, 8.45, 5.6);   // nothing else to read: the speech is said, the numbers are here
}

// ---------- 21 what matters ----------
{
  const s = S(21); const slide = content(s);
  addImg(slide, "ablD", M, 1.3, 12.15, 4.35);
  readPanel(slide, s, say(s), M + 1.5, 5.8, 9.15, 1.12, { max: 20, pad: 0.12, fill: C.accent6, center: true });
}

// ---------- 22 conclusion ----------
{
  const s = S(22);
  const slide = pres.addSlide({ masterName: "DARK", sectionTitle: "Speaker 4" });
  slide.addText(s.title, { placeholder: "title" });
  const t = say(s);   // four points, then thanks ("To conclude." is said, not shown)
  t.slice(0, t.length - 1).forEach((p, i) => {
    const y = 2.95 + i * 0.92;
    numCircle(slide, M, y + 0.12, i + 1, 0.5, C.accent1);
    const sz = fitSize([p], 11.4, 0.82, 18, 12);
    slide.addText(md(p, C.background1, C.accent1), { x: M + 0.75, y, w: 11.4, h: 0.82, fontSize: sz, valign: "middle", margin: 0, isTextBox: true });
    FIT.push([s.n, sz]);
  });
  slide.addText(t[t.length - 1], { x: 5.6, y: 6.62, w: 7.1, h: 0.5, fontSize: 20, bold: true, color: C.accent1, align: "right", margin: 0, isTextBox: true });
  notes(slide, s);
}

// ---------- 23 backup: how long does the door take (measured) ----------
{
  const s = S(23); const slide = content(s);
  addImg(slide, "timing", M, 1.35, 7.6, 3.2, "left");
  [["1,255", "crossings of door 6 timed\nin 5 runs, 250 robots"], ["10 ticks", "median gap, same direction\n(mostly 6 or 9 = 2 or 3 moves)"], ["34 ticks", "median gap when the door\nswitches direction"]].forEach(([b, l], i) => {
    const x = M + i * 2.55;
    card(slide, x, 4.85, 2.45, 2.05, C.accent6);
    bigStat(slide, x + 0.18, 4.92, 2.15, b, l, i === 2 ? C.accent3 : C.accent2, 28);
  });
  readPanel(slide, s, say(s), 8.45, 1.3, 4.3, 5.62, { max: 20, center: true });
}

console.log("read-panel font sizes:", FIT.map(([n, z]) => n + ":" + z).join(" "));
(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
