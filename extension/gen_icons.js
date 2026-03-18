/**
 * Run: node gen_icons.js
 * Generates icon16.png, icon48.png, icon128.png in icons/
 */
const fs = require("fs");
const path = require("path");

const dir = path.join(__dirname, "icons");
if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

// Minimal 16x16 blue square PNG (Twitter/X blue #1d9bf0)
const icon16 = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAOklEQVQ4T2NkYGD4z0ABYBw1gGE0DEaDYDQIRoNgNAhGg2A0CEaDYDQIRoNgNAhGg2A0CAYDAwMAANpEAx0Lp0LbAAAAAElFTkSuQmCC",
  "base64"
);
// 48x48 - scale up the 16x16 (simplified: same small PNG, Chrome will scale)
const icon48 = icon16;
const icon128 = icon16;

fs.writeFileSync(path.join(dir, "icon16.png"), icon16);
fs.writeFileSync(path.join(dir, "icon48.png"), icon48);
fs.writeFileSync(path.join(dir, "icon128.png"), icon128);
console.log("Icons generated in icons/");
