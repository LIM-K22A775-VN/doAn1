/* 
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/ClientSide/javascript.js to edit this template
 */
document.addEventListener("DOMContentLoaded", function () {
    // ==== Tăng giảm số lượng ====
    const dish = document.querySelector('.dish');
    const btnMinus = dish.querySelector('.quantity button:first-child');
    const btnPlus = dish.querySelector('.quantity button:last-child');
    const quantitySpan = dish.querySelector('.quantity span');

    let quantity = parseInt(quantitySpan.textContent);

    btnPlus.addEventListener('click', function () {
        quantity++;
        quantitySpan.textContent = quantity;
    });

    btnMinus.addEventListener('click', function () {
        if (quantity > 1) {
            quantity--;
            quantitySpan.textContent = quantity;
        }
    });

    // ==== Thêm vào yêu thích ====
    const favoriteBtn = dish.querySelector('.favorite');
    const heartIcon = favoriteBtn.querySelector('i');

    favoriteBtn.addEventListener('click', function (e) {
        e.preventDefault(); // Ngăn chuyển trang nếu là thẻ <a>
        heartIcon.classList.toggle('active-heart');
    });

    // ==== Chuyển tab (Mô tả / Đánh giá / Chính sách) ====
    const tabButtons = document.querySelectorAll(".tab-btn");
    const tabContents = document.querySelectorAll(".tab-content");

    tabButtons.forEach(button => {
        button.addEventListener("click", () => {
            // Reset trạng thái
            tabButtons.forEach(btn => btn.classList.remove("active"));
            tabContents.forEach(content => content.classList.remove("active"));

            // Kích hoạt tab được click
            button.classList.add("active");
            const selectedTab = button.dataset.tab;
            document.getElementById(selectedTab).classList.add("active");
        });
    });
    const stars = document.querySelectorAll(".star-rating .star");

    stars.forEach((star, index) => {
        star.addEventListener("click", () => {
            stars.forEach((s, i) => {
                s.classList.toggle("selected", i <= index);
            });
        });
    });

    // Gửi đánh giá (mẫu)
    const submitBtn = document.querySelector(".submit-feedback");
    if (submitBtn) {
        submitBtn.addEventListener("click", () => {
            const rating = [...stars].filter(s => s.classList.contains("selected")).length;
            const feedback = document.getElementById("user-feedback").value;
            if (rating === 0 || feedback.trim() === "") {
                alert("Vui lòng chọn số sao và nhập góp ý.");
            } else {
                alert(`Bạn đã đánh giá ${rating} sao\nGóp ý: ${feedback}`);
                // Sau này có thể gửi lên server tại đây
            }
        });
    }
});