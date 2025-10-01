const data = {
    donglanh:[
        {id:7, name:"Xúc xích", img: "media/6.webp"},
        {id:8, name:"Thịt đông" , img:"media/3.jpg"}
    ],
    kho: [
        {id: 1, name: "Gạo", img: "media/1.jpg"},
        {id: 2, name: "Mì tôm", img: "media/2.jpg"}
    ],
    tuoi: [
        {id: 3, name: "Rau cải", img: "media/3.jpg"},
        {id: 4, name: "Thịt bò", img: "media/4.jpg"}
    ],
    phache: [
        {id: 5, name: "Sữa đặc", img: "media/5.jpg"},
        {id: 6, name: "Trà xanh", img: "media/1.jpg"}
    ]
};

function showForm(type) {
    document.getElementById('form-nhap').style.display = type === 'nhap' ? 'block' : 'none';
    document.getElementById('form-xuat').style.display = type === 'xuat' ? 'block' : 'none';
}

function loadItems(type) {
    const category = document.getElementById(`category-${type}`).value;
    const container = document.getElementById(`items-${type}`);
    container.innerHTML = "";

    if (!data[category])
        return;

    data[category].forEach(item => {
        const div = document.createElement('div');
        div.className = "card";
        div.innerHTML = `
          <img src="${item.img}" alt="${item.name}">
          <strong>${item.name}</strong>
          <div class="tag">${category}</div>

          <label for="qty-${type}-${item.id}">Số lượng</label>
          <input type="number" name="soluong_${item.id}" id="qty-${type}-${item.id}" placeholder="Số lượng" min="1">

          ${type === 'nhap' ? `
            <label for="gia-${type}-${item.id}">Đơn giá</label>
            <input type="number" name="dongia_${item.id}" id="gia-${type}-${item.id}" placeholder="Đơn giá" min="0">
          ` : ''}

          <label><input type="checkbox" name="chon[]" value="${item.id}"> Chọn nguyên liệu này</label>
        `;
        container.appendChild(div);
    });
}