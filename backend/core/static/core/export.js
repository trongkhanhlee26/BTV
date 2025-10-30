/* Build bảng, sticky cột trái, filter & sort, tải XLSX (JS thuần) */

(function () {
  const columns = window.EXPORT_COLUMNS || [];
  const rows = window.EXPORT_ROWS || [];
  const FROZEN = window.FROZEN_COUNT || 3;

  const head = document.getElementById('head-row');
  const filter = document.getElementById('filter-row');
  const body = document.getElementById('body-rows');
  const table = document.getElementById('exportTable');

  // --- Render header + filter ---
  columns.forEach((name, i) => {
    const th = document.createElement('th');
    th.textContent = name;
    th.dataset.index = i;
    th.classList.add('col-min');
    if (i === 0) th.classList.add('col-stt');
    if (i === 1) th.classList.add('col-id');
    if (i === 2) th.classList.add('col-name');

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
  let viewRows = rows.map((r, idx) => ({ r, _i: idx })); // keep stable index for sort stability
  function renderBody(data = viewRows) {
    body.innerHTML = '';
    const frag = document.createDocumentFragment();
    data.forEach(({ r }) => {
      const tr = document.createElement('tr');
      r.forEach((cell, i) => {
        const td = document.createElement('td');
        td.textContent = (cell === null || cell === undefined) ? '' : cell;
        if (i === 0) td.classList.add('col-stt');
        if (i === 1) td.classList.add('col-id');
        if (i === 2) td.classList.add('col-name');
        tr.appendChild(td);
      });
      frag.appendChild(tr);
    });
    body.appendChild(frag);
    applySticky(); // re-calc sticky after render
    document.dispatchEvent(new Event('export:rendered')); // <-- thêm dòng này
  }
  renderBody();

  // --- Filtering ---
  function applyFilters() {
    const inputs = Array.from(filter.querySelectorAll('input'));
    const terms = inputs.map(ip => ip.value.trim().toLowerCase());
    const filtered = rows.map((r, idx) => ({ r, _i: idx })).filter(({ r }) => {
      return terms.every((q, i) => {
        if (!q) return true;
        const val = (r[i] ?? '').toString().toLowerCase();
        return val.includes(q);
      });
    });
    // keep current sort order if any
    if (sortState.index !== null) {
      filtered.sort(compare(sortState.index, sortState.dir));
    }
    renderBody(filtered);
    viewRows = filtered;
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
      th.textContent = columns[j] + (j === sortState.index ? (sortState.dir === 1 ? ' ▲' : ' ▼') : '');
    });
  }
  function compare(i, dir) {
    return (a, b) => {
      const va = a.r[i], vb = b.r[i];
      const na = parseFloat(va), nb = parseFloat(vb);
      const isNum = !isNaN(na) && !isNaN(nb);
      if (isNum) return (na - nb) * dir || (a._i - b._i);
      return (va ?? '').toString().localeCompare((vb ?? '').toString(), 'vi', { numeric: true }) * dir || (a._i - b._i);
    };
  }

  // --- Sticky frozen columns (3 cột trái) ---
  function applySticky() {
    // clear previous sticky classes
    table.querySelectorAll('.sticky-col,.sticky-col-1,.sticky-col-2,.sticky-shadow').forEach(el => {
      el.classList.remove('sticky-col','sticky-col-1','sticky-col-2','sticky-shadow');
      el.style.left = '';
    });

    const colWidths = [];
    // measure widths from thead
    Array.from(head.children).forEach((th, i) => {
      colWidths[i] = th.getBoundingClientRect().width;
    });

    const left0 = 0;
    const left1 = left0 + (colWidths[0] || 0);
    const left2 = left1 + (colWidths[1] || 0);

    // set CSS vars for sticky lefts
    table.style.setProperty('--col-left-1', left1 + 'px');
    table.style.setProperty('--col-left-2', left2 + 'px');
    lockWidths(colWidths);
    // apply sticky classes for first 3 columns
    const applyForRow = (rowEl) => {
      const cells = rowEl.children;
      if (!cells.length) return;
      cells[0].classList.add('sticky-col','sticky-shadow');                 // STT
      cells[1].classList.add('sticky-col','sticky-col-1','sticky-shadow');  // Mã NV
      cells[2].classList.add('sticky-col','sticky-col-2','sticky-shadow');  // Họ tên
      // set exact lefts for first column too
      cells[0].style.left = left0 + 'px';
    };
    // head
    applyForRow(head);
    applyForRow(filter);
    // body
    body.querySelectorAll('tr').forEach(applyForRow);
  }
  window.addEventListener('resize', applySticky);
  new ResizeObserver(applySticky).observe(table);
  // Public helper để tương thích snippet bạn gửi:
function setStickyOffsets() {
  // Giữ 1 nguồn sự thật: dùng lại đo đạc từ applySticky()
  applySticky();
}

// Gọi khi trang load xong (resize đã có ở trên)
window.addEventListener('load', setStickyOffsets);

// (Tùy chọn) Nếu nơi khác cần, có thể gọi window.setStickyOffsets()
window.setStickyOffsets = setStickyOffsets;

// --- Xuất XLSX (thực chất CSV TAB, Excel đọc tốt) ---
function toCSV(cols, data) {
  const esc = (v) => {
    const s = (v===null||v===undefined) ? '' : String(v);
    // Nếu có tab, dấu " hoặc xuống dòng → bọc bằng dấu "
    return /["\t\n]/.test(s) ? `"${s.replace(/"/g,'""')}"` : s;
  };
  const head = cols.map(esc).join('\t');
  const body = data.map(({r}) => r.map(esc).join('\t')).join('\n');
  // Excel hiểu delimiter qua dòng đầu tiên
  return 'sep=\t\n' + head + '\n' + body;
}

document.getElementById('btn-download-xlsx')?.addEventListener('click', () => {
  const csv = toCSV(columns, viewRows);
  // **THÊM BOM UTF-8** để Excel nhận đúng Unicode
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
  const a = document.createElement('a');
  const ts = new Date().toISOString().replace(/[:.]/g,'-');
  a.href = URL.createObjectURL(blob);
  a.download = `export_${ts}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
});
function lockWidths(widths) {
  // head
  Array.from(head.children).forEach((th, i) => {
    const w = widths[i] || th.getBoundingClientRect().width;
    th.style.width = w + 'px';
    th.style.minWidth = w + 'px';
    th.style.maxWidth = w + 'px';
  });
  // filter-row
  Array.from(filter.children).forEach((th, i) => {
    const w = widths[i] || th.getBoundingClientRect().width;
    th.style.width = w + 'px';
    th.style.minWidth = w + 'px';
    th.style.maxWidth = w + 'px';
  });
  // body
  body.querySelectorAll('tr').forEach(tr => {
    Array.from(tr.children).forEach((td, i) => {
      const w = widths[i] || td.getBoundingClientRect().width;
      td.style.width = w + 'px';
      td.style.minWidth = w + 'px';
      td.style.maxWidth = w + 'px';
    });
  });
}

})();
