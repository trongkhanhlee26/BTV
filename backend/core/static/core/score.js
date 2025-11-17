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
  sel.disabled = !(items && items.length > 0);
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
let TPL_CTX = { btid: null, max: 0, items: {}, errors: {} };

function openTemplateModal(btid, code) {
    TPL_CTX = { btid, max: 0, items: {}, errors: {}};
    const title = document.getElementById('tplTitle');
    const body = document.getElementById('tplBody');
    const modal = document.getElementById('tplModal');
    const maxEl = document.getElementById('tplMax');
    const totalEl = document.getElementById('tplTotal');
    const thiSinhInModal = document.getElementById('tplThiSinh')?.value || document.getElementById('saveBtn')?.dataset.ts || '';
    const ctIdInModal    = document.querySelector('[name="ct"]')?.value || null;
    const TPL_CACHE_KEY  = `tpl:${ctIdInModal || 'ct'}:${thiSinhInModal}:${btid}`;
    let TPL_CACHE = {};
    try { TPL_CACHE = JSON.parse(localStorage.getItem(TPL_CACHE_KEY) || '{}'); } catch(e) {}

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
                  data-itemid="${it.id}" value="${(TPL_CACHE.items && TPL_CACHE.items[it.id]) ?? ''}"
                  oninput="tplOnChange(this, ${it.id}, ${it.max}, this.value)"
                  style="width:70px; padding:6px">
                <small class="muted">/ ${it.max}</small>
              </div>
            </div>`
                    );
                });
                out.push(`</div>`);
            });
            out.push(`
              <div class="time-wrap" id="tpl-time-wrap" data-rules="[]" 
                  style="display:grid; grid-template-columns:1fr auto; align-items:center; margin-top:10px;">
                <div style="font-weight:600; padding-left: 20px;">Thời gian hoàn thành bài thi:</div>
                <div style="display:flex; justify-content:flex-end; align-items:center; gap:8px;">
                  <div class="wheel">
                    <div class="wheel-col" data-type="min">
                      <ul class="wheel-list">
                        <li class="wheel-item wheel-spacer"></li>
                        ${Array.from({length:60},(_,i)=>`<li class="wheel-item">${String(i).padStart(2,'0')}</li>`).join('')}
                        <li class="wheel-item wheel-spacer"></li>
                      </ul>
                      <div class="wheel-mask"></div>
                    </div>
                    <div class="wheel-col" data-type="sec">
                      <ul class="wheel-list">
                        <li class="wheel-item wheel-spacer"></li>
                        ${Array.from({length:60},(_,i)=>`<li class="wheel-item">${String(i).padStart(2,'0')}</li>`).join('')}
                        <li class="wheel-item wheel-spacer"></li>
                      </ul>
                      <div class="wheel-mask"></div>
                    </div>
                    <div class="wheel-indicator"></div>
                  </div>
                  <input type="hidden" id="tplTimeInput" class="time-input" value="00:00">
                  <span class="time-score" style="display:none"></span>
                </div>
              </div>
            `);
            body.innerHTML = out.join('');
            initTimeWheels();

            // Prefill điểm từng item từ cache (để cập nhật tổng)
            document.querySelectorAll('#tplBody input[data-itemid]').forEach(el => {
              const id  = parseInt(el.dataset.itemid, 10);
              const max = parseInt(el.getAttribute('max') || '0', 10);
              if (el.value !== '') tplOnChange(el, id, max, el.value);
            });

            // Prefill thời gian cho wheel từ cache
            if (TPL_CACHE.time) {
              const [mmRaw, ssRaw] = TPL_CACHE.time.split(':');
              const mm = Math.max(0, Math.min(59, parseInt(mmRaw||'0',10)));
              const ss = Math.max(0, Math.min(59, parseInt(ssRaw||'0',10)));
              const wrap  = document.getElementById('tpl-time-wrap');
              const minCol= wrap?.querySelector('[data-type="min"]');
              const secCol= wrap?.querySelector('[data-type="sec"]');
              const inp   = document.getElementById('tplTimeInput');
              const ITEM_H= 44;
              if (minCol && secCol && inp) {
                minCol.scrollTop = mm * ITEM_H;
                secCol.scrollTop = ss * ITEM_H;
                inp.value = `${String(mm).padStart(2,'0')}:${String(ss).padStart(2,'0')}`;
              }
            }

            // ✅ Chỉ tăng cường click cho picker trong CHẤM THEO MẪU
            (function enhanceTplWheelClick() {
              const wrap = document.getElementById('tpl-time-wrap');
              if (!wrap) return;
              const cols = wrap.querySelectorAll('.wheel-col');
              const ITEM_H = 44;      // đúng với initTimeWheels()
              const MAX_IDX = 59;     // 0..59
              function scrollToIndex(col, idx, smooth = true) {
                idx = Math.max(0, Math.min(MAX_IDX, idx));
                col.scrollTo({ top: idx * ITEM_H, behavior: smooth ? 'smooth' : 'auto' });
              }
              function updateHidden() {
                const input = wrap.querySelector('.time-input');
                const minCol = wrap.querySelector('[data-type="min"]');
                const secCol = wrap.querySelector('[data-type="sec"]');
                if (!input || !minCol || !secCol) return;
                const mm = Math.round(minCol.scrollTop / ITEM_H).toString().padStart(2,'0');
                const ss = Math.round(secCol.scrollTop / ITEM_H).toString().padStart(2,'0');
                input.value = `${mm}:${ss}`;
              }
              cols.forEach(col => {
                col.addEventListener('click', (e) => {
                  // Click ở BẤT KỲ vị trí trên cột -> cuộn tới số gần nhất
                  const rect = col.getBoundingClientRect();
                  const y = e.clientY - rect.top;       // vị trí click trong cột
                  const idxApprox = Math.floor((col.scrollTop + y) / ITEM_H) - 1; // bỏ spacer đầu
                  const idx = Math.max(0, Math.min(MAX_IDX, idxApprox));
                  scrollToIndex(col, idx, true);
                  setTimeout(updateHidden, 160);
                });
              });
            })();
        })
        .catch(err => {
            body.innerHTML = `<div style="color:#f87171">Lỗi: ${err.message}</div>`;
        });
}

function closeTplModal() {
    const modal = document.getElementById('tplModal');
    if (modal) modal.style.display = 'none';
}

function tplOnChange(el, itemId, maxVal, raw) {
  const vRaw = Number(raw);
  const invalid = Number.isNaN(vRaw) || vRaw < 0 || vRaw > maxVal;
  // đánh dấu lỗi tại ô nhập
  if (invalid) {
    el.classList.add('invalid');
    TPL_CTX.errors[itemId] = `0..${maxVal}`;
    // KHÔNG ghi vào items khi lỗi, để tổng không “tự kẹp về max”
    delete TPL_CTX.items[itemId];
  } else {
    el.classList.remove('invalid');
    delete TPL_CTX.errors[itemId];
    TPL_CTX.items[itemId] = vRaw;
  }

    let total = 0;
    for (const k in TPL_CTX.items) total += (Number(TPL_CTX.items[k]) || 0);
    const totalEl = document.getElementById('tplTotal');
    if (totalEl) totalEl.textContent = String(total);
}

function saveTplScores() {
  const saveBtn = document.getElementById('saveBtn');
  const hiddenTS = document.getElementById('tplThiSinh');
  const thiSinh = (hiddenTS?.value || saveBtn?.dataset.ts || '').trim();
  if (!thiSinh) { alert('Chưa chọn thí sinh ở màn hình chính.'); return; }

  const ctId = document.querySelector('[name="ct"]')?.value || null;
  const time = document.getElementById('tplTimeInput')?.value || '00:00';

  let hasError = false;
  document.querySelectorAll('#tplBody input[data-itemid]').forEach(el => {
    const id  = parseInt(el.dataset.itemid, 10);
    const max = parseInt(el.getAttribute('max') || '0', 10);
    const v   = el.value.trim();
    const num = Number(v);
    const invalid = v === '' || Number.isNaN(num) || num < 0 || num > max;
    if (invalid) {
      el.classList.add('invalid');
      TPL_CTX.errors[id] = `0..${max}`;
      hasError = true;
    }
  });
  if (hasError || Object.keys(TPL_CTX.errors).length > 0) {
    showToast('Có mục điểm không hợp lệ (chỉ cho phép trong khoảng cho trước).', true);
    return; // ⛔ không lưu, không đóng modal
  }

  // tính tổng từ TPL_CTX.items
  let total = 0;
  Object.values(TPL_CTX.items).forEach(v => { total += (parseInt(v,10) || 0); });

  // cập nhật preview & hidden ở hàng bài thi
  const pv     = document.getElementById(`preview-total-${TPL_CTX.btid}`);
  const hidden = document.getElementById(`score-input-${TPL_CTX.btid}`);
  const hTime  = document.getElementById(`tpl-time-${TPL_CTX.btid}`);
  if (pv)     pv.textContent = `Tổng: ${total}`;
  if (hidden) hidden.value   = total;
  if (hTime)  hTime.value    = time;

  // Lưu tạm vào localStorage
  const key = `tpl:${ctId || 'ct'}:${thiSinh}:${TPL_CTX.btid}`;
  localStorage.setItem(key, JSON.stringify({ items: TPL_CTX.items, time, total }));

  closeTplModal();
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
  const vtSelect = document.getElementById('vtSelect');
  const btSelect = document.getElementById('btSelect');
  const hintCard = document.getElementById('searchHintCard');
  const hintText = document.getElementById('searchHintText');
  const scoreCard = document.getElementById('scoreCard');

  if (!form || !btn || !input) return;

  function showHint(text) {
    if (!hintCard || !hintText) return;
    hintText.innerHTML = text;
    hintCard.style.display = 'block';
    hintCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function hideHint() {
    if (hintCard) hintCard.style.display = 'none';
  }

  hideHint();

  form.addEventListener('submit', async (e) => {
    const q = (input.value || '').trim();
    const ct = ctSelect ? ctSelect.value : '';
    const vt = vtSelect ? vtSelect.value : '';
    const bt = btSelect ? btSelect.value : '';

    if (!ct) {
      e.preventDefault();
      showHint('Vui lòng chọn <b>Cuộc thi</b> bên trên trước khi tìm thí sinh.');
      ctSelect && ctSelect.focus();
      return;
    }

    // BẮT BUỘC chọn Vòng thi
    if (!vt) {
      e.preventDefault();
      showHint('Vui lòng chọn <b>Vòng thi</b> trước khi chấm điểm.');
      if (scoreCard) scoreCard.style.display = 'none';
      vtSelect && vtSelect.focus();
      return;
    }

    // BẮT BUỘC chọn Bài thi
    if (!bt) {
      e.preventDefault();
      showHint('Vui lòng chọn <b>Bài thi</b> (mỗi lần chỉ chấm 1 bài) trước khi chấm điểm.');
      if (scoreCard) scoreCard.style.display = 'none';
      btSelect && btSelect.focus();
      return;
    }

    if (!q) {
      e.preventDefault();
      showHint('Vui lòng nhập <b>Mã NV</b> hoặc <b>họ tên</b> để tìm thí sinh.');
      input.focus();
      if (scoreCard) scoreCard.style.display = 'none';
      return;
    }

    // vẫn giữ phần kiểm tra thí sinh thuộc cuộc thi như cũ
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
          const ct = (ctSelect.value || '').trim();

          // 1) Reset UI nhẹ
          hintCard && (hintCard.style.display = 'none');
          scoreCard && (scoreCard.style.display = 'none');
          const input = document.getElementById('searchInput');
          const box = document.getElementById('suggestBox');
          const resultCard = document.querySelector('.card[data-type="result"]');
          if (input) input.value = '';
          if (box) { box.style.display = 'none'; box.innerHTML = ''; }
          if (resultCard) resultCard.style.display = 'none';

          // 2) Nếu CHƯA chọn cuộc thi -> xóa & khóa dropdown con rồi dừng
          if (!ct) {
            fillSelect(vtSelect, [], (v) => new Option(v.tenVongThi, v.id));
            fillSelect(btSelect, [], (b) => new Option(`${b.ma} — ${b.tenBaiThi}`, b.id));
            return;
          }

          // 3) Hiển thị trạng thái "đang tải" để người dùng thấy phản hồi ngay
          vtSelect.innerHTML = '';
          vtSelect.appendChild(new Option('Đang tải vòng thi...', ''));
          vtSelect.disabled = true;

          btSelect.innerHTML = '';
          btSelect.appendChild(new Option('— Tất cả —', ''));
          btSelect.disabled = true;

          // 4) Nạp rounds từ server
          try {
            const data = await fetchJSON(`/score/?ajax=meta&ct=${encodeURIComponent(ct)}`);
            // fillSelect sẽ tự bật/tắt disabled dựa trên độ dài mảng
            fillSelect(vtSelect, data.rounds || [], (v) => new Option(v.tenVongThi, v.id));
            // Bài thi luôn reset rỗng khi mới chọn CT
            fillSelect(btSelect, [], (b) => new Option(`${b.ma} — ${b.tenBaiThi}`, b.id));

            // Tùy UX: nếu có vòng thi thì focus vào vtSelect
            if (!vtSelect.disabled) vtSelect.focus();
          } catch (err) {
            // Lỗi thì reset sạch và thông báo
            fillSelect(vtSelect, [], (v) => new Option(v.tenVongThi, v.id));
            fillSelect(btSelect, [], (b) => new Option(`${b.ma} — ${b.tenBaiThi}`, b.id));
            showToast('Không tải được vòng thi. Vui lòng thử lại.', true);
          }
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


    // Toggle TIME enable/disable input (show wheel & default 00:00 + 10đ)
    if (document.querySelector('.done-toggle')) {
      document.querySelectorAll('.done-toggle').forEach(cb => {
        const id   = cb.dataset.btid;
        const wrap = document.querySelector(`.time-wrap[data-btid="${id}"]`);
        const input   = wrap ? wrap.querySelector('.time-input')  : null;
        const preview = wrap ? wrap.querySelector('.time-score')  : null;
        const wheel   = wrap ? wrap.querySelector('.wheel')       : null;
        const minCol  = wheel ? wheel.querySelector('[data-type="min"]') : null;
        const secCol  = wheel ? wheel.querySelector('[data-type="sec"]') : null;

        const hasSaved = !!(wrap && wrap.dataset && wrap.dataset.time && wrap.dataset.time !== "");
        if (hasSaved) cb.checked = true;

        const update = () => {
          if (!wrap || !input) return;
          if (cb.checked) {
            wrap.classList.remove('hidden');
            input.removeAttribute('disabled');

            // default: 00:00 + 10 điểm
            if (!hasSaved) {
              if (minCol) minCol.scrollTop = 0;
              if (secCol) secCol.scrollTop = 0;
              input.value = '00:00';
              if (preview) preview.textContent = '10';
            }
            // focus vào cột phút cho UX
            if (minCol) minCol.focus?.();
          } else {
            wrap.classList.add('hidden');
            input.setAttribute('disabled', 'disabled');
            input.value = '';
            if (preview) preview.textContent = '0';
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
            let bonus = 0;
            if (sec !== null) {
                for (const r of rules) {
                  if (sec >= r.s && sec <= r.e) { bonus = Number(r.bonus ?? r.score ?? 0); break; }
                }
            }
            out.textContent = String(Math.min(20, 10 + bonus));
        });
      });
    }


    // Save (AJAX)
    if (saveBtn) {
saveBtn.addEventListener('click', async () => {
  const thiSinh = saveBtn.dataset.ts || '';
  if (!thiSinh) {
    showToast('Không có thông tin thí sinh để lưu.', true);
    return;
  }

  const vtSel = document.getElementById('vtSelect');
  const btSel = document.getElementById('btSelect');
  const vt = vtSel ? vtSel.value : '';
  const bt = btSel ? btSel.value : '';

  // BẮT BUỘC chọn Vòng + Bài trước khi lưu
  if (!vt || !bt) {
    showToast('Vui lòng chọn đầy đủ Vòng thi và đúng 1 Bài thi trước khi lưu điểm.', true);
    return;
  }

  const payload = {
    thiSinh: saveBtn.dataset.ts || '',
    ct_id: document.querySelector('[name="ct"]')?.value || saveBtn.dataset.ct || null,
    vt_id: vt,
    bt_id: bt,
    scores: {},
    done: {},
    times: {}
  };

            // POINTS
            let hasPointsError = false;
            document.querySelectorAll('input[name^="score_"]').forEach(i => {
              const raw = i.value.trim();
              if (raw === '') { i.classList.remove('invalid'); return; }

              const val = parseInt(raw, 10);
              // ưu tiên max trên attribute; nếu không có thì lấy data-max (TEMPLATE)
              const maxAttr = i.getAttribute('max');
              const dataMax = i.dataset.max;
              const max = (maxAttr || dataMax) ? parseInt(maxAttr || dataMax, 10) : Number.POSITIVE_INFINITY;

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
            payload.tpl_times = {};
            document.querySelectorAll('input[name^="tpl_time_"]').forEach(i => {
              const id = i.name.replace('tpl_time_', '');
              if (i.value && i.value.trim() !== '') payload.tpl_times[id] = i.value.trim();
            });

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
            // clear cache tạm sau khi đã lưu DB
            const thiSinh = saveBtn.dataset.ts || '';
            const ctId    = payload.ct_id || null;
            Object.keys(payload.scores || {}).forEach(id => {
              // chỉ clear những bài có hidden tpl_time_ (tức là TEMPLATE)
              if (document.getElementById(`tpl-time-${id}`)) {
                const key = `tpl:${ctId || 'ct'}:${thiSinh}:${id}`;
                localStorage.removeItem(key);
              }
            });
            setTimeout(() => {
              const ct = (saveBtn?.dataset.ct || '').trim();
              const vt = document.getElementById('vtSelect')?.value || '';
              const bt = document.getElementById('btSelect')?.value || '';

              const params = new URLSearchParams();
              if (ct) params.set('ct', ct);
              if (vt) params.set('vt', vt);
              if (bt) params.set('bt', bt);

              const url = params.toString() ? `/score/?${params}` : '/score/';
              window.location.href = url;
            }, 800);
            } catch (e) {
            console.error(e);
            showToast('Không thể kết nối server.', true);
            }
        });
    }
  initTimeWheels();
})();

// === Wheel Picker 2-column (phút / giây) ===
function initTimeWheels() {
  document.querySelectorAll('.time-wrap').forEach((wrap) => {
    const wheel = wrap.querySelector('.wheel');
    if (!wheel) return;
    const minCol = wheel.querySelector('[data-type="min"]');
    const secCol = wheel.querySelector('[data-type="sec"]');
    const input = wrap.querySelector('.time-input');
    const preview = wrap.querySelector('.time-score');
    const max = 20;
    const rules = JSON.parse(wrap.dataset.rules || "[]");

    // scroll to 00 mặc định
    minCol.scrollTop = 0;
    secCol.scrollTop = 0;
    input.value = "00:00";
    preview.textContent = '10';
    
    // --- Prefill khi server đã trả time_current (giây) qua data-time ---
    const saved = wrap.dataset.time;
    if (saved !== undefined && saved !== null && saved !== "") {
      const total = parseInt(saved, 10);
      const mm = Math.floor(total / 60) % 60;
      const ss = total % 60;

      // mở picker (phòng khi checkbox chưa tick vì race)
      wrap.classList.remove('hidden');

      // cuộn tới đúng phút/giây
      const ITEM_H = 44, SPACER = 1;
      const scrollTo = (col, idx) => col && col.scrollTo({ top: (SPACER + idx) * ITEM_H, behavior: 'auto' });
      scrollTo(minCol, mm - 1);
      scrollTo(secCol, ss - 1);

      // set input + preview theo rules
      input.value = `${String(mm).padStart(2,'0')}:${String(ss).padStart(2,'0')}`;

      // dùng chính calcScore trong scope này
      const score = (function calcScorePrefill(totalSec){
        if (!(Array.isArray(rules) && rules.length)) return 10;
        let bonus = 0;
        for (const r of rules) {
          const inRange = (typeof r.s !== 'undefined' && typeof r.e !== 'undefined')
            ? (totalSec >= r.s && totalSec <= r.e)
            : (typeof r.max !== 'undefined' && totalSec <= r.max);
          if (inRange) { bonus = Number(r.bonus ?? r.score ?? 0); break; }
        }
        return Math.min(20, 10 + bonus);
      })(total);
      preview.textContent = String(score);
    }

    const ITEM_H = 44;             // chiều cao 1 dòng
    const SPACER = 1;              // số spacer đầu (1 item)
    const MAX_IDX = 59;

    function getIndex(col) {
      // do có 1 spacer đầu, index thực tế = round(scrollTop/ITEM_H)
      let idx = Math.round(col.scrollTop / ITEM_H);
      if (idx < 0) idx = 0;
      if (idx > MAX_IDX) idx = MAX_IDX;
      return idx;
    }
    function getValue(col) {
      const idx = getIndex(col);
      return idx.toString().padStart(2, "0");
    }
    function scrollToIndex(col, idx, smooth = true) {
      idx = Math.max(0, Math.min(MAX_IDX, idx));
      col.scrollTo({ top: idx * ITEM_H, behavior: smooth ? "smooth" : "auto" });
    }

    let dragging = false; 

    function addDrag(col) {
      let startY = 0, startTop = 0;

      const getY = (e) => (e.touches?.[0]?.clientY ?? e.clientY ?? 0);

      const onDown = (e) => {
        // Chỉ bật drag tùy theo loại con trỏ:
        if (e.pointerType && e.pointerType !== 'mouse') return; // giữ cuộn tự nhiên trên touch
        dragging = true;
        startY = getY(e);
        startTop = col.scrollTop;
        col.classList.add('dragging');
        col.setPointerCapture?.(e.pointerId);
        e.preventDefault();
      };

      const onMove = (e) => {
        if (!dragging) return;
        const dy = startY - getY(e);
        col.scrollTop = startTop + dy;
      };

      const onUp = () => {
        if (!dragging) return;
        dragging = false;
        col.classList.remove('dragging');
        const idx = getIndex(col);
        scrollToIndex(col, idx);   // snap vào rãnh
        update();
      };

      col.addEventListener('pointerdown', onDown);
      col.addEventListener('pointermove', onMove);
      col.addEventListener('pointerup', onUp);
      col.addEventListener('pointercancel', onUp);
      col.addEventListener('mouseleave', onUp);
    }

    function calcScore(totalSec) {
      if (!(Array.isArray(rules) && rules.length)) return 10;
      let bonus = 0;
      for (const r of rules) {
        const inRange = (typeof r.s !== 'undefined' && typeof r.e !== 'undefined')
          ? (totalSec >= r.s && totalSec <= r.e)
          : (typeof r.max !== 'undefined' && totalSec <= r.max);
        if (inRange) { bonus = Number(r.bonus ?? r.score ?? 0); break; }
      }
      return Math.min(20, 10 + bonus);
    }

    function update() {
      const mm = getValue(minCol);
      const ss = getValue(secCol);
      input.value = `${mm}:${ss}`;
      const total = parseInt(mm) * 60 + parseInt(ss);
      const score = calcScore(total);
      preview.textContent = score;
    }

    // cập nhật khi ngừng scroll (snap & update)
    [minCol, secCol].forEach((col) => {
      let timer;
      col.addEventListener("scroll", () => {
        addDrag(col);
        clearTimeout(timer);
        timer = setTimeout(() => {
          // snap đúng rãnh
          const idx = getIndex(col);
          scrollToIndex(col, idx);
          update();
        }, 120);
      });

      // click vào 1 số -> nhảy ngay
      col.addEventListener("click", (e) => {
        if (dragging) return;
        const li = e.target.closest(".wheel-item");
        if (!li || li.classList.contains("wheel-spacer")) return;
        const list = col.querySelector(".wheel-list");
        const all  = Array.from(list.children);
        const rawIndex = all.indexOf(li);   // có spacer đầu
        const idx = Math.max(0, Math.min(MAX_IDX, rawIndex - SPACER));
        scrollToIndex(col, idx);
        // update ngay sau khi snap
        setTimeout(update, 160);
      });
    });
  });
}

