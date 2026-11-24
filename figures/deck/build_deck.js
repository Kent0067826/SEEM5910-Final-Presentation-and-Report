// Build the 15-minute, 4-speaker deck (21 slides): DoorFlow.
// Run from the repo root:  NODE_PATH=<dir with pptxgenjs> node figures/deck/build_deck.js
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require(process.env.PPTX_SKILL + "/scripts/apply_theme.js");

const ROOT = path.resolve(__dirname, "../..");
const OUT = path.join(ROOT, process.env.DECK_OUT || "SEEM5910_演讲PPT_v21.pptx");
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

// ---------- 1 title ----------
section(1);
{
  const s = S(1);
  const slide = pres.addSlide({ masterName: "DARK", sectionTitle: "Speaker 1" });
  slide.addText(s.title, { placeholder: "title" });
  slide.addText("SEEM5910 Final Presentation\nLeague of Robot Runners (LoRR) 2026 · official room map", { x: M, y: 4.0, w: 7.3, h: 0.9, fontSize: 18, color: C.accent5, margin: 0, isTextBox: true });
  para(slide, "**Problem:** on a warehouse-like map, plan the robots' moves so that they finish **as many orders as possible**.\n**Approach:** a global, door-aware scheduling algorithm.", M, 5.05, 7.3, 1.1, 15, C.background1, C.accent1);
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
  bullets(slide, ["We ran two existing programs: the **official starter program** and the **2024 champion's** way of giving out orders.", "**The longer it runs, the slower it gets**: every curve goes down.", "No errors, so we decided to **start our optimization from this problem**."], 4.5, 5.45, 8.25, 1.5, 14);
}

// ---------- 4 jam ----------
{
  const s = S(4); const slide = content(s);
  addImg(slide, "jam", M, 1.35, 5.7, 5.75, "left");
  const cards = [
    ["1 week", "to write a **monitoring program** that replays the run **tick by tick**.", C.accent2, C.background2],
    ["97", "robots at tick 3,000 still heading through **door 6**: as time goes on, **many robots jam at one door**.", C.accent3, C.background2],
    ["?", "How did **earlier work** try to solve this?", C.accent1, C.accent6],
  ];
  cards.forEach(([b, l, col, fill], i) => {
    const y = 1.4 + i * 1.85;
    card(slide, 6.9, y, 5.85, 1.7, fill);
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
    ["Planning & collision avoidance", "PIBT, RHCR, WPPL", "Plans each robot's next steps: decides who moves first and avoids deadlocks and collisions."],
    ["Jam handling", "Keep part of the fleet idle; narrow-passage conflicts; AGV deadlock prevention", "Keeps some robots idle, or sorts out robots that meet in a narrow passage."],
  ];
  groups.forEach(([t, ex, how], i) => {
    const x = M + (i % 2) * 6.15, y = 1.4 + Math.floor(i / 2) * 2.2;
    card(slide, x, y, 5.95, 2.05, C.background2);
    slide.addText(t, { x: x + 0.25, y: y + 0.15, w: 5.5, h: 0.45, fontSize: 18, bold: true, color: C.text2, margin: 0, isTextBox: true });
    slide.addText(ex, { x: x + 0.25, y: y + 0.62, w: 5.5, h: 0.4, fontSize: 12, italic: true, color: C.accent4, margin: 0, isTextBox: true });
    slide.addText(how, { x: x + 0.25, y: y + 1.08, w: 5.5, h: 0.85, fontSize: 15, color: C.text1, margin: 0, isTextBox: true, valign: "top" });
  });
  card(slide, M, 5.8, 12.1, 1.1, C.accent6);
  para(slide, "**In all the methods we read**, each one fixes one kind of congestion locally. None starts from **the whole system** to avoid congestion **when orders are given out**.\n**Our question:** is there a **global scheduling algorithm** that avoids congestion?", M + 0.3, 5.8, 11.6, 1.1, 15, C.text1, C.text2, "middle");
}


// ---------- 6 everything we tried ----------
{
  const s = S(6); const slide = content(s);
  // [text, key?] ; numbers from report section 9 (both tables)
  const cols = [
    ["Early ideas · dispatch & quotas", [
      ["Early windows & prices: +0.53% on top of the champion"], ["Hungarian matching: −1.9%"], ["Pin broken robots: −2.3%, −4.9%"], ["4× planning compute: −1%"],
      ["Throttle after a jam is seen: −7 to −15 points on room maps", 1], ["20 small tweaks: none reliable"], ["AIMD quota: worse than fixed"],
      ["Quota = physical capacity 49: −17.2% (300 robots)", 1], ["Per-link windows: −1.28%, −1.13%, −4.28%"], ["Quotas for missed cuts: −1.12%, −2.78%"],
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
      ["Auto-bandwidth quotas: never triggered"], ["CoDel, DCTCP, ECN, DCQCN, BwE: skipped"]]],
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
    card(slide, x, 1.3, cw, 5.3, i < 2 ? C.accent6 : C.background2);
    slide.addText(head, { x: x + 0.1, y: 1.38, w: cw - 0.2, h: 0.45, fontSize: 11, bold: true, color: C.text2, margin: 0, isTextBox: true, valign: "top" });
    const runs = items.map(([txt, key], j) => ({ text: txt, options: { color: key ? C.accent3 : C.text1, bold: !!key, breakLine: j < items.length - 1, paraSpaceAfter: 4 } }));
    slide.addText(runs, { x: x + 0.1, y: 1.9, w: cw - 0.18, h: 4.65, fontSize: 9.5, valign: "top", margin: 0, isTextBox: true });
  });
  caption(slide, "Yellow = our early ideas; grey = existing mechanisms we tried later. Red = key attempts. Each result is vs the method at that time, on that round's test set (report, section 9). Skipped = stopped at a quick measurement.", M, 6.68, 12.1);
}

