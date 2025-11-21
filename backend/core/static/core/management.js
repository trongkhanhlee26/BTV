const card = document.getElementById('contestCard');
const modal = document.getElementById('contestModal');
const closeBtn = document.getElementById('closeModal');

if (card && modal && closeBtn) {
    card.addEventListener('click', () => modal.classList.remove('hidden'));
    closeBtn.addEventListener('click', () => modal.classList.add('hidden'));
    modal.addEventListener('click', e => {
        if (e.target === modal) modal.classList.add('hidden');
    });
}
// Ngăn không cho cuộn cả trang khi đang cuộn trong bảng xếp hạng
const rankingWrapper = document.querySelector('.ranking-table-wrapper');

if (rankingWrapper) {
    rankingWrapper.addEventListener('wheel', (e) => {
        const deltaY = e.deltaY;
        const scrollTop = rankingWrapper.scrollTop;
        const height = rankingWrapper.clientHeight;
        const scrollHeight = rankingWrapper.scrollHeight;

        const atTop = scrollTop === 0;
        const atBottom = scrollTop + height >= scrollHeight - 1;

        // Nếu đã tới đầu hoặc cuối bảng thì chặn không cho sự kiện “lọt” ra ngoài
        if ((deltaY < 0 && atTop) || (deltaY > 0 && atBottom)) {
            e.preventDefault();
            e.stopPropagation();
        }
    }, { passive: false });
}
