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

  // ===== Toggle hiện/ẩn form "Thêm Cuộc thi" =====
  const btnShowCreate = document.getElementById('btn-show-create');
  const createCard = document.getElementById('create-card');
  if (btnShowCreate && createCard) {
    btnShowCreate.addEventListener('click', () => {
      const open = createCard.style.display !== 'none';
      createCard.style.display = open ? 'none' : 'block';
      btnShowCreate.textContent = open ? '+ Tạo cuộc thi' : 'Ẩn form';
    });
  }

// ===== Gợi ý + Tìm kiếm (autocomplete giống index) =====
const searchBox = document.getElementById('search-ct');
const suggList  = document.getElementById('ct-suggest');   // dropdown
const table     = document.querySelector('table');

// Chuẩn hoá bỏ dấu
const vnNorm = s => (s || '')
  .toString()
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .toLowerCase()
  .trim();

if (table && searchBox) {
  const rows = Array.from(table.querySelectorAll('tbody tr'));
  const takeName = (tr) => {
    const inp = tr.querySelector('input[name="tenCuocThi"]');
    if (inp && inp.value) return inp.value.trim();
    return (tr.cells?.[1]?.innerText || '').trim();
  };
  const data = rows.map(tr => ({ tr, name: takeName(tr) }));

  // Lọc bảng
  function applyFilter(q) {
    const k = vnNorm(q);
    data.forEach(({ tr, name }) => {
      tr.style.display = (!k || vnNorm(name).includes(k)) ? '' : 'none';
    });
  }

  // ----- Dropdown gợi ý -----
  let activeIdx = -1;
  let itemEls = [];

  function closeList() {
    if (!suggList) return;
    suggList.style.display = 'none';
    suggList.innerHTML = '';
    activeIdx = -1;
    itemEls = [];
  }
  function openList() {
    if (!suggList) return;
    suggList.style.display = 'block';
  }
  function highlightFrag(text, q) {
    const tN = vnNorm(text), qN = vnNorm(q);
    const i = tN.indexOf(qN);
    if (i < 0 || !q) return text;
    return text.slice(0, i) + '<strong>' + text.slice(i, i + q.length) + '</strong>' + text.slice(i + q.length);
  }
  function renderList(q) {
    if (!suggList) return;
    const k = vnNorm(q);
    const matches = !k ? [] : data.filter(x => vnNorm(x.name).includes(k)).slice(0, 8);
    if (!matches.length) {
      suggList.innerHTML = `<div class="sugg-empty">Không có gợi ý phù hợp</div>`;
      openList(); activeIdx = -1; itemEls = []; return;
    }
    suggList.innerHTML = matches.map((m, i) => {
      const statusEl = m.tr.querySelector('[data-status]');
      const status = statusEl ? (statusEl.dataset.status || '') :
                    (m.tr.textContent.includes('Đang bật') ? 'Bật' :
                     m.tr.textContent.includes('Đang tắt') ? 'Tắt' : '');
      return `
        <div class="sugg-item" data-idx="${i}">
          <span class="sugg-badge"></span>
          <div class="sugg-name">${highlightFrag(m.name, q)}</div>
          <div class="sugg-status">${status}</div>
        </div>`;
    }).join('');
    itemEls = Array.from(suggList.querySelectorAll('.sugg-item'));
    activeIdx = -1;
    openList();
    itemEls.forEach(el => {
      el.addEventListener('click', () => {
        const i = Number(el.dataset.idx);
        const name = matches[i].name;
        searchBox.value = name;
        applyFilter(name);
        closeList();
        searchBox.focus();
      });
    });
  }

  // Gõ: mở gợi ý + lọc realtime
  let t;
  searchBox.addEventListener('input', () => {
    clearTimeout(t);
    t = setTimeout(() => {
      const v = searchBox.value;
      if (!v.trim()) { closeList(); applyFilter(''); return; }
      renderList(v);
      applyFilter(v);
    }, 60);
  });

  // Điều hướng: ↑/↓/Enter/Esc
  searchBox.addEventListener('keydown', (e) => {
    if (!suggList || suggList.style.display !== 'block') {
      if (e.key === 'Enter') applyFilter(searchBox.value);
      return;
    }
    if (!itemEls.length) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      activeIdx = (activeIdx + 1) % itemEls.length;
      itemEls.forEach((el,i)=>el.classList.toggle('is-active', i===activeIdx));
      itemEls[activeIdx].scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      activeIdx = (activeIdx - 1 + itemEls.length) % itemEls.length;
      itemEls.forEach((el,i)=>el.classList.toggle('is-active', i===activeIdx));
      itemEls[activeIdx].scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (activeIdx >= 0) itemEls[activeIdx].click();
      else { applyFilter(searchBox.value); closeList(); }
    } else if (e.key === 'Escape') {
      closeList();
    }
  });

  // Click ngoài để đóng
  document.addEventListener('click', (e) => {
    if (suggList && !suggList.contains(e.target) && e.target !== searchBox) closeList();
  });
}
  // ===== Popup "Cấu hình đã thêm" =====
  const viewModal = document.getElementById('tpl-view-modal');
  const viewContent = document.getElementById('tplv-content');
  const viewClose = document.getElementById('tplv-close');

  // Uỷ quyền click cho tất cả nút data-open-tpl-view
  document.body.addEventListener('click', function (e) {
    const btn = e.target.closest('[data-open-tpl-view]');
    if (!btn) return;

    const targetId = btn.getAttribute('data-target');
    const src = document.getElementById(targetId);
    if (!src) return;

    // copy HTML vào modal
    viewContent.innerHTML = src.innerHTML;
// ===== Làm sạch nội dung bảng trong popup =====
const rows = viewContent.querySelectorAll('tbody tr');

function stripCodes(txt) {
  // Bỏ tiền tố "BT123 - ", "VT02 - " ở bất kỳ vị trí nào
  txt = txt.replace(/\b(?:BT|VT)\d+\s*-\s*/gi, '');
  // Bỏ số trong ngoặc vuông: [1], [ 2 ], [10]
  txt = txt.replace(/\[\s*\d+\s*\]\s*/g, '');
  // Gộp dấu cách/thanh nối thừa
  txt = txt.replace(/\s*[-–—]\s*/g, ' - ');
  txt = txt.replace(/\s{2,}/g, ' ').trim();
  // Bỏ " - " ở đầu/cuối nếu lỡ dư
  txt = txt.replace(/^-\s+/, '').replace(/\s+-$/, '').trim();
  return txt;
}

rows.forEach(tr => {
  const tdSection = tr.cells?.[0];
  const tdItem    = tr.cells?.[1];

  if (!tdSection || !tdItem) return;

  // Làm sạch chung
  let s = stripCodes(tdSection.textContent || '');
  let i = stripCodes(tdItem.textContent || '');

  // Bỏ phần lặp "Mục lớn" trong "Mục nhỏ" nhưng KHÔNG để trống "Mục nhỏ"
  const sLower = s.toLowerCase();
  let iLower = i.toLowerCase();

  if (sLower) {
    // Các phân cách thường gặp sau phần lặp
    const seps = [' - ', ' — ', ': ', ' – ', ' —', '-', ':'];
    let trimmed = false;

    for (const sep of seps) {
      const prefix = sLower + sep.toLowerCase();
      if (iLower.startsWith(prefix)) {
        const rest = i.slice(prefix.length).trim();
        if (rest) {            // chỉ cắt khi có phần dư
          i = rest;
          iLower = i.toLowerCase();
          trimmed = true;
        }
        break;                  // gặp 1 sep là dừng
      }
    }

    // Nếu chưa cắt bằng sep, xem trường hợp i bắt đầu đúng bằng s (không có sep)
    if (!trimmed && iLower.startsWith(sLower) && iLower.length > sLower.length) {
      const rest = i.slice(s.length).replace(/^[-–—:]\s*/, '').trim();
      if (rest) i = rest;      // chỉ nhận nếu còn nội dung
    }
  }

  // Nếu vì bất kỳ lý do gì i rỗng → giữ nguyên như s để "Mục nhỏ" không bị trống
  if (!i) {
    i = s;
  }

  // Gán lại text đã làm sạch
  tdSection.textContent = s;
  tdItem.textContent    = i;

});
    // mở modal (flex)
    viewModal.style.display = 'flex';
  });

  // đóng modal
  if (viewClose) {
    viewClose.addEventListener('click', () => viewModal.style.display = 'none');
  }
  // click nền để đóng
  viewModal.addEventListener('click', (e) => {
    if (e.target === viewModal) viewModal.style.display = 'none';
  });

  console.log('[organize] JS ready');
});
