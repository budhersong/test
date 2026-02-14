/* ── 네이버 플레이스 리뷰 분석기 프론트엔드 ── */

let currentData = null;
let chartInstances = {};

/* ───── API 호출 ───── */

async function startAnalysis() {
  const url = document.getElementById("urlInput").value.trim();
  if (!url) {
    showError("네이버 플레이스 URL을 입력해주세요.");
    return;
  }

  showLoading(true);
  hideError();
  hideDashboard();

  try {
    const resp = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `서버 오류 (${resp.status})`);
    }

    currentData = await resp.json();
    renderDashboard(currentData);
  } catch (e) {
    showError(e.message);
  } finally {
    showLoading(false);
  }
}

/* Enter 키 지원 */
document.getElementById("urlInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter") startAnalysis();
});

/* ───── 렌더링 ───── */

function renderDashboard(data) {
  renderPlaceInfo(data.place);
  renderKPIs(data.summary);
  renderInsights(data.insights);
  renderSentimentChart(data.sentiment_distribution);
  renderRatingChart(data.rating_distribution);
  renderCategoryChart(data.category_analysis);
  renderTrendChart(data.monthly_trend);
  renderKeywords(data.top_positive_keywords, data.top_negative_keywords);
  renderReviews(data.reviews);
  document.getElementById("dashboard").classList.remove("hidden");
}

function renderPlaceInfo(place) {
  document.getElementById("placeName").textContent = place.name;
  document.getElementById("placeCategory").textContent = place.category || "";
  document.getElementById("placeAddress").textContent = place.address || "";
}

function renderKPIs(s) {
  document.getElementById("kpiTotal").textContent = s.total_reviews.toLocaleString();
  document.getElementById("kpiRating").textContent = s.avg_rating ? s.avg_rating.toFixed(1) + "점" : "-";
  document.getElementById("kpiPositive").textContent = s.positive_ratio + "%";
  document.getElementById("kpiNegative").textContent = s.negative_ratio + "%";
  document.getElementById("kpiReply").textContent = s.reply_rate + "%";
}

function renderInsights(insights) {
  const el = document.getElementById("insightsList");
  if (!insights.length) {
    el.innerHTML = '<p style="color:var(--text-light)">분석 결과가 없습니다.</p>';
    return;
  }
  el.innerHTML = insights
    .map(
      (ins) => `
    <div class="insight-card ${ins.type}">
      <div class="insight-title">
        <span class="insight-badge ${ins.priority}">${priorityLabel(ins.priority)}</span>
        ${ins.title}
      </div>
      <div class="insight-desc">${ins.description}</div>
    </div>`
    )
    .join("");
}

function priorityLabel(p) {
  return { high: "긴급", medium: "권장", low: "참고" }[p] || p;
}

/* ───── Chart.js 차트 ───── */

function destroyChart(key) {
  if (chartInstances[key]) {
    chartInstances[key].destroy();
    chartInstances[key] = null;
  }
}

function renderSentimentChart(dist) {
  destroyChart("sentiment");
  const ctx = document.getElementById("sentimentChart").getContext("2d");
  chartInstances.sentiment = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["긍정", "부정", "중립"],
      datasets: [
        {
          data: [dist["긍정"] || 0, dist["부정"] || 0, dist["중립"] || 0],
          backgroundColor: ["#22c55e", "#ef4444", "#a3a3a3"],
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: "bottom" },
      },
    },
  });
}

function renderRatingChart(dist) {
  destroyChart("rating");
  const labels = ["1", "2", "3", "4", "5"];
  const values = labels.map((l) => dist[l] || 0);
  const ctx = document.getElementById("ratingChart").getContext("2d");
  chartInstances.rating = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels.map((l) => l + "점"),
      datasets: [
        {
          label: "리뷰 수",
          data: values,
          backgroundColor: ["#ef4444", "#f97316", "#f59e0b", "#84cc16", "#22c55e"],
          borderRadius: 6,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1 } },
      },
    },
  });
}

