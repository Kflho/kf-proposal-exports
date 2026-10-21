// gen_deck.js — proposal-exports 的页片起手模板（pptxgenjs）
//
// 用法：
//   1) npm i pptxgenjs（一次）
//   2) python ../scripts/formula_png.py formulas.example.json --out formulas
//   3) node gen_deck.js --out deck.pptx
//
// 约定（见 references/ppt-deck.md）：
//   画布 13.333x7.5in；安全边距 0.5in；中文字体 Microsoft YaHei；
//   公式用 formula_png.py 出的透明 PNG（尺寸从 formulas/sizes.json 读）；
//   每页写 addNotes（口播），deck_check.py 会查备注。
//
// 改内容只改下面「内容区」；版式函数与令牌不要每页临时改。

const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

const HERE = __dirname;
const sizesPath = path.join(HERE, "formulas", "sizes.json");
const sizes = fs.existsSync(sizesPath) ? JSON.parse(fs.readFileSync(sizesPath, "utf8")) : {};

const NAVY = "1E2761", ICE = "CADCFC", AMBER = "E8A33D";
const INK = "1F2937", MUTED = "6B7A90", TINT = "F4F7FC", AMBER_DARK = "B45309";
const CN = "Microsoft YaHei";
const W = 13.333, H = 7.5, MARGIN = 0.5;

const FORMULA_SCALE = 2.5 / 400;   // 公式 PNG 是 400dpi，放到页面上放大 2.5 倍（约 25pt）
const FORMULA_MAX_W = 5.2;         // 卡片内可用宽度
function formulaBox(name) {
  if (!sizes[name]) return { w: 4, h: 0.6 };
  const [px, py] = sizes[name];
  let w = px * FORMULA_SCALE;
  let h = py * FORMULA_SCALE;
  if (w > FORMULA_MAX_W) {
    h *= FORMULA_MAX_W / w;
    w = FORMULA_MAX_W;
  }
  return { w, h };
}

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "proposal-exports";
pres.title = "示例汇报标题";

function pageNum(slide, n, total) {
  slide.addText(`${n} / ${total}`, {
    x: W - MARGIN - 1.2, y: H - MARGIN - 0.3, w: 1.2, h: 0.3,
    fontFace: CN, fontSize: 10, color: MUTED, align: "right", margin: 0,
  });
}

function eyebrow(slide, text) {
  slide.addText(text, { x: 0.7, y: 0.52, w: 6, h: 0.3, fontFace: CN, fontSize: 11,
                        color: MUTED, charSpacing: 2, margin: 0 });
}

function slideTitle(slide, text) {
  slide.addText(text, { x: 0.68, y: 0.86, w: W - 1.4, h: 0.8, fontFace: CN, fontSize: 30,
                        bold: true, color: NAVY, margin: 0 });
}

// 封面：深底 + 一个母题（这里用圆环，可换成你的）
function cover(title, subtitle, tail) {
  const s = pres.addSlide();
  s.background = { color: NAVY };
  s.addShape(pres.ShapeType.ellipse, {
    x: 9.7, y: 4.0, w: 5.0, h: 5.0, fill: { color: NAVY },
    line: { color: ICE, width: 1.2, transparency: 35 },
  });
  s.addShape(pres.ShapeType.ellipse, {
    x: 11.55, y: 4.62, w: 0.15, h: 0.15, fill: { color: AMBER }, line: { color: AMBER },
  });
  s.addText("PROJECT BRIEFING · 2026", { x: 0.85, y: 1.35, w: 8, h: 0.35, fontFace: CN,
                                         fontSize: 12, color: ICE, charSpacing: 3, margin: 0 });
  s.addText(title, { x: 0.8, y: 1.95, w: 9.3, h: 1.2, fontFace: CN, fontSize: 34,
                     bold: true, color: "FFFFFF", margin: 0 });
  s.addText(subtitle, { x: 0.85, y: 3.35, w: 8.6, h: 0.45, fontFace: CN, fontSize: 18,
                        color: ICE, margin: 0 });
  s.addText(tail, { x: 0.85, y: 4.0, w: 8.3, h: 0.5, fontFace: CN, fontSize: 14,
                    color: "A9BCE0", italic: true, margin: 0 });
  s.addText("汇报人：________　　日期：________", {
    x: 0.85, y: 6.6, w: 8, h: 0.35, fontFace: CN, fontSize: 12, color: ICE, margin: 0,
  });
  s.addNotes("封面口播：一句话说明这次汇报要解决什么问题、给出什么结论。");
  return s;
}

