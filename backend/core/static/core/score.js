// === Toast helper ===
function showToast(msg, isError) {
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg;
    t.className = 'toast' + (isError ? ' error' : '');
    t.style.display = 'block';
    setTimeout(() => { t.style.display = 'none'; }, 2500);
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

// === Custom confirm (glass modal) ===
function confirmDialog(message, title = 'Xác nhận') {
  return new Promise((resolve) => {
    const overlay = document.getElementById('confirmModal');
    const msgEl   = document.getElementById('confirmMessage');
    const titleEl = document.getElementById('confirmTitle');
    const okBtn   = document.getElementById('confirmOk');
    const cancelBtn = document.getElementById('confirmCancel');

    if (!overlay || !msgEl || !okBtn || !cancelBtn) {
      // fallback nếu thiếu markup
      resolve(window.confirm(message));
      return;
    }

    titleEl && (titleEl.textContent = title);
    msgEl.textContent = message;
    overlay.style.display = 'flex';

    // đóng & trả kết quả
    const cleanup = (val) => {
      overlay.style.display = 'none';
      okBtn.removeEventListener('click', onOk);
      cancelBtn.removeEventListener('click', onCancel);
      overlay.removeEventListener('click', onClickOutside);
      document.removeEventListener('keydown', onKey);
      resolve(val);
    };
    const onOk = () => cleanup(true);
    const onCancel = () => cleanup(false);
    const onClickOutside = (e) => { if (e.target === overlay) cleanup(false); };
    const onKey = (e) => { if (e.key === 'Escape') cleanup(false); };

    okBtn.addEventListener('click', onOk);
    cancelBtn.addEventListener('click', onCancel);
    overlay.addEventListener('click', onClickOutside);
    document.addEventListener('keydown', onKey);

    // focus mặc định vào OK
    setTimeout(() => okBtn.focus(), 0);
  });
}

// === Debounce helper ===
function debounce(fn, delay = 250) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), delay);
  };
}

// === Suggestion helpers ===
function buildSuggestURL(q, ctVal) {
  // Nếu bạn dùng endpoint khác, đổi ở đây (vd: `/score/suggest/?q=...&ct=...`)
  const params = new URLSearchParams({
    ajax: 'suggest',
    q: q || '',
    ct: ctVal || ''
  });
  return `/score/?${params.toString()}`;
}

function renderSuggestions(box, list) {
  if (!box) return;
  if (!Array.isArray(list) || list.length === 0) {
    box.style.display = 'none';
    box.innerHTML = '';
    return;
  }
  box.innerHTML = list
    .map(it => `<a href="#" data-code="${it.maNV}" data-name="${it.hoTen}">${it.maNV} — ${it.hoTen}</a>`)
    .join('');
  box.style.display = 'block';
}

async function fetchJSON(url) {
  const r = await fetch(url, { credentials: 'same-origin' });
  return r.json();
}
function fillSelect(sel, items, makeOption) {
  sel.innerHTML = '';
  sel.appendChild(new Option('— Tất cả —', ''));
  items.forEach(it => sel.appendChild(makeOption(it)));
  sel.disabled = items.length === 0;
  if (!sel.disabled) sel.focus();
}


// === TIME helpers ===
function parseSeconds(v) {
    if (!v) return null;
    v = v.trim();
    if (v.includes(':')) {
        const [m, s] = v.split(':');
        const mm = parseInt(m, 10), ss = parseInt(s, 10);
        if (Number.isNaN(mm) || Number.isNaN(ss)) return null;
        return mm * 60 + ss;
    }
    const f = parseFloat(v);
    return Number.isNaN(f) ? null : Math.floor(f);
}

// === TEMPLATE modal state ===
let TPL_CTX = { btid: null, max: 0, items: {} };

