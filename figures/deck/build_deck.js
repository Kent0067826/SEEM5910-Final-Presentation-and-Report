// Build the 15-minute, 4-speaker deck.
// Run from the repo root:  NODE_PATH=<dir with pptxgenjs> node figures/deck/build_deck.js
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require(process.env.PPTX_SKILL + "/scripts/apply_theme.js");

const ROOT = path.resolve(__dirname, "../..");
const OUT = path.join(ROOT, process.env.DECK_OUT || "SEEM5910_演讲PPT_v14.pptx");
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
    const o = { paraSpaceAfter: 8, breakLine: i < items.length - 1 };
    if (Array.isArray(t)) return t.map((r, j) => ({ text: r.text, options: { ...r.options, ...(j === 0 ? o : {}), breakLine: j === t.length - 1 && i < items.length - 1 } }));
    return [{ text: t, options: o }];
  }).flat();
  slide.addText(runs, { x, y, w, h, fontSize: size, color: C.text1, valign: "top", margin: 0, isTextBox: true });
}
function notes(slide, s) {
  const clean = (t) => t.replace(/\*\*/g, "");
  const hints = s.hints.map((h) => "- " + h).join("\n");
  const body = s.segs.map((g) => `${clean(g.en)}\n中：${clean(g.zh)}`).join("\n\n");
  slide.addNotes(`[Speaker ${s.speaker} · ${s.time}]\n\n提示 / Cues:\n${hints}\n\nScript（英文一段，下面跟中文）:\n\n${body}`);
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

// ---------- 1 title ----------
section(1);
{
  const s = S(1);
  const slide = pres.addSlide({ masterName: "DARK", sectionTitle: "Speaker 1" });
  slide.addText(s.title, { placeholder: "title" });
  slide.addText("SEEM5910 Final Presentation\nLeague of Robot Runners (LoRR) 2026 · official room map", { x: M, y: 4.0, w: 7.3, h: 0.9, fontSize: 18, color: C.accent5, margin: 0, isTextBox: true });
  para(slide, "**Problem:** on a warehouse-like map, plan the robots' moves so that they finish **as many orders as possible**.\n**Approach:** borrow ideas from **computer networks**.", M, 5.05, 7.3, 1.1, 15, C.background1, C.accent1);
  slide.addText("15 minutes", { x: M, y: 6.55, w: 6, h: 0.4, fontSize: 14, color: C.accent1, bold: true, margin: 0, isTextBox: true });
  card(slide, 8.2, 0.75, 4.55, 6.0, C.background1);
  addImg(slide, "bg", 8.3, 0.85, 4.35, 5.8);
  notes(slide, s);
}

// ---------- 2 background ----------
{
  const s = S(2); const slide = content(s);
  addImg(slide, "bg", M, 1.4, 5.6, 5.6, "left");
  const x0 = 6.8;
  bullets(slide, ["Each grey dot is a robot. Robots pick up and deliver orders for **5,000 ticks** (1 tick = 1 time step).", "Score = **how many orders they finish**.", "Blue path: this one order passes **8 doors**."], x0, 1.45, 5.95, 1.55, 14);
  slide.addText("Each tick the program decides", { x: x0, y: 3.05, w: 5.9, h: 0.4, fontSize: 17, bold: true, color: C.text2, margin: 0, isTextBox: true });
  const steps = [["Assign", "who takes which order"], ["Route", "which way to go (cells and doors)"], ["Execute", "move now, or wait?"]];
  steps.forEach(([a, b], i) => {
    const y = 3.55 + i * 0.6;
    numCircle(slide, x0, y, i + 1, 0.45);
    slide.addText([{ text: a + "  ", options: { bold: true, color: C.text2 } }, { text: b, options: { color: C.text1 } }], { x: x0 + 0.65, y, w: 5.2, h: 0.45, fontSize: 15, valign: "middle", margin: 0, isTextBox: true });
  });
  card(slide, x0, 5.45, 5.95, 1.45, C.background2);
  const facts = [["16", "rooms"], ["31", "doors, most 1 cell wide"], ["200–300", "robots"], ["5,000", "ticks per run"]];
  facts.forEach(([b, l], i) => {
    const x = x0 + 0.2 + i * 1.45;
    slide.addText(b, { x, y: 5.55, w: 1.4, h: 0.55, fontSize: 22, bold: true, color: C.accent2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
    slide.addText(l, { x, y: 6.15, w: 1.35, h: 0.65, fontSize: 12, color: C.text1, margin: 0, isTextBox: true, valign: "top" });
  });
}

// ---------- 3 slower ----------
{
  const s = S(3); const slide = content(s);
  card(slide, M, 1.5, 3.4, 5.35, C.accent6);
  slide.addText("127", { x: M + 0.3, y: 1.75, w: 2.8, h: 0.9, fontSize: 54, bold: true, color: C.accent2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  slide.addText("orders per 500 ticks at the start", { x: M + 0.3, y: 2.65, w: 2.9, h: 0.5, fontSize: 14, color: C.text1, margin: 0, isTextBox: true });
  slide.addText("37", { x: M + 0.3, y: 3.35, w: 2.8, h: 0.9, fontSize: 54, bold: true, color: C.accent3, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  slide.addText("at the end of the run", { x: M + 0.3, y: 4.25, w: 2.9, h: 0.5, fontSize: 14, color: C.text1, margin: 0, isTextBox: true });
  para(slide, "2024 champion's way of giving out orders, average of **60 runs**. **No errors, no collisions.**", M + 0.3, 5.0, 2.9, 1.6, 13);
  addImg(slide, "collapse", 4.4, 1.4, 8.35, 3.6);
  caption(slide, "Official room map, 200 / 250 / 300 robots, 20 runs per program", 4.5, 5.0, 8.2);
  bullets(slide, ["We ran two existing programs: the **official starter program** and the **2024 champion's** way of giving out orders.", "**The longer it runs, the slower it gets**: every curve goes down.", "No robot is broken, so **something builds up over time**."], 4.5, 5.45, 8.25, 1.5, 14);
}

// ---------- 4 jam ----------
{
  const s = S(4); const slide = content(s);
  addImg(slide, "jam", M, 1.35, 5.7, 5.75, "left");
  const cards = [
    ["97", "robots at tick 3,000 that still must go through **door 6** into the lower-left rooms: some wait at the door, the rest are on the way.", C.accent3],
    ["38% → 86%", "easy orders are done first, so more and more of the **orders left need door 6**.", C.accent2],
    ["3.4–7.0 vs 26", "robots meet **face to face** in the one-cell door. Per 500 ticks: **3.4–7.0** get through late in the run, **26** when they take turns. **More robots, fewer crossings.**", C.accent2],
  ];
  cards.forEach(([b, l, col], i) => {
    const y = 1.4 + i * 1.85;
    card(slide, 6.9, y, 5.85, 1.7, C.background2);
    slide.addText(b, { x: 7.15, y: y + 0.08, w: 5.4, h: 0.6, fontSize: 30, bold: true, color: col, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
    para(slide, l, 7.15, y + 0.72, 5.45, 0.92, 13);
  });
}

// ---------- 5 prior work ----------
{
  const s = S(5); const slide = content(s);
  const groups = [
    ["Order assignment", "Official starter, 2024 champion, flow-based assignment", "Decides which robot takes which order. Picks close, cheap orders first."],
    ["Route guidance", "Traffic-flow optimisation, guidance graphs", "Makes busy roads cost more, so robots spread out to other roads."],
    ["Planning & collision avoidance", "PIBT, RHCR, WPPL", "Plans each robot's next steps: decides who moves first and avoids collisions."],
    ["Jam handling", "Keep part of the fleet idle; narrow-passage conflicts; AGV deadlock prevention", "Keeps some robots idle, or sorts out robots that meet in a narrow passage."],
  ];
  groups.forEach(([t, ex, how], i) => {
    const x = M + (i % 2) * 6.15, y = 1.4 + Math.floor(i / 2) * 2.2;
    card(slide, x, y, 5.95, 2.05, C.background2);
    slide.addText(t, { x: x + 0.25, y: y + 0.15, w: 5.5, h: 0.45, fontSize: 18, bold: true, color: C.text2, margin: 0, isTextBox: true });
    slide.addText(ex, { x: x + 0.25, y: y + 0.62, w: 5.5, h: 0.4, fontSize: 12, italic: true, color: C.accent4, margin: 0, isTextBox: true });
    slide.addText(how, { x: x + 0.25, y: y + 1.08, w: 5.5, h: 0.85, fontSize: 15, color: C.text1, margin: 0, isTextBox: true, valign: "top" });
  });
  card(slide, M, 5.9, 12.1, 0.95, C.accent6);
  slide.addText([{ text: "In the methods we read: ", options: { bold: true, color: C.text2 } }, { text: "each one improves its own step. None looks at the whole system and weighs many factors together.", options: { color: C.text1 } }], { x: M + 0.3, y: 5.9, w: 11.6, h: 0.95, fontSize: 16, valign: "middle", margin: 0, isTextBox: true });
}

// ---------- 6 idea ----------
{
  const s = S(6); const slide = content(s);
  card(slide, M, 1.35, 12.15, 0.75, C.accent6);
  para(slide, "We wanted a **more systematic** approach. One of us has **implemented and optimized traffic scheduling on a global carrier's backbone network**, so we explored from the computer-network angle.", M + 0.25, 1.35, 11.7, 0.75, 14, C.text1, C.text2, "middle");
  slide.addText("It looks like a computer network", { x: M, y: 2.25, w: 5.8, h: 0.4, fontSize: 17, bold: true, color: C.text2, margin: 0, isTextBox: true });
  const like = [["Door", "link: carries only so much"], ["Order through 8 doors", "packet through 8 routers"], ["More robots, fewer crossings", "network congestion"]];
  like.forEach(([a, b], i) => {
    const y = 2.75 + i * 0.75;
    card(slide, M, y, 5.8, 0.62, C.background2);
    slide.addText([{ text: a, options: { bold: true, color: C.text2 } }, { text: "  →  " + b, options: { color: C.text1 } }], { x: M + 0.25, y, w: 5.4, h: 0.62, fontSize: 15, valign: "middle", margin: 0, isTextBox: true });
  });
  slide.addText("Why computer networks", { x: 6.95, y: 2.25, w: 5.8, h: 0.4, fontSize: 17, bold: true, color: C.text2, margin: 0, isTextBox: true });
  const why = ["**Whole-system view:** decades of work on many senders sharing few links.", "**Proven methods:** routing (which path to take) and scheduling (who goes when).", "**Hands-on experience** with these methods, so we know what they assume."];
  why.forEach((t, i) => {
    const y = 2.75 + i * 0.75;
    numCircle(slide, 6.95, y + 0.08, i + 1, 0.45);
    para(slide, t, 7.55, y, 5.2, 0.65, 14, C.text1, C.text2, "middle");
  });
  card(slide, M, 5.15, 12.1, 1.7, C.text2);
  slide.addText([{ text: "Hypothesis  ", options: { bold: true, color: C.accent1 } }, { text: "Borrowing routing and scheduling methods from computer networks may help the robots finish more orders.", options: { color: C.background1 } }], { x: M + 0.35, y: 5.22, w: 11.4, h: 0.9, fontSize: 18, valign: "middle", margin: 0, isTextBox: true });
  slide.addText("It is only a guess. Which kind helps, routing or scheduling, must be tested: that is the next part.", { x: M + 0.35, y: 6.1, w: 11.4, h: 0.6, fontSize: 15, italic: true, color: C.accent5, valign: "middle", margin: 0, isTextBox: true });
}

// ---------- 7 model ----------
{
  const s = S(7); const slide = content(s);
  addImg(slide, "map", M, 1.4, 7.6, 4.3, "left");
  para(slide, "3,646 cells → **16 rooms (nodes)** and **31 doors (links)**. **Door 6 is a cut**: remove it, and the 4 lower-left rooms are cut off from the rest.", M, 5.85, 7.5, 0.95, 14);
  const rows = [["Giving out orders", "sender", "decides what enters the network"], ["Robot", "packet", "carries one order"], ["Door", "half-duplex link", "one direction at a time"], ["Within 8 steps of a door", "router port", "decides who goes next"]];
  rows.forEach(([a, b, c], i) => {
    const y = 1.4 + i * 0.78;
    slide.addText([{ text: a, options: { bold: true, color: C.text2 } }, { text: "  =  " + b, options: { color: C.text1, bold: true } }, { text: "\n" + c, options: { color: C.accent4, fontSize: 12 } }], { x: 8.5, y, w: 4.3, h: 0.72, fontSize: 15, valign: "top", margin: 0, isTextBox: true });
  });
  card(slide, 8.5, 4.6, 4.25, 2.25, C.accent6);
  slide.addText("Why at the door?", { x: 8.75, y: 4.7, w: 3.9, h: 0.4, fontSize: 15, bold: true, color: C.text2, margin: 0, isTextBox: true });
  para(slide, "Near a door, robots stand still **4.2×** as long as they move. The door cell and 2 steps around it: **10% of the area, 30% of all waiting**. Time is lost at the door, so the router goes there.", 8.75, 5.1, 3.85, 1.7, 13);
}

// ---------- 8 differences ----------
{
  const s = S(8); const slide = content(s);
  addImg(slide, "mapping", M, 1.4, 6.6, 4.6, "left");
  const diffs = [["Cannot be dropped", "a router can drop a packet; a robot can only wait"], ["Waiting blocks a cell", "a queued robot takes space and may block robots coming the other way"], ["Fixed fleet", "robots stay on the map after delivery; nothing leaves"], ["Different cause of jams", "1986 internet collapse: endless resending. Here: robots meet face to face"]];
  diffs.forEach(([a, b], i) => {
    const y = 1.4 + i * 1.2;
    card(slide, 7.45, y, 5.3, 1.08, C.background2);
    numCircle(slide, 7.6, y + 0.28, i + 1, 0.5, C.accent3);
    slide.addText(a, { x: 8.25, y: y + 0.06, w: 4.4, h: 0.4, fontSize: 16, bold: true, color: C.text2, margin: 0, isTextBox: true });
    slide.addText(b, { x: 8.25, y: y + 0.46, w: 4.4, h: 0.58, fontSize: 13, color: C.text1, margin: 0, isTextBox: true, valign: "top" });
  });
  card(slide, M, 6.2, 12.15, 0.7, C.accent6);
  para(slide, "**So:** we skip methods built for resending. Robots are closer to a **lossless data-center network**: no drops, only pauses, and deadlock is possible.", M + 0.25, 6.2, 11.7, 0.7, 14, C.text1, C.text2, "middle");
}

// ---------- 9 routing or scheduling ----------
{
  const s = S(9); const slide = content(s);
  para(slide, "We tried **routing first**. It did not help. The ceiling shows why:", M, 1.4, 6.3, 0.45, 15);
  const steps = [
    ["Lower-left share", "The lower-left rooms hold 906 of 3,614 room cells: 906 ÷ 3,614 = **0.2507**"],
    ["Orders that need door 6", "Two ends on different sides: 2 × 0.2507 × 0.7493 = **37.6%** (task file: 38.5%)"],
    ["Ceiling", "Door 6 passes 26 per 500 ticks: 26 ÷ 0.376 = **69.1 orders per 500 ticks**. A new route cannot raise it."],
  ];
  steps.forEach(([a, b], i) => {
    const y = 1.95 + i * 0.97;
    numCircle(slide, M, y + 0.05, i + 1, 0.45);
    slide.addText(a, { x: M + 0.65, y, w: 5.7, h: 0.35, fontSize: 15, bold: true, color: C.text2, margin: 0, isTextBox: true });
    para(slide, b, M + 0.65, y + 0.35, 5.7, 0.6, 13);
  });
  addImg(slide, "bound", 7.0, 1.4, 5.75, 3.0);
  card(slide, M, 4.95, 12.15, 1.9, C.background2);
  slide.addText("11", { x: M + 0.3, y: 5.1, w: 1.4, h: 0.9, fontSize: 48, bold: true, color: C.accent3, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  para(slide, "rerouting methods tried later: **all were worse**. Only door 6 sets the ceiling, so the real question is **how many robots to send, and which side goes first**. That is **scheduling**.", M + 1.8, 5.05, 10.1, 1.7, 17, C.text1, C.text2, "middle");
}

// ---------- 10 TCP window principle ----------
{
  const s = S(10); const slide = content(s);
  addImg(slide, "tcp", M, 1.35, 6.6, 5.5, "left");
  const x0 = 7.35, w0 = 5.4;
  card(slide, x0, 1.4, w0, 1.15, C.accent6);
  para(slide, "**Question:** how many robots should head for door 6 at the same time?", x0 + 0.25, 1.4, w0 - 0.45, 1.15, 16, C.text1, C.text2, "middle");
  bullets(slide, [
    "**TCP window:** how much data may be sent but not yet confirmed.",
    "**Too little in flight:** the link sometimes sits idle.",
    "**Too much:** no faster; extra data only queues, delay grows.",
    "**Best point:** in flight = **bandwidth × delay**. Google's **BBR** aims right here (next slide).",
    "**Robots are worse than a queue:** extra robots stand in the door area and block the other side, so crossings **fall**.",
    "**So:** cap robots heading for the door at bandwidth × delay.",
  ], x0, 2.75, w0, 4.15, 14);
}

// ---------- 11 BBR ----------
{
  const s = S(11); const slide = content(s);
  addImg(slide, "bbr", M, 1.35, 6.6, 4.55, "left");
  card(slide, M, 6.0, 6.6, 0.9, C.background2);
  para(slide, "**Loss-based TCP** stops growing only when a packet is lost. **Robots are never dropped**, so it would never stop: we measured **211** robots heading for one door.", M + 0.2, 6.0, 6.2, 0.9, 13, C.text1, C.text2, "middle");
  bullets(slide, [
    "**BBR (Google, 2016):** measures the **highest delivery rate** and the **shortest round-trip time**; keeps in flight near their product. **No loss needed**, so it fits robots.",
    "**Use the shortest delay, not the current one:** a jam makes delay longer; following the current delay would let **the jam raise the window**.",
  ], 7.35, 1.4, 5.4, 2.2, 15);
  card(slide, 7.35, 3.7, 5.4, 3.2, C.accent6);
  slide.addText("What we took from BBR", { x: 7.6, y: 3.8, w: 5.0, h: 0.4, fontSize: 16, bold: true, color: C.text2, margin: 0, isTextBox: true });
  bullets(slide, [
    "Quota from **measured** door bandwidth × travel time.",
    "Rounds 50–51: narrow spots our model missed had **2.2–2.9×** the model delay → **BBR-style cap** (max crossing rate × min delay): big losses gone, average only **+0.08%** → kept the fixed quota.",
    "Not copied: BBR's probing cycle and pacing.",
  ], 7.6, 4.3, 5.0, 2.55, 14);
}

// ---------- 12 our quota ----------
{
  const s = S(12); const slide = content(s);
  addImg(slide, "knee", M, 1.35, 7.4, 3.3, "left");
  caption(slide, "Measured: red = no door control, blue = with the quota. Each dot is one 500-tick window.", M, 4.68, 7.4);
  card(slide, M, 5.05, 7.4, 1.85, C.background1);
  addImg(slide, "quota", M + 0.1, 5.1, 7.2, 1.75, "left");
  bullets(slide, [
    "**Count** robots that hold a door-6 order but have not crossed yet, even far away. **Full:** give an order that does not cross.",
    "**Bandwidth:** door 6 passes 26 per 500 ticks → **13 per direction**.",
    "**Delay:** 247 ticks to the door × **2.23** for breakdowns → **15 in**; 158 ticks → **10 out**.",
    "**Result:** no control, 211 head for the door and only **3** cross; quota, about 25 (the knee) and **26** cross.",
    "**Unlike TCP:** nothing dropped, quota fixed. A self-adjusting window (**AIMD**) did worse than the fixed value, so we kept the formula.",
  ], 8.2, 1.4, 4.55, 5.5, 15);
}

// ---------- 13 half-duplex ----------
{
  const s = S(13); const slide = content(s);
  addImg(slide, "door", M, 1.3, 12.1, 3.55);
  const stats = [["Half-duplex", "A one-cell door is a **half-duplex link**: it carries **one direction at a time**."], ["Wind down, switch", "Serve one side. When it is empty, stop letting new robots in, then switch. **No timer.**"], ["4 cells", "**Not from networks:** robots on the other side step back 4 cells to keep the exit clear. A waiting robot blocks the way."]];
  stats.forEach(([b, l], i) => {
    const x = M + i * 4.1;
    card(slide, x, 5.0, 3.9, 1.85, C.background2);
    slide.addText(b, { x: x + 0.25, y: 5.08, w: 3.5, h: 0.55, fontSize: 24, bold: true, color: i === 2 ? C.accent1 : C.accent2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
    para(slide, l, x + 0.25, 5.68, 3.5, 1.1, 13);
  });
}

// ---------- 14 queue scheduling ----------
{
  const s = S(14); const slide = content(s);
  card(slide, M, 1.4, 6.5, 0.95, C.accent6);
  para(slide, "**Door = router port with 2 queues**, one per direction (robots within 8 cells that want to cross). Which queue, and for how long?", M + 0.25, 1.4, 6.05, 0.95, 14, C.text1, C.text2, "middle");
  addImg(slide, "doorf", M, 2.5, 6.5, 2.05);
  const st = [["43%", "**Round-robin**, 1 robot per turn: 9 ÷ 21"], ["88%", "**10 per turn**: 90 ÷ 102"]];
  st.forEach(([b, l], i) => {
    const x = M + i * 3.3;
    card(slide, x, 4.75, 3.15, 2.1, C.background2);
    slide.addText(b, { x: x + 0.25, y: 4.85, w: 2.7, h: 0.75, fontSize: 34, bold: true, color: C.accent2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
    para(slide, l, x + 0.25, 5.65, 2.7, 1.1, 14);
  });
  slide.addText("Queue scheduling at the door", { x: 7.45, y: 1.4, w: 5.3, h: 0.45, fontSize: 18, bold: true, color: C.text2, margin: 0, isTextBox: true });
  bullets(slide, [
    "**Switching is expensive:** same direction every **9 ticks**, change direction **21 ticks**.",
    "**Polling:** serve one queue, then the other.",
    "**Tried:** at most 80 steps per turn → **kept: exhaustive service**, serve a queue **until it is empty**.",
    "**Priority:** robots stopped by the rule drop to the **lowest priority** in the planner, so they never hold up others.",
  ], 7.45, 1.95, 5.3, 3.6, 14);
  card(slide, 7.45, 5.65, 5.3, 1.2, C.accent6);
  para(slide, "**Difference:** polling theory assumes arrivals do not depend on the scheduler. Here they depend on our quota, so the theory is a guide; we tested it.", 7.7, 5.65, 4.85, 1.2, 13, C.text1, C.text2, "middle");
}

// ---------- 15 executor bug fix ----------
{
  const s = S(15); const slide = content(s);
  addImg(slide, "exec", M, 1.35, 8.3, 4.0, "left");
  caption(slide, "Top: official executor (bug). Bottom: fixed executor (3-line patch).", M, 5.4, 8.2);
  card(slide, 9.15, 1.4, 3.6, 2.2, C.accent6);
  slide.addText("22 → 26", { x: 9.4, y: 1.55, w: 3.2, h: 0.8, fontSize: 36, bold: true, color: C.accent2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  slide.addText("robots through door 6 per 500 ticks, before → after the fix", { x: 9.4, y: 2.4, w: 3.2, h: 1.0, fontSize: 14, color: C.text1, margin: 0, isTextBox: true, valign: "top" });
  bullets(slide, ["With both rules, door 6 was still **stuck at 22**.", "**Credit flow control:** a freed slot must be reported **at once**.", "The official executor kept a robot in a cell's queue **after it left**, so the next robot waited a whole round.", "**3 lines** fixed it."], 9.15, 3.8, 3.6, 3.05, 13);
  card(slide, M, 5.85, 8.3, 1.0, C.background2);
  para(slide, "**All three changes so far were tuned on the official map, whose doors never move.** Next: do they still work when the doors move?", M + 0.25, 5.85, 7.85, 1.0, 14, C.text1, C.text2, "middle");
}

// ---------- 16 random-door maps + safety nets ----------
{
  const s = S(16); const slide = content(s);
  addImg(slide, "gen", M, 1.35, 7.6, 3.6, "left");
  card(slide, 8.45, 1.4, 4.3, 3.5, C.background2);
  para(slide, "**Worry:** our changes may only fit the official map and its doors. So we wrote a program that **places doors at random**.", 8.7, 1.5, 3.85, 1.05, 13);
  slide.addText("+86.9%", { x: 8.7, y: 2.55, w: 3.85, h: 0.75, fontSize: 38, bold: true, color: C.accent2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  para(slide, "vs the same base on **8 new room maps** × 199 / 249 robots (**640 runs**): **wins on every map**.", 8.7, 3.35, 3.85, 1.45, 13);
  const nets = [
    ["Safety net 1 · Global cap", "Problem: narrow spots the door rules do not cover. **Little's law:** 1.76 × 69.2 ÷ 500 × 2.23 × 255 = 138.5 → **138** robots hold orders at most (official map). Without it: **−16.9%** on one new map (249 robots)."],
    ["Safety net 2 · Deadlock watchdog", "Problem: rare deadlock, one run fell **1,114 → 700**. Waited **300 ticks** and no entry at its door: skip the door rule for one tick. **Relax the rule, never drop a robot.** No measurable effect on these 8 maps; earlier confirmation: **+2.30%** on 15 generated room-map instances."],
  ];
  nets.forEach(([a, b], i) => {
    const x = M + i * 6.15;
    card(slide, x, 5.05, 5.95, 1.85, C.accent6);
    slide.addText(a, { x: x + 0.25, y: 5.1, w: 5.5, h: 0.4, fontSize: 15, bold: true, color: C.text2, margin: 0, isTextBox: true });
    para(slide, b, x + 0.25, 5.5, 5.5, 1.35, 12);
  });
}

// ---------- 17 results ----------
{
  const s = S(17); const slide = content(s);
  const st = [["+140.5%", "vs official starter program", C.accent2], ["+76.5%", "vs same assignment + fixed executor: only our control differs (fairest)", C.accent3], ["618 → 1,106", "orders per run, 250 robots", C.accent2]];
  st.forEach(([b, l, col], i) => {
    const y = 1.5 + i * 1.65;
    slide.addText(b, { x: M, y, w: 3.7, h: 0.7, fontSize: 34, bold: true, color: col, fontFace: THEME.headFontFace, margin: 0, isTextBox: true, valign: "bottom" });
    slide.addText(l, { x: M, y: y + 0.74, w: 3.7, h: 0.75, fontSize: 14, color: C.text1, margin: 0, isTextBox: true, valign: "top" });
  });
  addImg(slide, "ladder", 4.5, 1.35, 8.25, 4.75);
  para(slide, "Official room map, 3 fleet sizes × **20 runs**. Each group adds one step: starter → champion's assignment → fixed executor → **our control (orange)**.", 4.6, 6.2, 8.1, 0.7, 13, C.accent4, C.text2);
}

// ---------- 18 what matters ----------
{
  const s = S(18); const slide = content(s);
  addImg(slide, "abl", M, 1.35, 12.1, 3.9);
  caption(slide, "Re-test on the official room map: 600 runs, one part removed or added at a time", M, 5.3, 12);
  card(slide, M, 5.7, 12.15, 1.2, C.accent6);
  para(slide, "**Remove one part:** door rule −25.6%, quota −13.6%, executor fix −6.7%.   **Add alone:** door rule +29.7%, quota +29.3%; **together +76.4%**.\n**Quota** decides how many robots come; **door rule** decides how they pass.", M + 0.3, 5.72, 11.6, 1.15, 15, C.text1, C.text2, "middle");
}

// ---------- 19 failures ----------
{
  const s = S(19); const slide = content(s);
  addImg(slide, "funnel", M, 1.3, 12.1, 3.05);
  para(slide, "**69 network mechanisms tried:** 38 dropped after a quick check, 23 failed development tests, 7 not confirmed on new maps, **only 1 passed (the watchdog)**. Every rerouting idea lost.", M, 4.42, 12.1, 0.62, 14);
  const les = [["Assumptions break", "Network methods assume packets can be dropped and take no space; robots cannot be dropped and occupy cells."], ["Door 6 sets the limit", "That is why every rerouting method lost."], ["Confirm on new maps", "Gains on development maps often shrink."]];
  les.forEach(([a, b], i) => {
    const x = M + i * 4.1;
    card(slide, x, 5.15, 3.9, 1.75, C.background2);
    numCircle(slide, x + 0.2, 5.28, i + 1, 0.45, C.accent3);
    slide.addText(a, { x: x + 0.8, y: 5.25, w: 3.0, h: 0.5, fontSize: 16, bold: true, color: C.text2, margin: 0, isTextBox: true, valign: "middle" });
    slide.addText(b, { x: x + 0.25, y: 5.85, w: 3.5, h: 1.0, fontSize: 13, color: C.text1, margin: 0, isTextBox: true, valign: "top" });
  });
}

// ---------- 20 conclusion ----------
{
  const s = S(20);
  const slide = pres.addSlide({ masterName: "DARK", sectionTitle: "Speaker 4" });
  slide.addText(s.title, { placeholder: "title" });
  const pts = [
    ["We did not make each robot smarter", "we controlled how many robots head for a door, and which side goes first"],
    ["Hypothesis half right", "routing: all 11 rerouting methods were worse; scheduling: +76.5% vs the same base on the official room map"],
    ["In a real warehouse", "a quota per direction when giving out orders; one direction at a time in narrow aisles"],
    ["Limits", "simulation only; quotas and timers must be re-measured for a new layout"],
  ];
  pts.forEach(([a, b], i) => {
    const y = 2.95 + i * 0.92;
    numCircle(slide, M, y + 0.1, i + 1, 0.5, C.accent1);
    slide.addText([{ text: a, options: { bold: true, color: C.background1 } }, { text: "\n" + b, options: { color: C.accent5, fontSize: 15 } }], { x: M + 0.75, y, w: 11.6, h: 0.82, fontSize: 17, valign: "top", margin: 0, isTextBox: true });
  });
  slide.addText("Thank you", { x: 9.6, y: 6.75, w: 3.1, h: 0.5, fontSize: 22, bold: true, color: C.accent1, align: "right", margin: 0, isTextBox: true });
  notes(slide, s);
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
