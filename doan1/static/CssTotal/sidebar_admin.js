/* 
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/ClientSide/javascript.js to edit this template
 */
const submenuToggles = document.querySelectorAll('.submenu-toggle');

submenuToggles.forEach(toggle => {
    toggle.addEventListener('click', e => {
        e.preventDefault();
        const parent = toggle.parentElement;
        const isOpen = parent.classList.contains('open');

        // Đóng tất cả submenu khác
        document.querySelectorAll('.has-submenu').forEach(item => {
            if (item !== parent) {
                item.classList.remove('open');
            }
        });

        // Toggle submenu hiện tại
        parent.classList.toggle('open');
    });
});

//// Xử lý active cho submenu dựa trên URL
//document.addEventListener('DOMContentLoaded', function () {
//    const links = document.querySelectorAll('.submenu li a');
//    const currentPath = window.location.pathname;
//
//    links.forEach(link => {
//        const href = link.getAttribute('href');
//        if (href && currentPath.includes(href)) {
//            link.classList.add('active');
//            // Mở submenu cha
//            const parent = link.closest('.has-submenu');
//            if (parent) {
//                parent.classList.add('open');
//            }
//        }
//    });
//});

