// ~/claude-telegram/scrapers/threads/scraper.js
import { chromium } from "playwright";
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const CONFIG = JSON.parse(readFileSync(join(__dirname, "config.json"), "utf-8"));

const COOKIE_PATH = join(__dirname, "..", "..", "session", "threads-cookies.json");
const OUTPUT_PATH = join(__dirname, "output");

class ThreadsScraper {
  constructor() {
    this.browser = null;
    this.page = null;
  }

  async init() {
    this.browser = await chromium.launch({ headless: true });
    const context = await this.browser.newContext({
      userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
      viewport: { width: 1280, height: 900 },
    });

    // Load cookies if available
    if (existsSync(COOKIE_PATH)) {
      const cookies = JSON.parse(readFileSync(COOKIE_PATH, "utf-8"));
      await context.addCookies(cookies);
    }

    this.page = await context.newPage();
  }

  async login() {
    await this.page.goto("https://www.threads.com/");
    await this.page.waitForTimeout(3000);

    // Check if logged in
    const isLoggedIn = await this.page.evaluate(() => {
      return document.querySelector('[aria-label="Home"]') !== null ||
             document.querySelector('[aria-label="홈"]') !== null;
    });

    if (!isLoggedIn) {
      console.log("NOT LOGGED IN - Manual login required");
      console.log("Run with --login flag for interactive login");
      return false;
    }

    // Save cookies for next time
    const cookies = await this.page.context().cookies();
    mkdirSync(dirname(COOKIE_PATH), { recursive: true });
    writeFileSync(COOKIE_PATH, JSON.stringify(cookies, null, 2));
    console.log("Logged in, cookies saved");
    return true;
  }

  async interactiveLogin() {
    this.browser = await chromium.launch({ headless: false });
    const context = await this.browser.newContext();
    this.page = await context.newPage();

    await this.page.goto("https://www.threads.com/login");
    console.log("Please log in manually in the browser window...");
    console.log("Waiting for login to complete...");

    // Poll until redirected back to threads.com home (SPA doesn't fire clean load events)
    const deadline = Date.now() + 120000;
    while (Date.now() < deadline) {
      const url = this.page.url();
      if (url.includes("threads.com") && !url.includes("/login")) {
        console.log("Login detected, saving cookies...");
        break;
      }
      await this.page.waitForTimeout(1000);
    }
    await this.page.waitForTimeout(5000);

    const cookies = await context.cookies();
    mkdirSync(dirname(COOKIE_PATH), { recursive: true });
    writeFileSync(COOKIE_PATH, JSON.stringify(cookies, null, 2));
    console.log(`Cookies saved to ${COOKIE_PATH}`);

    await this.browser.close();
  }

  async scrollAndCollect() {
    const posts = [];

    await this.page.goto("https://www.threads.com/");
    await this.page.waitForTimeout(3000);

    for (let i = 0; i < CONFIG.scrollCount; i++) {
      // Extract visible posts — full text, robust link extraction
      const newPosts = await this.page.evaluate(() => {
        const articles = document.querySelectorAll('[data-pressable-container="true"]');
        return Array.from(articles).map((article) => {
          // Get ALL text content from the post (not truncated)
          const textBlocks = article.querySelectorAll('[dir="auto"]');
          const fullText = Array.from(textBlocks)
            .map((el) => el.innerText?.trim())
            .filter((t) => t && t.length > 5)
            .join("\n");

          // Author: try multiple selectors
          const authorEl = article.querySelector('a[href*="/@"]');
          const authorName = authorEl?.textContent?.trim() || "unknown";
          const authorHref = authorEl?.getAttribute("href") || "";

          // Time
          const timeEl = article.querySelector("time");
          const postTime = timeEl?.getAttribute("datetime") || "";

          // Link: try post link first, then construct from author + time
          const linkEl = article.querySelector('a[href*="/post/"]');
          let postLink = "";
          if (linkEl) {
            const href = linkEl.getAttribute("href");
            postLink = href.startsWith("http") ? href : "https://www.threads.com" + href;
          } else if (authorHref) {
            // Fallback: use author profile link as reference
            postLink = "https://www.threads.com" + authorHref;
          }

          return {
            text: fullText || article.innerText?.trim()?.substring(0, 5000) || "",
            author: authorName,
            authorProfile: authorHref ? "https://www.threads.com" + authorHref : "",
            time: postTime,
            link: postLink,
          };
        });
      });

      for (const post of newPosts) {
        if (!post.text || post.text.length < 10) continue;
        // Deduplicate by link or by text similarity
        const isDupe = posts.some((p) =>
          (post.link && p.link === post.link) ||
          (!post.link && p.text.substring(0, 80) === post.text.substring(0, 80))
        );
        if (!isDupe) posts.push(post);
      }

      // Scroll with random delay (anti-detection)
      await this.page.mouse.wheel(0, 800 + Math.random() * 400);
      const delay = CONFIG.delayMin + Math.random() * (CONFIG.delayMax - CONFIG.delayMin);
      await this.page.waitForTimeout(delay);

      if ((i + 1) % 10 === 0) {
        console.log(`Scrolled ${i + 1}/${CONFIG.scrollCount}, collected ${posts.length} posts`);
      }
    }

    return posts;
  }

  filterAIPosts(posts) {
    const kwLower = CONFIG.aiKeywords.map((k) => k.toLowerCase());
    return posts.filter((post) => {
      const textLower = post.text.toLowerCase();
      return kwLower.some((kw) => textLower.includes(kw));
    });
  }

  categorize(post) {
    const textLower = post.text.toLowerCase();
    for (const [category, keywords] of Object.entries(CONFIG.categories)) {
      if (keywords.some((kw) => textLower.includes(kw.toLowerCase()))) {
        return category;
      }
    }
    return "general";
  }

  async scrape() {
    await this.init();
    const loggedIn = await this.login();
    if (!loggedIn) {
      await this.browser.close();
      return { success: false, error: "Not logged in" };
    }

    console.log("Starting feed scroll...");
    const allPosts = await this.scrollAndCollect();
    console.log(`Total posts collected: ${allPosts.length}`);

    const aiPosts = this.filterAIPosts(allPosts);
    console.log(`AI-related posts: ${aiPosts.length}`);

    const categorized = aiPosts.map((post) => ({
      ...post,
      category: this.categorize(post),
    }));

    // Save output
    mkdirSync(OUTPUT_PATH, { recursive: true });
    const date = new Date().toISOString().split("T")[0];
    const time = new Date().toISOString().split("T")[1].split(":")[0];
    const outFile = join(OUTPUT_PATH, `${date}-${time}.json`);
    writeFileSync(outFile, JSON.stringify(categorized, null, 2));

    await this.browser.close();

    return {
      success: true,
      total: allPosts.length,
      aiRelated: categorized.length,
      file: outFile,
      posts: categorized,
    };
  }

  async close() {
    if (this.browser) await this.browser.close();
  }
}

// CLI entry
const args = process.argv.slice(2);

if (args.includes("--login")) {
  const scraper = new ThreadsScraper();
  await scraper.interactiveLogin();
} else {
  const scraper = new ThreadsScraper();
  const result = await scraper.scrape();
  if (result.success) {
    console.log(`\nDone! ${result.aiRelated} AI posts saved to ${result.file}`);
  } else {
    console.error(`Failed: ${result.error}`);
    console.log("Run: node scraper.js --login");
  }
}
