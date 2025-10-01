const toggleBtn = document.getElementById('toggleSidebar');
const sidebar = document.getElementById('sidebar');

toggleBtn.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
});

// Toggle notification
const notificationBtn = document.getElementById("notificationBtn");
const notificationBox = document.getElementById("notificationBox");
notificationBtn.addEventListener("click", () => {
    notificationBox.style.display = notificationBox.style.display === "block" ? "none" : "block";
});

// Toggle user dropdown
const usernameDisplay = document.getElementById("usernameDisplay");
const userDropdown = document.getElementById("userDropdown");
usernameDisplay.addEventListener("click", () => {
    userDropdown.style.display = userDropdown.style.display === "block" ? "none" : "block";
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

// Handle logout
const logoutBtn = document.getElementById("logoutBtn");
logoutBtn.addEventListener("click", (e) => {
    e.preventDefault();
    localStorage.setItem("isLoggedIn", "false");
    localStorage.removeItem("username");
    authButtons.style.display = "flex";
    userInfo.style.display = "none";
    userDropdown.style.display = "none";
    window.location.href = "dashboard_staff.html";
});

// Ẩn thông báo và dropdown khi click ra ngoài
window.addEventListener('click', function (e) {
    if (!notificationBox.contains(e.target) && !notificationBtn.contains(e.target)) {
        notificationBox.style.display = 'none';
    }
    if (!userDropdown.contains(e.target) && usernameDisplay && !usernameDisplay.contains(e.target)) {
        userDropdown.style.display = 'none';
    }
});

const isLoggedIn = localStorage.getItem("isLoggedIn") === "true";
const username = localStorage.getItem("username") || "Người dùng";

const authButtons = document.getElementById("authButtons");
const userInfo = document.getElementById("userInfo");

if (isLoggedIn) {
    authButtons.style.display = "none";
    userInfo.style.display = "flex";
} else {
    authButtons.style.display = "flex";
    userInfo.style.display = "none";
}