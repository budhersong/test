// 크롤링 상태 폴링
async function updateCrawlStatus() {
  const el = document.getElementById("last-crawl-status");
  if (!el) return;
  try {
    const res = await fetch("/crawl/status");
    const data = await res.json();
    const statusMap = { success: "✅ 성공", error: "❌ 오류", running: "⏳ 실행 중", never: "미실행" };
    el.textContent = statusMap[data.status] || data.status;
    if (data.status === "running") {
      setTimeout(updateCrawlStatus, 5000);
    }
  } catch {}
}

document.addEventListener("DOMContentLoaded", updateCrawlStatus);
