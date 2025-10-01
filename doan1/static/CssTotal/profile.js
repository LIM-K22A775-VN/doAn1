/* 
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/ClientSide/javascript.js to edit this template
 */


function toggleEdit(editable) {
    const inputs = document.querySelectorAll('#profile-form input');
    inputs.forEach(input => input.readOnly = !editable);

    document.querySelector('.save-btn').style.display = editable ? 'inline-block' : 'none';
    document.querySelector('.edit-btn').style.display = editable ? 'none' : 'inline-block';
}

function saveProfile() {
    const form = document.getElementById('profile-form');
    const data = {};

    Array.from(form.elements).forEach(el => {
        if (el.name)
            data[el.name] = el.value;
    });

    toggleEdit(false);
    alert("Thông tin đã lưu!");
}

