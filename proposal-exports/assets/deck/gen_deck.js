// gen_deck.js — proposal-exports 的页片起手模板（pptxgenjs）
//
// 用法：
//   1) npm i pptxgenjs（一次）
//   2) python ../scripts/formula_png.py formulas.example.json --out formulas
//   3) node gen_deck.js --out deck.pptx
//
// 约定（见 references/ppt-deck.md、design-notes/deck-aesthetics.md）：
//   - 画布 13.333x7.5in；安全边距 0.5in；中文字体 Microsoft YaHei（单字体族）；
//   - 字号只有四档：54 只给封面主标与唯一的数字，33 页标题，18 正文/要点/表格，
//     12 图注·来源·页码·元信息；不再出现 22/30/40 这类中间档；
//   - 一底一墨一强调：正文用 INK，MUTED 只给图注/页码；AMBER 每页最多两处；
//   - 面用色阶（TINT）分层，不画细线框、不用渐变与阴影；
//   - 每页 addNotes 写口播，deck_check.py 会查备注；字号/强调色/渐变也由它查。
//
// 改内容只改下面「内容区」；版式函数与令牌不要每页临时改。

const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

const HERE = __dirname;
const sizesPath = path.join(HERE, "formulas", "sizes.json");
const sizes = fs.existsSync(sizesPath) ? JSON.parse(fs.readFileSync(sizesPath, "utf8")) : {};

const NAVY = "1E2761", ICE = "CADCFC", AMBER = "E8A33D";
const INK = "1F2937", MUTED = "6B7A90", TINT = "F4F7FC";
const CN_TITLE = "SimHei";   // 标题：黑体（project note-论文撰写-字体）
const CN_BODY = "SimSun";    // 正文：宋体
const W = 13.333, H = 7.5, MARGIN = 0.5;

// 四档字号：只改这里，不在页面里写裸数字
const T = { display: 54, title: 33, body: 18, small: 12 };

const FORMULA_SCALE = 2.5 / 400;   // 公式 PNG 是 400dpi，放到页面上放大 2.5 倍
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
    fontFace: CN_BODY, fontSize: T.small, color: MUTED, align: "right", margin: 0,
  });
}

// 页标题：写结论，不写话题；占两行以内
function slideTitle(slide, text) {
  slide.addText(text, { x: 0.78, y: 0.72, w: W - 1.56, h: 0.9, fontFace: CN_TITLE,
                        fontSize: T.title, bold: true, color: NAVY, margin: 0,
                        lineSpacingMultiple: 1.15 });
}

// 封面：色块底 + 一句结论；不用装饰形状与小标签
function cover(title, subtitle, tail) {
  const s = pres.addSlide();
  s.background = { color: NAVY };
  s.addText(title, { x: 0.85, y: 2.05, w: 9.6, h: 1.9, fontFace: CN_TITLE, fontSize: T.display,
                     bold: true, color: "FFFFFF", margin: 0, lineSpacingMultiple: 1.05 });
  s.addText(subtitle, { x: 0.88, y: 3.55, w: 8.6, h: 0.5, fontFace: CN_BODY, fontSize: T.body,
                        color: ICE, margin: 0 });
  s.addText(tail, { x: 0.88, y: 4.15, w: 8.3, h: 0.4, fontFace: CN_BODY, fontSize: T.small,
                    color: ICE, margin: 0 });
  s.addText("汇报人：________　　日期：________", {
    x: 0.88, y: 6.6, w: 8, h: 0.35, fontFace: CN_BODY, fontSize: T.small, color: ICE, margin: 0,
  });
  s.addNotes("封面口播：一句话说明这次汇报要解决什么问题、给出什么结论。");
  return s;
}

