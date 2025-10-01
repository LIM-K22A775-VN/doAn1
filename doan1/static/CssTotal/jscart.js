/* 
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/ClientSide/javascript.js to edit this template
 */
document.querySelector('.update-btn').addEventListener('click', function () {
  const items = document.querySelectorAll('.cart-item');
  let total = 0;

  items.forEach(item => {
    const priceText = item.querySelector('.item-price').textContent;
    const price = parseInt(priceText.match(/\d+/g).join(''));
    const qty = parseInt(item.querySelector('.item-qty').value);
    const itemTotal = price * qty;
    item.querySelector('.item-total').textContent = itemTotal.toLocaleString() + ' VND';
    total += itemTotal;
  });

  document.querySelector('.grand-total').textContent = total.toLocaleString() + ' VND';
});

