document.addEventListener('DOMContentLoaded', () => {
    const filterButtons = document.querySelectorAll('.filter-btn');
    const foodGrid = document.getElementById('foodGrid');

    // Lấy data JSON đã render sẵn từ Flask
    const foodData = JSON.parse(document.getElementById('foodData').textContent);

    function renderFoodItems(category) {
        foodGrid.innerHTML = '';
        let items;

        if (category === 'all') {
            items = foodData;
        } else {
            items = foodData.filter(item => item.category === category);
        }

        items.forEach(item => {
            const foodItem = document.createElement('div');
            foodItem.classList.add('food-item');
            const discount = (100 - (item.price / item.orig_price * 100)).toFixed(0);

            foodItem.innerHTML = `
                <img src="${item.img}" alt="${item.name}">
                <p>-${discount}% ${item.price} VND <span>${item.orig_price} VND</span></p>
                <button class="detail-btn">Xem chi tiết</button>
            `;
            foodGrid.appendChild(foodItem);
        });
    }

    // Mặc định load ALL
    renderFoodItems('all');

    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            filterButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            const category = button.getAttribute('data-category');
            renderFoodItems(category);
        });
    });

    // Các phần tin tức (nếu có)
    const newsItems = document.querySelectorAll('.news-item');
    function showSection(section) {
        const sections = document.querySelectorAll('.content');
        sections.forEach(s => s.style.display = 'none');
        const targetSection = document.getElementById(`content-${section}`);
        if (targetSection) targetSection.style.display = 'block';
    }

    function showArticle(id) {
        showSection('articles');
        const articles = document.querySelectorAll('.article-content');
        articles.forEach(a => a.style.display = 'none');
        const targetArticle = document.getElementById(`article-${id}`);
        if (targetArticle) targetArticle.style.display = 'block';
    }

    newsItems.forEach(item => {
        item.addEventListener('click', () => {
            const articleId = item.getAttribute('data-article-id');
            showArticle(articleId);
        });
    });

    // Khởi tạo content bài viết mẫu (nếu cần)
    const articlesContent = document.createElement('div');
    articlesContent.id = 'content-articles';
    articlesContent.className = 'content';
    articlesContent.innerHTML = `
        <div id="article-1" class="article-content" style="display: none;">
            <h2>Mách bạn cách nấu món ăn ngon</h2>
            <p>Đây là bài viết về cách nấu món ăn ngon với các bước đơn giản.</p>
        </div>
        <div id="article-2" class="article-content" style="display: none;">
            <h2>Tuyển tập món xào ngon</h2>
            <p>Đây là bài viết về tuyển tập món xào ngon, tiết kiệm thời gian.</p>
        </div>
        <div id="article-3" class="article-content" style="display: none;">
            <h2>Hé lộ cách làm món ngon</h2>
            <p>Đây là bài viết về cách làm món ngon tiết kiệm thời gian.</p>
        </div>
        <div id="article-4" class="article-content" style="display: none;">
            <h2>Gợi ý món ngon ngày Tết</h2>
            <p>Đây là bài viết về gợi ý món ngon ngày Tết.</p>
        </div>
        <div id="article-5" class="article-content" style="display: none;">
            <h2>Cách làm món ngon</h2>
            <p>Đây là bài viết về cách làm món ngon đơn giản tại nhà.</p>
        </div>
    `;
    document.body.appendChild(articlesContent);

    window.onload = () => showSection('home');
});