// 要点 + 公式卡片（左文右式）
function bulletsFormula(title, items, formulas) {
  const s = pres.addSlide();
  s.background = { color: "FFFFFF" };
  slideTitle(s, title);

  const runs = [];
  items.forEach(([lead, body]) => {
    runs.push({ text: lead, options: { bold: true, color: NAVY, bullet: { code: "25CF" } } });
    runs.push({ text: body, options: { breakLine: true, paraSpaceAfter: 18 } });
  });
  s.addText(runs, { x: 0.78, y: 1.9, w: 5.55, h: 3.2, fontFace: CN_BODY, fontSize: T.body,
                    color: INK, lineSpacingMultiple: 1.4, margin: 0 });


  const boxes = formulas.map((name) => ({ name, ...formulaBox(name) }));
  const totalH = boxes.reduce((sum, box) => sum + box.h, 0) + 0.3 * (boxes.length - 1);
  const cardH = Math.min(4.4, totalH + 1.0);
  s.addShape(pres.ShapeType.rect, {
    x: 6.5, y: 1.9, w: 6.2, h: cardH, fill: { color: TINT }, line: { color: TINT },
  });
  let y = 1.9 + (cardH - totalH) / 2;
  boxes.forEach((box) => {
    const x = 6.5 + (6.2 - box.w) / 2;          // 卡片内水平居中
    s.addImage({ path: path.join(HERE, "formulas", `${box.name}.png`), x, y, w: box.w, h: box.h });
    y += box.h + 0.3;
  });
  s.addNotes("本页口播：先讲结论，再指公式里的哪一项对应结论（≤120 字）。");
  return s;
}

// 原生表格 + 右侧一个大数（大数是全页唯一强调色）
function tableSlide(title, rows, big) {
  const s = pres.addSlide();
  s.background = { color: "FFFFFF" };
  slideTitle(s, title);

  const head = (t) => ({ text: t, options: { bold: true, color: "FFFFFF",
                                             fill: { color: NAVY }, fontSize: T.body } });
  const cell = (t, opt = {}) => ({ text: t, options: { color: INK, fontSize: T.body, ...opt } });
  const table = [[head(rows[0][0]), head(rows[0][1]), head(rows[0][2])]];
  rows.slice(1).forEach((r) => table.push([cell(r[0]), cell(r[1], { align: "center" }), cell(r[2])]));

  s.addTable(table, {
    x: 0.78, y: 2.05, w: 7.55, colW: [2.72, 1.55, 3.28], rowH: 0.75,
    fontFace: CN_BODY, valign: "middle", margin: 0.1,
    fill: { color: "FFFFFF" },
  });

  s.addText(big.value, { x: 8.85, y: 2.05, w: 3.4, h: 1.2, fontFace: CN_TITLE, fontSize: T.display,
                         bold: true, color: AMBER, margin: 0 });
  s.addText(big.label, { x: 8.85, y: 3.25, w: 3.9, h: 0.35, fontFace: CN_BODY, fontSize: T.small,
                         color: MUTED, margin: 0 });
  s.addText(big.note, { x: 8.85, y: 3.75, w: 3.9, h: 1.7, fontFace: CN_BODY, fontSize: T.body,
                        color: INK, lineSpacingMultiple: 1.4, margin: 0 });
  s.addNotes("本页口播：表格只讲关键一行，大数字解释它为什么重要。");
  return s;
}

// 大图（55–75% 面积）+ 右侧窄解读栏 + 图注贴在图边上
function figureSlide(title, imagePath, bullets, caption) {
  const s = pres.addSlide();
  s.background = { color: "FFFFFF" };
  slideTitle(s, title);

  s.addImage({ path: imagePath, x: 0.78, y: 1.9, w: 7.85, h: 4.42 });

  const runs = [];
  bullets.forEach(([lead, body]) => {
    runs.push({ text: lead, options: { bold: true, color: NAVY, bullet: { code: "25CF" } } });
    runs.push({ text: body, options: { breakLine: true, paraSpaceAfter: 18 } });
  });
  s.addText(runs, { x: 8.85, y: 1.9, w: 3.9, h: 3.6, fontFace: CN_BODY, fontSize: T.body,
                    color: INK, lineSpacingMultiple: 1.4, margin: 0 });
  s.addText(caption, { x: 8.85, y: 5.5, w: 3.9, h: 0.8, fontFace: CN_BODY, fontSize: T.small,
                       color: MUTED, margin: 0 });
  s.addNotes("本页口播：先读图的高低，再指一条最关键的对比，最后说限制（≤120 字）。");
  return s;
}

