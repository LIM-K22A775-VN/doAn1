/* 
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/ClientSide/javascript.js to edit this template
 */
document.querySelector('.btn.login').addEventListener('click', function (event) {
    const fullName = document.getElementById('fullName').value;
    const username = document.getElementById('username').value;
    const address = document.getElementById('address').value;
    const email = document.getElementById('email').value;
    const confirmEmail = document.getElementById('confirmEmail').value;
    const phone = document.getElementById('phone').value;
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const avatar = document.getElementById('avatar').files[0];

    if (!fullName || !username || !address || !email || !confirmEmail || !phone || !password || !confirmPassword) {
        alert('Vui lòng điền tất cả các trường.');
        return;
    }

    if (email !== confirmEmail) {
        alert('Email và Email xác nhận không khớp.');
        return;
    }

    if (password !== confirmPassword) {
        alert('Mật khẩu và Nhập lại mật khẩu không khớp.');
        return;
    }

    if (!/^\d{10}$/.test(phone)) {
        alert('Số điện thoại phải là 10 chữ số.');
        return;
    }

    // Optional: Validate avatar (e.g., ensure it's an image)
    if (avatar && !avatar.type.startsWith('image/')) {
        alert('Vui lòng chọn một tệp hình ảnh.');
        return;
    }

    alert('Đăng ký thành công!'); // Replace with actual submission logic
});
