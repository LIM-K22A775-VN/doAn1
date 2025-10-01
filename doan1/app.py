from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import mysql.connector
import random
import smtplib
from email.message import EmailMessage
import qrcode
import os
import base64
import io
import sys
import face_recognition
from PIL import Image
from datetime import datetime
# ✅ Thiết lập môi trường
model_path = r"C:\Users\mis\AppData\Local\Programs\Python\Python313\Lib\site-packages\face_recognition_models\models"
os.environ["FACE_RECOGNITION_MODEL"] = model_path
sys.path.append(r"C:\Users\mis\AppData\Local\Programs\Python\Python313\Lib\site-packages")


app = Flask(__name__)
app.secret_key = 'otp-secret-key'

UPLOAD_FOLDER = os.path.join(app.root_path, 'static/avatars/media')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Kết nối DB tin nhắn ---

# KHÔNG tạo cursor_msg global ở đây

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="quanlynhahangvadoan"
)
# KHÔNG tạo cursor_user global ở đây

@app.route('/')
def index():    
    return render_template("intro_qc.html")
@app.route('/intro_qc')
def intro_qc():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"status": "error", "message": "Người dùng chưa đăng nhập."})
    return render_template("intro_qc.html")

# ---------- GỬI TIN NHẮN ----------
@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    message = data.get('message')
    sender_type = data.get('sender')  # 'user' hoặc 'agent'

    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"status": "error", "message": "Người dùng chưa đăng nhập."})

    with db.cursor() as cursor:
        # Tìm nhân viên (staff)
        cursor.execute("SELECT IdUser FROM users WHERE role = 'staff' LIMIT 1")
        staff = cursor.fetchone()
        if not staff:
            return jsonify({"status": "error", "message": "Không tìm thấy nhân viên hỗ trợ."})
        staff_id = staff[0]

        # Xác định ai gửi ai nhận
        if sender_type == 'agent':
            # Auto-reply: nhân viên là người gửi, khách là người nhận
            sender_id = staff_id
            receiver_id = user_id
        else:
            # Mặc định: khách gửi → khách là sender, nhân viên là receiver
            sender_id = user_id
            receiver_id = staff_id

        # Thêm tin nhắn vào DB
        cursor.execute(
            "INSERT INTO chatbox (IdSender, IdReceiver, content) VALUES (%s, %s, %s)",
            (sender_id, receiver_id, message)
        )

    db.commit()
    return jsonify({"status": "ok"})




# ---------- LẤY TIN NHẮN ----------
@app.route('/get_messages', methods=['GET'])
def get_messages():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify([])

    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT IdSender, content
            FROM chatbox
            WHERE IdSender = %s OR IdReceiver = %s
            ORDER BY Idmess ASC
            """,
            (user_id, user_id)
        )
        rows = cursor.fetchall()

        messages = []
        for r in rows:
            if r[0] == user_id:
                sender = "user"
            else:
                sender = "agent"
            messages.append({
                "sender": sender,
                "content": r[1]
            })

    return jsonify(messages)



# ---------- XÓA TIN NHẮN THEO EMAIL ----------
@app.route('/clear_messages', methods=['POST'])
def clear_messages():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"status": "error", "message": "Chưa đăng nhập."})

    with db.cursor() as cursor:
        cursor.execute(
            "DELETE FROM chatbox WHERE IdSender = %s OR IdReceiver = %s",
            (user_id, user_id)
        )
    db.commit()

    return jsonify({"status": "cleared"})



# ---------- ĐĂNG KÝ ----------
@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")


@app.route("/register-send-otp", methods=["POST"])
def register_send_otp():
    # Lấy dữ liệu từ form
    email = request.form["email"]
    password = request.form["password"]
    username = request.form["username"]
    address = request.form["address"]
    phone = request.form["phone"]
    gender = request.form["gender"]
    avatar = request.form.get("avatar", "")
    faceid_image = request.form.get("faceid_image")  # base64 từ client
    role = request.form["role"]
    session["register_role"] = role

    otp_code = str(random.randint(100000, 999999))

    # Lưu dữ liệu vào session (trừ ảnh base64)
    session["register_email"] = email
    session["register_password"] = password
    session["register_username"] = username
    session["register_address"] = address
    session["register_phone"] = phone
    session["register_gender"] = gender

    # Lấy tên file avatar
    avatar_file = request.files.get("avatar")
    avatar_filename = avatar_file.filename if avatar_file else ""
    
    # Lưu tên file vào session hoặc xử lý tiếp
    session["register_avatar"] = avatar_filename

    session["register_otp"] = otp_code 

    # Xử lý tạo file ảnh faceid luôn, nếu có
    faceid_filename = ""
    if faceid_image:
        try:
            # Tạo user_id tạm thời để đặt tên file ảnh (uuid)
            import uuid
            temp_user_id = str(uuid.uuid4())

            img_data = faceid_image.split(",")[1]
            img_bytes = base64.b64decode(img_data)

            faceid_filename = f"faceid_{temp_user_id}.jpg"
            faceid_path = os.path.join("static/avatars/media", faceid_filename)

            os.makedirs(os.path.dirname(faceid_path), exist_ok=True)

            with open(faceid_path, "wb") as f:
                f.write(img_bytes)

            # Lưu tên file vào session
            session["register_faceid_filename"] = faceid_filename
            session["temp_user_id"] = temp_user_id  # lưu tạm user id để dùng sau
        except Exception as e:
            print("Lỗi lưu ảnh FaceID lúc gửi OTP:", e)

    # Gửi mail OTP như cũ
    msg = EmailMessage()
    msg["Subject"] = "Mã OTP đăng ký tài khoản"
    msg["From"] = "yourmail@example.com"
    msg["To"] = email
    msg.set_content(f"Mã OTP của bạn là: {otp_code}")

    try:
        with smtplib.SMTP("sandbox.smtp.mailtrap.io", 587) as server:
            server.starttls()
            server.login("adcc7fb807a69e", "c5dd90947be935")
            server.send_message(msg)
        return render_template("verify_register_otp.html")
    except Exception as e:
        print("Lỗi gửi email:", e)
        return "Gửi OTP thất bại!"


import uuid 
@app.route("/register-verify-otp", methods=["POST"])
def register_verify_otp():
    user_otp = request.form["otp"]
    real_otp = session.get("register_otp", "")
    role = session.get("register_role", "user")
    if user_otp != real_otp:
        return render_template("verify_register_otp.html", success="Mã OTP không đúng")

    email = session.get("register_email")
    password = session.get("register_password")
    username = session.get("register_username")
    address = session.get("register_address")
    phone = session.get("register_phone")
    gender = session.get("register_gender")
    avatar = session.get("register_avatar", "")
    faceid_filename = session.get("register_faceid_filename", "")

    # Dùng temp_user_id nếu bạn muốn làm IdUser theo uuid lúc tạo ảnh luôn,
    # hoặc tạo lại IdUser mới (nên đồng bộ user id và file tên file)
    user_id = "U" + session.get("temp_user_id", str(uuid.uuid4()))

    with db.cursor() as cursor:
        cursor.execute("""
            INSERT INTO users (IdUser, username, address, email, phone, gender, password, Avatar, faceID,role)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,%s)
        """, (user_id, username, address, email, phone, gender, password, avatar, faceid_filename,role))

        db.commit()

    session.clear()  # Xoá session sau đăng ký

    return render_template("login.html", success="✅ Đăng Ký thành công.")


# ----------Form ĐĂNG NHẬP ----------
@app.route("/login")
def login():
    
    success_message = session.pop("success_message", None)
    return render_template("login.html", success=success_message)


@app.route("/intro", methods=["POST","GET"] )
def intro():
    user_info = get_user_info(True)
    
    with db.cursor() as cursor:
        # Lấy tất cả món ăn phổ biến
        cursor.execute("SELECT name, category, price, orig_price, img FROM food_phobien")
        foods_phobien = cursor.fetchall()

        food_list_phobien = [
            {
                'name': row[0],
                'category': row[1],
                'price': row[2],
                'orig_price': row[3],
                'img': row[4]
            }
            for row in foods_phobien
        ]

        # Lấy tất cả món ăn mới
        cursor.execute("SELECT name, category, price, orig_price, img FROM food_moi")
        foods_moi = cursor.fetchall()

        food_list_moi = [
            {
                'name': row[0],
                'category': row[1],
                'price': row[2],
                'orig_price': row[3],
                'img': row[4]
            }
            for row in foods_moi
        ]
    order_id = request.args.get("order_id")
    success = None
    if order_id and payment_status.get(order_id) == "paid":
        success = "✅ Thanh toán thành công!"
        payment_status.pop(order_id)

    return render_template(
        "intro.html",
        user=user_info,
        foods_phobien=food_list_phobien,
        foods_moi=food_list_moi,
        success=success,        
    )

# đã xong ->
@app.route("/login_intro", methods=["POST"])
def login_intro():
    email = request.form["email"]
    password = request.form["password"]

    with db.cursor() as cursor:
        # SELECT thêm role
        cursor.execute(
            "SELECT IdUser, userName, Avatar, role FROM users WHERE Email = %s AND Password = %s",
            (email, password)
        )
        user = cursor.fetchone()

        if user:
            session["user_id"] = user[0]   # Lưu IdUser
            session["user_email"] = email
            session["login_success"] = "Đăng nhập thành công!"  
            auto_generate_discount(session["user_id"])
            user_info = get_user_info(full=True)

            if user[3] == "user":
                # Dữ liệu riêng intro
                cursor.execute("SELECT name, category, price, orig_price, img FROM food_phobien")
                foods_phobien = cursor.fetchall()

                food_list_phobien = [
                    {
                        'name': row[0],
                        'category': row[1],
                        'price': row[2],
                        'orig_price': row[3],
                        'img': row[4]
                    }
                    for row in foods_phobien
                ]

                cursor.execute("SELECT name, category, price, orig_price, img FROM food_moi")
                foods_moi = cursor.fetchall()

                food_list_moi = [
                    {
                        'name': row[0],
                        'category': row[1],
                        'price': row[2],
                        'orig_price': row[3],
                        'img': row[4]
                    }
                    for row in foods_moi
                ]

                return render_template(
                    "intro.html",
                    success=session.get("login_success"),
                    user=user_info,
                    foods_phobien=food_list_phobien,
                    foods_moi=food_list_moi
                )
            
            elif user[3] == "staff":
                return render_template("dashboard_staff.html", user=user_info)

            elif user[3] == "admin":
                return render_template("admin.html", user=user_info)

            else:
                # Nếu role lạ
                return render_template("login.html", error="Vai trò không hợp lệ!")

        else:
            return render_template("login.html", error="Sai thông tin😖😖😖")


# đã xong <-

@app.route('/login_intro_face')
def login_intro_face():
    success = session.pop("login_success", None)  # Lấy rồi xoá khỏi session

    user_info = None
    if "user_email" in session:
        with db.cursor() as cursor:
            cursor.execute("SELECT username, avatar FROM users WHERE email = %s", (session["user_email"],))
            row = cursor.fetchone()
            if row:
                user_info = {
                    "username": row[0],
                    "avatar": row[1]  # chỉ tên file, HTML tự nối /static/avatars/
                }

    return render_template("intro.html", success=success, user=user_info)


# ---------- ĐĂNG NHẬP FACEID ----------
@app.route('/login-faceid', methods=['GET', 'POST'])
def login_faceid():
    if request.method == "GET":
        return render_template("login_faceid.html")
    else:
        data = request.get_json()
        email = data.get('email')
        image_data = data.get("image")

        if not email or not image_data:
            return jsonify({"success": False, "message": "Thiếu email hoặc ảnh"})

        with db.cursor() as cursor:
            cursor.execute("SELECT faceID FROM users WHERE email = %s", (email,))
            row = cursor.fetchone()

        if not row or not row[0]:
            return jsonify({"success": False, "message": "Chưa đăng ký FaceID cho tài khoản này"})

        saved_image_path = os.path.join(app.config['UPLOAD_FOLDER'], row[0])

        try:
            # Decode ảnh mới
            header, encoded = image_data.split(",", 1)
            img_bytes = base64.b64decode(encoded)

            live_image = face_recognition.load_image_file(io.BytesIO(img_bytes))
            saved_image = face_recognition.load_image_file(saved_image_path)

            # Mã hóa khuôn mặt
            live_encodings = face_recognition.face_encodings(live_image)
            if not live_encodings:
                return jsonify({"success": False, "message": "Không tìm thấy khuôn mặt trong ảnh chụp"})

            saved_encodings = face_recognition.face_encodings(saved_image)
            if not saved_encodings:
                return jsonify({"success": False, "message": "Khuôn mặt không khớp"})

            # So khớp
            match_results = face_recognition.compare_faces([saved_encodings[0]], live_encodings[0])
            if match_results[0]:
                session["user_email"] = email
                session["login_success"] = "Đăng nhập FaceID thành công!"
                return jsonify({"success": True})
            else:
                return jsonify({"success": False, "message": "Khuôn mặt không khớp"})

        except Exception as e:
            return jsonify({"success": False, "message": f"Lỗi: {e}"})


# ---------- ĐĂNG NHẬP BẰNG MÃ QR ----------
@app.route('/login-qr', methods=['POST'])
def login_qr():
    data = request.get_json()
    code = data.get("code")

    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE email = %s", (code,))
        user = cursor.fetchone()

    if user:
        session["user_email"] = code
        session["login_success"] = "Đăng nhập thành công!"
        return jsonify({"success": True})
    else:
        return jsonify({"success": False})


# ---------- đăng xuất ----------
@app.route('/log_out', methods=['GET'])
def log_out():
    session.clear()
    return render_template("login.html")


# ----------------------------------------- quên mật khẩu
@app.route("/forgot_password")
def forgot_password():
    return render_template("forgot_password.html")


@app.route("/send-otp", methods=["POST"])
def send_otp():
    user_email = request.form["email"]

    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE email = %s", (user_email,))
        user = cursor.fetchone()

    if not user:
        return render_template("forgot_password.html", error="Email không tồn tại.")

    otp_code = str(random.randint(100000, 999999))
    session["otp"] = otp_code
    session["email"] = user_email

    msg = EmailMessage()
    msg["Subject"] = "Mã OTP khôi phục mật khẩu"
    msg["From"] = "emtaamno-reply@example.com"
    msg["To"] = user_email
    msg.set_content(f"Mã OTP của bạn là: {otp_code}")

    try:
        with smtplib.SMTP("sandbox.smtp.mailtrap.io", 587) as server:
            server.starttls()
            server.login("adcc7fb807a69e", "c5dd90947be935")
            server.send_message(msg)
        return render_template("otp_form.html")
    except Exception as e:
        print("Lỗi khi gửi email:", e)
        return "❌ Gửi OTP thất bại!"


@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    user_input = request.form["otp"]
    correct_otp = session.get("otp", "")

    if user_input == correct_otp:
        return redirect(url_for("reset_password"))
    else:
        return "❌ Mã OTP không đúng. Hãy thử lại."


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if request.method == "GET":
        return render_template("reset_password.html")
    else:
        password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            return "❌ Mật khẩu không khớp. Vui lòng thử lại."

        email = session.get("email")

        with db.cursor() as cursor:
            cursor.execute("UPDATE users SET password = %s WHERE email = %s", (password, email))
            db.commit()

        return render_template("login.html", success="✅ Đặt lại mật khẩu thành công.")



# ✅ Hàm chung: Lấy thông tin user từ session (nên đầy đủ)
# ✅ Hàm chung: Lấy thông tin user từ session (đầy đủ)
def get_user_info(full=False):
    if "user_id" in session:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT IdUser, userName, Email, phone, Avatar, address, gender, faceID, role, total_spent, points
                FROM users
                WHERE IdUser = %s
                """,
                (session["user_id"],)
            )
            row = cursor.fetchone()
            if row:
                session["user_email"] =  row[2]
                return {
                    "id": row[0],            # ➜ THÊM id
                    "username": row[1],
                    "email": row[2],
                    "phone": row[3],
                    "avatar": row[4],
                    "address": row[5],
                    "gender": row[6],
                    "face_id": row[7],
                    "role": row[8],
                    "total_spent": row[9],
                    "points": row[10]
                }
    if "user_email" in session:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT IdUser, userName, Email, phone, Avatar, address, gender, faceID, role, total_spent, points
                FROM users
                WHERE Email = %s
                """,
                (session["user_email"],)
            )
            row = cursor.fetchone()
            if row:
                session["user_id"] = row[0]
                return {
                    "id": row[0],            # ➜ THÊM id
                    "username": row[1],
                    "email": row[2],
                    "phone": row[3],
                    "avatar": row[4],
                    "address": row[5],
                    "gender": row[6],
                    "face_id": row[7],
                    "role": row[8],
                    "total_spent": row[9],
                    "points": row[10]
                }
        

    return None

# đã xong ->
@app.route('/refarral')
def refarral():
    user_info = get_user_info()
    return render_template("refarral.html", user=user_info, breadcrumb="Giới thiệu")
# đã xong <-
# đã xong ->
@app.route('/profile')
def profile():
    user_info = get_user_info(True)
    return render_template("profile.html", user=user_info)


# đã xong->
@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    username = request.form.get('username')
    address = request.form.get('address')
    phone = request.form.get('phone')
    gender = request.form.get('gender')

    # Lấy tên file từ hidden input
    avatar_filename = request.form.get('avatar')

    user_id = session['user_id']

    with db.cursor() as cursor:
        if avatar_filename:
            cursor.execute("""
                UPDATE users
                SET userName=%s, address=%s, phone=%s, gender=%s, Avatar=%s
                WHERE IdUser=%s
            """, (username, address, phone, gender, avatar_filename, user_id))
        else:
            cursor.execute("""
                UPDATE users
                SET userName=%s, address=%s, phone=%s, gender=%s
                WHERE IdUser=%s
            """, (username, address, phone, gender, user_id))
        db.commit()

    return redirect(url_for('profile'))

# đã xong<-

@app.route('/favorite')
def favorite():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    user_info = get_user_info(full=True)

    query = """
    SELECT food_name, category, brand, price, orig_price, img
    FROM food_yeuthich
    WHERE IdUser = %s
    ORDER BY id ASC
    """

    with db.cursor() as cursor:
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()

    foods = []
    for row in rows:
        foods.append({
            'name': row[0],
            'category': row[1],
            'brand': row[2],
            'price': row[3],
            'orig_price': row[4],
            'img': row[5],
            'in_favorite': True
        })

    return render_template(
        'favorite.html',
        user=user_info,
        foods=foods,
        breadcrumb="Yêu thích"
    )


# đã xong ->
@app.route('/Menu')
def menu():
    user_id = session.get('user_id')
    user_info = get_user_info(True)
    query = """
      SELECT f.nameFood, f.style, f.category, f.price, f.orig_price, f.image,
             CASE WHEN fy.id IS NOT NULL THEN 1 ELSE 0 END AS in_favorite,
             CASE WHEN c.id IS NOT NULL THEN 1 ELSE 0 END AS in_cart
      FROM food_thucdon ft
      JOIN food f ON ft.idFood = f.IdFood
      LEFT JOIN food_yeuthich fy
        ON f.nameFood = fy.food_name AND fy.IdUser = %s
      LEFT JOIN cart c
        ON f.nameFood = c.food_name AND c.IdUser = %s
      ORDER BY ft.idFood ASC
    """

    with db.cursor() as cursor:
        cursor.execute(query, (user_id, user_id))
        rows = cursor.fetchall()

    foods = []
    for row in rows:
        foods.append({
            'name': row[0],
            'brand': row[1],
            'category': row[2],
            'price': row[3],
            'orig_price': row[4],
            'img': row[5],
            'in_favorite': bool(row[6]),
            'in_cart': bool(row[7])
        })

    return render_template('Menu.html', user=user_info, foods=foods, breadcrumb="Thực đơn")

# đã xong <-

# đã xong->
@app.route('/add_to_favorite', methods=['POST'])
def add_to_favorite():
    food_name = request.json.get('name')
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({"status": "error", "message": "Bạn chưa đăng nhập!"}), 401

    try:
        with db.cursor() as cursor:
            # Lấy thông tin món ăn (LIMIT 1)
            cursor.execute(
                """
                SELECT nameFood, category, price, orig_price, image, style
                FROM food 
                WHERE nameFood = %s
                LIMIT 1
                """,
                (food_name,)
            )
            food = cursor.fetchone()

            if not food:
                return jsonify({"status": "error", "message": "Không tìm thấy món ăn!"}), 404

            # Kiểm tra đã có trong yêu thích chưa (bằng nameFood)
            cursor.execute(
                """
                SELECT id FROM food_yeuthich 
                WHERE IdUser = %s AND food_name = %s
                LIMIT 1
                """,
                (user_id, food_name)
            )
            exists = cursor.fetchone()

            if exists:
                return jsonify({"status": "exists", "message": "Món ăn này đã có trong yêu thích!"})

            # Thêm mới
            cursor.execute(
                """
                INSERT INTO food_yeuthich 
                (IdUser, food_name, category, price, orig_price, img, brand) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (user_id, food[0], food[1], food[2], food[3], food[4], food[5])
            )

        db.commit()
        return jsonify({"status": "success", "message": "Đã thêm vào yêu thích!"})

    except Exception as e:
        db.rollback()
        print("Lỗi khi thêm vào yêu thích:", e)
        return jsonify({"status": "error", "message": "Có lỗi khi lưu yêu thích!"}), 500

