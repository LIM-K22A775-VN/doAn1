/* 
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/ClientSide/javascript.js to edit this template
 */
    const toggleBtn = document.getElementById('toggleSidebar');
    const sidebar = document.getElementById('sidebar');
    const submenuToggles = document.querySelectorAll('.submenu-toggle');

    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
    });

    submenuToggles.forEach(toggle => {
      toggle.addEventListener('click', e => {
        e.preventDefault();
        toggle.parentElement.classList.toggle('open');
      });
    });
    // Toggle notification
  const notificationBtn = document.getElementById("notificationBtn");
  const notificationBox = document.getElementById("notificationBox");
  notificationBtn.addEventListener("click", () => {
    notificationBox.style.display = notificationBox.style.display === "block" ? "none" : "block";
  });

  // Toggle full screen
  const fullscreenBtn = document.getElementById("fullscreenBtn");
  fullscreenBtn.addEventListener("click", () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  });

  // Ẩn thông báo khi click ra ngoài
  window.addEventListener('click', function(e) {
    if (!notificationBox.contains(e.target) && !notificationBtn.contains(e.target)) {
      notificationBox.style.display = 'none';
    }
  });