// 要点 + 公式卡片（左文右式）
function bulletsFormula(title, kicker, items, formulas) {
  const s = pres.addSlide();
  s.background = { color: "FFFFFF" };
  eyebrow(s, kicker);
  slideTitle(s, title);

  const runs = [];
  items.forEach(([lead, body]) => {
    runs.push({ text: lead, options: { bold: true, color: NAVY, bullet: { code: "25CF" } } });
    runs.push({ text: body, options: { breakLine: true, paraSpaceAfter: 16 } });
  });
  s.addText(runs, { x: 0.78, y: 2.05, w: 5.6, h: 3.6, fontFace: CN, fontSize: 16,
                    color: INK, lineSpacingMultiple: 1.4, margin: 0 });

  s.addShape(pres.ShapeType.roundRect, {
    x: 6.5, y: 1.8, w: 6.2, h: 4.2, rectRadius: 0.12,
    fill: { color: TINT }, line: { color: TINT },
  });
  const boxes = formulas.map((name) => ({ name, ...formulaBox(name) }));
  const totalH = boxes.reduce((sum, box) => sum + box.h, 0) + 0.3 * (boxes.length - 1);
  let y = Math.max(1.95, 1.8 + (4.2 - totalH) / 2);
  boxes.forEach((box) => {
    const x = 6.5 + (6.2 - box.w) / 2;          // 卡片内水平居中
    s.addImage({ path: path.join(HERE, "formulas", `${box.name}.png`), x, y, w: box.w, h: box.h });
    y += box.h + 0.3;
  });
  s.addNotes("本页口播：先讲结论，再指公式里的哪一项对应结论（≤120 字）。");
  return s;
}

// 原生表格 + 右侧大数字
function tableSlide(title, kicker, rows, big) {
  const s = pres.addSlide();
  s.background = { color: "FFFFFF" };
  eyebrow(s, kicker);
  slideTitle(s, title);

  const head = (t) => ({ text: t, options: { bold: true, color: "FFFFFF",
                                             fill: { color: NAVY }, fontSize: 14 } });
  const cell = (t, opt = {}) => ({ text: t, options: { color: INK, fontSize: 14, ...opt } });
  const table = [[head(rows[0][0]), head(rows[0][1]), head(rows[0][2])]];
  rows.slice(1).forEach((r) => table.push([cell(r[0]), cell(r[1], { align: "center" }), cell(r[2])]));

  s.addTable(table, {
    x: 0.7, y: 1.95, w: 7.6, colW: [2.75, 1.55, 3.3], rowH: 0.72,
    fontFace: CN, valign: "middle", margin: 0.1,
    border: { type: "solid", color: "DCE6F5", pt: 1 }, fill: { color: "FFFFFF" },
  });

  s.addText(big.value, { x: 8.85, y: 1.7, w: 3.0, h: 1.3, fontFace: CN, fontSize: 60,
                         bold: true, color: AMBER, margin: 0 });
  s.addText(big.label, { x: 8.88, y: 3.05, w: 3.9, h: 0.35, fontFace: CN, fontSize: 12,
                         color: MUTED, margin: 0 });
  s.addText(big.note, { x: 8.88, y: 3.6, w: 3.9, h: 1.6, fontFace: CN, fontSize: 13,
                        color: INK, lineSpacingMultiple: 1.5, margin: 0 });
  s.addNotes("本页口播：表格只讲关键一行，大数字解释它为什么重要。");
  return s;
}

// 大图 + 右侧结论（16:9 图按真实比例入槽）
function figureSlide(title, kicker, imagePath, bullets, caption) {
  const s = pres.addSlide();
  s.background = { color: "FFFFFF" };
  eyebrow(s, kicker);
  slideTitle(s, title);

  s.addImage({ path: imagePath, x: 0.7, y: 1.95, w: 7.6, h: 4.275 });

  const runs = [];
  bullets.forEach(([lead, body]) => {
    runs.push({ text: lead, options: { bold: true, color: NAVY, bullet: { code: "25CF" } } });
    runs.push({ text: body, options: { breakLine: true, paraSpaceAfter: 16 } });
  });
  s.addText(runs, { x: 8.45, y: 1.95, w: 4.3, h: 3.6, fontFace: CN, fontSize: 14,
                    color: INK, lineSpacingMultiple: 1.4, margin: 0 });
  s.addText(caption, { x: 8.45, y: 5.75, w: 4.3, h: 0.6, fontFace: CN, fontSize: 10,
                       color: MUTED, margin: 0 });
  s.addNotes("本页口播：先读图的高低，再指一条最关键的对比，最后说限制（≤120 字）。");
  return s;
}