# đã xong<-

# đã xong->
@app.route('/remove_from_favorite', methods=['POST'])
def remove_from_favorite():
    food_name = request.json.get('name')
    user_id = session.get('user_id')  # PHẢI LÀ IdUser

    if not user_id:
        return jsonify({"status": "error", "message": "Bạn chưa đăng nhập!"}), 401

    with db.cursor() as cursor:
        cursor.execute(
            "DELETE FROM food_yeuthich WHERE IdUser = %s AND food_name = %s",
            (user_id, food_name)
        )
        db.commit()

    return jsonify({"status": "success", "message": "Đã xoá khỏi yêu thích!"})


# đã xong<-

# đã xong->
@app.route('/article')
def article():
    user_info = get_user_info()
    return render_template('article.html', user=user_info, breadcrumb="Bài viết")
# đã xong<-
# đã xong->
@app.route('/gallery')
def gallery():
    user_info = get_user_info()
    return render_template('gallery.html', user=user_info, breadcrumb="Hình ảnh")
# đã xong<-


@app.route('/danhgia', methods=['POST'])
def danhgia():
    order_id = request.form.get('order_id')
    food_id = request.form.get('food_id')
    rating = request.form.get('rating')
    comment = request.form.get('comment', '')
    if not all([order_id, food_id, rating]):
        return jsonify({"status": "fail", "message": "Thiếu dữ liệu bắt buộc"}), 400

    try:
        with db.cursor() as cursor:
            # Kiểm tra xem review đã có chưa
            cursor.execute("""
                SELECT IdReview FROM reviews
                WHERE IdOrder = %s AND IdFood = %s
            """, (order_id, food_id))
            result = cursor.fetchone()

            if result:
                # Update review đã có
                cursor.execute("""
                    UPDATE reviews
                    SET rating = %s, comment = %s, created_at = NOW()
                    WHERE IdReview = %s
                """, (rating, comment, result[0]))
            else:
                # Thêm review mới
                cursor.execute("""
                    INSERT INTO reviews (IdOrder, IdFood, rating, comment)
                    VALUES (%s, %s, %s, %s)
                """, (order_id, food_id, rating, comment))
            db.commit()
        return jsonify({"status": "success", "message": "Đánh giá đã được lưu"})
    except Exception as e:
        print(e)
        return jsonify({"status": "fail", "message": "Lỗi server"}), 500