function renderCategoryChart(catData) {
  destroyChart("category");
  const categories = Object.keys(catData);
  if (!categories.length) return;

  const pos = categories.map((c) => catData[c].positive_mentions);
  const neg = categories.map((c) => -catData[c].negative_mentions);

  const ctx = document.getElementById("categoryChart").getContext("2d");
  chartInstances.category = new Chart(ctx, {
    type: "bar",
    data: {
      labels: categories,
      datasets: [
        {
          label: "긍정",
          data: pos,
          backgroundColor: "#22c55e",
          borderRadius: 4,
        },
        {
          label: "부정",
          data: neg,
          backgroundColor: "#ef4444",
          borderRadius: 4,
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      plugins: { legend: { position: "bottom" } },
      scales: {
        x: {
          ticks: {
            callback: (v) => Math.abs(v),
          },
        },
      },
    },
  });
}

function renderTrendChart(trend) {
  destroyChart("trend");
  if (!trend.length) return;

  const labels = trend.map((t) => t.month);
  const ctx = document.getElementById("trendChart").getContext("2d");
  chartInstances.trend = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "긍정",
          data: trend.map((t) => t.positive),
          borderColor: "#22c55e",
          backgroundColor: "rgba(34,197,94,.1)",
          fill: true,
          tension: 0.3,
        },
        {
          label: "부정",
          data: trend.map((t) => t.negative),
          borderColor: "#ef4444",
          backgroundColor: "rgba(239,68,68,.1)",
          fill: true,
          tension: 0.3,
        },
        {
          label: "중립",
          data: trend.map((t) => t.neutral),
          borderColor: "#a3a3a3",
          backgroundColor: "rgba(163,163,163,.1)",
          fill: true,
          tension: 0.3,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { position: "bottom" } },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1 } },
      },
    },
  });
}

/* ───── 키워드 ───── */

function renderKeywords(pos, neg) {
  const posEl = document.getElementById("positiveKeywords");
  const negEl = document.getElementById("negativeKeywords");

  posEl.innerHTML = pos
    .map(([kw, cnt]) => `<span class="keyword-tag pos">${kw} (${cnt})</span>`)
    .join("");
  negEl.innerHTML = neg
    .map(([kw, cnt]) => `<span class="keyword-tag neg">${kw} (${cnt})</span>`)
    .join("");
}

/* ───── 리뷰 테이블 ───── */

function renderReviews(reviews) {
  const tbody = document.getElementById("reviewsBody");
  tbody.innerHTML = reviews.map((r) => buildReviewRow(r)).join("");
}

function buildReviewRow(r) {
  const sentClass =
    r.sentiment === "긍정" ? "sentiment-pos" : r.sentiment === "부정" ? "sentiment-neg" : "sentiment-neu";
  const stars = r.rating ? "★".repeat(r.rating) + "☆".repeat(5 - r.rating) : "-";
  return `<tr data-sentiment="${r.sentiment}">
    <td>${escHtml(r.nickname)}</td>
    <td>${stars}</td>
    <td class="${sentClass}">${r.sentiment}</td>
    <td>${r.categories.join(", ") || "-"}</td>
    <td>${escHtml(r.body)}</td>
    <td>${r.created || "-"}</td>
  </tr>`;
}

function filterReviews(filter, btn) {
  document.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("active"));
  btn.classList.add("active");

  const rows = document.querySelectorAll("#reviewsBody tr");
  rows.forEach((row) => {
    if (filter === "all" || row.dataset.sentiment === filter) {
      row.style.display = "";
    } else {
      row.style.display = "none";
    }
  });
}

/* ───── 유틸리티 ───── */

function showLoading(show) {
  document.getElementById("loading").classList.toggle("hidden", !show);
  document.getElementById("analyzeBtn").disabled = show;
}

function showError(msg) {
  document.getElementById("errorMsg").textContent = msg;
  document.getElementById("error").classList.remove("hidden");
}

function hideError() {
  document.getElementById("error").classList.add("hidden");
}

function hideDashboard() {
  document.getElementById("dashboard").classList.add("hidden");
}

function escHtml(str) {
  const d = document.createElement("div");
  d.textContent = str || "";
  return d.innerHTML;
}