// ---------- 7 congestion monitor ----------
{
  const s = S(7); const slide = content(s);
  addImg(slide, "monitor", M, 1.25, 12.15, 4.72);
  caption(slide, "Congestion monitor at tick 3,000 (congestion_monitor.html). Same map, 250 robots, same seeds (9700 / 101), no door control, one run each; only the routing differs. Red dot = robot holding an order, not moved for 12+ ticks; glowing door = 8+ stuck robots within 5 steps.", M, 6.02, 12.15);
  card(slide, M, 6.55, 12.15, 0.42, C.accent6);
  para(slide, "**Door 6 is jammed 91–94% of the run under all three routings.** Orders finished: champion **609** · HN-SPF **435** · Fortz–Thorup **612**.", M + 0.2, 6.55, 11.8, 0.42, 13, C.text1, C.text2, "middle");
}

// ---------- 8 model + what makes robots special ----------
{
  const s = S(8); const slide = content(s);
  addImg(slide, "map", M, 1.35, 6.6, 3.3, "left");
  para(slide, "3,646 cells → **16 rooms (nodes)** and **31 doors (links)**. **Door 6 is a cut**: remove it, and the 4 lower-left rooms are cut off.", M, 4.72, 6.6, 0.55, 13);
  card(slide, M, 5.3, 6.6, 0.8, C.accent6);
  para(slide, "**Jams form at the doors:** near a door, robots stand still **4.2×** as long as they move; the door cell and 2 steps around it are **10% of the area** but hold **30% of all waiting**.", M + 0.2, 5.3, 6.2, 0.8, 12, C.text1, C.text2, "middle");
  slide.addText("What makes robots special", { x: 7.45, y: 1.35, w: 5.3, h: 0.4, fontSize: 17, bold: true, color: C.text2, margin: 0, isTextBox: true });
  const props = [
    ["Cannot be dropped", "a robot can only wait; it never disappears"],
    ["Waiting takes up a cell", "a robot waiting near a door may block the other side"],
    ["Fixed fleet", "the same robots stay on the map for the whole run"],
    ["Face to face", "jams come from robots meeting in a one-cell door"],
  ];
  props.forEach(([a, b], i) => {
    const y = 1.92 + i * 1.02;
    numCircle(slide, 7.45, y + 0.1, i + 1, 0.45, C.accent3);
    slide.addText(a, { x: 8.08, y, w: 4.67, h: 0.4, fontSize: 15, bold: true, color: C.text2, margin: 0, isTextBox: true });
    slide.addText(b, { x: 8.08, y: y + 0.42, w: 4.67, h: 0.5, fontSize: 13, color: C.text1, margin: 0, isTextBox: true, valign: "top" });
  });
  card(slide, M, 6.22, 12.15, 0.66, C.background2);
  para(slide, "**So a good algorithm** never drops a robot. It only decides **who goes and when**, and keeps the exits clear.", M + 0.25, 6.22, 11.7, 0.66, 15, C.text1, C.text2, "middle");
}

