// Build the 15-minute, 4-speaker deck.
// Run from the repo root:  NODE_PATH=<dir with pptxgenjs> node figures/deck/build_deck.js
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require(process.env.PPTX_SKILL + "/scripts/apply_theme.js");

const ROOT = path.resolve(__dirname, "../..");
const OUT = path.join(ROOT, process.env.DECK_OUT || "SEEM5910_演讲PPT_v4.pptx");
const IMG = JSON.parse(fs.readFileSync(path.join(__dirname, "images.json"), "utf8"));
const SCRIPT = JSON.parse(fs.readFileSync(path.join(__dirname, "script.json"), "utf8"));

const THEME = {
  name: "Robot Network",
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
pres.title = "Managing Warehouse Robots Like a Computer Network";
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
  slide.addText("Speaker " + n, { x: 11.25, y: 0.5, w: 1.5, h: 0.45, fontSize: 13, bold: true, color: C.text2, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "speaker-label" });
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
    const o = { bullet: { indent: 18 }, paraSpaceAfter: 8, breakLine: i < items.length - 1 };
    if (Array.isArray(t)) return t.map((r, j) => ({ text: r.text, options: { ...r.options, ...(j === 0 ? o : {}), breakLine: j === t.length - 1 && i < items.length - 1 } }));
    return [{ text: t, options: o }];
  }).flat();
  slide.addText(runs, { x, y, w, h, fontSize: size, color: C.text1, valign: "top", margin: 0, isTextBox: true });
}
function notes(slide, s) {
  const clean = (t) => t.replace(/\*\*/g, "");
  const hints = s.hints.map((h) => "- " + h).join("\n");
  slide.addNotes(`[Speaker ${s.speaker} · ${s.time}]\n\n提示 / Cues:\n${hints}\n\nScript:\n${clean(s.en)}\n\n中文对照：\n${clean(s.zh)}`);
}
function content(s) {
  section(s.speaker);
  const slide = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Speaker " + s.speaker });
  slide.addText(s.title, { placeholder: "title" });
  speakerChip(slide, s.speaker);
  notes(slide, s);
  return slide;
}
const S = (n) => SCRIPT[n - 1];
const sections = new Set();
function section(n) { const t = "Speaker " + n; if (!sections.has(t)) { pres.addSection({ title: t }); sections.add(t); } }

// ---------- 1 title ----------
section(1);
{
  const s = S(1);
  const slide = pres.addSlide({ masterName: "DARK", sectionTitle: "Speaker 1" });
  slide.addText(s.title, { placeholder: "title" });
  slide.addText("SEEM5910 Final Presentation\nLeague of Robot Runners 2026 · official room map", { x: M, y: 4.15, w: 7.8, h: 0.9, fontSize: 18, color: C.accent5, margin: 0, isTextBox: true });
  slide.addText("15 minutes", { x: M, y: 6.3, w: 6, h: 0.4, fontSize: 14, color: C.accent1, bold: true, margin: 0, isTextBox: true });
  card(slide, 8.2, 0.75, 4.55, 6.0, C.background1);
  addImg(slide, "bg", 8.3, 0.85, 4.35, 5.8);
  notes(slide, s);
}

