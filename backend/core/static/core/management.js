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