// 收尾：三条结论（结论行是深底上唯一的强调色）
function closing(title, lines, next) {
  const s = pres.addSlide();
  s.background = { color: NAVY };
  s.addText(title, { x: 0.85, y: 0.9, w: 10.6, h: 0.9, fontFace: CN_TITLE, fontSize: T.title,
                     bold: true, color: "FFFFFF", margin: 0, lineSpacingMultiple: 1.15 });
  const runs = [];
  lines.forEach(([a, b]) => {
    runs.push({ text: a, options: { bullet: { code: "25CF" } } });
    runs.push({ text: b, options: { bold: true, color: "FFFFFF", breakLine: true, paraSpaceAfter: 20 } });
  });
  s.addText(runs, { x: 0.85, y: 2.1, w: 10.6, h: 2.8, fontFace: CN_BODY, fontSize: T.body,
                    color: ICE, lineSpacingMultiple: 1.5, margin: 0 });
  s.addText(next, { x: 0.85, y: 5.1, w: 9.4, h: 0.4, fontFace: CN_BODY, fontSize: T.small,
                    color: ICE, margin: 0 });
  s.addText("谢谢", { x: 0.85, y: 6.35, w: 4, h: 0.6, fontFace: CN_TITLE, fontSize: T.title,
                      bold: true, color: AMBER, margin: 0 });
  s.addNotes("收尾口播：复述三条结论，指出下一步工作。");
  return s;
}

// ---------------- 内容区（改这里） ----------------
const total = 5;
cover(
  "组网调度把可用率做到 96%",
  "8 站、100 ms 约束 · 同场景 500 次蒙特卡洛",
  "求解 5 ms；遮挡 30% 时增益 18 个百分点",
);
bulletsFormula(
  "单站遮挡时可用率只有 78%",
  [
    ["现状", "：遮挡时可用率仅 78%。"],
    ["机理", "：站簇与频段独立选择，遮挡后无替补。"],
    ["判断", "：仅增加站数无法恢复可用率。"],
  ],
  ["eq_obj", "eq_budget"],
);
tableSlide(
  "联合分配把可用率做到 96%",
  [
    ["路线", "可用率", "代价"],
    ["随机调度（基线）", "78%", "12 ms / 8 站"],
    ["贪心站簇", "88%", "11 ms / 8 站"],
    ["本文联合分配", "96%", "5 ms / 8 站"],
  ],
  {
    value: "+18",
    label: "可用率提升（百分点，相对基线）",
    note: "口径：8 站、100 ms\n遮挡 30%，500 次\n考核：外场试验",
  },
);
figureSlide(
  "遮挡 40% 时增益收窄至 11 个百分点",
  path.join(HERE, "figs", "availability.png"),
  [
    ["30% 遮挡", "：96%，较基线高 18 个百分点。"],
    ["40% 遮挡", "：89%，增益收窄至 11 个百分点。"],
    ["50% 遮挡", "：81%，需增设第 9 站。"],
  ],
  "图注：同场景 500 次；误差线为 95% 置信区间。",
);
closing(
  "遮挡超过 40% 时需增设第 9 站",
  [
    ["达到：", "8 站、100 ms 下 96% 可用率。"],
    ["未达到：", "50% 遮挡时 81%，低于 90% 目标。"],
    ["下一步：", "补充外场数据，评估第 9 站代价。"],
  ],
  "下一步：外场 3 个场景，6 月底前完成",
);

const outArg = process.argv.indexOf("--out");
const outFile = path.resolve(outArg > 0 ? process.argv[outArg + 1] : "deck.pptx");
fs.mkdirSync(path.dirname(outFile), { recursive: true });
pres.writeFile({ fileName: outFile }).then((f) => console.log("written:", f));