// ---------- 2 background ----------
{
  const s = S(2); const slide = content(s);
  addImg(slide, "bg", M, 1.4, 5.6, 5.6, "left");
  const x0 = 6.8, steps = [
    ["Assign", "which robot takes which order"],
    ["Route", "which cells and doors it goes through"],
    ["Execute", "can the next step go now, or wait?"],
  ];
  slide.addText("Each tick the program decides", { x: x0, y: 1.5, w: 5.9, h: 0.45, fontSize: 18, bold: true, color: C.text2, margin: 0, isTextBox: true });
  steps.forEach(([a, b], i) => {
    const y = 2.15 + i * 0.85;
    numCircle(slide, x0, y, i + 1);
    slide.addText([{ text: a + "  ", options: { bold: true, color: C.text2 } }, { text: b, options: { color: C.text1 } }], { x: x0 + 0.7, y, w: 5.2, h: 0.5, fontSize: 16, valign: "middle", margin: 0, isTextBox: true });
  });
  card(slide, x0, 4.9, 5.9, 1.6, C.background2);
  const facts = [["16", "rooms"], ["31", "doors, mostly 1 cell wide"], ["200–300", "robots"], ["5,000", "ticks per run"]];
  facts.forEach(([b, l], i) => {
    const x = x0 + 0.2 + i * 1.45;
    slide.addText(b, { x, y: 5.05, w: 1.4, h: 0.6, fontSize: 24, bold: true, color: C.accent2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
    slide.addText(l, { x, y: 5.7, w: 1.35, h: 0.7, fontSize: 12, color: C.text1, margin: 0, isTextBox: true, valign: "top" });
  });
}

// ---------- 3 slower ----------
{
  const s = S(3); const slide = content(s);
  card(slide, M, 1.6, 3.4, 4.6, C.accent6);
  slide.addText("127", { x: M + 0.3, y: 1.9, w: 2.8, h: 0.9, fontSize: 54, bold: true, color: C.accent2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  slide.addText("tasks per 500 ticks at the start", { x: M + 0.3, y: 2.8, w: 2.9, h: 0.5, fontSize: 14, color: C.text1, margin: 0, isTextBox: true });
  slide.addText("37", { x: M + 0.3, y: 3.55, w: 2.8, h: 0.9, fontSize: 54, bold: true, color: C.accent3, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  slide.addText("at the end of the run", { x: M + 0.3, y: 4.45, w: 2.9, h: 0.5, fontSize: 14, color: C.text1, margin: 0, isTextBox: true });
  slide.addText("Champion task assignment, 60 runs. No errors, no collisions.", { x: M + 0.3, y: 5.15, w: 2.9, h: 0.8, fontSize: 12, italic: true, color: C.accent4, margin: 0, isTextBox: true });
  addImg(slide, "collapse", 4.4, 1.5, 8.35, 4.9);
  caption(slide, "Official room map, 200 / 250 / 300 robots, 20 runs per program", 4.5, 6.55, 8.2);
}

// ---------- 4 jam ----------
{
  const s = S(4); const slide = content(s);
  addImg(slide, "jam", M, 1.35, 5.7, 5.75, "left");
  const cards = [
    ["97", "robots at tick 3,000 that still must cross door 6 inward, incl. ones not yet at the door", C.accent3],
    ["38% → 86%", "share of open orders that must cross door 6", C.accent2],
    ["3.4–7.0 vs 26", "robots through door 6 per 500 ticks: jammed vs orderly", C.accent2],
  ];
  cards.forEach(([b, l, col], i) => {
    const y = 1.55 + i * 1.75;
    card(slide, 6.9, y, 5.85, 1.5, C.background2);
    slide.addText(b, { x: 7.15, y: y + 0.12, w: 5.4, h: 0.7, fontSize: 32, bold: true, color: col, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
    slide.addText(l, { x: 7.15, y: y + 0.85, w: 5.4, h: 0.5, fontSize: 15, color: C.text1, margin: 0, isTextBox: true });
  });
}

// ---------- 5 prior work ----------
{
  const s = S(5); const slide = content(s);
  const groups = [
    ["Task assignment", "Official starter, 2024 champion, flow-based assignment", "Picks near, cheap orders; ignores how many already head for the door"],
    ["Route guidance", "Traffic-flow optimisation, guidance graphs", "Spreads traffic to other roads; door 6 has no other road"],
    ["Planning & collision avoidance", "PIBT, RHCR, WPPL", "Decides who moves next; not how many are coming"],
    ["Congestion handling", "Keep part of the fleet idle; narrow-passage conflicts; AGV deadlock prevention", "Fixed global ratio, or only robots already at the passage"],
  ];
  groups.forEach(([t, ex, gap], i) => {
    const x = M + (i % 2) * 6.15, y = 1.45 + Math.floor(i / 2) * 2.15;
    card(slide, x, y, 5.95, 1.95, C.background2);
    slide.addText(t, { x: x + 0.25, y: y + 0.15, w: 5.5, h: 0.45, fontSize: 18, bold: true, color: C.text2, margin: 0, isTextBox: true });
    slide.addText(ex, { x: x + 0.25, y: y + 0.6, w: 5.5, h: 0.5, fontSize: 13, italic: true, color: C.accent4, margin: 0, isTextBox: true });
    slide.addText([{ text: "Gap here: ", options: { bold: true, color: C.accent3 } }, { text: gap, options: { color: C.text1 } }], { x: x + 0.25, y: y + 1.1, w: 5.5, h: 0.7, fontSize: 14, margin: 0, isTextBox: true, valign: "top" });
  });
  card(slide, M, 5.9, 12.1, 0.95, C.accent6);
  slide.addText([{ text: "Missing in the methods we read: ", options: { bold: true, color: C.text2 } }, { text: "at assignment time, count robots that already hold an order crossing this door in this direction", options: { color: C.text1 } }], { x: M + 0.3, y: 5.9, w: 11.6, h: 0.95, fontSize: 16, valign: "middle", margin: 0, isTextBox: true });
}

// ---------- 6 idea ----------
{
  const s = S(6); const slide = content(s);
  slide.addText("It looks like a computer network", { x: M, y: 1.45, w: 5.8, h: 0.45, fontSize: 18, bold: true, color: C.text2, margin: 0, isTextBox: true });
  const like = [["Door", "link with limited bandwidth"], ["Order through 8 doors", "packet through 8 routers"], ["More robots, fewer crossings", "congestion"]];
  like.forEach(([a, b], i) => {
    const y = 2.05 + i * 1.0;
    card(slide, M, y, 5.8, 0.8, C.background2);
    slide.addText([{ text: a, options: { bold: true, color: C.text2 } }, { text: "  →  " + b, options: { color: C.text1 } }], { x: M + 0.25, y, w: 5.4, h: 0.8, fontSize: 16, valign: "middle", margin: 0, isTextBox: true });
  });
  slide.addText("Why computer networks", { x: 6.95, y: 1.45, w: 5.8, h: 0.45, fontSize: 18, bold: true, color: C.text2, margin: 0, isTextBox: true });
  const why = ["Decades of work on many senders sharing limited links", "A mature field: many proven routing and scheduling algorithms", "We are CS students: we know these algorithms and their assumptions"];
  why.forEach((t, i) => {
    const y = 2.05 + i * 1.0;
    numCircle(slide, 6.95, y + 0.15, i + 1);
    slide.addText(t, { x: 7.6, y, w: 5.15, h: 0.8, fontSize: 16, color: C.text1, valign: "middle", margin: 0, isTextBox: true });
  });
  card(slide, M, 5.3, 12.1, 1.45, C.text2);
  slide.addText([{ text: "Hypothesis  ", options: { bold: true, color: C.accent1 } }, { text: "Borrow routing and scheduling methods from computer networks, and the fleet may finish more orders. Which kind helps must be tested.", options: { color: C.background1 } }], { x: M + 0.35, y: 5.3, w: 11.4, h: 1.45, fontSize: 18, valign: "middle", margin: 0, isTextBox: true });
}

// ---------- 7 model ----------
{
  const s = S(7); const slide = content(s);
  addImg(slide, "map", M, 1.4, 7.6, 4.3, "left");
  caption(slide, "3,646 cells → 16 rooms (nodes) and 31 doors (links); door 6 is a cut", M, 5.85, 7.4);
  const rows = [["Assignment center", "sender"], ["Robot", "packet"], ["Door", "half-duplex link"], ["Within 8 steps of a door", "router port"]];
  rows.forEach(([a, b], i) => {
    const y = 1.5 + i * 0.72;
    slide.addText([{ text: a, options: { bold: true, color: C.text2 } }, { text: "  =  " + b, options: { color: C.text1 } }], { x: 8.5, y, w: 4.3, h: 0.6, fontSize: 15, valign: "middle", margin: 0, isTextBox: true });
  });
  card(slide, 8.5, 4.55, 4.25, 2.2, C.accent6);
  slide.addText("30% of waiting", { x: 8.75, y: 4.7, w: 3.9, h: 0.65, fontSize: 28, bold: true, color: C.accent2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  slide.addText("sits on the door cell and 2 steps around it: 10% of the area. So the router goes at the door.", { x: 8.75, y: 5.35, w: 3.85, h: 1.3, fontSize: 14, color: C.text1, margin: 0, isTextBox: true, valign: "top" });
}

// ---------- 8 differences ----------
{
  const s = S(8); const slide = content(s);
  addImg(slide, "mapping", M, 1.4, 6.6, 4.6, "left");
  const diffs = [["Cannot be dropped", "robots wait; packets can be dropped"], ["Waiting blocks a cell", "a queued robot may block the other side"], ["Fixed fleet", "robots stay on the map after delivery"], ["No retransmission", "1986 collapse: resends. Here: face-to-face jams"]];
  diffs.forEach(([a, b], i) => {
    const y = 1.45 + i * 1.18;
    card(slide, 7.45, y, 5.3, 1.0, C.background2);
    numCircle(slide, 7.6, y + 0.25, i + 1, 0.5, C.accent3);
    slide.addText(a, { x: 8.25, y: y + 0.08, w: 4.4, h: 0.42, fontSize: 16, bold: true, color: C.text2, margin: 0, isTextBox: true });
    slide.addText(b, { x: 8.25, y: y + 0.5, w: 4.4, h: 0.42, fontSize: 13, color: C.text1, margin: 0, isTextBox: true });
  });
  caption(slide, "Closer to a lossless data-center network: no drops, only pauses, and deadlock is possible", M, 6.35, 12.1);
}

// ---------- 9 routing or scheduling ----------
{
  const s = S(9); const slide = content(s);
  const steps = [
    ["Lower-left share", "906 ÷ 3,614 = 0.2507"],
    ["Orders that must cross door 6", "2 × 0.2507 × 0.7493 = 37.6%  (task file: 38.5%)"],
    ["Ceiling", "26 ÷ 0.376 = 69.1 orders per 500 ticks"],
  ];
  steps.forEach(([a, b], i) => {
    const y = 1.5 + i * 1.05;
    numCircle(slide, M, y + 0.1, i + 1);
    slide.addText(a, { x: M + 0.7, y, w: 5.6, h: 0.4, fontSize: 16, bold: true, color: C.text2, margin: 0, isTextBox: true });
    slide.addText(b, { x: M + 0.7, y: y + 0.42, w: 5.6, h: 0.45, fontSize: 15, color: C.text1, margin: 0, isTextBox: true });
  });
  addImg(slide, "bound", 7.0, 1.4, 5.75, 2.6);
  card(slide, M, 4.85, 12.1, 1.9, C.background2);
  slide.addText("11", { x: M + 0.3, y: 5.0, w: 1.4, h: 0.9, fontSize: 48, bold: true, color: C.accent3, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  slide.addText("rerouting methods tried later; all were worse. Only door 6 sets the ceiling, so the question is how many robots to send and which side goes first: scheduling.", { x: M + 1.8, y: 5.0, w: 10.0, h: 1.6, fontSize: 17, color: C.text1, valign: "middle", margin: 0, isTextBox: true });
}

// ---------- 10 quota ----------
{
  const s = S(10); const slide = content(s);
  addImg(slide, "knee", M, 1.35, 7.6, 4.2, "left");
  caption(slide, "Red: no door control. Blue: with the quota. Each dot is one 500-tick window.", M, 5.65, 7.5);
  card(slide, 8.45, 1.45, 4.3, 2.35, C.accent6);
  slide.addText([{ text: "15", options: { fontSize: 44, bold: true, color: C.accent2, fontFace: THEME.headFontFace } }, { text: " in   ", options: { fontSize: 18, color: C.text1 } }, { text: "10", options: { fontSize: 44, bold: true, color: C.accent2, fontFace: THEME.headFontFace } }, { text: " out", options: { fontSize: 18, color: C.text1 } }], { x: 8.7, y: 1.55, w: 3.9, h: 1.0, margin: 0, isTextBox: true, valign: "middle" });
  slide.addText("2.23 × 247 ÷ 500 × 13 = 14.3 → 15\n2.23 × 158 ÷ 500 × 13 = 9.2 → 10", { x: 8.7, y: 2.6, w: 3.95, h: 1.0, fontSize: 14, color: C.text1, margin: 0, isTextBox: true });
  body(slide, ["Count robots that hold a door-6 order but have not crossed, even far away", "Quota full: assign an order that does not cross", "Unlike TCP: nothing dropped, quota fixed"], 8.45, 4.1, 4.3, 2.7, 15);
}

// ---------- 11 door rule ----------
{
  const s = S(11); const slide = content(s);
  addImg(slide, "door", M, 1.3, 12.1, 3.7);
  const stats = [["43%", "door busy if it switches after every robot (9 ÷ 21)"], ["88%", "door busy with batches of 10 (90 ÷ 102)"], ["4 cells", "the other side backs out to keep the exit clear"]];
  stats.forEach(([b, l], i) => {
    const x = M + i * 4.1;
    card(slide, x, 5.2, 3.9, 1.6, C.background2);
    slide.addText(b, { x: x + 0.25, y: 5.3, w: 3.5, h: 0.7, fontSize: 32, bold: true, color: i === 2 ? C.accent1 : C.accent2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
    slide.addText(l, { x: x + 0.25, y: 6.0, w: 3.5, h: 0.7, fontSize: 14, color: C.text1, margin: 0, isTextBox: true, valign: "top" });
  });
}

// ---------- 12 executor + safety nets ----------
{
  const s = S(12); const slide = content(s);
  addImg(slide, "exec", M, 1.35, 6.9, 3.3, "left");
  card(slide, M, 4.85, 6.9, 1.9, C.background2);
  slide.addText([{ text: "22 → 26", options: { fontSize: 32, bold: true, color: C.accent2, fontFace: THEME.headFontFace } }], { x: M + 0.25, y: 4.95, w: 3.0, h: 0.75, margin: 0, isTextBox: true });
  slide.addText("robots per 500 ticks through door 6 after a 3-line executor fix (credit returned on time)", { x: M + 0.25, y: 5.7, w: 6.4, h: 0.9, fontSize: 14, color: C.text1, margin: 0, isTextBox: true, valign: "top" });
  const nets = [
    ["Global cap: 138 robots", "Little's law: 1.76 × 69.2 ÷ 500 × 2.23 × 255 = 138.5 → 138"],
    ["Deadlock watchdog: 300 ticks", "Stuck 300 ticks and no entry at its door: may ignore the door rule for one tick. Robots are never dropped."],
  ];
  nets.forEach(([a, b], i) => {
    const y = 1.45 + i * 2.7;
    card(slide, 7.8, y, 4.95, 2.45, C.accent6);
    slide.addText("Safety net " + (i + 1), { x: 8.05, y: y + 0.15, w: 4.5, h: 0.35, fontSize: 12, bold: true, color: C.accent1, margin: 0, isTextBox: true });
    slide.addText(a, { x: 8.05, y: y + 0.5, w: 4.5, h: 0.5, fontSize: 19, bold: true, color: C.text2, margin: 0, isTextBox: true });
    slide.addText(b, { x: 8.05, y: y + 1.05, w: 4.5, h: 1.3, fontSize: 14, color: C.text1, margin: 0, isTextBox: true, valign: "top" });
  });
}

// ---------- 13 results ----------
{
  const s = S(13); const slide = content(s);
  const st = [["+140.5%", "vs official starter program"], ["+76.5%", "vs same assignment + fixed executor (fairest)"], ["618 → 1,106", "orders per run, 250 robots"]];
  st.forEach(([b, l], i) => stat(slide, M, 1.45 + i * 1.7, 3.6, b, l, i === 1 ? C.accent3 : C.accent2, 36));
  addImg(slide, "ladder", 4.5, 1.35, 8.25, 5.0);
  caption(slide, "Official room map, 20 runs per bar. All 8 official instances: +113.6% vs starter.", 4.6, 6.5, 8.1);
}

// ---------- 14 what matters ----------
{
  const s = S(14); const slide = content(s);
  addImg(slide, "abl", M, 1.35, 8.2, 3.5, "left");
  caption(slide, "Re-test on the official map: 600 runs", M, 4.95, 8);
  const st = [["+86.9%", "on 8 generated maps with random doors (640 runs); wins on every map"], ["−16.9%", "on one generated map if the global cap is removed: keep the safety nets"]];
  st.forEach(([b, l], i) => {
    const y = 1.45 + i * 2.6;
    card(slide, 9.05, y, 3.7, 2.35, C.background2);
    slide.addText(b, { x: 9.3, y: y + 0.15, w: 3.3, h: 0.8, fontSize: 36, bold: true, color: i ? C.accent3 : C.accent2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
    slide.addText(l, { x: 9.3, y: y + 1.0, w: 3.3, h: 1.25, fontSize: 14, color: C.text1, margin: 0, isTextBox: true, valign: "top" });
  });
  card(slide, M, 5.45, 8.2, 1.3, C.accent6);
  slide.addText([{ text: "Quota ", options: { bold: true, color: C.text2 } }, { text: "controls how many robots come.  ", options: { color: C.text1 } }, { text: "Door rule ", options: { bold: true, color: C.text2 } }, { text: "controls how they pass. Each alone ≈ +29%; together +76%.", options: { color: C.text1 } }], { x: M + 0.3, y: 5.45, w: 7.7, h: 1.3, fontSize: 16, valign: "middle", margin: 0, isTextBox: true });
}

// ---------- 15 failures ----------
{
  const s = S(15); const slide = content(s);
  addImg(slide, "funnel", M, 1.3, 12.1, 3.3);
  const les = [["Assumptions break", "robots cannot be dropped and occupy cells"], ["Door 6 sets throughput", "every rerouting method lost"], ["Confirm on new maps", "development gains often shrink"]];
  les.forEach(([a, b], i) => {
    const x = M + i * 4.1;
    card(slide, x, 4.95, 3.9, 1.8, C.background2);
    numCircle(slide, x + 0.2, 5.12, i + 1, 0.45, C.accent3);
    slide.addText(a, { x: x + 0.8, y: 5.1, w: 3.0, h: 0.5, fontSize: 16, bold: true, color: C.text2, margin: 0, isTextBox: true, valign: "middle" });
    slide.addText(b, { x: x + 0.25, y: 5.75, w: 3.5, h: 0.85, fontSize: 14, color: C.text1, margin: 0, isTextBox: true, valign: "top" });
  });
}

// ---------- 16 conclusion ----------
{
  const s = S(16);
  const slide = pres.addSlide({ masterName: "DARK", sectionTitle: "Speaker 4" });
  slide.addText(s.title, { placeholder: "title" });
  const pts = [
    ["Control the count, not each robot", "how many robots head for a door, and which side it serves"],
    ["Hypothesis half right", "routing did not transfer; scheduling did"],
    ["In a real warehouse", "a quota per direction at assignment time; one direction at a time in the aisle"],
    ["Limits", "simulation only; re-measure parameters for a new layout"],
  ];
  pts.forEach(([a, b], i) => {
    const y = 3.0 + i * 0.95;
    numCircle(slide, M, y + 0.05, i + 1, 0.5, C.accent1);
    slide.addText([{ text: a + "   ", options: { bold: true, color: C.background1 } }, { text: b, options: { color: C.accent5 } }], { x: M + 0.75, y, w: 11.4, h: 0.6, fontSize: 17, valign: "middle", margin: 0, isTextBox: true });
  });
  slide.addText("Thank you", { x: 9.6, y: 6.55, w: 3.1, h: 0.6, fontSize: 22, bold: true, color: C.accent1, align: "right", margin: 0, isTextBox: true });
  notes(slide, s);
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