# Hủy món ăn khi đã đặt xong
@app.route('/cancel_order/<int:order_id>', methods=['POST'])
def cancel_order(order_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Bạn chưa đăng nhập"}), 401

    with db.cursor() as cursor:
        cursor.execute("""
            UPDATE orders
            SET status = 'Đã hủy'
            WHERE IdOrder = %s AND IdUser = %s AND status = 'Đang chờ xử lý'
        """, (order_id, user_id))
        db.commit()

        if cursor.rowcount == 0:
            return jsonify({"status": "error", "message": "Không thể hủy đơn hàng này"}), 400

    return jsonify({"status": "success", "message": "Hủy đơn hàng thành công"})





# đánh giá sản phẩm
@app.route('/evaluate_dish', methods=['POST'])
def evaluate_dish():
    food_id = request.form.get('food_id')   # IdFood
    order_id = request.form.get('order_id') # IdOrder
    user_id = session.get('user_id')        # Lấy user_id từ session
    user_info = get_user_info(True)

    if not user_id:
        return redirect('/login')  # Nếu chưa đăng nhập thì chuyển hướng login

    if not food_id or not order_id:
        return "Thiếu dữ liệu!", 400

    with db.cursor() as cursor:
        cursor.execute("""
            SELECT f.nameFood, f.image, r.rating, r.comment
            FROM order_items oi
            JOIN food f ON oi.IdFood = f.IdFood
            LEFT JOIN reviews r 
                ON r.IdOrder = oi.IdOrder AND r.IdFood = oi.IdFood
            JOIN orders o ON o.IdOrder = oi.IdOrder
            WHERE oi.IdOrder = %s AND oi.IdFood = %s AND o.IdUser = %s
        """, (order_id, food_id, user_id))
        item = cursor.fetchone()

    if not item:
        return "Không tìm thấy món ăn hoặc bạn không có quyền đánh giá!", 404

    return render_template(
        'evaluate_dish.html',
        food_name=item[0],
        img=item[1],
        rating=item[2],
        comment=item[3],
        food_id=food_id,
        order_id=order_id,
        user=user_info,
        breadcrumb="Đánh giá"
    )


@app.route('/order_detail/<int:order_id>')
def order_detail(order_id):
    user_info = get_user_info(True)
    user_id = session.get('user_id')

    if not user_id:
        return redirect('/login')

    with db.cursor() as cursor:
        # Lấy thông tin đơn hàng để kiểm tra user
        cursor.execute("""
            SELECT IdOrder, status, timeOrder
            FROM orders
            WHERE IdOrder = %s AND IdUser = %s
        """, (order_id, user_id))
        order_row = cursor.fetchone()

        if not order_row:
            return "Không tìm thấy đơn hàng", 404

        order_info = {
            'id': order_row[0],
            'status': order_row[1],
            'date_ordered': order_row[2],
            'items': [],
            'total': 0
        }

        # Lấy chi tiết các món ăn
        cursor.execute("""
            SELECT f.nameFood, oi.quantity, oi.unit_price, f.image
            FROM order_items oi
            JOIN food f ON oi.IdFood = f.IdFood
            WHERE oi.IdOrder = %s
        """, (order_id,))
        item_rows = cursor.fetchall()

        total = 0
        for row in item_rows:
            item = {
                'food_name': row[0],
                'quantity': row[1],
                'price': row[2],
                'img': row[3],
                'subtotal': row[1] * row[2]
            }
            total += item['subtotal']
            order_info['items'].append(item)

        order_info['total'] = total

    return render_template('order_detail.html',
                           user=user_info,
                           breadcrumb="Chi Tiết Đơn Hàng",
                           order=order_info)


@app.route('/order')
def order():
    user_info = get_user_info(True)
    user_id = session.get('user_id')

    if not user_id:
        return redirect('/login')

    with db.cursor() as cursor:
        cursor.execute("""
            SELECT 
                o.IdOrder,
                o.timeOrder,
                o.status,
                oi.IdFood,
                oi.quantity,
                oi.unit_price,
                f.nameFood,      -- ✅ tên món
                f.category,
                f.image          -- ✅ ảnh món
            FROM orders o
            JOIN order_items oi ON o.IdOrder = oi.IdOrder
            JOIN food f ON oi.IdFood = f.IdFood
            WHERE o.IdUser = %s
            ORDER BY o.IdOrder DESC
        """, (user_id,))

        rows = cursor.fetchall()

    orders_dict = {}
    for row in rows:
        order_id = row[0]
        if order_id not in orders_dict:
            orders_dict[order_id] = {
                'id': order_id,
                'date_ordered': row[1],
                'status': row[2],
                'items': []
            }

        orders_dict[order_id]['items'].append({
            'food_id': row[3],
            'quantity': row[4],
            'price': row[5],
            'name': row[6],         # nameFood → name, dùng cho template
            'category': row[7],
            'img': row[8]           # image → img, dùng cho template
        })

    orders = list(orders_dict.values())

    return render_template(
        'order.html',
        user=user_info,
        breadcrumb="Đơn hàng",
        orders=orders,
        status='all'
    )

# đã xong->
@app.route('/reorder/<int:order_id>', methods=['POST'])
def reorder(order_id):
    user_id = session.get('user_id')  # Lấy IdUser đã lưu trong session
    if not user_id:
        return jsonify({"status": "error", "message": "Bạn chưa đăng nhập"}), 401

    with db.cursor() as cursor:
        cursor.execute("""
            SELECT grand_total, status
            FROM orders
            WHERE IdUser = %s AND IdOrder = %s AND status = 'Đã hủy'
        """, (user_id, order_id))
        row = cursor.fetchone()

    if not row:
        return jsonify({"status": "error", "message": "Không tìm thấy đơn hàng để đặt lại"}), 404

    total_price = row[0]

    with db.cursor() as cursor:
        cursor.execute("""
            UPDATE orders
            SET status = 'Đang chờ xử lý'
            WHERE IdOrder = %s AND IdUser = %s
        """, (order_id, user_id))
        db.commit()

    return jsonify({
        "status": "success",
        "message": f"Đơn hàng #{order_id} đã được đặt lại!",
        "trued_amount": total_price
    })
# đã xong<-
# đã xong->
@app.route('/contact')
def contact():
    user_info = get_user_info(True)
    return render_template('contact.html', user=user_info, breadcrumb="Liên hệ")
# đã xong<-

@app.route("/customer_point", methods=["GET"])
def customer_point():
    user_info = get_user_info(True)

    if not user_info:
        return redirect("/login")

    with db.cursor() as cursor:
        # 👉 1. Lấy rewards (JOIN với food để lấy nameFood, category, image)
        cursor.execute("""
            SELECT f.nameFood, r.cost, f.category, f.image
            FROM rewards r
            JOIN food f ON r.idFood = f.IdFood
        """)
        rewards = cursor.fetchall()

        reward_list = [
            {
                'name': row[0],
                'cost': row[1],
                'category': row[2],
                'img': row[3]
            }
            for row in rewards
        ]

        # 👉 2. Lấy discount_codes dùng IdUser
        cursor.execute("""
            SELECT amount, discount_code, img
            FROM discount_codes
            WHERE IdUser = %s
        """, (session["user_id"],))

        discount_codes = cursor.fetchall()

        discount_list = [
            {
                'points': row[0],
                'discount_code': row[1],
                'img': row[2]
            }
            for row in discount_codes
        ]

        # 👉 3. Lấy điểm từ user_info
        # user_points = user_info.get('points', 0)
        user_points = user_info['points'] if user_info and 'points' in user_info else 0
        

    # 👉 4. Trả về giao diện
    return render_template(
        "customer_point.html",
        user=user_info,
        rewards=reward_list,
        discount_codes=discount_list,
        user_points=user_points,
        breadcrumb="Đổi thưởng"
    )

@app.route('/thanhtoan', methods=['POST'])
def thanhtoan():
    data = request.get_json()
    name = data.get('name')
    category = data.get('category')
    img = data.get('img')
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({"status": "error", "message": "Chưa đăng nhập!"}), 401

    with db.cursor() as cursor:
        # 1️⃣ Lấy cost từ JOIN food + rewards
        cursor.execute("""
            SELECT r.cost, r.idFood
            FROM rewards r
            JOIN food f ON r.idFood = f.IdFood
            WHERE f.nameFood = %s AND f.category = %s
        """, (name, category))
        row = cursor.fetchone()
        if not row:
            return jsonify({"status": "error", "message": "Phần thưởng không tồn tại!"}), 400

        cost, idFood = row

        # 2️⃣ Lấy điểm user
        cursor.execute(
            "SELECT points FROM users WHERE IdUser = %s",
            (user_id,)
        )
        user_row = cursor.fetchone()
        if not user_row:
            return jsonify({"status": "error", "message": "Không tìm thấy user!"}), 400

        current_points = user_row[0]

        if current_points < cost:
            return jsonify({"status": "error", "message": "Không đủ điểm để đổi!"}), 400

        # 3️⃣ Trừ điểm user
        new_points = current_points - cost
        cursor.execute(
            "UPDATE users SET points = %s WHERE IdUser = %s",
            (new_points, user_id)
        )

        # 4️⃣ Thêm phần thưởng vào cart
        cursor.execute("""
            INSERT INTO cart (IdUser, food_name, quantity, category, price, orig_price, img, brand, IdFood)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id,
            name,
            1,
            category,
            0,
            0,
            img,
            None,
            idFood
        ))

    db.commit()

    return jsonify({
        "status": "success",
        "message": "Đã thêm vào giỏ và trừ điểm!",
        "new_points": new_points
    })



# đã xong->
@app.route('/lienhe', methods=['POST'])
def lienhe():
    user_id = session.get('user_id')  # Lấy IdUser đã lưu trong session
    phone = request.form.get('phone')
    message = request.form.get('message')

    if not user_id:
        return render_template('contact.html', error="❌ Bạn chưa đăng nhập!", breadcrumb="Liên hệ")

    try:
        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO contact (IdUser, phone, message)
                VALUES (%s, %s, %s)
                """,
                (user_id, phone, message)
            )
        db.commit()
        user_info = get_user_info(True)
        return render_template(
            'contact.html',
            user=user_info,
            success="✅ Nhân viên sẽ gọi lại bạn ngay!",
            breadcrumb="Liên hệ"
        )
    except Exception as e:
        db.rollback()
        print("Lỗi lưu contact:", e)
        return render_template('contact.html', error="❌ Lỗi khi gửi liên hệ!", breadcrumb="Liên hệ")
# đã xong<-

@app.route('/Cart')
def Cart():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    user_info = get_user_info(True)

    cart_items = []
    grand_total = 0

    with db.cursor() as cursor:
        # Lấy giỏ hàng, thêm cột 'id' vào SELECT
        cursor.execute(
            """
            SELECT id, food_name, category, brand, price, orig_price, img, quantity,IdFood
            FROM cart
            WHERE IdUser = %s
            """,
            (user_id,)
        )
        rows = cursor.fetchall()

        # Lấy mã giảm giá (có amount)
        cursor.execute(
            """
            SELECT discount_code, amount, created_at, img
            FROM discount_codes
            WHERE IdUser = %s
            """,
            (user_id,)
        )
        discounts = cursor.fetchall()

    # Tạo list cart_items có trường 'id'
    for row in rows:
        cart_items.append({
            'id': row[0],           # id sản phẩm trong giỏ hàng
            'name': row[1],
            'category': row[2],
            'brand': row[3],
            'price': row[4],
            'orig_price': row[5],
            'img': row[6],
            'qty': row[7],
            'idFood':row[8]
        })
        grand_total += row[4] * row[7]

    # Tạo list discount_codes từ dữ liệu db
    discount_codes = [
        {
            'code': d[0],
            'amount': d[1],
            'created_at': d[2],
            'img': d[3]
        }
        for d in discounts
    ]

    return render_template(
        'Cart.html',
        user=user_info,
        breadcrumb="Giỏ hàng",
        cart_items=cart_items,
        grand_total=grand_total,
        discount_codes=discount_codes
    )

import json
@app.route("/payment", methods=["POST"])
def payment():
    phone = request.form.get("phone")
    grand_total = request.form.get("grand_total")
    discount_code = request.form.get("discount_code")
    user_id = session.get("user_id")  # Lấy user_id thay vì email
    user_info = get_user_info()

    # Parse items
    items_raw = request.form.get("items")
    items = json.loads(items_raw) if items_raw else []

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="quanlynhahangvadoan"
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT userName FROM users WHERE IdUser = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template(
        "payment.html",
        name=user["userName"] if user else "",
        phone=phone,
        email=session.get("user_email"),  # Nếu vẫn muốn truyền email xuống template
        discount_code=discount_code,
        user=user_info,
        grand_total=int(grand_total) if grand_total else 0,
        breadcrumb="Thanh Toán",
        items=items
    )



#===============================THANH TOÁN ONLINE========================================

@app.route("/confirm_booking_online", methods=["POST"])
def confirm_booking_online():
    name = request.form.get("name")
    phone = request.form.get("phone") or "unknown"
    total = request.form.get("total") or "0"
    payment_method = request.form.get("payment") or "atm"
    # cập nhật tiền và điểm cộng 
    update_user_stats(session["user_id"], total)
    # kiểm tra mã giảm giá
    auto_generate_discount(session["user_id"])
    # 👉 LẤY ITEMS từ form:
    import json
    items_raw = request.form.get("items")  # hidden input name="items"
    items = json.loads(items_raw) if items_raw else []

    order_id = f"ORDER_{phone}" 
    ip_lan = "192.168.43.31"
    # ip_lan = "192.168.100.202"
    from urllib.parse import quote

    items_encoded = quote(items_raw)  # Vì items_raw là JSON string, nên cần encode
    url = f"http://{ip_lan}:5000/fake_payment/{order_id}?total={total}&name={name}&phone={phone}&items={items_encoded}"

    if not os.path.exists("static"):
        os.makedirs("static")

    img = qrcode.make(url)
    img_path = os.path.join("static", f"qr_{order_id}.png")
    img.save(img_path)

    payment_status[order_id] = "unpaid"

    return render_template(
    "confirm_booking_online.html",
    name=name,
    phone=phone,
    total=total,
    payment_method=payment_method,
    order_id=order_id,
    url=url,
    items=items,                 # danh sách món
    discount_code=request.form.get("discount_code") or ""   # mã giảm giá
)


#  thêm danh sách món ăn vào orders
@app.route('/save_order_items', methods=['POST'])
def save_order_items():
    data = request.get_json()

    items = data.get('items')
    total = data.get('total') or 0
    discount_code = data.get('discount_code')
    user_id = session.get('user_id')
    phone = data.get('phone')
    if not items or not user_id:
        return jsonify({'success': False, 'message': 'Thiếu dữ liệu hoặc chưa đăng nhập'})

    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='quanlynhahangvadoan'
        )
        cursor = conn.cursor()

        # Thêm đơn hàng vào bảng orders
        cursor.execute("""
            INSERT INTO orders (IdUser, timeOrder, status, grand_total, discount_code,phone)
            VALUES (%s, NOW(), %s, %s, %s,%s)
        """, (
            user_id,
            'Đang chờ xử lý',
            total,
            discount_code,
            phone
        ))

        order_id_db = cursor.lastrowid

        # Thêm chi tiết từng món vào bảng order_items
        for item in items:
            cursor.execute("""
                INSERT INTO order_items (IdOrder, IdFood, quantity, unit_price)
                VALUES (%s, %s, %s, %s)
            """, (
                order_id_db,
                item.get('idFood'),
                item.get('qty'),
                item.get('unitPrice')
            ))

        # Xóa món đã đặt khỏi giỏ hàng theo IdFood và IdUser
        food_ids = [item.get('idFood') for item in items if item.get('idFood')]

        if food_ids:
            format_strings = ','.join(['%s'] * len(food_ids))
            sql_delete = f"DELETE FROM cart WHERE IdUser = %s AND IdFood IN ({format_strings})"
            cursor.execute(sql_delete, (user_id, *food_ids))
            # Xóa discount_code đã dùng nếu có
            if discount_code:
                cursor.execute("""
                    DELETE FROM discount_codes
                    WHERE IdUser = %s AND discount_code = %s
                """, (user_id, discount_code))
        conn.commit()
        return jsonify({'success': True, 'order_id': order_id_db})

    except Exception as e:
        conn.rollback()
        print('Lỗi lưu đơn hàng:', e)
        return jsonify({'success': False, 'message': str(e)})

    finally:
        cursor.close()
        conn.close()



