/* Build bảng, filter/sort, sticky 3 cột trái + AUTO-FIT WIDTH THEO NỘI DUNG */

(function () {
  const columns = window.EXPORT_COLUMNS || [];
  const rows = window.EXPORT_ROWS || [];
  const FROZEN = window.FROZEN_COUNT || 3;

  const head = document.getElementById('head-row');
  const filter = document.getElementById('filter-row');
  const body = document.getElementById('body-rows');
  const table = document.getElementById('exportTable');
    // ===== CẤU HÌNH WIDTH CỐ ĐỊNH CHO CỘT "BÀI THI" =====
    const SCORE_COL_WIDTH = 100;   // px. Có thể chỉnh 96 / 110 tùy ý.
    const SCORE_COL_MIN   = 90;    // px. Sàn để tránh hẹp quá.
    const SCORE_COL_MAX   = 140;   // px. Trần nếu bạn muốn nới.
    // Nhận diện cột "bài thi": tiêu đề có xuống dòng (Vòng...\nBài thi...)
    // Nếu sau này bạn muốn chỉ định thủ công từ cột thứ N trở đi: đổi implement ở hàm isScoreCol.
    const isScoreCol = (headerText, index) => {
    return String(headerText || '').includes('\n');
    };

  // --- Utilities ---
  const fmtHeader = (title) => (title ?? '').toString().replace(/\n/g, '<br>');

  // --- Render header + filter ---
  columns.forEach((name, i) => {
    const th = document.createElement('th');
    th.innerHTML = fmtHeader(name);
    th.dataset.index = i;
    // sort
    th.style.cursor = 'pointer';
    th.addEventListener('click', () => toggleSort(i));
    head.appendChild(th);

    // filter inputs
    const fh = document.createElement('th');
    const ip = document.createElement('input');
    ip.placeholder = 'Lọc...';
    ip.dataset.index = i;
    ip.addEventListener('input', applyFilters);
    fh.appendChild(ip);
    filter.appendChild(fh);
  });

  // --- Render body ---
  let viewRows = rows.map((r, idx) => ({ r, _i: idx }));
  function renderBody(data = viewRows) {
    body.innerHTML = '';
    const frag = document.createDocumentFragment();
    data.forEach(({ r }) => {
      const tr = document.createElement('tr');
      r.forEach((cell, i) => {
        const td = document.createElement('td');
        td.textContent = (cell === null || cell === undefined) ? '' : cell;
        tr.appendChild(td);
      });
      frag.appendChild(tr);
    });
    body.appendChild(frag);

    autoFit();   // đo & set width mỗi lần render
    applySticky();
  }
  renderBody();

  // --- Filtering ---
  function applyFilters() {
    const inputs = Array.from(filter.querySelectorAll('input'));
    const terms = inputs.map(ip => ip.value.trim().toLowerCase());
    const filtered = rows.map((r, idx) => ({ r, _i: idx })).filter(({ r }) =>
      terms.every((q, i) => !q || (r[i] ?? '').toString().toLowerCase().includes(q))
    );
    if (sortState.index !== null) filtered.sort(compare(sortState.index, sortState.dir));
    viewRows = filtered;
    renderBody(filtered);
  }

  // --- Sorting ---
  const sortState = { index: null, dir: 1 }; // 1=asc, -1=desc
  function toggleSort(i) {
    if (sortState.index === i) sortState.dir *= -1;
    else { sortState.index = i; sortState.dir = 1; }
    viewRows.sort(compare(i, sortState.dir));
    renderBody(viewRows);
    // UI cue
    Array.from(head.children).forEach((th, j) => {
      const base = columns[j] || '';
      th.innerHTML = fmtHeader(base + (j === sortState.index ? (sortState.dir === 1 ? ' ▲' : ' ▼') : ''));
    });
  }
  function compare(i, dir) {
    return (a, b) => {
      const va = a.r[i], vb = b.r[i];
      const na = parseFloat(va), nb = parseFloat(vb);
      const isNum = !isNaN(na) && !isNaN(nb);
      if (isNum) return (na - nb) * dir || (a._i - b._i);
      return (String(va ?? '')).localeCompare(String(vb ?? ''), 'vi', { numeric: true }) * dir || (a._i - b._i);
    };
  }

  // --- Auto-fit width theo nội dung ---
function autoFit() {
  // Tạo/đảm bảo colgroup
  let colgroup = table.querySelector('colgroup');
  if (!colgroup) {
    colgroup = document.createElement('colgroup');
    for (let i = 0; i < columns.length; i++) colgroup.appendChild(document.createElement('col'));
    table.insertBefore(colgroup, table.firstChild);
  } else {
    // sync số col
    const diff = columns.length - colgroup.children.length;
    if (diff > 0) for (let i = 0; i < diff; i++) colgroup.appendChild(document.createElement('col'));
    if (diff < 0) for (let i = 0; i < -diff; i++) colgroup.lastElementChild.remove();
  }

  // Measurer
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');

  // Lấy style để biết font & padding
  const anyTH = head.children[0];
  const anyTD = body.querySelector('td');
  const thStyle = anyTH ? getComputedStyle(anyTH) : null;
  const tdStyle = anyTD ? getComputedStyle(anyTD) : null;

  const thPadX = thStyle ? (parseFloat(thStyle.paddingLeft) + parseFloat(thStyle.paddingRight)) : 16;
  const tdPadX = tdStyle ? (parseFloat(tdStyle.paddingLeft) + parseFloat(tdStyle.paddingRight)) : 16;

  const thFont = thStyle ? `${thStyle.fontWeight} ${thStyle.fontSize} ${thStyle.fontFamily}` : '700 16px system-ui';
  const tdFont = tdStyle ? `${tdStyle.fontWeight} ${tdStyle.fontSize} ${tdStyle.fontFamily}` : '400 14px system-ui';

  const buffer = 18;           // đệm thêm cho dễ thở
  const MAX_COL = 480;         // trần cho cột auto-fit
  const MIN_DEFAULT = 60;      // sàn cho cột auto-fit

  // Sàn riêng cho 3 cột trái (STT/Mã NV/Họ tên)
  const minFor = (i) => (i === 0 ? 36 : i === 1 ? 70 : i === 2 ? 150 : MIN_DEFAULT);

  for (let i = 0; i < columns.length; i++) {
    const header = columns[i] ? String(columns[i]) : '';

    // ===== Nếu là cột "BÀI THI": set cố định và bỏ đo =====
    if (isScoreCol(header, i)) {
      const fixed = Math.max(SCORE_COL_MIN, Math.min(SCORE_COL_MAX, SCORE_COL_WIDTH));
      colgroup.children[i].style.width = `${fixed}px`;
      continue;
    }

    // ===== Ngược lại (meta/info): auto-fit như cũ =====
    let maxW = 0;

    // đo header (2 dòng tách bằng \n)
    const headerLines = header.split('\n');
    ctx.font = thFont;
    headerLines.forEach(line => {
      const w = ctx.measureText(line).width;
      if (w > maxW) maxW = w;
    });
    maxW += thPadX;

    // đo body cells (giới hạn 200 hàng cho nhanh)
    ctx.font = tdFont;
    const limit = Math.min(viewRows.length, 200);
    for (let r = 0; r < limit; r++) {
      const val = viewRows[r].r[i];
      const text = (val === null || val === undefined) ? '' : String(val);
      const w = ctx.measureText(text).width + tdPadX;
      if (w > maxW) maxW = w;
    }

    const final = Math.max(minFor(i), Math.min(MAX_COL, Math.ceil(maxW + buffer)));
    colgroup.children[i].style.width = `${final}px`;
  }
}


  // --- Sticky frozen columns (3 cột trái) ---
  function applySticky() {
    table.querySelectorAll('.sticky-col,.sticky-col-1,.sticky-col-2,.sticky-shadow').forEach(el => {
      el.classList.remove('sticky-col','sticky-col-1','sticky-col-2','sticky-shadow');
      el.style.left = '';
    });

    // Sau autoFit(), đã có colgroup width → đo lại
    const colWidths = [];
    Array.from(head.children).forEach((th, i) => {
      colWidths[i] = th.getBoundingClientRect().width;
    });

    const left0 = 0;
    const left1 = left0 + (colWidths[0] || 0);
    const left2 = left1 + (colWidths[1] || 0);

    table.style.setProperty('--col-left-1', left1 + 'px');
    table.style.setProperty('--col-left-2', left2 + 'px');

    const applyForRow = (rowEl) => {
      const cells = rowEl.children;
      if (!cells.length) return;
      cells[0].classList.add('sticky-col','sticky-shadow');
      cells[1].classList.add('sticky-col','sticky-col-1','sticky-shadow');
      cells[2].classList.add('sticky-col','sticky-col-2','sticky-shadow');
      cells[0].style.left = left0 + 'px';
    };
    applyForRow(head);
    applyForRow(filter);
    body.querySelectorAll('tr').forEach(applyForRow);
  }

  // Re-calc khi resize/zoom
  window.addEventListener('resize', () => { autoFit(); applySticky(); });

  // fonts có thể load chậm → đo lại sau một vòng frame
  requestAnimationFrame(() => { autoFit(); applySticky(); });
})();