// ---------- 9 routing or scheduling ----------
{
  const s = S(9); const slide = content(s);
  para(slide, "Why did changing routes not help? The ceiling explains it:", M, 1.4, 6.3, 0.45, 15);
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
  para(slide, "rerouting methods: **all were worse**. Only door 6 sets the ceiling, so the real question is **how many robots to send, and which side goes first**: **scheduling**. Our algorithm **DoorFlow** regulates the flow through every door, for the whole map.", M + 1.8, 5.05, 10.1, 1.7, 17, C.text1, C.text2, "middle");
}

// ---------- 10 the logic of TCP's window ----------
{
  const s = S(10); const slide = content(s);
  addImg(slide, "bdp", M, 1.3, 6.9, 5.65, "left");
  const x0 = 7.75, w0 = 5.0;
  card(slide, x0, 1.4, w0, 0.95, C.accent6);
  para(slide, "**Question:** how many robots should head for door 6 at the same time?", x0 + 0.25, 1.4, w0 - 0.45, 0.95, 15, C.text1, C.text2, "middle");
  bullets(slide, [
    "**TCP's window** = data on the way (sent, not yet confirmed).",
    "**Little's law:** on the way = **rate × trip time**.",
    "**Too few:** the door waits; capacity is wasted.",
    "**Too many:** the rate is stuck at **26** per 500 ticks, so extra robots only **queue**.",
    "**Best:** rate × trip time with no queue = the **bandwidth-delay product**, the window TCP aims for.",
    "**Robots are worse than a queue:** waiting robots block the other side, so crossings **fall**.",
    "**So:** our quota = **bandwidth × delay**.",
  ], x0, 2.55, w0, 4.4, 13.5);
}

// ---------- 11 global regulation, like BBR ----------
{
  const s = S(11); const slide = content(s);
  addImg(slide, "bbrloop", M, 1.3, 7.0, 5.65, "left");
  const x0 = 7.85, w0 = 4.9;
  card(slide, x0, 1.4, w0, 1.3, C.accent6);
  para(slide, "**Goal: global regulation.** Control the crossings at every door at once, with a **buffer size** (the quota) for each door and direction.", x0 + 0.2, 1.4, w0 - 0.35, 1.3, 13.5, C.text1, C.text2, "middle");
  bullets(slide, [
    "**Reno / CUBIC:** grow the window until a packet is lost. Robots are never lost, so the queue just grows.",
    "**BBR:** bandwidth = **highest** delivery rate seen; delay = **shortest** round trip seen. A jam cannot raise its own limit.",
    "**Our delay:** real time (Little's law) vs **shortest-path time**. On spots our first model missed: **2.2–2.9×**, so robots were stuck there.",
    "**Tested:** a BBR-style cap on those spots. Big losses gone, but overall only **+0.08%** → kept the fixed quota; stuck robots → watchdog.",
  ], x0, 2.9, w0, 4.05, 13);
}

// ---------- 12 the quota, version by version ----------
{
  const s = S(12); const slide = content(s);
  addImg(slide, "knee", M, 1.35, 7.4, 3.3, "left");
  caption(slide, "Measured: red = no door control, blue = with the quota. Each dot is one 500-tick window.", M, 4.68, 7.4);
  card(slide, M, 5.05, 7.4, 1.85, C.background1);
  addImg(slide, "quota", M + 0.1, 5.1, 7.2, 1.75, "left");
  bullets(slide, [
    "**Count** robots that hold a door-6 order but have not crossed yet, even far away. **Full:** give an order that does not cross.",
    "**v1:** one window for all robots: only **+0.53%**.",
    "**v2:** count **per door and direction**: **+29.1%** alone (17 room-map instances).",
    "**Size:** hand-tuned, 8 was too tight and 32+ jammed → formula **bandwidth × delay**: **15 in, 10 out**, no worse than hand-tuned.",
    "**Result:** no control, 211 head for the door and only **3** cross; with the quota, about 25 (the knee) and **26** cross.",
  ], 8.2, 1.4, 4.55, 5.5, 15);
}

