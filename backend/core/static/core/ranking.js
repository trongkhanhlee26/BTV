  (function(){
    const table = document.getElementById('rankTable');
    if(!table) return;

    const tbody = document.getElementById('rankBody');
    const rows  = Array.from(tbody.querySelectorAll('tr'));
    const pageSize      = parseInt(table.dataset.pageSize || '10', 10);
    const intervalMs    = parseInt(table.dataset.intervalMs || '3000', 10);
    const colGroupSize  = parseInt(table.dataset.colGroupSize || '5', 10);
    const pageInfoEl    = document.getElementById('pageInfo');

    if(rows.length === 0) return;

    // Xác định index cột cố định và cột bài thi
    const ths = Array.from(table.tHead.rows[0].cells);
    const totalIndex = ths.length - 1;                // cột "Tổng" là cuối
    const fixedIdxSet = new Set([0,1,2,3,totalIndex]); // #, Mã NV, Họ tên, Đơn vị, Tổng
    const allIdx = ths.map((_,i)=>i);
    const varIdx = allIdx.filter(i => !fixedIdxSet.has(i)); // các cột bài thi ở giữa

    // --- Tạo nhóm cột bài thi theo quy tắc “chạm đuôi và đủ G cột” ---
    const varCount = varIdx.length;
    const colGroups = [];

    // Nhóm theo bước G: [0..G-1], [G..2G-1], ... (nhóm cuối có thể bị ngắn)
    for (let start = 0; start < varCount; start += colGroupSize) {
    const end = Math.min(start + colGroupSize, varCount);
    colGroups.push(varIdx.slice(start, end));
    }

    // Nếu có nhóm cuối bị NGẮN và tổng số cột > G
    if (varCount > colGroupSize && (varCount % colGroupSize) !== 0) {
    // Tạo nhóm “chạm đuôi”: đủ G cột, kết thúc tại cột cuối
    const tailStart = varCount - colGroupSize;     // ví dụ 13-5=8 → (index 8 là cột thứ 9)
    const tailGroup = varIdx.slice(tailStart, varCount);
    // Thay THẲNG nhóm CUỐI (ngắn) bằng tailGroup (đủ G) — KHÔNG push thêm
    colGroups[colGroups.length - 1] = tailGroup;
    }

    const totalColGroups = Math.max(1, colGroups.length);


    const totalRowPages  = Math.ceil(rows.length / pageSize);
    let rowPage = 0;   // trang người
    let colGroup = 0;  // nhóm cột bài thi

    function applyColumnVisibility(){
      const showIdx = new Set([ ...fixedIdxSet, ...colGroups[colGroup] ]);
      // Header
      ths.forEach((th, i) => { th.style.display = showIdx.has(i) ? '' : 'none'; });
      // Body rows
      rows.forEach(tr => {
        const cells = Array.from(tr.cells);
        cells.forEach((td, i) => { td.style.display = showIdx.has(i) ? '' : 'none'; });
      });
    }

    function showRowPage(){
      // Ẩn/Hiện 10 người theo trang
      rows.forEach(r => r.style.display = 'none');
      const start = rowPage * pageSize;
      const end = Math.min(start + pageSize, rows.length);
      for(let i=start; i<end; i++){ rows[i].style.display = ''; }
      // Áp nhóm cột
      applyColumnVisibility();

      if(pageInfoEl){
        pageInfoEl.textContent = `Trang người ${rowPage+1}/${totalRowPages} • Nhóm cột ${colGroup+1}/${totalColGroups}`;
      }
    }

    function advance(){
      // Tiến nhóm cột trước; hết nhóm thì sang 10 người tiếp theo
      colGroup++;
      if(colGroup >= totalColGroups){
        colGroup = 0;
        rowPage = (rowPage + 1) % totalRowPages;
      }
      showRowPage();
    }

    let timer = null;
    function startTimer(){ stopTimer(); timer = setInterval(advance, intervalMs); }
    function stopTimer(){ if(timer){ clearInterval(timer); timer = null; } }
    function jumpNext(){ advance(); startTimer(); }

    // Init
    showRowPage();
    startTimer();

    // Click bảng → sang nhóm cột kế (hết nhóm thì sang người kế)
    table.addEventListener('click', jumpNext);

    // Phím tắt: → tiến nhóm, ← lùi nhóm (có lùi "chạm đuôi" tương ứng)
    document.addEventListener('keydown', (e) => {
      if(e.key === 'ArrowRight'){
        e.preventDefault(); jumpNext();
      } else if(e.key === 'ArrowLeft'){
        e.preventDefault();
        colGroup--;
        if(colGroup < 0){
          colGroup = totalColGroups - 1;
          rowPage = (rowPage - 1 + totalRowPages) % totalRowPages;
        }
        showRowPage(); startTimer();
      }
    }, { passive: false });

    // Pause khi hover controls (select), không ảnh hưởng bảng
    const controls = document.querySelector('.controls');
    if(controls){
      controls.addEventListener('mouseenter', stopTimer);
      controls.addEventListener('mouseleave', startTimer);
    }

    // Giữ đúng hiển thị khi resize
    window.addEventListener('resize', () => { showRowPage(); });
  })();