payment_status = {}  # Dict lưu trạng thái { order_id: "unpaid"/"paid" }
@app.route("/check_payment_status/<order_id>")
def check_payment_status(order_id):
    status = payment_status.get(order_id, "unpaid")
    return status

@app.route("/fake_payment/<order_id>", methods=["GET", "POST"])
def fake_payment(order_id):
    if request.method == "POST":
        name = request.form.get("name")
        total = request.form.get("total")
        fake_account = request.form.get("fake_account")

        print(f"[FAKE PAY] Đơn {order_id} | Tên: {name} | Số tiền: {total} | STK: {fake_account}")

        payment_status[order_id] = "paid"
        return redirect(url_for("intro", success="✅ Thanh toán thành công!"))

    # 👉 NHẬN items từ query string:
    name = request.args.get("name", "")
    phone = request.args.get("phone", "")
    total = request.args.get("total", "0")
    items_raw = request.args.get("items", "[]")  # thêm dòng này
    items = json.loads(items_raw)  # parse JSON string

    return render_template(
        "fake_payment.html",
        order_id=order_id,
        name=name,
        phone=phone,
        total=total,
        items=items  # 👈 QUAN TRỌNG: truyền items sang template
    )

@app.route("/add_orders/<order_id>")
def add_orders(order_id):
    import json
    items = json.loads(request.args.get("items", "[]"))

    phone = order_id.replace("ORDER_", "")
    username = phone

    with db.cursor() as cursor:
        for item in items:
            cursor.execute("""
                INSERT INTO orders (username, food_name, img, quantity)
                VALUES (%s, %s, %s, %s)
            """, (username, item["name"], item["img"], item["qty"]))

    db.commit()
    return {"status": "success"}

@app.route('/update_cart', methods=['POST'])
def update_cart():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Bạn chưa đăng nhập!"}), 401

    data = request.get_json()
    if not data or 'items' not in data:
        return jsonify({"status": "error", "message": "Dữ liệu không hợp lệ!"}), 400

    items = data['items']

    try:
        with db.cursor() as cursor:
            for item in items:
                name = item.get('name')
                quantity = item.get('qty')
                idFood = item.get('idFood')

                if not name or quantity is None or idFood is None:
                    continue  # hoặc trả lỗi tùy bạn

                # Cập nhật quantity cho món ăn của user trong cart
                cursor.execute("""
                    UPDATE cart SET quantity = %s 
                    WHERE IdUser = %s AND food_name = %s AND idFood = %s
                """, (quantity, user_id, name, idFood))

        db.commit()
        return jsonify({"status": "success", "message": "Cập nhật giỏ hàng thành công!"})

    except Exception as e:
        db.rollback()
        print("Lỗi cập nhật giỏ hàng:", e)
        return jsonify({"status": "error", "message": "Lỗi khi cập nhật giỏ hàng!"}), 500


#===============================THANH TOÁN ONLINE========================================
# đã xong->
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    food_name = request.json.get('name')  # dữ liệu client gửi lên vẫn là "name"
    user_id = session.get('user_id')      # Đã sửa session key

    if not user_id:
        return jsonify({"status": "error", "message": "Bạn chưa đăng nhập!"}), 401

    try:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT nameFood, category, price, orig_price, image, style,idFood FROM food WHERE nameFood = %s",
                (food_name,)
            )
            food = cursor.fetchone()

            if not food:
                return jsonify({"status": "error", "message": "Không tìm thấy món ăn!"}), 404

            cursor.execute(
                "SELECT id FROM cart WHERE IdUser = %s AND food_name = %s",
                (user_id, food_name)
            )
            exists = cursor.fetchone()

            if exists:
                return jsonify({"status": "exists", "message": "Món ăn này đã có trong giỏ hàng!"})

            cursor.execute(
                """
                INSERT INTO cart 
                (IdUser, food_name, category, price, orig_price, img, brand,idFood, quantity) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s,%s)
                """,
                (user_id, food[0], food[1], food[2], food[3], food[4], food[5],food[6], 1)
            )

        db.commit()
        return jsonify({"status": "success", "message": "Đã thêm vào giỏ hàng!"})

    except Exception as e:
        db.rollback()
        print("Lỗi khi thêm vào giỏ hàng:", e)
        return jsonify({"status": "error", "message": "Có lỗi khi lưu giỏ hàng!"}), 500
# đã xong<-

# đã xong->
@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    food_name = request.json.get('name')
    user_id = session.get('user_id')  # dùng key chuẩn

    if not user_id:
        return jsonify({"status": "error", "message": "Bạn chưa đăng nhập!"}), 401

    try:
        with db.cursor() as cursor:
            # 🔍 Lấy idFood và price của món hàng cần xóa
            cursor.execute(
                "SELECT idFood, price FROM cart WHERE IdUser = %s AND food_name = %s",
                (user_id, food_name)
            )
            row = cursor.fetchone()

            if not row:
                return jsonify({"status": "error", "message": "Sản phẩm không tồn tại trong giỏ hàng!"}), 404

            idFood, price = row

            # ✅ Nếu là phần thưởng (price = 0), thì hoàn điểm lại
            if price == 0:
                cursor.execute(
                    "SELECT cost FROM rewards WHERE idFood = %s",
                    (idFood,)
                )
                reward_row = cursor.fetchone()
                if reward_row:
                    cost = reward_row[0]

                    # 👉 Cộng lại điểm cho người dùng
                    cursor.execute(
                        "UPDATE users SET points = points + %s WHERE IdUser = %s",
                        (cost, user_id)
                    )

            # ❌ Xóa khỏi giỏ hàng
            cursor.execute(
                "DELETE FROM cart WHERE IdUser = %s AND food_name = %s",
                (user_id, food_name)
            )

        db.commit()
        return jsonify({"status": "success", "message": "Đã xoá khỏi giỏ hàng!"})

    except Exception as e:
        db.rollback()
        print("Lỗi khi xoá khỏi giỏ hàng:", e)
        return jsonify({"status": "error", "message": "Có lỗi khi xoá!"}), 500
# đã xong<-

# ✅ Đặt bàn
# đã xong->
@app.route('/reserve')
def reserve():
    user_info = get_user_info(full=True)
    return render_template('reserve.html', user=user_info, breadcrumb="Đặt bàn")
# đã xong<-

@app.route("/reserve-send-otp", methods=["POST"])
def reserve_send_otp():
    if "user_email" not in session:
        return redirect("/login")

    user_info = get_user_info(full=True)
    if not user_info:
        return "❌ Không tìm thấy thông tin user."

    name = user_info["username"]
    email = user_info["email"]
    phone = user_info["phone"]

    people = request.form["people"]
    date = request.form["date"]
    time = request.form["time"]
    notes = request.form["notes"]

    session["reserve_name"] = name
    session["reserve_email"] = email
    session["reserve_phone"] = phone
    session["reserve_people"] = people
    session["reserve_date"] = date
    session["reserve_time"] = time
    session["reserve_notes"] = notes

    otp_code = str(random.randint(100000, 999999))
    session["reserve_otp"] = otp_code

    msg = EmailMessage()
    msg["Subject"] = "Mã OTP xác nhận đặt bàn"
    msg["From"] = "yourmail@example.com"
    msg["To"] = email
    msg.set_content(f"Mã OTP đặt bàn của bạn là: {otp_code}")

    try:
        with smtplib.SMTP("sandbox.smtp.mailtrap.io", 587) as server:
            server.starttls()
            server.login("adcc7fb807a69e", "c5dd90947be935")
            server.send_message(msg)
        return render_template("verify_reserve_otp.html")
    except Exception as e:
        print("Lỗi gửi email:", e)
        return "❌ Gửi OTP thất bại!"


@app.route("/verify-reserve-otp", methods=["POST"])
def verify_reserve_otp():
    user_otp = request.form["otp"]
    real_otp = session.get("reserve_otp", "")

    if user_otp == real_otp:
        name = session.get("reserve_name")
        email = session.get("reserve_email")
        phone = session.get("reserve_phone")
        people = session.get("reserve_people")
        date = session.get("reserve_date")
        time = session.get("reserve_time")
        notes = session.get("reserve_notes")

        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO booking (name, email, phone, people, date, time, notes, booking_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """, (name, email, phone, people, date, time, notes))

            db.commit()

        user_info = get_user_info(full=True)
        return render_template("intro.html", user=user_info, success="✅ Đặt bàn thành công!")
    else:
        return render_template("verify_reserve_otp.html", error="❌ Mã OTP không đúng.")

# thanh toán hóa đơn
@app.route("/payment_mortgate", methods=["POST"])
def payment_mortgate():
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        people = request.form.get("people")
        date = request.form.get("date")
        time = request.form.get("time")
        notes = request.form.get("notes")

        return render_template(
            "payment_mortgate.html",
            name=name,
            email=email,
            phone=phone,
            people=people,
            date=date,
            time=time,
            notes=notes
        )

# Route /confirm_booking xử lý lưu DB
@app.route("/confirm_booking", methods=["POST"])
def confirm_booking():
    # Lấy user_id từ session
    user_id = session.get("user_id")
    if not user_id:
        return "Bạn chưa đăng nhập!", 401

    # Kết nối DB
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="quanlynhahangvadoan"
    )

    # Lấy thông tin user (nếu cần)
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT userName, Avatar FROM users WHERE IdUser = %s",
            (user_id,)
        )
        row = cursor.fetchone()
        user_info = {"username": row[0], "avatar": row[1]} if row else None

    # Lấy form
    people = request.form.get("people")
    date = request.form.get("date")
    time_value = request.form.get("time")
    notes = request.form.get("notes")
    # Insert vào table_reservation
    with conn.cursor() as cursor:
        sql = """
            INSERT INTO table_reservation (IdUser, number, createdAt, time, status, notes)
            VALUES (%s, %s, %s, %s, 'Đã đặt', %s)
            """
        cursor.execute(sql, (user_id, people, date, time_value, notes))
        conn.commit()

    conn.close()

    # Trả về trang intro.html
    return render_template(
        "intro.html",
        success="Đặt bàn thành công!",
        user=user_info
    )






# ------------------------------------------ADMIN---------------------------------

















#-------------------------------- NHÂN VIÊN
# đơn hàng->
@app.route('/order_staff')
def order_staff():
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT 
                o.IdOrder,
                o.timeOrder,
                u.userName,
                COALESCE(o.phone, u.phone) AS phone,
                u.address,
                o.note,
                o.grand_total,
                f.image,
                f.nameFood,
                oi.unit_price,
                oi.quantity,
                u.avatar,   -- ẢNH NGƯỜI ĐẶT
                o.status    -- TRẠNG THÁI ĐƠN HÀNG
            FROM orders o
            JOIN users u ON o.IdUser = u.IdUser
            JOIN order_items oi ON o.IdOrder = oi.IdOrder
            JOIN food f ON oi.IdFood = f.IdFood
            ORDER BY o.timeOrder DESC;
        """)
        rows = cursor.fetchall()

    order_dict = {}
    for row in rows:
        oid = row[0]
        if oid not in order_dict:
            order_dict[oid] = {
                "IdOrder": oid,
                "timeOrder": row[1],
                "userName": row[2],
                "phone": row[3],
                "address": row[4],
                "note": row[5],
                "grand_total": row[6],
                "items": [],
                "avatar": row[11],   # AVATAR NGƯỜI ĐẶT
                "status": row[12]    # TRẠNG THÁI ĐƠN HÀNG
            }
        subtotal = row[10] * row[9]  # quantity * unit_price
        order_dict[oid]["items"].append({
            "image": row[7],
            "nameFood": row[8],
            "unit_price": row[9],
            "quantity": row[10],
            "subtotal": subtotal
        })

    order_list = list(order_dict.values())

    user_info = get_user_info(True)  # Thông tin STAFF đang đăng nhập
    return render_template('order_staff.html', orders=order_list, user=user_info)

