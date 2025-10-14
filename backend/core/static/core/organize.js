(function(){
  // Ẩn/hiện "Điểm tối đa" theo lựa chọn phương thức chấm trong form "Thêm bài"
  document.querySelectorAll('form').forEach(function(f){
    const sel = f.querySelector('select[name="phuongThucCham"]');
    if(!sel) return;
    const maxLabel = f.querySelector('.js-max-label');
    const maxInput = f.querySelector('.js-max-input');
    function sync(){
      if(sel.value === 'POINTS'){
        if(maxLabel) maxLabel.style.display = '';
        if(maxInput) { maxInput.style.display = ''; maxInput.required = true; }
      } else {
        if(maxLabel) maxLabel.style.display = 'none';
        if(maxInput) { maxInput.style.display = 'none'; maxInput.required = false; maxInput.value = ''; }
      }
    }
    sel.addEventListener('change', sync);
    sync();
  });

  // Modal cấu hình thời gian
  const modal = document.getElementById('time-modal');
  const rowsBox = document.getElementById('tm-rows');
  const btnClose = document.getElementById('tm-close');
  const btnAdd = document.getElementById('tm-add');
  const inputBT = document.getElementById('tm-btid');
  const inputJSON = document.getElementById('tm-json');
  const form = document.getElementById('tm-form');

  function openModal(btid, rules){
    inputBT.value = btid;
    rowsBox.innerHTML = '';
    (rules || []).forEach(addRowFromObj);
    modal.style.display = 'flex';
  }
  function closeModal(){ modal.style.display = 'none'; }

  function addRowFromObj(obj){
    addRow(obj?.start ?? '', obj?.end ?? '', obj?.score ?? '');
  }
  function addRow(start, end, score){
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
    row.querySelector('.tm-del').addEventListener('click', ()=>row.remove());
    rowsBox.appendChild(row);
  }

  // mở modal khi click
  document.querySelectorAll('[data-open-time-modal]').forEach(function(btn){
    btn.addEventListener('click', function(){
      const btid = this.getAttribute('data-btid');
      let rules = [];
      try { rules = JSON.parse(this.getAttribute('data-rules') || '[]'); } catch(e){}
      openModal(btid, rules);
    });
  });

  btnAdd?.addEventListener('click', ()=>addRow('','',''));
  btnClose?.addEventListener('click', closeModal);
  modal?.addEventListener('click', (e)=>{ if(e.target===modal) closeModal(); });

  // submit: gom dữ liệu → JSON
  form?.addEventListener('submit', function(e){
    const rows = [];
    rowsBox.querySelectorAll('.row').forEach(function(r){
      const s = r.querySelector('.tm-start')?.value || '0';
      const e2 = r.querySelector('.tm-end')?.value || '0';
      const sc = r.querySelector('.tm-score')?.value || '0';
      rows.push({start: parseInt(s,10)||0, end: parseInt(e2,10)||0, score: parseInt(sc,10)||0});
    });
    inputJSON.value = JSON.stringify(rows);
  });
})();
