# 💬 Chat App với Video Calling

Ứng dụng chat real-time với tính năng gọi video sử dụng WebRTC, Flask và Socket.IO.

## ✨ Tính năng

- ✅ **Đăng ký/Đăng nhập** với username và password
- ✅ **Chat real-time** với Socket.IO
- ✅ **Gửi file và hình ảnh** với preview
- ✅ **Video calling** với WebRTC
- ✅ **Bảo mật** mật khẩu với SHA-256
- ✅ **Giao diện đẹp** như Messenger
- ✅ **Responsive design** cho mọi thiết bị

## 🚀 Cách chạy dự án

### 1. Cài đặt Python packages
```bash
cd c:\Users\asus\Downloads\webrtc_p2p_video_call
pip install -r requirements.txt
```

### 2. Chạy server
```bash
python source/server/app.py
```

### 3. Truy cập ứng dụng
- **Trang chủ:** http://127.0.0.1:5001
- **Chat:** http://127.0.0.1:5001/chat

### 4. Test với nhiều người
- **Cách 1:** Mở tab ẩn danh (Ctrl+Shift+N) và đăng ký tài khoản khác
- **Cách 2:** Chia sẻ IP với bạn bè: `http://[IP_máy_bạn]:5001`

## 🗃️ Quản lý Database

### Xem database nhanh
```bash
python show_db.py
```

### Các options database viewer
```bash
python show_db.py --all      # Hiển thị TẤT CẢ tin nhắn
python show_db.py --users    # Chỉ hiển thị users
python show_db.py --menu     # Menu tương tác
```

### Database manager đầy đủ
```bash
python db_viewer.py
```
- **Option 1:** Xem database
- **Option 2:** Xóa database  
- **Option 3:** Tạo test database với users mẫu
- **Option 4:** Kiểm tra file database

### Tạo test data
```bash
# Chạy db_viewer.py và chọn option 3
# Sẽ tạo các user test:
# Username: alice, Password: 123456
# Username: bob, Password: 123456
# Username: charlie, Password: 123456
# Username: test, Password: password
```

## 📂 Cấu trúc dự án

```
webrtc_p2p_video_call/
├── source/
│   └── server/
│       └── app.py              # Flask server chính
├── templates/
│   ├── index.html             # Trang đăng nhập/đăng ký
│   └── chat.html              # Trang chat và video call
├── uploads/                   # Thư mục lưu file upload
├── messenger.db               # Database SQLite
├── requirements.txt           # Python dependencies
├── show_db.py                # Xem database nhanh
├── db_viewer.py              # Quản lý database đầy đủ
└── README.md                 # File hướng dẫn này
```

## 🎯 Hướng dẫn sử dụng

### Đăng ký tài khoản mới
1. Truy cập http://127.0.0.1:5001
2. Click tab "Đăng ký"
3. Nhập username và password (tối thiểu 6 ký tự)
4. Click "Tạo tài khoản"

### Đăng nhập
1. Click tab "Đăng nhập"
2. Nhập username và password
3. Click "Đăng nhập"

### Chat với người khác
1. Chọn user từ danh sách bên trái
2. Gõ tin nhắn và Enter hoặc click ➤
3. Click 📎 để gửi file/ảnh

### Video call
1. Chọn user muốn gọi
2. Click "📹 Gọi video"
3. Cho phép quyền Camera/Microphone
4. Đợi người kia chấp nhận cuộc gọi

## 🔧 Troubleshooting

### Lỗi thường gặp

**1. Database not found**
```bash
# Chạy server lần đầu để tạo database
python source/server/app.py
```

**2. Port 5001 đã được sử dụng**
```bash
# Kiểm tra process đang dùng port
netstat -ano | findstr :5001
# Hoặc đổi port trong app.py
```

**3. Video call không hoạt động**
- Sử dụng `127.0.0.1:5001` thay vì IP khác
- Cho phép quyền Camera/Microphone
- Sử dụng Chrome hoặc Firefox
- Deploy lên HTTPS cho production

**4. File upload lỗi**
- Kiểm tra file size < 16MB
- Kiểm tra thư mục `uploads/` tồn tại
- Restart server nếu cần

### Reset database
```bash
# Xóa toàn bộ dữ liệu
python db_viewer.py
# Chọn option 2, gõ "DELETE" để xác nhận
```

## 🌐 Deploy Production

### Chuẩn bị deploy
1. Tạo GitHub repository
2. Push code lên GitHub
3. Deploy lên Render.com hoặc Heroku
4. Cấu hình HTTPS để video call hoạt động

### Environment variables cần thiết
```
PORT=5000
FLASK_ENV=production
```

## 📝 Dependencies

```
Flask==2.3.3
Flask-SocketIO==5.3.6
python-socketio==5.8.0
python-engineio==4.7.1
Werkzeug==2.3.7
gunicorn==21.2.0
```

## 🆘 Liên hệ hỗ trợ

Nếu gặp vấn đề:
1. Kiểm tra phần Troubleshooting ở trên
2. Xem logs trong terminal
3. Kiểm tra browser console (F12)
4. Restart server và thử lại

---