@app.route('/update_order_status', methods=['POST'])
def update_order_status():
    order_id = request.form['order_id']
    new_status = request.form['new_status']
    with db.cursor() as cursor:
        cursor.execute("UPDATE orders SET status = %s WHERE IdOrder = %s", (new_status, order_id))
        db.commit()
    return jsonify({"success": True})

# đơn hàng<-


#------------------------------------------------- THANH TOÁN--------------------------------------
@app.route('/staff_order')
def staff_order():
    user_info = get_user_info(True)
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT 
              t.id,
              t.idFood,
              f.nameFood,
              f.price,
              f.orig_price,
              f.nameChef,
              f.quantity,
              f.category,
              f.description,
              f.image,
            #   f.idIngredient,
              f.style
            FROM food_thucdon t
            JOIN food f ON t.idFood = f.idFood;
        """)
        rows = cursor.fetchall()

    foods = []
    for row in rows:
        foods.append({
            "id": row[0],
            "idFood": row[1],
            "nameFood": row[2],
            "price": row[3],
            "orig_price": row[4],
            "nameChef": row[5],
            "quantity": row[6],
            "category": row[7],
            "description": row[8],
            "image": row[9],
            # "idIngredient": row[10],
            "style": row[10]
        })
    
    success = request.args.get("success")
    booking_id = request.args.get("bookingId")   # 👈 Thêm dòng này

    return render_template(
        "staff_order.html",
        user=user_info,
        foods=foods,
        success=success,
        booking_id=booking_id   # 👈 Truyền ra template
    )


payment_status = {}
@app.route("/checkout", methods=["POST"])
def checkout():
    import qrcode, os, json, uuid
    from urllib.parse import quote

    # Lấy form data (KHÔNG PHẢI JSON)
    total = request.form.get("total")
    payment_method = request.form.get("payment")
    items_raw = request.form.get("cart")
    items = json.loads(items_raw)
    booking_id = request.form.get("booking_id")  # None nếu không gửi
    order_id = f"ORDER_{uuid.uuid4().hex[:8]}"

    ip_lan = "192.168.43.31"
    # ip_lan = "192.168.100.202"
    items_encoded = quote(json.dumps(items))

    url = f"http://{ip_lan}:5000/fake_payment_tructiep/{order_id}?total={total}"

    if not os.path.exists("static"):
        os.makedirs("static")
    img = qrcode.make(url)  
    img.save(f"static/qr_{order_id}.png")

    # Đánh dấu trạng thái ban đầu
    payment_status[order_id] = "pending"

    return render_template(
        "qr_checkout.html",
        total=total,
        payment_method=payment_method,
        order_id=order_id,
        url=url,
        items=items,
        booking_id=booking_id  # Có thể là None
    )


@app.route("/fake_payment_tructiep/<order_id>", methods=["GET", "POST"])
def fake_payment_tructiep(order_id):
    import json

    if request.method == "POST":
        fake_account = request.form.get("fake_account")
        total = request.form.get("total")

        print(f"[FAKE PAY] Đơn {order_id} | Số tiền: {total} | STK: {fake_account}")

        payment_status[order_id] = "paid"
        return redirect(url_for("staff_order", success="✅ Thanh toán thành công!"))

    # NHẬN total + items từ query string:
    total = request.args.get("total", "0")
    items_raw = request.args.get("items", "[]")
    items = json.loads(items_raw)

    return render_template(
        "fake_payment_tructiep.html",
        order_id=order_id,
        total=total,
        items=items
    )

@app.route('/save_order_items_counter', methods=['POST'])
def save_order_items_counter():
    from datetime import datetime
    import os

    data = request.get_json()
    items = data.get('items')
    raw_total = data.get('total') or "0"
    total = int(raw_total.replace('.', '').replace('VNĐ', '').strip())
    user_id = session.get('user_id')
    id_table = data.get('id_table')

    if not items:
        return jsonify({'success': False, 'message': 'Thiếu món ăn!'}), 400

    try:
        with db.cursor() as cursor:
            if id_table:  # ✅ Nếu tại bàn
                cursor.execute("""
                    INSERT INTO order_booking_table (IdTable, IdUser, status, grand_total, createdAt)
                    VALUES (%s, %s, %s, %s, NOW())
                """, (
                    id_table,
                    user_id,
                    'Đã thanh toán',
                    total
                ))
                order_id = cursor.lastrowid

                for item in items:
                    cursor.execute("""
                        INSERT INTO order_items_booking (IdOrderBooking, IdFood, quantity, unit_price)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        order_id,
                        item['idFood'],
                        item['quantity'],
                        item['price']
                    ))               
                filename = f"static/hoadon/hoadon_booking_{order_id}.txt"

            else:  # ✅ Nếu tại quầy
                cursor.execute("""
                    INSERT INTO orders (IdUser, timeOrder, status, grand_total)
                    VALUES (%s, NOW(), %s, %s)
                """, (
                    user_id,
                    'Đã thanh toán QR',
                    total
                ))
                order_id = cursor.lastrowid

                for item in items:
                    cursor.execute("""
                        INSERT INTO order_items (IdOrder, IdFood, quantity, unit_price)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        order_id,
                        item['idFood'],
                        item['quantity'],
                        item['price']
                    ))

                filename = f"static/hoadon/hoadon_{order_id}.txt"

            db.commit()

            # ✅ Tạo file hoá đơn TXT
            now = datetime.now()
            os.makedirs('static/hoadon', exist_ok=True)

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"HÓA ĐƠN BÁN HÀNG\n")
                f.write(f"Mã đơn: {order_id}\n")
                f.write(f"Thời gian: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Nhân viên: {user_id}\n")
                if id_table:
                    f.write(f"Bàn số: {id_table}\n")
                f.write("-" * 40 + "\n")
                for item in items:
                    line_total = item['price'] * item['quantity']
                    f.write(f"{item['nameFood']} x {item['quantity']} = {line_total}\n")
                f.write(f"Tổng: {total} VNĐ\n")

        return jsonify({'success': True, 'order_id': order_id})

    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


    
@app.route('/hoadon/<int:order_id>')
def hoadon(order_id):
    from datetime import datetime
    now = datetime.now()

    order_type = request.args.get('type')

    with db.cursor(dictionary=True) as cursor:
        if order_type == 'booking':
            cursor.execute("SELECT * FROM order_booking_table WHERE IdOrderBooking = %s", (order_id,))
            order = cursor.fetchone()

            cursor.execute("""
                SELECT oi.quantity, oi.unit_price as price, f.nameFood
                FROM order_items_booking oi
                JOIN food f ON oi.IdFood = f.IdFood
                WHERE oi.IdOrderBooking = %s
            """, (order_id,))
            cart = cursor.fetchall()

            file_path = f"static/hoadon/hoadon_booking_{order_id}.txt"

        else:
            cursor.execute("SELECT * FROM orders WHERE IdOrder = %s", (order_id,))
            order = cursor.fetchone()

            cursor.execute("""
                SELECT oi.quantity, oi.unit_price as price, f.nameFood
                FROM order_items oi
                JOIN food f ON oi.IdFood = f.IdFood
                WHERE oi.IdOrder = %s
            """, (order_id,))
            cart = cursor.fetchall()

            file_path = f"static/hoadon/hoadon_{order_id}.txt"

    if not order:
        return "Hóa đơn không tồn tại!", 404

    for item in cart:
        if item['price'] is not None:
            item['price'] = int(item['price'])

    return render_template(
        'hoadon.html',
        order_id=order_id,
        cart=cart,
        total=int(order['grand_total']),   # ép ở đây
        payment=order['status'],
        now=now,
        file_path=file_path
    )



@app.route('/tienmat', methods=['POST'])
def tienmat():
    import os
    from datetime import datetime
    import json

    raw_total = request.form.get('total')
    total = int(raw_total.replace('.', '').replace('VNĐ', '').strip())
    cart_json = request.form.get('cart')
    payment = request.form.get('payment')
    cart = json.loads(cart_json)

    user_id = session.get('user_id')
    id_table = request.form.get('booking_id')  # 💡 thêm nếu từ form gửi lên

    with db.cursor() as cursor:
        if id_table:  # ✅ Tại bàn
            cursor.execute("""
                INSERT INTO order_booking_table (IdTable, IdUser, status, grand_total, createdAt)
                VALUES (%s, %s, %s, %s, NOW())
            """, (
                id_table,
                user_id,
                'Đã thanh toán',
                total
            ))
            order_id = cursor.lastrowid

            for item in cart:
                cursor.execute("""
                    INSERT INTO order_items_booking (IdOrderBooking, IdFood, quantity, unit_price)
                    VALUES (%s, %s, %s, %s)
                """, (
                    order_id,
                    item['idFood'],
                    item['quantity'],
                    item['price']
                ))

            filename = f"static/hoadon/hoadon_booking_{order_id}.txt"

        else:  # ✅ Tại quầy
            cursor.execute("""
                INSERT INTO orders (IdUser, timeOrder, status, grand_total)
                VALUES (%s, NOW(), %s, %s)
            """, (
                user_id,
                'Đã thanh toán tiền mặt',
                total
            ))
            order_id = cursor.lastrowid

            for item in cart:
                cursor.execute("""
                    INSERT INTO order_items (IdOrder, IdFood, quantity, unit_price)
                    VALUES (%s, %s, %s, %s)
                """, (
                    order_id,
                    item['idFood'],
                    item['quantity'],
                    item['price']
                ))

            filename = f"static/hoadon/hoadon_{order_id}.txt"

        db.commit()

    # ✅ Tạo hoá đơn TXT
    now = datetime.now()
    os.makedirs('static/hoadon', exist_ok=True)

    with open(filename, 'w', encoding='utf-8') as f:
        f.write("            HÓA ĐƠN BÁN HÀNG            \n")
        f.write(f"Mã đơn: {order_id}\n")
        f.write(f"Thời gian: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Nhân viên ID: {user_id}\n")
        if id_table:
            f.write(f"Bàn số: {id_table}\n")
        f.write("-" * 50 + "\n")
        f.write(f"{'Tên món':20} {'SL':>3} {'Đơn giá':>10} {'Thành tiền':>12}\n")
        f.write("-" * 50 + "\n")

        tong = 0
        for item in cart:
            name = item['nameFood'][:20]
            sl = item['quantity']
            price = item['price']
            thanhtien = sl * price
            tong += thanhtien
            f.write(f"{name:20} {sl:>3} {price:>10,} {thanhtien:>12,}\n")

        f.write("\n")
        f.write("-" * 50 + "\n")
        f.write(f"{'TỔNG CỘNG:'} {tong:>12,} VNĐ\n")
        f.write(f"{'KHÁCH TRẢ:'} {tong:>12,} VNĐ\n")
        f.write("\nXin cảm ơn quý khách!\n")

    return render_template('hoadon.html',
                           order_id=order_id,
                           cart=cart,
                           total=tong,
                           payment=payment,
                           file_path=filename,
                           now=now)

#------------------------------------------------- THANH TOÁN--------------------------------------


# Đặt bàn
@app.route('/booking_staff')
def booking_staff():
    user_info = get_user_info(True)

    with db.cursor(dictionary=True) as cursor:
        cursor.execute("""
            SELECT 
                t.IdTable,
                t.status AS table_status,
                t.IdUser,
                t.number,
                t.createdAt,
                t.time,
                t.notes,
                u.IdUser,
                u.userName,
                u.Email,
                u.Password,
                u.address,
                u.gender,
                u.faceID,
                u.phone,
                u.role,
                u.Avatar,
                u.total_spent,
                u.points,
                obt.status AS booking_status
            FROM 
                table_reservation t
            JOIN 
                users u ON t.IdUser = u.IdUser
            LEFT JOIN 
                order_booking_table obt ON t.IdTable = obt.IdTable
        """)
        reservations = cursor.fetchall()

    return render_template(
        "booking_staff.html",
        reservations=reservations,
        user=user_info
    )

# Đặt bàn<-

@app.route('/consultant_staff')
def consultant_staff():
    user_info = get_user_info(True)

    with db.cursor() as cursor:
        # Lấy tất cả tin nhắn
        cursor.execute("""
            SELECT Idmess, IdSender, IdReceiver, content, time
            FROM chatbox
            ORDER BY Idmess ASC
        """)
        rows = cursor.fetchall()

        messages = []
        for row in rows:
            messages.append({
                "Idmess": row[0],
                "IdSender": row[1],
                "IdReceiver": row[2],
                "content": row[3],
                "time": row[4].strftime("%Y-%m-%d %H:%M:%S")
            })

        # Lấy danh sách khách hàng (role = 'user')
        cursor.execute("""
            SELECT IdUser, userName, Avatar, Email
            FROM users
            WHERE role = 'user'
        """)
        user_rows = cursor.fetchall()

    # Gom khách với tin nhắn cuối
    sidebar_customers = []
    for user_row in user_rows:
        user_id, user_name, user_avatar, user_email = user_row

        # Tìm tin nhắn cuối của khách này
        last_msg = None
        for msg in reversed(messages):  # duyệt ngược
            if (msg["IdSender"] == user_id and msg["IdReceiver"].startswith("U")) or \
               (msg["IdReceiver"] == user_id and msg["IdSender"].startswith("U")):
                last_msg = msg
                break

        if last_msg:
            sidebar_customers.append({
                "IdUser": user_id,
                "userName": user_name,
                "avatar": user_avatar or "default.jpg",
                "last_message": last_msg["content"],
                "time": last_msg["time"]
            })

    return render_template(
        "consultant_staff.html",
        user=user_info,
        messages=messages,  # toàn bộ tin nhắn
        sidebar_customers=sidebar_customers  # khách duy nhất + tin cuối
    )


@app.route('/api/send_message', methods=['POST'])
def send_message_staff():
    data = request.get_json()
    receiver_id = data.get('receiver_id')
    content = data.get('content', '').strip()
    if not receiver_id or not content:
        return jsonify({'success': False, 'message': 'Thiếu dữ liệu'}), 400

    sender_id = session.get('user_id')
    if not sender_id:
        return jsonify({'success': False, 'message': 'Chưa đăng nhập'}), 401

    # Tạo connection mới cho mỗi request
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='quanlynhahangvadoan'   # 👉 đổi thành tên DB của bạn
    )

    try:
        with conn.cursor() as cursor:
            sql = "INSERT INTO chatbox (IdSender, IdReceiver, content) VALUES (%s, %s, %s)"
            cursor.execute(sql, (sender_id, receiver_id, content))
            conn.commit()
    finally:
        conn.close()

    return jsonify({'success': True})

@app.route("/api/update-contact-status", methods=["POST"])
def update_contact_status():
    contact_id = request.form.get("id")
    new_status = request.form.get("status")

    if not contact_id or not new_status:
        return jsonify({"success": False, "message": "Thiếu dữ liệu"}), 400

    with db.cursor() as cursor:
        # Lấy trạng thái hiện tại
        cursor.execute("SELECT status FROM contact WHERE idContact = %s", (contact_id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({"success": False, "message": "Không tìm thấy liên hệ"}), 404

        current_status = result[0]
        if current_status == "Đã liên hệ":
            return jsonify({"success": False, "message": "Không thể cập nhật. Liên hệ đã được xử lý."}), 403

        # Cập nhật nếu chưa phải "Đã liên hệ"
        cursor.execute("UPDATE contact SET status = %s WHERE idContact = %s", (new_status, contact_id))
        db.commit()

    return jsonify({"success": True, "message": "Cập nhật thành công"})


# Trả về HTML
@app.route('/contact_staff')
def contact_staff_page():
    user_info = get_user_info(True)
    return render_template('contact_staff.html', user = user_info)

# API riêng trả JSON
@app.route('/api/contact_staff', methods=['GET'])
def api_get_contacts():
    try:
        with db.cursor() as cursor:
            sql = """
                SELECT 
                    c.idContact,
                    c.status,
                    c.IdUser,
                    c.phone,
                    c.message,
                    u.userName,
                    u.Email
                FROM contact c
                LEFT JOIN users u ON c.IdUser = u.IdUser
            """
            cursor.execute(sql)
            results = cursor.fetchall()
            data = []
            for row in results:
                data.append({
                    "idContact": row[0],
                    "status": row[1],
                    "IdUser": row[2],
                    "phone": row[3],
                    "message": row[4],
                    "userName": row[5],
                    "Email": row[6]
                })
            return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/evaluate_staff')
def evaluate_staff():
    user_info = get_user_info(True)
    return render_template('evaluate_staff.html', user = user_info)
@app.route('/api/reviews', methods=['GET'])
def api_get_reviews():
    try:
        with db.cursor() as cursor:
            sql = """
                SELECT 
                    r.IdReview,
                    r.IdOrder,
                    r.IdFood,
                    r.rating,
                    r.comment,
                    r.created_at,
                    f.nameFood,
                    u.UserName,
                    rr.response_text   -- 👈 thêm trường này
                FROM reviews r
                LEFT JOIN orders o ON r.IdOrder = o.IdOrder
                LEFT JOIN users u ON o.IdUser = u.IdUser
                LEFT JOIN food f ON r.IdFood = f.IdFood
                LEFT JOIN review_responses rr ON r.IdReview = rr.IdReview  -- 👈 thêm JOIN này
            """
            cursor.execute(sql)
            results = cursor.fetchall()
            data = []
            for row in results:
                data.append({
                    "IdReview": row[0],
                    "IdOrder": row[1],
                    "IdFood": row[2],
                    "rating": row[3],
                    "comment": row[4],
                    "created_at": row[5].strftime("%Y-%m-%d %H:%M:%S") if row[5] else "",
                    "FoodName": row[6],
                    "UserName": row[7],
                    "response": row[8]   # 👈 thêm trường này trả về client
                })
            return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/reply-review', methods=['POST'])
def reply_review():
    id_review = request.form.get("id")
    response = request.form.get("response")

    # Lấy từ session thay vì form
    staff_id = session.get("user_id")  

    if not id_review or not response or not staff_id:
        return jsonify({"success": False, "message": "Thiếu dữ liệu."})

    try:
        with db.cursor() as cursor:
            sql = """
                INSERT INTO review_responses (IdReview, StaffId, response_text)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE response_text = VALUES(response_text)
            """
            cursor.execute(sql, (id_review, staff_id, response))
            db.commit()
            return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route('/profile_staff')
def profile_staff():
    user_info = get_user_info(True)

    
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT HeSoLuong, NgayVaoLam, ChucVu, CaLam, DanhGia
        FROM employees
        WHERE IdUser = %s
    """, (session["user_id"],))
    employee = cursor.fetchone()
    cursor.close()

    return render_template(
        "profile_staff.html",
        user=user_info,
        employee=employee
    )