function openTemplateModal(btid, code) {
    TPL_CTX = { btid, max: 0, items: {} };
    const title = document.getElementById('tplTitle');
    const body = document.getElementById('tplBody');
    const modal = document.getElementById('tplModal');
    const maxEl = document.getElementById('tplMax');
    const totalEl = document.getElementById('tplTotal');
    if (!title || !body || !modal) return;

    title.textContent = `Chấm theo mẫu - ${code}`;
    body.innerHTML = 'Đang tải...';
    totalEl.textContent = '0';
    maxEl.textContent = '0';
    modal.style.display = 'block';

    fetch(`/score/template/${btid}/`, { credentials: 'same-origin' })
        .then(async r => {
            const text = await r.text();
            try { return JSON.parse(text); }
            catch { throw new Error('Server không trả JSON (có thể lỗi 500/403).'); }
        })
        .then(res => {
            if (!res.ok) { throw new Error(res.message || 'Lỗi tải mẫu'); }
            TPL_CTX.max = res.total_max || 0;
            maxEl.textContent = TPL_CTX.max;

            const out = [];
            res.sections.forEach(sec => {
                out.push(
                    `<div style="margin:8px 0; padding:8px; border:1px solid #1f2937; border-radius:8px">
            <div style="font-weight:600; margin-bottom:6px">${sec.stt}. ${sec.title}${sec.note ? `<em style="color:#94a3b8"> – ${sec.note}</em>` : ''}</div>`
                );
                sec.items.forEach(it => {
                    out.push(
                        `<div style="display:grid; grid-template-columns:1fr 120px; gap:8px; align-items:center; margin:6px 0">
              <div>${it.stt}. ${it.content}${it.note ? ` <em style="color:#94a3b8">(${it.note})</em>` : ''}</div>
              <div>
                <input type="number" min="0" max="${it.max}" step="1"
                       oninput="tplOnChange(${it.id}, ${it.max}, this.value)"
                       style="width:100px; padding:6px">
                <small class="muted">/ ${it.max}</small>
              </div>
            </div>`
                    );
                });
                out.push(`</div>`);
            });
            body.innerHTML = out.join('');
        })
        .catch(err => {
            body.innerHTML = `<div style="color:#f87171">Lỗi: ${err.message}</div>`;
        });
}

function closeTplModal() {
    const modal = document.getElementById('tplModal');
    if (modal) modal.style.display = 'none';
}

function tplOnChange(itemId, maxVal, raw) {
    let v = parseInt(raw || '0', 10);
    if (isNaN(v) || v < 0) v = 0;
    if (v > maxVal) v = maxVal;
    TPL_CTX.items[itemId] = v;

    let total = 0;
    for (const k in TPL_CTX.items) total += TPL_CTX.items[k] || 0;
    const totalEl = document.getElementById('tplTotal');
    if (totalEl) totalEl.textContent = String(total);
}

