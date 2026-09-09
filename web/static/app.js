'use strict';

const $ = (id) => document.getElementById(id);
const PRESETS = {
  east:  { north: 50.5, south: 33.5, west: 125.9, east: 141.8 },
  west:  { north: 41.0, south: 32.0, west: 117.0, east: 127.0 },
  south: { north: 35.3, south: 32.0, west: 125.0, east: 130.0 },
  // 서해·남해·동해를 한 장에 담는 한반도 주변 해역 (176 deg² — 소용돌이 제한 안)
  korea: { north: 43.0, south: 32.0, west: 117.0, east: 133.0 },
};

let polling = null;
let lastResults = [];
let lastDate = '';

// ── 영역 프리셋 ────────────────────────────────────────────────
function applyPreset(p) {
  for (const k of Object.keys(p)) $(k).value = p[k];
}
$('preset-east').onclick = () => applyPreset(PRESETS.east);
$('preset-west').onclick = () => applyPreset(PRESETS.west);
$('preset-south').onclick = () => applyPreset(PRESETS.south);
$('preset-korea').onclick = () => applyPreset(PRESETS.korea);

// ── CMEMS 로그인 상태 ─────────────────────────────────────────
// 계정은 이 화면에서 받지 않는다. 서버가 쓰는 자격증명은 이 PC 에 저장된
// `copernicusmarine login` 하나뿐이라 여기서는 그 상태만 보여준다.
(async () => {
  const el = $('cmems-status');
  if (!el) return;
  const warn = (html) => { el.classList.add('warn'); el.innerHTML = html; };
  try {
    const res = await fetch('/api/health', { cache: 'no-store' });
    const data = await res.json();
    if (data.cmems_login === undefined) {
      // 서버가 이 코드보다 먼저 떠 있으면 예전 응답이 온다 — 재시작이 필요하다.
      warn('서버가 예전 버전으로 떠 있습니다 — 터미널에서 <code>Ctrl+C</code> 후 다시 실행하세요.');
    } else if (data.cmems_login) {
      el.classList.remove('warn');
      el.textContent = 'CMEMS 로그인됨 — 자료가 없는 날짜는 자동으로 내려받습니다.';
    } else {
      warn('CMEMS 로그인 안 됨 — 이미 받아둔 날짜만 볼 수 있습니다.<br>'
        + '터미널에서 <code>copernicusmarine login</code> 을 한 번 실행한 뒤 새로고침하세요.');
    }
  } catch (err) {
    warn('서버 상태를 확인하지 못했습니다 — 터미널에서 서버가 떠 있는지 확인하세요.');
  }
})();

// ── 실행 ──────────────────────────────────────────────────────
$('form').addEventListener('submit', async (e) => {
  e.preventDefault();
  if (polling) return;

  const layers = [...document.querySelectorAll('input[name=layer]:checked')].map((c) => c.value);
  if (!layers.length) { setStep('표출할 항목을 하나 이상 선택하세요.', true); return; }

  const body = {
    date: $('date').value.replaceAll('-', ''),
    north: +$('north').value, south: +$('south').value,
    west: +$('west').value, east: +$('east').value,
    layers,
    quality: document.querySelector('input[name=quality]:checked').value,
  };

  setRunning(true);
  setStep('요청 보내는 중…', false, 0.02);
  try {
    const res = await fetch('/api/render', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '요청이 거부되었습니다.');
    lastDate = body.date;
    poll(data.job_id);
  } catch (err) {
    setStep(err.message, true, 1);
    setRunning(false);
  }
});

// ── 진행 상황 폴링 ─────────────────────────────────────────────
function poll(jobId) {
  polling = setInterval(async () => {
    let job;
    try {
      const res = await fetch(`/api/jobs/${jobId}`);
      job = await res.json();
      if (!res.ok) throw new Error(job.detail || '작업 상태를 가져오지 못했습니다.');
    } catch (err) {
      stopPolling();
      setStep(err.message, true, 1);
      return;
    }

    setStep(job.step, job.state === 'error', job.progress);

    if (job.state === 'done') {
      stopPolling();
      render(job.results);
    } else if (job.state === 'error') {
      stopPolling();
      setStep(job.error, true, 1);
    }
  }, 900);
}

