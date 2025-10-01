
        setTimeout(function () {
            const toast = document.getElementById('toast');
            if (toast) {
                toast.style.opacity = '0';
                setTimeout(() => toast.remove(), 500); // Xóa hẳn sau fade out
            }
        }, 3000);
 
    // <!-- thong bao doi mat khau thanh cong -->