// 收尾：三条结论
function closing(title, lines, next, total) {
  const s = pres.addSlide();
  s.background = { color: NAVY };
  s.addShape(pres.ShapeType.ellipse, {
    x: 10.2, y: 5.2, w: 4.4, h: 4.4, fill: { color: NAVY },
    line: { color: ICE, width: 0.8, transparency: 65 },
  });
  s.addText(title, { x: 0.8, y: 0.9, w: 10.6, h: 0.7, fontFace: CN, fontSize: 28,
                     bold: true, color: "FFFFFF", margin: 0 });
  const runs = [];
  lines.forEach(([a, b]) => {
    runs.push({ text: a, options: { bullet: { code: "25CF" } } });
    runs.push({ text: b, options: { bold: true, color: "FFFFFF", breakLine: true, paraSpaceAfter: 18 } });
  });
  s.addText(runs, { x: 0.85, y: 1.95, w: 10.6, h: 2.6, fontFace: CN, fontSize: 18,
                    color: ICE, lineSpacingMultiple: 1.5, margin: 0 });
  s.addText(next, { x: 0.85, y: 4.75, w: 9.4, h: 0.45, fontFace: CN, fontSize: 14,
                    color: "A9BCE0", italic: true, margin: 0 });
  s.addText("谢谢", { x: 0.85, y: 6.2, w: 4, h: 0.6, fontFace: CN, fontSize: 20,
                      bold: true, color: AMBER, margin: 0 });
  s.addNotes("收尾口播：复述三条结论，指出下一步工作。");
  return s;
}

// ---------------- 内容区（改这里） ----------------
const total = 5;
cover(
  "组网协作调度把可用率提升到 96%",
  "8 站、100 ms 约束下 · 对照实验",
  "证据：同场景 500 次蒙特卡洛，求解 5 ms",
);
bulletsFormula(
  "单站测距遇遮挡就掉点，资源必须联合分配",
  "01 / 问题",
  [
    ["现状", "：单站测距在遮挡时可用率只有 78%。"],
    ["机理", "：站簇和频段分开选，遮挡后没有替补站。"],
    ["判断", "：不联合分配，站数加到 12 个也补不回来。"],
  ],
  ["eq_obj", "eq_budget"],
);
tableSlide(
  "联合分配把可用率做到 96%，求解时间降到 5 ms",
  "02 / 对照",
  [
    ["路线", "可用率", "代价"],
    ["随机调度（基线）", "78%", "12 ms / 8 站"],
    ["贪心站簇", "88%", "11 ms / 8 站"],
    ["本文联合分配", "96%", "5 ms / 8 站"],
  ],
  {
    value: "+18",
    label: "可用率点数（相对基线）",
    note: "口径：8 站、100 ms\n遮挡率 30%，500 次\n（考核环节：外场试验）",
  },
);
figureSlide(
  "遮挡率升到 40% 时仍保持 89%，但增益收窄",
  "03 / 验证",
  path.join(HERE, "figs", "availability.png"),
  [
    ["30% 遮挡", "：96%，比基线高 18 个点。"],
    ["40% 遮挡", "：89%，增益收窄到 11 点。"],
    ["50% 遮挡", "：81%，需要加第 9 站。"],
  ],
  "图注：同场景 500 次；误差线为 95% 置信区间。",
);
closing(
  "方案可用，遮挡率超过 40% 要加站",
  [
    ["达到：", "8 站、100 ms 下 96% 可用率。"],
    ["未达到：", "50% 遮挡时 81%，低于 90% 目标。"],
    ["下一步：", "补外场数据，评估第 9 站代价。"],
  ],
  "下一步：外场 3 个场景，6 月底前完成",
  total,
);

// 每页页码（除封面/收尾也可统一加）
// pres.slides.forEach((s, i) => pageNum(s, i + 1, total));

const outArg = process.argv.indexOf("--out");
const outFile = path.resolve(outArg > 0 ? process.argv[outArg + 1] : "deck.pptx");
fs.mkdirSync(path.dirname(outFile), { recursive: true });
pres.writeFile({ fileName: outFile }).then((f) => console.log("written:", f));