function saveTplScores() {
    const saveBtn = document.getElementById('saveBtn');
    const thiSinh = (saveBtn?.dataset.ts || '').trim();
    if (!thiSinh) { alert('Chưa chọn thí sinh ở màn hình chính.'); return; }

    fetch(`/score/template/${TPL_CTX.btid}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
        credentials: 'same-origin',
        body: JSON.stringify({
            thiSinh,
            items: TPL_CTX.items,
            ct_id: document.querySelector('[name="ct"]')?.value || null
        })
    })
        .then(r => r.json())
        .then(res => {
            if (!res.ok) throw new Error(res.message || 'Không lưu được');
            const total = res.saved_total ?? 0;
            const pv = document.getElementById(`preview-total-${TPL_CTX.btid}`);
            const hidden = document.getElementById(`score-input-${TPL_CTX.btid}`);
            if (pv) pv.textContent = `Tổng: ${total}`;
            if (hidden) hidden.value = total;
            closeTplModal();
        })
        .catch(err => alert(err.message));
}

// === Page init ===
(function initScorePage() {
  const saveBtn = document.getElementById('saveBtn');

  // --- SUGGEST: gợi ý theo ký tự gõ ---
  const input = document.getElementById('searchInput');
  const box = document.getElementById('suggestBox');
  if (input && box) {
    const getCT = () =>
      (document.querySelector('select[name="ct"]')?.value) ||
      (document.querySelector('input[name="ct"]')?.value) || '';

    const onType = debounce(async () => {
      const q = (input.value || '').trim();
      const ct = getCT();
      if (!ct || q.length === 0) {
        box.style.display = 'none';
        box.innerHTML = '';
        return;
      }
      try {
        const res = await fetch(buildSuggestURL(q, ct), { credentials: 'same-origin' });
        const data = await res.json(); // [{maNV, hoTen}, ...]
        renderSuggestions(box, data);
      } catch (e) {
        box.style.display = 'none';
        box.innerHTML = '';
      }
    }, 250);

    // Gõ để tìm
    input.addEventListener('input', onType);

    // Chọn 1 dòng suggestion -> điền vào input và ẩn box
    box.addEventListener('click', (e) => {
      const a = e.target.closest('a');
      if (!a) return;
      e.preventDefault();
      input.value = `${a.dataset.code} — ${a.dataset.name}`;
      box.style.display = 'none';
    });

    // Click ra ngoài -> ẩn box
    document.addEventListener('click', (e) => {
      if (e.target === input || box.contains(e.target)) return;
      box.style.display = 'none';
    });
  }

  (function enhanceSearchGuard() {
    const form = document.getElementById('searchForm');
    const btn = form ? form.querySelector('button[type="submit"]') : null;
    const input = document.getElementById('searchInput');
    const ctSelect = document.getElementById('ctSelect');
    const hintCard = document.getElementById('searchHintCard');
    const hintText = document.getElementById('searchHintText');

    if (!form || !btn || !input) return;

    // helper hiển thị/ẩn thẻ thông báo
    function showHint(text) {
      if (!hintCard || !hintText) return;
      hintText.innerHTML = text;
      hintCard.style.display = 'block';
      hintCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function hideHint() {
      if (hintCard) hintCard.style.display = 'none';
    }

    // ban đầu luôn ẩn thông báo
    hideHint();

    // xử lý khi submit
    form.addEventListener('submit', async (e) => {
      const q = (input.value || '').trim();
      const ct = ctSelect ? ctSelect.value : '';

      if (!ct) {
        e.preventDefault();
        showHint('Vui lòng chọn <b>Cuộc thi</b> bên trên trước khi tìm thí sinh.');
        ctSelect && ctSelect.focus();
        return;
      }

      // nếu ô nhập rỗng => show thông báo & chặn form
      if (!q) {
        e.preventDefault();
        showHint('Vui lòng nhập <b>Mã NV</b> hoặc <b>họ tên</b> để tìm thí sinh.');
        input.focus();

         const scoreCard = document.getElementById('scoreCard');
         if (scoreCard) scoreCard.style.display = 'none';
        return;
      }

      // nếu có nhập -> kiểm tra thí sinh thuộc cuộc thi hay không
      try {
        const url = `/score/?ajax=suggest&q=${encodeURIComponent(q)}&ct=${encodeURIComponent(ct)}`;
        const res = await fetch(url, { credentials: 'same-origin' });
        const list = await res.json();

        if (Array.isArray(list) && list.length > 0) {
          hideHint();
          return;
        }
      } catch (err) {
        e.preventDefault();
        showHint('Không thể kiểm tra thí sinh lúc này. Vui lòng thử lại sau.');
      }
    });
  })();


    const ctSelect = document.getElementById('ctSelect');
    const vtSelect = document.getElementById('vtSelect');
    const btSelect = document.getElementById('btSelect');
    const hintCard = document.getElementById('searchHintCard');
    const scoreCard = document.getElementById('scoreCard');
    

    if (ctSelect && vtSelect && btSelect) {
        ctSelect.addEventListener('change', async () => {
            const ct = ctSelect.value || '';
            hintCard.style.display = 'none';
            scoreCard.style.display = 'none';
            const input = document.getElementById('searchInput');
            const box = document.getElementById('suggestBox');
            if (input) input.value = '';
            if (box) { box.style.display = 'none'; box.innerHTML = ''; }
            const resultCard = document.querySelector('.card[data-type="result"]');
            if (resultCard) resultCard.style.display = 'none';

            // nạp rounds
            const data = await fetchJSON(`/score/?ajax=meta&ct=${encodeURIComponent(ct)}`);
            fillSelect(vtSelect, data.rounds || [], (v) => new Option(v.tenVongThi, v.id));
            // sau khi đổi CT thì reset BT
            fillSelect(btSelect, [], (b) => new Option(`${b.ma} — ${b.tenBaiThi}`, b.id));
        });

        // khi đổi vòng thi → nạp bài thi
        vtSelect.addEventListener('change', async () => {
            const ct = ctSelect.value || '';
            const vt = vtSelect.value || '';
            if (!vt) {
            fillSelect(btSelect, [], (b) => new Option(`${b.ma} — ${b.tenBaiThi}`, b.id));
            return;
            }
            const data = await fetchJSON(`/score/?ajax=meta&ct=${encodeURIComponent(ct)}&vt=${encodeURIComponent(vt)}`);
            fillSelect(btSelect, data.tests || [], (b) => new Option(`${b.ma} — ${b.tenBaiThi}`, b.id));
        });
    }


  // --- Delegate: mở modal TEMPLATE – luôn hoạt động ---
  document.addEventListener('click', function (e) {
    const btn = e.target.closest('.tpl-open-btn');
    if (!btn) return;
    const btid = parseInt(btn.dataset.btid, 10);
    const bcode = btn.dataset.bcode || '';
    openTemplateModal(btid, bcode);
  });


    // Toggle TIME enable/disable input
    if (document.querySelector('.done-toggle')) {
        document.querySelectorAll('.done-toggle').forEach(cb => {
            const id = cb.dataset.btid;
            const wrap = document.querySelector(`.time-wrap[data-btid="${id}"]`);
            const input = wrap ? wrap.querySelector('.time-input') : null;
            const pv = document.getElementById(`preview_${id}`);
            const update = () => {
            if (!wrap || !input) return;
            if (cb.checked) {
                wrap.classList.remove('hidden');
                input.removeAttribute('disabled');
                input.focus();
            } else {
                wrap.classList.add('hidden');
                input.setAttribute('disabled', 'disabled');
                input.value = '';
                if (pv) pv.textContent = '0';
            }
            };
            cb.addEventListener('change', update);
            update();
        });
    }


    // TIME preview by rules
    if (document.querySelector('.time-wrap')) {
        document.querySelectorAll('.time-wrap').forEach(wrap => {
            const rules = JSON.parse(wrap.dataset.rules || '[]');
            const input = wrap.querySelector('.time-input');
            const out = wrap.querySelector('.time-score');
            if (!input || !out) return;
            input.addEventListener('input', () => {
            const sec = parseSeconds(input.value);
            let score = 0;
            if (sec !== null) {
                for (const r of rules) {
                if (sec >= r.s && sec <= r.e) { score = r.score; break; }
                }
            }
            out.textContent = score;
            });
        });
    }


    // Save (AJAX)
    if (saveBtn) {
        saveBtn.addEventListener('click', async function () {
            const payload = {
            thiSinh: saveBtn.dataset.ts || '',
            ct_id: saveBtn.dataset.ct || null,
            scores: {}, done: {}, times: {}
            };

            // POINTS
            let hasPointsError = false;
            document.querySelectorAll('input[name^="score_"]').forEach(i => {
              const raw = i.value.trim();
              if (raw === '') { i.classList.remove('invalid'); return; }

              const val = parseInt(raw, 10);
              const max = parseInt(i.getAttribute('max') || '0', 10);

              if (Number.isNaN(val) || val < 0 || val > max) {
                hasPointsError = true;
                i.classList.add('invalid');
              } else {
                i.classList.remove('invalid');
                payload.scores[i.name.replace('score_', '')] = val;
              }
            });

            if (hasPointsError) {
              showToast('Có điểm không hợp lệ.', true);
              return;
            }

            // TIME
            let hasTimeError = false;
            document.querySelectorAll('.done-toggle').forEach(cb => {
            const id = cb.dataset.btid;
            payload.done[id] = cb.checked;
            if (cb.checked) {
                const t = document.querySelector(`input[name="time_${id}"]`);
                if (!t || t.value.trim() === '') {
                hasTimeError = true;
                t && t.classList.add('border-red-500');
                } else {
                t.classList.remove('border-red-500');
                payload.times[id] = t.value.trim();
                }
            }
            });
            if (hasTimeError) {
            showToast('Vui lòng nhập thời gian cho bài đã tick Hoàn thành (mm:ss hoặc giây).', true);
            return;
            }

            try {
            async function postScores(body) {
              const res = await fetch(window.location.pathname + window.location.search, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'X-Requested-With': 'XMLHttpRequest',
                  'X-CSRFToken': getCookie('csrftoken')
                },
                credentials: 'same-origin',
                body: JSON.stringify(body),
              });
              const data = await res.json();
              return { res, data };
            }

            let { res, data } = await postScores(payload);

            // Nếu server báo đã có điểm → hỏi xác nhận
            if (res.status === 409 && data?.code === 'already_scored') {
              const ok = await confirmDialog(data.message || 'Thí sinh này đã được chấm điểm. Bạn có chắc chắn muốn chấm lại không?');
              if (!ok) {
                showToast('Đã hủy chấm lại.', true);
                return;
              }
              // gửi lại với cờ force=1
              payload.force = 1;
              ({ res, data } = await postScores(payload));
            }

            // xử lý lỗi khác
            if (!res.ok || data?.ok === false) {
              showToast(data?.message || 'Lưu điểm thất bại.', true);
              return;
            }

            // cập nhật preview ngay khi lưu thành công
            const saved = data.saved_scores || {};
            Object.keys(saved).forEach(id => {
              const pv = document.getElementById(`preview_${id}`);
              if (pv) pv.textContent = saved[id];
              const inp = document.querySelector(`input[name="score_${id}"]`);
              if (inp) inp.value = saved[id];
            });

            showToast(data.message || 'Đã lưu.');

            } catch (e) {
            console.error(e);
            showToast('Không thể kết nối server.', true);
            }
        });
    }

})();
