



    // <!-- hiển thị drd tài khoản -->
    //   <!-- Của account (dropdown tài khoản) -->
        document.addEventListener("DOMContentLoaded", function () {
            const toggle = document.querySelector(".account-toggle");
            const dropdown = document.querySelector(".account-dropdown");

            toggle.addEventListener("click", function (e) {
                e.stopPropagation();
                dropdown.classList.toggle("active");
            });

            document.addEventListener("click", function (e) {
                if (!dropdown.contains(e.target)) {
                    dropdown.classList.remove("active");
                }
            });
        });

 