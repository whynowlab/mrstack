// ~/claude-telegram/scrapers/threads/briefing.js
// Reads scraper output → sends Telegram briefing
import { readFileSync } from "fs";

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const CHAT_ID = process.env.NOTIFICATION_CHAT_IDS;

function formatBriefing(posts) {
  const grouped = {};
  const labels = {
    "model-release": "🚀 모델/도구 출시",
    tool: "🔧 AI 도구",
    tip: "💡 팁/워크플로우",
    news: "📰 뉴스/트렌드",
    research: "📄 연구/논문",
    opinion: "💬 의견/토론",
    general: "📌 기타 AI",
  };

  for (const post of posts) {
    const cat = post.category || "general";
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(post);
  }

  let msg = `📋 *AI 브리핑* (${new Date().toLocaleDateString("ko-KR")})\n\n`;

  for (const [cat, label] of Object.entries(labels)) {
    const items = grouped[cat];
    if (!items || items.length === 0) continue;
    msg += `*${label}* (${items.length}건)\n`;
    for (const item of items.slice(0, 5)) {
      const summary = item.text.substring(0, 100).replace(/\n/g, " ");
      msg += `• ${item.author}: ${summary}...\n`;
    }
    msg += "\n";
  }

  msg += `총 ${posts.length}건 수집`;
  return msg;
}

async function sendTelegram(message) {
  const url = `https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: CHAT_ID,
      text: message,
      parse_mode: "Markdown",
    }),
  });
  return res.json();
}

// Main
const inputFile = process.argv[2];
if (!inputFile) {
  console.error("Usage: node briefing.js <scraper-output.json>");
  process.exit(1);
}

const posts = JSON.parse(readFileSync(inputFile, "utf-8"));
const message = formatBriefing(posts);
console.log(message);

if (BOT_TOKEN && CHAT_ID) {
  const result = await sendTelegram(message);
  console.log("Telegram sent:", result.ok);
}