@app.route('/api/update_employee', methods=['POST'])
def update_employee():
    data = request.json

    id_user = data.get('idUser')
    full_name = data.get('fullName')
    address = data.get('address')
    gender = data.get('gender')
    phone = data.get('phone')
    avatar = data.get("avatar")
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                UPDATE users
                SET username=%s, address=%s, gender=%s, phone=%s,Avatar=%s
                WHERE IdUser=%s
            """, (full_name, address, gender, phone,avatar, id_user))

        db.commit()
        return jsonify({'status': 'success'})

    except Exception as e:
        db.rollback()
        return jsonify({'status': 'error', 'message': str(e)})




# Nhập Xuất Kho
# Hàm tính tồn kho
def sync_inventory():
    try:
        with db.cursor() as cursor:
            # 1️⃣ Tính đã tiêu mới
            cursor.execute("""
                SELECT
                  fi.IdIngredient,
                  SUM(o.total_quantity * fi.quantity_needed) AS used_quantity
                FROM
                  (
                    SELECT IdFood, SUM(quantity) AS total_quantity
                    FROM (
                      SELECT IdFood, quantity FROM order_items
                      UNION ALL
                      SELECT IdFood, quantity FROM order_items_booking
                    ) AS all_orders
                    GROUP BY IdFood
                  ) AS o
                JOIN food_ingredient fi ON o.IdFood = fi.IdFood
                GROUP BY fi.IdIngredient
            """)
            used_now = cursor.fetchall()

            for row in used_now:
                id_ing = row[0]
                used_qty_now = row[1]

                # 2️⃣ Lấy số đã lưu trước đó
                cursor.execute("""
                    SELECT used_quantity FROM save_tieu WHERE IdIngredient = %s
                """, (id_ing,))
                result = cursor.fetchone()
                saved_qty = result[0] if result else 0

                # 3️⃣ Tính chênh lệch
                diff = used_qty_now - saved_qty

                if diff > 0:
                    # 4️⃣ Trừ tồn kho
                    cursor.execute("""
                        UPDATE ingredient
                        SET quantity = GREATEST(quantity - %s, 0)
                        WHERE IdIngredient = %s
                    """, (diff, id_ing))

                # 5️⃣ Cập nhật lại save_tieu
                cursor.execute("""
                    INSERT INTO save_tieu (IdIngredient, used_quantity)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE used_quantity = VALUES(used_quantity)
                """, (id_ing, used_qty_now))

            db.commit()
            print("✅ Đồng bộ kho thành công (theo chênh lệch)!")

    except Exception as e:
        db.rollback()
        print("❌ Lỗi:", str(e))

  
from flask import request, render_template
from collections import defaultdict
from datetime import date

# @app.route('/import_staff')
# def import_staff():
#     user_info = get_user_info(True)
#     sync_inventory()

#     from_date = request.args.get('from')
#     to_date = request.args.get('to')

#     # Nếu chưa chọn ngày thì mặc định lấy hôm nay
#     if not from_date or not to_date:
#         today = date.today().isoformat()
#         from_date = today
#         to_date = today

#     # ⚡ Gắn thêm giờ để không mất dữ liệu
#     from_date_full = f"{from_date} 00:00:00"
#     to_date_full = f"{to_date} 23:59:59"

#     with db.cursor(dictionary=True) as cursor:
#         # 1️⃣ Tính từ orders
#         cursor.execute("""
#             SELECT
#               fi.IdIngredient,
#               i.nameIngredient,
#               SUM(oi.quantity * fi.quantity_needed) AS used_quantity
#             FROM
#               orders o
#               JOIN order_items oi ON o.IdOrder = oi.IdOrder
#               JOIN food_ingredient fi ON oi.IdFood = fi.IdFood
#               JOIN ingredient i ON fi.IdIngredient = i.IdIngredient
#             WHERE o.timeOrder BETWEEN %s AND %s
#             GROUP BY fi.IdIngredient, i.nameIngredient
#         """, (from_date_full, to_date_full))
#         orders_used = cursor.fetchall()

#         # 2️⃣ Tính từ order_booking_table
#         cursor.execute("""
#             SELECT
#               fi.IdIngredient,
#               i.nameIngredient,
#               SUM(oib.quantity * fi.quantity_needed) AS used_quantity
#             FROM
#               order_booking_table obt
#               JOIN order_items_booking oib ON obt.IdOrderBooking = oib.IdOrderBooking
#               JOIN food_ingredient fi ON oib.IdFood = fi.IdFood
#               JOIN ingredient i ON fi.IdIngredient = i.IdIngredient
#             WHERE obt.createdAt BETWEEN %s AND %s
#             GROUP BY fi.IdIngredient, i.nameIngredient
#         """, (from_date_full, to_date_full))
#         booking_used = cursor.fetchall()

#         # 3️⃣ Gộp lại
#         used_dict = defaultdict(lambda: {"IdIngredient": None, "nameIngredient": None, "used_quantity": 0})

#         for row in orders_used + booking_used:
#             key = row['IdIngredient']
#             used_dict[key]['IdIngredient'] = key
#             used_dict[key]['nameIngredient'] = row['nameIngredient']
#             used_dict[key]['used_quantity'] += row['used_quantity']

#         used_ingredients = list(used_dict.values())

#         # 4️⃣ Tồn kho hiện tại
#         cursor.execute("""
#             SELECT
#               IdIngredient,
#               nameIngredient,
#               quantity AS remaining_quantity
#             FROM
#               ingredient
#             ORDER BY IdIngredient
#         """)
#         remaining_ingredients = cursor.fetchall()

#     return render_template(
#         "import_staff.html",
#         user=user_info,
#         used_ingredients=used_ingredients,
#         remaining_ingredients=remaining_ingredients,
#         from_date=from_date,
#         to_date=to_date
#     )

from flask import request, render_template
from collections import defaultdict
from datetime import date

from flask import request, render_template
from collections import defaultdict
from datetime import date