// ---------- 13 one direction at a time ----------
{
  const s = S(13); const slide = content(s);
  addImg(slide, "door", M, 1.3, 12.1, 3.55);
  const cards = [
    ["v1 · no effect", "Only stopped robots from entering against the flow. Robots on the other side still waited at the exit, so robots coming out had nowhere to go.", C.accent4],
    ["v2 · +27.6% alone", "Robots on the other side **step back out of the door area**; robots stopped by the rule get the **lowest priority** (17 room-map instances).", C.accent2],
    ["4 cells, not 3", "Later the door area was set to **4 cells**. With only 3, deadlocked runs rose from **11 to 29**, so we kept 4.", C.accent1],
  ];
  cards.forEach(([b, l, col], i) => {
    const x = M + i * 4.1;
    card(slide, x, 5.0, 3.9, 1.85, C.background2);
    slide.addText(b, { x: x + 0.25, y: 5.08, w: 3.5, h: 0.5, fontSize: 21, bold: true, color: col, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
    para(slide, l, x + 0.25, 5.6, 3.5, 1.2, 12.5);
  });
}

// ---------- 14 queue scheduling at the door ----------
{
  const s = S(14); const slide = content(s);
  card(slide, M, 1.4, 6.5, 0.95, C.accent6);
  para(slide, "**Door = a server with 2 queues**, one per direction (robots within 8 cells that want to cross). Which queue, and for how long?", M + 0.25, 1.4, 6.05, 0.95, 14, C.text1, C.text2, "middle");
  addImg(slide, "doorutil", M, 2.5, 6.5, 2.05);
  const st = [["43%", "**1 robot per turn**: 9 ÷ 21"], ["88%", "**10 per turn**: 90 ÷ 102"]];
  st.forEach(([b, l], i) => {
    const x = M + i * 3.3;
    card(slide, x, 4.75, 3.15, 2.1, C.background2);
    slide.addText(b, { x: x + 0.25, y: 4.85, w: 2.7, h: 0.75, fontSize: 34, bold: true, color: C.accent2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
    para(slide, l, x + 0.25, 5.65, 2.7, 1.1, 14);
  });
  slide.addText("Queue scheduling at the door", { x: 7.45, y: 1.4, w: 5.3, h: 0.45, fontSize: 18, bold: true, color: C.text2, margin: 0, isTextBox: true });
  bullets(slide, [
    "**Switching is expensive:** same direction every **9 ticks**, change direction **21 ticks**.",
    "**Serve in turns (polling):** one queue, then the other.",
    "**v1:** at most 80 steps per turn → wasted switches. **Kept: exhaustive service**, serve a queue **until it is empty**.",
    "**Priority:** robots stopped by the rule drop to the **lowest priority**, so they never hold up others.",
  ], 7.45, 1.95, 5.3, 3.6, 15);
  card(slide, 7.45, 5.65, 5.3, 1.2, C.accent6);
  para(slide, "**Theory vs here:** exhaustive service is best when switching is costly, if arrivals do not depend on the scheduler. Ours depend on the quota, so we tested it.", 7.7, 5.65, 4.85, 1.2, 13, C.text1, C.text2, "middle");
}

// ---------- 15 executor bug fix ----------
{
  const s = S(15); const slide = content(s);
  addImg(slide, "exec", M, 1.35, 8.3, 4.0, "left");
  caption(slide, "Top: official executor (bug). Bottom: fixed executor (3-line patch).", M, 5.4, 8.2);
  card(slide, 9.15, 1.4, 3.6, 2.2, C.accent6);
  slide.addText("22 → 26", { x: 9.4, y: 1.55, w: 3.2, h: 0.8, fontSize: 36, bold: true, color: C.accent2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
  slide.addText("robots through door 6 per 500 ticks, before → after the fix", { x: 9.4, y: 2.4, w: 3.2, h: 1.0, fontSize: 14, color: C.text1, margin: 0, isTextBox: true, valign: "top" });
  bullets(slide, ["With both rules, door 6 was still **stuck at 22**.", "A cell should be free **as soon as** its robot leaves.", "The official executor kept a robot in a cell's queue **after it left**, so the next robot waited a whole round.", "**3 lines** fixed it."], 9.15, 3.8, 3.6, 3.05, 13);
  card(slide, M, 5.85, 8.3, 1.0, C.background2);
  para(slide, "**Found by following robots tick by tick in replays.** Next: the whole algorithm as code, and how we checked that it runs as we meant.", M + 0.25, 5.85, 7.85, 1.0, 14, C.text1, C.text2, "middle");
}

// ---------- 16 pseudocode ----------
{
  const s = S(16); const slide = content(s);
  card(slide, M, 1.35, 9.0, 5.55, "16212B");
  // "~" = safety-net line (grey); text after "#" = comment
  code(slide, [
    ["every planning round:", "1 · who gets an order"],
    ["  L[d,s] ← robots holding an order that still crosses door d in direction s"],
    ["~ free ← GLOBAL_CAP − robots holding orders", "safety net 1"],
    ["  for (robot r, order q) in order of increasing cost:"],
    ["      if L[d,s] < Q[d,s] for every door (d,s) that q crosses"],
    ["~         and free > 0"],
    ["      then give q to r;  L[d,s] += 1 for those doors;  free −= 1"],
    ["      else try r's next-cheapest order"],
    ["  where Q[d,s] = ⌈ 2.23 × T[d,s] ÷ 500 × 13 ⌉", "bandwidth × delay"],
    [""],
    ["every tick, inside the planner (PIBT):", "2 · who moves first"],
    ["  for each door d:"],
    ["      if idle: serve the side with more robots waiting"],
    ["      if no crosser of this side within 8 cells and the other side waits: wind down"],
    ["      once the door and this side's 4-cell zone are empty: switch side"],
    ["  forbid moves into a door against its direction"],
    ["  crossers of the other side within 4 cells may only move away"],
    ["  robots held by these rules get the lowest priority"],
    ["~ watchdog: stuck 300 ticks, and nobody entered its door for 300 ticks"],
    ["~           → ignore the door rule this tick", "safety net 2"],
  ], M + 0.25, 1.55, 8.6, 5.2, 11.5);
  const side = [
    ["1 · Who gets an order", "Before an order is given, check the quota of every door and direction it crosses.", C.accent2],
    ["2 · Who moves first", "Every tick: one direction at a time, the other side steps back, held robots go last.", C.accent1],
    ["Grey · safety nets", "Global cap and deadlock watchdog, added after the random-door test (shown soon).", C.accent4],
  ];
  side.forEach(([a, b, col], i) => {
    const y = 1.35 + i * 1.88;
    card(slide, 9.85, y, 2.9, 1.75, C.background2);
    slide.addText(a, { x: 10.05, y: y + 0.12, w: 2.55, h: 0.4, fontSize: 14, bold: true, color: col, margin: 0, isTextBox: true });
    slide.addText(b, { x: 10.05, y: y + 0.55, w: 2.55, h: 1.1, fontSize: 12.5, color: C.text1, margin: 0, isTextBox: true, valign: "top" });
  });
}

// ---------- 17 the hardest part + demo ----------
{
  const s = S(17); const slide = content(s);
  const cards = [
    ["Rounds 1–8 were void", "A fixed planner seed and an unset variable: the same program, run **54 times**, gave the same result only **5 times**. After the fix, those early gains were not significant."],
    ["A +6.8% that was not real", "One version gained **6.8%**, but its mechanism picked **no door in 32 instances**. The gain came from somewhere else, so we did not keep it."],
    ["Visible only tick by tick", "The executor bug (door 6 stuck at **22**) showed up only when we followed robots tick by tick in replays."],
  ];
  cards.forEach(([a, b], i) => {
    const y = 1.4 + i * 1.62;
    card(slide, M, y, 5.0, 1.5, C.background2);
    slide.addText(a, { x: M + 0.22, y: y + 0.08, w: 4.6, h: 0.4, fontSize: 15, bold: true, color: C.accent3, margin: 0, isTextBox: true });
    para(slide, b, M + 0.22, y + 0.5, 4.6, 0.95, 12);
  });
  addImg(slide, "demo", 5.85, 1.4, 6.9, 4.07);
  para(slide, "**The same congestion monitor, on our own code.** Official room map, 250 robots, one run. Red dot = robot holding an order that has not moved for 12+ ticks; glowing door = jam. Left: no door control, **609** orders. Right: DoorFlow, **1,130** orders.", 5.85, 5.52, 6.9, 0.8, 11.5, C.accent4, C.text2);
  card(slide, M, 6.38, 12.15, 0.55, C.accent6);
  para(slide, "**Our loop:** write the code → run it → replay it → check that the robots do **what the code means**.", M + 0.25, 6.38, 11.7, 0.55, 14, C.text1, C.text2, "middle");
}

// ---------- 18 random-door maps + safety nets ----------
{
  const s = S(18); const slide = content(s);
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

// ---------- 19 results ----------
{
  const s = S(19); const slide = content(s);
  const st = [["+140.5%", "vs official starter program", C.accent2], ["+76.5%", "vs same assignment + fixed executor: only DoorFlow differs (fairest)", C.accent3], ["618 → 1,106", "orders per run, 250 robots", C.accent2]];
  st.forEach(([b, l, col], i) => {
    const y = 1.5 + i * 1.65;
    slide.addText(b, { x: M, y, w: 3.7, h: 0.7, fontSize: 34, bold: true, color: col, fontFace: THEME.headFontFace, margin: 0, isTextBox: true, valign: "bottom" });
    slide.addText(l, { x: M, y: y + 0.74, w: 3.7, h: 0.75, fontSize: 14, color: C.text1, margin: 0, isTextBox: true, valign: "top" });
  });
  addImg(slide, "ladder", 4.5, 1.35, 8.25, 4.75);
  para(slide, "Official room map, 3 fleet sizes × **20 runs**. Each group adds one step: starter → champion's assignment → fixed executor → **DoorFlow (orange)**.", 4.6, 6.2, 8.1, 0.7, 13, C.accent4, C.text2);
}

// ---------- 20 what matters ----------
{
  const s = S(20); const slide = content(s);
  addImg(slide, "ablD", M, 1.35, 12.1, 3.9);
  caption(slide, "Re-test on the official room map: 600 runs, one part removed or added at a time", M, 5.3, 12);
  card(slide, M, 5.7, 12.15, 1.2, C.accent6);
  para(slide, "**Remove one part:** door rule −25.6%, quota −13.6%, executor fix −6.7%.   **Add alone:** door rule +29.7%, quota +29.3%; **together +76.4%**.\n**Quota** decides how many robots come; **door rule** decides how they pass.", M + 0.3, 5.72, 11.6, 1.15, 15, C.text1, C.text2, "middle");
}


// ---------- 21 lessons ----------
{
  const s = S(21); const slide = content(s);
  const L = [
    ["Door 6 cannot be bypassed", "14 of 15 rerouting methods lowered results (HN-SPF −25.88%).", "Control **how many** robots go, not where they go."],
    ["Robots cannot be dropped, and take up cells", "Methods built on dropping or buffering do not carry over.", "Only decide **who goes and when**; keep exits clear."],
    ["Waiting less ≠ crossing more", "Hop-by-hop credit flow cut waiting but lowered results by **2.74%**.", "Judge every change by **orders finished**."],
    ["Gains on a few maps do not count", "7 of 69 passed development but not new maps.", "Confirm on **new seeds and random-door maps**."],
    ["Measure the possible gain first", "38 of 69 stopped at a quick measurement, before any code.", "Write code only where there is **something to gain**."],
  ];
  L.forEach(([h, ev, so], i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = M + col * 4.1 + (row === 1 ? 2.05 : 0), y = 1.4 + row * 2.75;
    card(slide, x, y, 3.9, 2.5, C.background2);
    numCircle(slide, x + 0.2, y + 0.2, i + 1, 0.45, C.accent3);
    slide.addText(h, { x: x + 0.8, y: y + 0.15, w: 2.95, h: 0.6, fontSize: 14.5, bold: true, color: C.text2, margin: 0, isTextBox: true, valign: "middle" });
    para(slide, ev, x + 0.25, y + 0.9, 3.45, 0.75, 12.5);
    card(slide, x + 0.15, y + 1.7, 3.6, 0.65, C.accent6);
    para(slide, "→ " + so, x + 0.3, y + 1.7, 3.35, 0.65, 13, C.text1, C.text2, "middle");
  });
  caption(slide, "From all versions on slide 6; numbers from report, section 9.", M, 6.85, 12.1);
}


// ---------- 22 conclusion ----------
{
  const s = S(22);
  const slide = pres.addSlide({ masterName: "DARK", sectionTitle: "Speaker 4" });
  slide.addText(s.title, { placeholder: "title" });
  const pts = [
    ["DoorFlow does not make each robot smarter", "it controls how many robots head for a door, and which side goes first"],
    ["Routes did not help; scheduling did", "all 11 rerouting methods were worse; DoorFlow: +76.5% vs the same base on the official room map"],
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
