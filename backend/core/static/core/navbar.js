// navbar.js
(function () {
    const btn  = document.getElementById('navUserBtn');
    const menu = document.getElementById('navDropdown');
    if (!btn || !menu) return;

    function syncWidth() {
    // đặt chiều rộng dropdown = bề ngang nút gmail (pill)
    menu.style.width = btn.offsetWidth + 'px';
    }

    function openMenu() {
    syncWidth();
    menu.classList.remove('hidden');
    }
    function toggle() {
    if (menu.classList.contains('hidden')) openMenu();
    else menu.classList.add('hidden');
    }
    function close()  { menu.classList.add('hidden'); }

    btn.addEventListener('click', toggle);
    window.addEventListener('resize', () => {
    if (window.innerWidth >= 768) close();
    else if (!menu.classList.contains('hidden')) syncWidth();
    });


    // click ra ngoài → đóng
    document.addEventListener('click', (e) => {
        if (menu.classList.contains('hidden')) return;
        if (e.target === btn || btn.contains(e.target)) return;
        if (menu.contains(e.target)) return;
        close();
    });

    // nhấn ESC → đóng
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') close();
    });

    // đổi lên desktop → đóng
    window.addEventListener('resize', () => {
        if (window.innerWidth >= 768) close();
    });
})();
