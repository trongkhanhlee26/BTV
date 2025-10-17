// static/core/organize.js

document.addEventListener('DOMContentLoaded', function () {
  // ===== Form "Thêm bài" — Ẩn/hiện Điểm tối đa theo phương thức chấm =====
  document.querySelectorAll('form').forEach(function (f) {
    const sel = f.querySelector('select[name="phuongThucCham"]');
    if (!sel) return;
    const maxLabel = f.querySelector('.js-max-label');
    const maxInput = f.querySelector('.js-max-input');

    function sync() {
      if (sel.value === 'POINTS') {
        if (maxLabel) maxLabel.style.display = '';
        if (maxInput) { maxInput.style.display = ''; maxInput.required = true; }
      } else {
        if (maxLabel) maxLabel.style.display = 'none';
        if (maxInput) { maxInput.style.display = 'none'; maxInput.required = false; maxInput.value = ''; }
      }
    }
    sel.addEventListener('change', sync);
    sync();
  });

  // ===== Modal cấu hình THỜI GIAN =====
  const modal = document.getElementById('time-modal');
  const rowsBox = document.getElementById('tm-rows');
  const btnClose = document.getElementById('tm-close');
  const btnAdd = document.getElementById('tm-add');
  const inputBT = document.getElementById('tm-btid');
  const inputJSON = document.getElementById('tm-json');
  const form = document.getElementById('tm-form');

  function openTimeModal(btid, rules) {
    if (!modal || !rowsBox || !inputBT) {
      console.warn('[time] elements not found');
      return;
    }
    inputBT.value = btid || '';
    rowsBox.innerHTML = '';
    (rules || []).forEach(addRowFromObj);
    modal.style.display = 'flex';
  }
  function closeTimeModal() { if (modal) modal.style.display = 'none'; }

  function addRowFromObj(obj) {
    addRow(obj?.start ?? '', obj?.end ?? '', obj?.score ?? '');
  }
  function addRow(start, end, score) {
    const row = document.createElement('div');
    row.className = 'row';
    row.innerHTML = `
      <label>Thời gian bắt đầu (giây)</label>
      <input type="number" min="0" step="1" class="tm-start" value="${start}">
      <label>Thời gian kết thúc (giây)</label>
      <input type="number" min="0" step="1" class="tm-end" value="${end}">
      <label>Điểm</label>
      <input type="number" step="1" class="tm-score" value="${score}" style="width:100px">
      <button type="button" class="btn tm-del">Xoá</button>
    `;
    row.querySelector('.tm-del').addEventListener('click', () => row.remove());
    rowsBox.appendChild(row);
  }

  // mở modal thời gian khi click nút
  document.querySelectorAll('[data-open-time-modal]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const btid = this.getAttribute('data-btid');
      let rules = [];
      try { rules = JSON.parse(this.getAttribute('data-rules') || '[]'); } catch (e) { }
      openTimeModal(btid, rules);
    });
  });

  btnAdd?.addEventListener('click', () => addRow('', '', ''));
  btnClose?.addEventListener('click', closeTimeModal);
  modal?.addEventListener('click', (e) => { if (e.target === modal) closeTimeModal(); });

  // submit: gom dữ liệu → JSON
  form?.addEventListener('submit', function () {
    if (!rowsBox || !inputJSON) return;
    const rows = [];
    rowsBox.querySelectorAll('.row').forEach(function (r) {
      const s = r.querySelector('.tm-start')?.value || '0';
      const e2 = r.querySelector('.tm-end')?.value || '0';
      const sc = r.querySelector('.tm-score')?.value || '0';
      rows.push({
        start: parseInt(s, 10) || 0,
        end: parseInt(e2, 10) || 0,
        score: parseInt(sc, 10) || 0
      });
    });
    inputJSON.value = JSON.stringify(rows);
  });

  // ===== Modal import TEMPLATE =====
  const tplModal = document.getElementById('tpl-modal');
  const tplCloseBtn = document.getElementById('tpl-close');
  const tplForm = document.getElementById('tpl-form');
  const tplBT = document.getElementById('tpl-btid');
  const tplFile = document.getElementById('tpl-file');

  function openTpl(btid) {
    if (!tplModal || !tplBT) {
      console.warn('[tpl] modal elements not found');
      return;
    }
    tplBT.value = btid || '';
    if (tplFile) tplFile.value = '';
    tplModal.style.display = 'flex';
  }
  function closeTpl() { if (tplModal) tplModal.style.display = 'none'; }

  // Delegation: click bất kỳ phần tử có [data-open-tpl-modal]
  document.addEventListener('click', function (e) {
    const btn = e.target.closest && e.target.closest('[data-open-tpl-modal]');
    if (btn) {
      e.preventDefault();
      openTpl(btn.getAttribute('data-btid'));
    }
  });

  tplCloseBtn?.addEventListener('click', closeTpl);
  tplModal?.addEventListener('click', (e) => { if (e.target === tplModal) closeTpl(); });

  // NEW: log khi submit để xác nhận có chạy
  tplForm?.addEventListener('submit', function () {
    console.log('[tpl] submit fired');
  });
  // Debug hooks
  window.__openTimeModal = openTimeModal;
  window.__openTpl = openTpl;
  console.log('[organize] JS ready');
});