@app.route('/import_staff')
def import_staff():
    user_info = get_user_info(True)
    sync_inventory()

    from_date = request.args.get('from')
    to_date = request.args.get('to')

    # Nếu chưa chọn ngày thì lấy hôm nay
    if not from_date or not to_date:
        today = date.today().isoformat()
        from_date = today
        to_date = today

    from_date_full = f"{from_date} 00:00:00"
    to_date_full = f"{to_date} 23:59:59"

    print("From:", from_date_full)
    print("To:", to_date_full)

    with db.cursor(dictionary=True) as cursor:
        # 1️⃣ Tiêu hao từ orders
        cursor.execute("""
            SELECT
              fi.IdIngredient,
              i.nameIngredient,
              SUM(oi.quantity * fi.quantity_needed) AS used_quantity
            FROM
              orders o
              JOIN order_items oi ON o.IdOrder = oi.IdOrder
              JOIN food_ingredient fi ON oi.IdFood = fi.IdFood
              JOIN ingredient i ON fi.IdIngredient = i.IdIngredient
            WHERE o.timeOrder BETWEEN %s AND %s
            GROUP BY fi.IdIngredient, i.nameIngredient
        """, (from_date_full, to_date_full))
        orders_used = cursor.fetchall()

        # 2️⃣ Tiêu hao từ order_booking_table
        cursor.execute("""
            SELECT
              fi.IdIngredient,
              i.nameIngredient,
              SUM(oib.quantity * fi.quantity_needed) AS used_quantity
            FROM
              order_booking_table obt
              JOIN order_items_booking oib ON obt.IdOrderBooking = oib.IdOrderBooking
              JOIN food_ingredient fi ON oib.IdFood = fi.IdFood
              JOIN ingredient i ON fi.IdIngredient = i.IdIngredient
            WHERE obt.createdAt BETWEEN %s AND %s
            GROUP BY fi.IdIngredient, i.nameIngredient
        """, (from_date_full, to_date_full))
        booking_used = cursor.fetchall()

        # 3️⃣ Gộp tiêu hao thực tế
        used_dict = defaultdict(lambda: {"IdIngredient": None, "nameIngredient": None, "used_quantity": 0})

        for row in orders_used + booking_used:
            key = row['IdIngredient']
            used_dict[key]['IdIngredient'] = key
            used_dict[key]['nameIngredient'] = row['nameIngredient']
            used_dict[key]['used_quantity'] += row['used_quantity']

        used_ingredients = list(used_dict.values())

        # 4️⃣ Xuất kho thực tế trong khoảng lọc
        cursor.execute("""
            SELECT
              we.IdIngredient,
              i.nameIngredient,
              SUM(we.quantity) AS exported_quantity
            FROM
              warehouse_export we
              JOIN ingredient i ON we.IdIngredient = i.IdIngredient
            WHERE we.export_date BETWEEN %s AND %s
            GROUP BY we.IdIngredient, i.nameIngredient
        """, (from_date_full, to_date_full))
        exported_ingredients = cursor.fetchall()

        # 5️⃣ Tồn kho thực tế = tổng nhập - tổng xuất
        cursor.execute("""
            SELECT
              i.IdIngredient,
              i.nameIngredient,
              IFNULL(im.total_import, 0) - IFNULL(ex.total_export, 0) AS remaining_quantity
            FROM
              ingredient i
              LEFT JOIN (
                SELECT IdIngredient, SUM(quantity) AS total_import
                FROM warehouse_import
                GROUP BY IdIngredient
              ) im ON i.IdIngredient = im.IdIngredient
              LEFT JOIN (
                SELECT IdIngredient, SUM(quantity) AS total_export
                FROM warehouse_export
                GROUP BY IdIngredient
              ) ex ON i.IdIngredient = ex.IdIngredient
            ORDER BY i.IdIngredient
        """)
        remaining_ingredients = cursor.fetchall()

    return render_template(
        "import_staff.html",
        user=user_info,
        used_ingredients=used_ingredients,
        exported_ingredients=exported_ingredients,
        remaining_ingredients=remaining_ingredients,
        from_date=from_date,
        to_date=to_date
    )


@app.route('/adjust_stock_post', methods=['POST'])
def adjust_stock_post():
    data = request.get_json()
    adjustments = data.get('adjustments', [])
    user_id = session.get('user_id', 'admin')

    try:
        with db.cursor() as cursor:
            for adj in adjustments:
                id_ing = adj['IdIngredient']
                diff = adj['diff']

                if diff > 0:
                    # Dư → Ghi thêm IMPORT
                    cursor.execute(
                        "INSERT INTO warehouse_import (IdIngredient, quantity, import_date, IdUser) VALUES (%s, %s, NOW(), %s)",
                        (id_ing, diff, user_id)
                    )
                elif diff < 0:
                    # Thiếu → Ghi thêm EXPORT
                    cursor.execute(
                        "INSERT INTO warehouse_export (IdIngredient, quantity, export_date, IdUser) VALUES (%s, %s, NOW(), %s)",
                        (id_ing, abs(diff), user_id)
                    )
                # Nếu diff == 0 thì không làm gì

        db.commit()
        return jsonify({'status': 'success', 'message': 'Điều chỉnh tồn kho thành công!'})
    except Exception as e:
        db.rollback()
        print("Lỗi:", e)
        return jsonify({'status': 'error', 'message': str(e)})



@app.route('/import_staff_post', methods=['POST'])
def import_staff_post():
    data = request.json
    items = data.get('items', [])
    staff_id = session.get('staff_id', 'staff_default')
    today = datetime.today().strftime('%Y-%m-%d')

    try:
        with db.cursor() as cursor:
            for item in items:
                # Ghi vào bảng lịch sử nhập kho
                sql_import = """
                    INSERT INTO warehouse_import 
                    (idUser, IdIngredient, quantity, unit_price, import_date)
                    VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(sql_import, (
                    staff_id,
                    item['IdIngredient'],
                    item['quantity'],
                    item['unit_price'],
                    today
                ))

                # Cộng dồn tồn kho nguyên liệu
                sql_update = """
                    UPDATE ingredient
                    SET quantity = quantity + %s
                    WHERE IdIngredient = %s
                """
                cursor.execute(sql_update, (
                    item['quantity'],
                    item['IdIngredient']
                ))

        db.commit()
        return jsonify({'status': 'success', 'message': 'Nhập kho thành công!'})

    except Exception as e:
        print('Error:', e)
        db.rollback()
        return jsonify({'status': 'error', 'message': 'Lỗi nhập kho!'}), 500


# 1️⃣ Route tạo phiếu xuất 
@app.route('/export_staff_post', methods=['POST'])
def export_staff_post():
    data = request.json
    items = data.get('items', [])
    IdUser = session.get('user_id')
    today = datetime.today().strftime('%Y-%m-%d')

    try:
        with db.cursor() as cursor:
            for item in items:
                # Ghi log xuất kho
                cursor.execute("""
                    INSERT INTO warehouse_export 
                    (IdUser, IdIngredient, quantity, export_date)
                    VALUES (%s, %s, %s, %s)
                """, (IdUser, item['IdIngredient'], item['quantity'], today))

                # Trừ tồn kho
                cursor.execute("""
                    UPDATE ingredient
                    SET quantity = quantity - %s
                    WHERE IdIngredient = %s
                """, (item['quantity'], item['IdIngredient']))

        db.commit()
        return jsonify({'status': 'success', 'message': 'Xuất kho thành công!'})

    except Exception as e:
        db.rollback()
        return jsonify({'status': 'error', 'message': str(e)})

# 2️⃣ Route điều chỉnh cuối ngày
@app.route('/adjust_export', methods=['POST'])
def adjust_export():
    data = request.json
    adjustments = data.get('adjustments', [])
    staff_id = session.get('staff_id', 'staff_default')
    today = datetime.today().strftime('%Y-%m-%d')

    try:
        with db.cursor() as cursor:
            for adj in adjustments:
                chenh_lech = adj['real_used'] - adj['exported']

                if chenh_lech > 0:
                    # Xuất bổ sung
                    cursor.execute("""
                        INSERT INTO warehouse_export
                        (StaffId, IdIngredient, quantity, export_date)
                        VALUES (%s, %s, %s, %s)
                    """, (staff_id, adj['IdIngredient'], chenh_lech, today))

                    cursor.execute("""
                        UPDATE ingredient
                        SET quantity = quantity - %s
                        WHERE IdIngredient = %s
                    """, (chenh_lech, adj['IdIngredient']))

                elif chenh_lech < 0:
                    # Nhập trả
                    cursor.execute("""
                        INSERT INTO warehouse_import
                        (StaffId, IdIngredient, quantity, unit_price, import_date)
                        VALUES (%s, %s, %s, 0, %s)
                    """, (staff_id, adj['IdIngredient'], -chenh_lech, today))

                    cursor.execute("""
                        UPDATE ingredient
                        SET quantity = quantity + %s
                        WHERE IdIngredient = %s
                    """, (-chenh_lech, adj['IdIngredient']))

        db.commit()
        return jsonify({'status': 'success', 'message': 'Điều chỉnh thành công!'})

    except Exception as e:
        db.rollback()
        return jsonify({'status': 'error', 'message': str(e)})



@app.route('/booking_admin')
def booking_admin():
    user_info = get_user_info(True)
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT 
                tr.IdTable, ob.status, tr.number, tr.createdAt, tr.time, tr.notes,
                u.userName, u.phone, u.email
            FROM 
                table_reservation tr
            JOIN 
                users u ON tr.IdUser = u.IdUser
            JOIN
                order_booking_table ob ON tr.IdTable = ob.IdTable
        """)
        bookings = cursor.fetchall()
    return render_template(
        'booking_admin.html',
        user=user_info,
        bookings=bookings,
        datetime=datetime  # Truyền datetime nếu dùng trong template
    )



@app.route('/detail_booking', methods=['POST'])
def detail_booking():
    id_table = request.form.get('IdTable')
    user_info = get_user_info(True)
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT 
                tr.IdTable, tr.status, tr.number, tr.createdAt, tr.time, tr.notes,
                u.userName, u.phone, u.email
            FROM 
                table_reservation tr
            JOIN 
                users u ON tr.IdUser = u.IdUser
            WHERE 
                tr.IdTable = %s
        """, (id_table,))
        booking_detail = cursor.fetchone()
    return render_template('detail_booking.html',user=user_info, detail=booking_detail, datetime=datetime)



@app.route('/consultant_admin', methods=['GET'])
def consultant_admin():
    user_info = get_user_info(True)
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT 
                u.IdUser, 
                u.userName, 
                u.phone, 
                u.email,
                MAX(c.time) AS latest_time
            FROM 
                chatbox c
            JOIN 
                users u ON c.IdSender = u.IdUser
            WHERE 
                u.role = 'user'
            GROUP BY 
                u.IdUser, u.userName, u.phone, u.email
            ORDER BY 
                latest_time DESC;
        """)
        consultants = cursor.fetchall()
    return render_template(
        'consultant_admin.html',
        user=user_info,
        consultants=consultants
    )




@app.route('/detail_consultant_admin')
def detail_consultant_admin():
    user_info = get_user_info(True)

    id_user = request.args.get('IdUser')  # <-- Phải lấy đúng ID từ URL
    if not id_user:
        return "Missing IdUser", 400

    with db.cursor() as cursor:
        cursor.execute("""
            SELECT Idmess, IdSender, IdReceiver, content, time 
            FROM chatbox 
            WHERE IdSender = %s OR IdReceiver = %s 
            ORDER BY time ASC
        """, (id_user, id_user))
        rows = cursor.fetchall()

    messages = []
    for row in rows:
        messages.append({
            "Idmess": row[0],
            "IdSender": str(row[1]),  # Nhớ ép kiểu nếu IdUser là VARCHAR
            "IdReceiver": str(row[2]),
            "content": row[3],
            "time": row[4].strftime("%Y-%m-%d %H:%M:%S")
        })

    return render_template(
        "detail_consultant_admin.html",
        user=user_info,
        messages=messages,
        id_user=id_user  # <-- truyền chính xác xuống template
    )


