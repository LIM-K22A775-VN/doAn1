/* 
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/ClientSide/javascript.js to edit this template
 */
function toggleDropdown() {
        const menu = document.getElementById("dropdownMenu");
        menu.style.display = (menu.style.display === "block") ? "none" : "block";
    }

    // Đóng dropdown khi click ra ngoài
    document.addEventListener("click", function (e) {
        const dropdown = document.getElementById("accoundropdownMenutDropdown");
        const menu = document.getElementById("");
        if (!dropdown.contains(e.target)) {
            menu.style.display = "none";
        }
    });