function stopPolling() {
  clearInterval(polling);
  polling = null;
  setRunning(false);
}

function setRunning(on) {
  $('run').disabled = on;
  $('run').textContent = on ? '처리 중…' : '분석 실행';
  $('progress').hidden = false;
}

function setStep(text, isError, progress) {
  $('step').textContent = text || '';
  $('progress').classList.toggle('err', !!isError);
  if (progress != null) $('bar').style.width = `${Math.round(progress * 100)}%`;
}

// ── 결과 표시 ─────────────────────────────────────────────────
function render(results) {
  lastResults = results;
  $('empty').hidden = results.length > 0;
  $('zip-wrap').hidden = results.length < 2;

  const bust = Date.now();
  $('cards').innerHTML = results.map((r) => `
    <div class="card">
      <h3>${r.label}</h3>
      <button class="thumb" data-full="${r.url}?t=${bust}">
        <img src="${r.url}?t=${bust}" alt="${r.label} 그림" loading="lazy">
      </button>
      <div class="stats">${statLine(r)}</div>
      <div class="actions">
        <a href="${r.download_url}?filename=${encodeURIComponent(r.filename)}" download>내려받기</a>
        <span class="stats" style="border:none;padding:0">${(r.size / 1048576).toFixed(1)} MB</span>
      </div>
    </div>`).join('');

  for (const b of document.querySelectorAll('.thumb')) {
    b.onclick = () => {
      $('viewer-img').src = b.dataset.full;
      $('viewer').showModal();
    };
  }

  const d = lastDate;
  $('result-title').textContent = `${d.slice(0, 4)}년 ${+d.slice(4, 6)}월 ${+d.slice(6, 8)}일`;
  $('result-note').textContent = results.length ? '썸네일을 누르면 원본 크기로 봅니다.' : '';
}

function statLine(r) {
  const s = r.stats || {};
  if (r.layer === 'eddy') {
    const v = s.view;
    const main = `${s.scope || '동해'} 난수성 <b>${s.warm}</b> · 냉수성 <b>${s.cold}</b>`;
    const region = `울릉 난수성 <b>${s.ulleung_warm}</b> · 독도 냉수성 <b>${s.dokdo_cold}</b>`;
    const inView = v ? `<span>표출영역 내 난 <b>${v.warm}</b> · 냉 <b>${v.cold}</b></span>` : '';
    return `<span>${main}</span><span>${region}</span>${inView}`;
  }
  if (r.layer === 'sst') {
    const a = s.view || s.eastsea || {};
    if (a.mean == null) return '';
    const scope = s.view ? '표출영역' : '동해 전역';
    return `<span>${scope} 평균 <b>${a.mean}°C</b></span>`
         + `<span>최저 <b>${a.min}°C</b> · 최고 <b>${a.max}°C</b></span>`
         + (s.front ? `<span>수온전선 <b>${s.front.lat}°N</b></span>` : '');
  }
  if (r.layer === 'current' && s.speed) {
    return `<span>평균 유속 <b>${s.speed.mean} m/s</b></span>`
         + `<span>최대 <b>${s.speed.max} m/s</b></span>`;
  }
  return '';
}

// ── ZIP ───────────────────────────────────────────────────────
$('zip').onclick = () => {
  const names = lastResults.map((r) => r.url.split('/').pop()).join(',');
  window.location = `/api/download/${lastDate}.zip?names=${encodeURIComponent(names)}`;
};

// ── 원본 보기 ─────────────────────────────────────────────────
$('viewer-close').onclick = () => $('viewer').close();
$('viewer').addEventListener('click', (e) => { if (e.target === $('viewer')) $('viewer').close(); });