@app.route('/contact_admin')
def contact_admin():
    user_info = get_user_info(True)
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT 
                c.idContact,
                u.IdUser,
                u.userName,
                u.email,
                c.phone,
                c.message,
                c.status
            FROM 
                contact c
            JOIN 
                users u ON c.IdUser = u.IdUser
            ORDER BY 
                c.idContact DESC
        """)
        contacts = cursor.fetchall()
    return render_template(
        "contact_admin.html",
        user=user_info,
        contacts=contacts
    )































# ADMIN

# ---------- ADMIN DASHBOARD ----------

@app.route('/order_admin')
def order_admin():
    with db.cursor(dictionary=True) as cursor:
        sql = """
            SELECT 
                orders.IdOrder,
                orders.IdUser,
                users.userName,
                users.address,
                orders.timeOrder,
                orders.status,
                orders.phone,
                orders.payment_method,
                orders.note
            FROM orders
            JOIN users ON orders.IdUser = users.IdUser
        """
        cursor.execute(sql)
        orders = cursor.fetchall()
        user = get_user_info(True)
    return render_template('order_admin.html', orders=orders,user = user)

@app.route('/infor_order_admin', methods=['POST'])
def infor_order_admin():
    order_id = request.form.get('order_id')
    if not order_id:
        return "Thiếu ID đơn hàng", 400

    with db.cursor(dictionary=True) as cursor:
        # Lấy thông tin đơn hàng và user
        cursor.execute("""
            SELECT 
                o.IdOrder,
                o.IdUser,
                o.timeOrder,
                o.status,
                o.grand_total,
                o.discount_code,
                o.phone AS order_phone,
                o.payment_method,
                o.note,
                u.userName,
                u.phone AS user_phone,
                u.address
            FROM orders o
            JOIN users u ON o.IdUser = u.IdUser
            WHERE o.IdOrder = %s
        """, (order_id,))
        order = cursor.fetchone()

        if not order:
            return "Không tìm thấy đơn hàng", 404

        # Lấy các món trong đơn hàng
        cursor.execute("""
            SELECT 
                f.nameFood, 
                f.Image, 
                f.price, 
                oi.quantity
            FROM order_items oi
            JOIN food f ON oi.IdFood = f.IdFood
            WHERE oi.IdOrder = %s
        """, (order_id,))
        items = cursor.fetchall()
    user = get_user_info(True)
    return render_template('infor_order_admin.html', order=order, items=items , user = user)

# Trả về HTML
@app.route('/dish_admin')
def dish_admin():
    user_info = get_user_info(True)
    # Kết nối DB
    cursor = db.cursor()
    cursor.execute("""
        SELECT 
            IdFood, nameFood, price, orig_price, 
            quantity, category, description, image, style 
        FROM food
    """)
    foods = cursor.fetchall()
    cursor.close()
    return render_template('dish_admin.html', user=user_info, foods=foods)



@app.route('/api/update_food', methods=['POST'])
def update_food():
    data = request.json
    id_food = data['IdFood']
    name_food = data['nameFood']
    category = data['category']
    style = data['style']
    orig_price = data['orig_price']
    price = data['price']

    try:
        with db.cursor() as cursor:
            sql = """
                UPDATE food
                SET nameFood=%s, category=%s, style=%s, orig_price=%s, price=%s
                WHERE IdFood=%s
            """
            cursor.execute(sql, (name_food, category, style, orig_price, price, id_food))
            db.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.rollback()
        return jsonify({'status': 'fail', 'error': str(e)})

@app.route('/api/delete_food', methods=['POST'])
def delete_food():
    data = request.json
    id_food = data.get('IdFood')

    try:
        with db.cursor() as cursor:
            # Xóa rewards liên quan trước
            cursor.execute("DELETE FROM rewards WHERE idFood = %s", (id_food,))
            # Xóa food_ingredient liên quan
            cursor.execute("DELETE FROM food_ingredient WHERE IdFood = %s", (id_food,))
            # Cuối cùng xóa food
            cursor.execute("DELETE FROM food WHERE IdFood = %s", (id_food,))
        db.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.rollback()
        return jsonify({'status': 'error', 'error': str(e)})

@app.route('/detail_dish_admin/<id_food>')
def detail_dish_admin(id_food):
    user_info = get_user_info(True)
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT IdFood, nameFood, image, style, category, orig_price, price, description
            FROM food WHERE IdFood = %s
        """, (id_food,))
        food = cursor.fetchone()

        cursor.execute("SELECT AVG(rating) FROM reviews WHERE IdFood = %s", (id_food,))
        avg_rating = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT 
                COALESCE((SELECT SUM(quantity) FROM order_items WHERE IdFood = %s), 0) +
                COALESCE((SELECT SUM(quantity) FROM order_items_booking WHERE IdFood = %s), 0) 
        """, (id_food, id_food))
        total_sold = cursor.fetchone()[0] or 0

    return render_template("detail_dish_admin.html", food=food, avg_rating=avg_rating, total_sold=total_sold,user = user_info)


@app.route('/admin')
def admin():
    user_info = get_user_info(True)  
    return render_template('admin.html', user=user_info)

@app.route('/bill_admin')
def bill_admin():
    with db.cursor() as cursor:
        cursor.execute("""
            (
              SELECT 
                  o.IdOrder AS order_id,
                  'Online' AS order_type,
                  o.payment_method,
                  o.grand_total AS total_price,
                  o.timeOrder AS created_at
              FROM orders o
            )
            UNION ALL
            (
              SELECT 
                  obt.IdOrderBooking AS order_id,
                  'Tại quầy' AS order_type,
                  NULL AS payment_method,
                  obt.grand_total AS total_price,
                  obt.createdAt AS created_at
              FROM order_booking_table obt
            )
        """)
        bills = cursor.fetchall()

    user_info = get_user_info(True)
    return render_template('bill_admin.html', bills=bills, user=user_info)


@app.route('/detail_bill')
def detail_bill():
    order_id = request.args.get('order_id')
    order_type = request.args.get('order_type')  # Lấy thêm loại đơn hàng từ URL

    if not order_id:
        return "Thiếu order_id", 400

    raw_id = order_id.replace("HD", "")  # Nếu đang có tiền tố HD

    with db.cursor() as cursor:
        if order_type == 'Online':
            # Lấy từ bảng orders
            cursor.execute("""
                SELECT IdOrder, 'Online' AS order_type, payment_method, grand_total, timeOrder 
                FROM orders 
                WHERE IdOrder = %s
            """, (raw_id,))
            order = cursor.fetchone()

            # Chi tiết món ăn từ order_items
            cursor.execute("""
                SELECT f.image, f.nameFood, oi.unit_price, oi.quantity, (oi.unit_price * oi.quantity) AS total
                FROM order_items oi
                JOIN food f ON oi.IdFood = f.IdFood
                WHERE oi.IdOrder = %s
            """, (raw_id,))
            items = cursor.fetchall()

        elif order_type == 'Tại quầy':
            # Lấy từ order_booking_table
            cursor.execute("""
                SELECT IdOrderBooking AS IdOrder, 'Tại quầy' AS order_type, NULL AS payment_method, grand_total, createdAt 
                FROM order_booking_table
                WHERE IdOrderBooking = %s
            """, (raw_id,))
            order = cursor.fetchone()

            # Lấy chi tiết món ăn cũng từ order_items (nếu vẫn dùng chung)
            cursor.execute("""
                SELECT f.image, f.nameFood, oi.unit_price, oi.quantity, (oi.unit_price * oi.quantity) AS total
                FROM order_items oi
                JOIN food f ON oi.IdFood = f.IdFood
                WHERE oi.IdOrder = %s
            """, (raw_id,))
            items = cursor.fetchall()

        else:
            return "Thiếu hoặc sai order_type", 400

    if not order:
        return "Không tìm thấy hóa đơn", 404
    user_info = get_user_info(True)
    return render_template('detail_bill.html', order=order, items=items,user = user_info)




# @app.route('/revenue_admin')
# def revenue_admin():
#     user_info = get_user_info(True)

#     total_revenue = 0
#     total_cost = 0

#     with db.cursor() as cursor:
#         # Doanh thu online
#         cursor.execute("SELECT IFNULL(SUM(grand_total), 0) FROM orders")
#         total_orders = cursor.fetchone()[0]

#         # Doanh thu tại quầy
#         cursor.execute("SELECT IFNULL(SUM(grand_total), 0) FROM order_booking_table")
#         total_booking = cursor.fetchone()[0]

#         total_revenue = total_orders + total_booking

#         # Chi phí
#         cursor.execute("""
#             SELECT SUM(s.used_quantity * i.price)
#             FROM save_tieu s
#             JOIN ingredient i ON s.IdIngredient = i.IdIngredient
#         """)
#         result = cursor.fetchone()[0]
#         total_cost = result if result else 0

#     # Format tiền: làm tròn và thêm dấu phân tách
#     total_revenue = "{:,.0f}".format(total_revenue)
#     total_cost = "{:,.0f}".format(total_cost)
#     profit = total_orders + total_booking - (result if result else 0)
#     profit = "{:,.2f}".format(profit)
#     return render_template(
#         "revenue_admin.html",
#         user=user_info,
#         total_revenue=total_revenue,
#         total_cost=total_cost,
#         profit=profit
#     )

@app.route('/revenue_admin')
def revenue_admin():
    user_info = get_user_info(True)

    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    print("From date:", from_date)
    print("To date:", to_date)

    where_orders = ""
    where_booking = ""
    where_import = ""
    params = ()

    if from_date and to_date:
        where_orders = "WHERE DATE(timeOrder) BETWEEN %s AND %s"
        where_booking = "WHERE DATE(createdAt) BETWEEN %s AND %s"
        where_import = "WHERE DATE(import_date) BETWEEN %s AND %s"
        params = (from_date, to_date)

    with db.cursor() as cursor:
        # Tổng doanh thu online
        cursor.execute(f"SELECT IFNULL(SUM(grand_total), 0) FROM orders {where_orders}", params)
        total_orders = cursor.fetchone()[0] or 0

        # Tổng doanh thu tại quầy
        cursor.execute(f"SELECT IFNULL(SUM(grand_total), 0) FROM order_booking_table {where_booking}", params)
        total_booking = cursor.fetchone()[0] or 0

        total_revenue_raw = total_orders + total_booking

        # Tổng chi phí nhập kho
        cursor.execute(f"""
            SELECT IFNULL(SUM(quantity * unit_price), 0)
            FROM warehouse_import
            {where_import}
        """, params)
        total_cost_raw = cursor.fetchone()[0] or 0

        # Tổng số đơn online
        cursor.execute(f"SELECT COUNT(*) FROM orders {where_orders}", params)
        total_orders_count = cursor.fetchone()[0] or 0

        # Tổng số đơn tại quầy
        cursor.execute(f"SELECT COUNT(*) FROM order_booking_table {where_booking}", params)
        total_booking_count = cursor.fetchone()[0] or 0

        total_orders_all = total_orders_count + total_booking_count

        # ✅ LẤY DOANH THU THEO THÁNG (năm hiện tại)
        cursor.execute("""
            SELECT MONTH(timeOrder) AS month, SUM(grand_total) AS total
            FROM orders
            WHERE YEAR(timeOrder) = YEAR(CURDATE())
            GROUP BY MONTH(timeOrder)
            ORDER BY month
        """)
        monthly = cursor.fetchall()

        # ✅ LẤY CHI PHÍ THEO THÁNG (năm hiện tại)
        cursor.execute("""
            SELECT MONTH(import_date) AS month, SUM(quantity * unit_price) AS total_cost
            FROM warehouse_import
            WHERE YEAR(import_date) = YEAR(CURDATE())
            GROUP BY MONTH(import_date)
            ORDER BY month
        """)
        monthly_cost = cursor.fetchall()

        # ✅ TẠO labels 12 tháng cố định
        chart_labels = [f"Tháng {i}" for i in range(1, 13)]
        chart_revenue = [0] * 12
        chart_cost = [0] * 12

        for row in monthly:
            month = row[0]
            value = row[1] or 0
            chart_revenue[month - 1] = value

        for row in monthly_cost:
            month = row[0]
            value = row[1] or 0
            chart_cost[month - 1] = value

    profit_raw = total_revenue_raw - total_cost_raw

    total_revenue = "{:,.0f}".format(total_revenue_raw)
    total_cost = "{:,.0f}".format(total_cost_raw)
    profit = "{:,.0f}".format(profit_raw)

    return render_template(
        "revenue_admin.html",
        user=user_info,
        total_revenue=total_revenue,
        total_cost=total_cost,
        profit=profit,
        total_orders_all=total_orders_all,
        from_date=from_date,
        to_date=to_date,
        chart_labels=chart_labels,
        chart_revenue=chart_revenue,
        chart_cost=chart_cost
    )


# ADMIN END
# cập nhật điểm
def update_user_stats(user_id, amount_spent):
    try:
        with db.cursor() as cursor:
            # Cập nhật điểm và tổng chi tiêu
            sql = """
                UPDATE users
                SET 
                    points = points + 1,
                    total_spent = total_spent + %s
                WHERE IdUser = %s
            """
            cursor.execute(sql, (amount_spent, user_id))
        db.commit()
        print(f"✅ Đã cập nhật user {user_id}")
    except Exception as e:
        print("❌ Lỗi khi cập nhật:", e)

# cập nhật cập nhật mã
def auto_generate_discount(user_id):
    cursor = db.cursor()

    # 1. Lấy tổng chi tiêu của người dùng
    cursor.execute("SELECT total_spent FROM users WHERE IdUser = %s", (user_id,))
    result = cursor.fetchone()
    if not result:
        cursor.close()
        return

    total_spent = result[0]
    milestone = int(total_spent // 1_000_000)

    # 2. Lấy mã giảm giá lớn nhất đã có
    cursor.execute("""
        SELECT MAX(amount) FROM discount_codes WHERE IdUser = %s
    """, (user_id,))
    amount_max = cursor.fetchone()[0]

    if amount_max:
        current_max_milestone = amount_max // 100_000  # Vì mỗi mã +100k
    else:
        current_max_milestone = 0

    # 3. Chỉ for các mốc mới
    for i in range(current_max_milestone + 1, milestone + 1):
        code = f"SALE{i * 100}"
        amount = i * 100_000
        cursor.execute("""
            INSERT INTO discount_codes (IdUser, discount_code, amount, created_at, img, used)
            VALUES (%s, %s, %s, %s, %s, 0)
        """, (
            user_id,
            code,
            amount,
            datetime.now(),
            f"{code.lower()}.jpg"
        ))
        print(f"🎉 Đã tạo mã {code} cho user {user_id}")

    db.commit()
    cursor.close()

#-------------------------------- NHÂN VIÊN


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
