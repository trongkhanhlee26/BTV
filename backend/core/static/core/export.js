/* Build bảng, sticky cột trái, filter & sort (không còn phần xuất CSV phía client) */

(function () {
  const columns = window.EXPORT_COLUMNS || [];
  const rows = window.EXPORT_ROWS || [];
  const FROZEN = window.FROZEN_COUNT || 3;

  const head = document.getElementById('head-row');
  const filter = document.getElementById('filter-row');
  const body = document.getElementById('body-rows');
  const table = document.getElementById('exportTable');

  const fmtHeader = (title) => {
    // Hỗ trợ hiển thị "Vòng...\nBài thi..." thành 2 dòng
    const s = (title ?? '').toString();
    return s.replace(/\n/g, '<br>');
  };

  // --- Render header + filter ---
  columns.forEach((name, i) => {
    const th = document.createElement('th');
    th.innerHTML = fmtHeader(name);        // đổi textContent -> innerHTML
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
  let viewRows = rows.map((r, idx) => ({ r, _i: idx }));
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
    applySticky();
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
      const base = columns[j];
      th.innerHTML = fmtHeader(base + (j === sortState.index ? (sortState.dir === 1 ? ' ▲' : ' ▼') : ''));
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
    table.querySelectorAll('.sticky-col,.sticky-col-1,.sticky-col-2,.sticky-shadow').forEach(el => {
      el.classList.remove('sticky-col','sticky-col-1','sticky-col-2','sticky-shadow');
      el.style.left = '';
    });

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
  window.addEventListener('resize', applySticky);
  new ResizeObserver(applySticky).observe(table);
})();
