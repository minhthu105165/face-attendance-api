# 📷 Face Attendance API

Hệ thống điểm danh tự động bằng nhận diện khuôn mặt, xây dựng với **FastAPI** + **ArcFace** (thư viện `uniface`).

---

## Tính năng

- Đăng ký khuôn mặt sinh viên (upload ảnh hoặc chụp webcam)
- Điểm danh tự động từ ảnh — nhận diện nhiều khuôn mặt cùng lúc
- Lưu lịch sử từng phiên điểm danh, hết hạn sau 30 ngày
- Giao diện web tích hợp tại `/ui`
- REST API đầy đủ, tài liệu Swagger tại `/docs`

---

## Cài đặt

### Yêu cầu

- Python 3.10+
- (Khuyến nghị) tạo virtualenv

### Các bước

```bash
# 1. Clone repo
git clone <repo-url>
cd face-attendance-api

# 2. Tạo và kích hoạt virtualenv
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Cài dependencies
pip install -r requirements.txt

# 4. Chạy server
uvicorn app.main:app --reload
```

Server chạy tại: `http://localhost:8000`

---

## Cấu hình

Tạo file `.env` ở thư mục gốc (tuỳ chọn, có giá trị mặc định):

```env
APP_NAME=face-attendance
DB_URL=sqlite:///./face_attendance.db
STORAGE_DIR=./storage
RETENTION_DAYS=30
```

---

## Giao diện Web

Truy cập **`http://localhost:8000/ui`** để sử dụng giao diện đồ hoạ gồm 2 tab:

| Tab                 | Chức năng                                             |
| ------------------- | ----------------------------------------------------- |
| 👤 Đăng ký khuôn mặt | Nhập thông tin sinh viên, upload ảnh hoặc chụp webcam |
| ✅ Điểm danh         | Chọn lớp, upload ảnh / chụp webcam, xem bảng kết quả  |

---

## API Endpoints

Base URL: `http://localhost:8000`

### Health Check

```
GET /
```
Trả về trạng thái service.

---

### Đăng ký khuôn mặt

```
POST /enroll/
Content-Type: multipart/form-data
```

| Field          | Kiểu   | Mô tả                                      |
| -------------- | ------ | ------------------------------------------ |
| `class_id`     | string | Mã lớp học (VD: `10A1`)                    |
| `student_id`   | string | Mã sinh viên — phải là duy nhất            |
| `student_name` | string | Họ tên sinh viên                           |
| `images`       | file[] | Ảnh chân dung (1 hoặc nhiều, JPG/PNG/WEBP) |

**Response 200:**
```json
{
  "ok": true,
  "student_id": "HS001",
  "student_name": "Nguyễn Văn A",
  "images_used": 3,
  "embeddings_saved": 3
}
```

> **Tip:** Đăng ký từ 3–5 ảnh ở nhiều góc, ánh sáng khác nhau để tăng độ chính xác.

---

### Điểm danh

```
POST /attendance/
Content-Type: multipart/form-data
```

| Field       | Kiểu   | Mặc định | Mô tả                       |
| ----------- | ------ | -------- | --------------------------- |
| `class_id`  | string | —        | Mã lớp học                  |
| `images`    | file[] | —        | Ảnh chụp lớp (1 hoặc nhiều) |
| `threshold` | float  | `0.40`   | Ngưỡng cosine similarity    |

**Response 200:**
```json
{
  "class_id": "10A1",
  "count_total": 30,
  "count_present": 25,
  "present": [
    {"name": "Nguyễn Văn A", "score": 0.47}
  ],
  "absent": ["Trần Thị B"],
  "unknown_faces_count": 2,
  "threshold": 0.40,
  "session_id": "uuid-...",
  "debug": { ... }
}
```

> **Lưu ý ngưỡng (`threshold`):** Model ArcFace dùng cosine similarity — giá trị thực tế cùng 1 người thường chỉ đạt **0.30–0.50**.
>
> | Giá trị | Đặc điểm |
> |---------|----------|
> | `0.35` | Dễ nhận (ít bỏ sót, có thể nhận nhầm) |
> | `0.40` | ✅ Khuyến nghị — cân bằng tốt |
> | `0.45` | Chặt hơn, cần ảnh đăng ký chất lượng cao |
> | `≥ 0.55` | ⚠️ Quá chặt — webcam thường không đạt |

---

### Danh sách phiên điểm danh

```
GET /attendance/sessions?class_id=10A1
```

Trả về danh sách các phiên điểm danh của lớp, kèm ngày hết hạn (30 ngày).

---

### Chi tiết phiên điểm danh

```
GET /attendance/sessions/{session_id}
```

---

### Danh sách sinh viên trong lớp

```
GET /students?class_id=10A1
```

---

### Danh sách lớp học

```
GET /classes
```

---

## Cấu trúc thư mục

```
face-attendance-api/
├── app/
│   ├── main.py              # FastAPI app, mount static UI
│   ├── settings.py          # Cấu hình (pydantic-settings)
│   ├── deps.py              # Dependency injection (DB session)
│   ├── api/
│   │   ├── routes_enroll.py      # POST /enroll/
│   │   ├── routes_attendance.py  # POST /attendance/, GET /attendance/sessions
│   │   ├── routes_students.py    # GET /students
│   │   └── routes_classes.py     # GET /classes
│   ├── core/
│   │   ├── uniface_engine.py  # RetinaFace (detect) + ArcFace (embedding)
│   │   ├── matching.py        # Cosine similarity, best_match
│   │   ├── quality.py         # Lọc ảnh kém chất lượng
│   │   └── attendance_logic.py # Tổng hợp kết quả present/absent
│   ├── db/
│   │   ├── database.py        # SQLAlchemy engine + session
│   │   ├── models.py          # ORM models
│   │   └── crud.py            # Thao tác DB
│   ├── schemas/               # Pydantic schemas
│   ├── utils/
│   │   ├── image.py           # Decode ảnh upload → BGR
│   │   ├── files.py
│   │   └── time.py
│   └── jobs/                  # Scheduler dọn dẹp dữ liệu cũ
├── static/
│   └── index.html             # Giao diện web (/ui)
├── storage/                   # Ảnh đã upload
│   ├── enroll/
│   └── attendance/
├── tests/
│   ├── test_api.py
│   └── test_matching.py
├── endpoints.json             # Postman collection
├── requirements.txt
└── .env                       # Cấu hình local (tự tạo)
```

---

## Công nghệ sử dụng

| Thành phần       | Thư viện                            |
| ---------------- | ----------------------------------- |
| Web framework    | FastAPI                             |
| ASGI server      | Uvicorn                             |
| Face detection   | RetinaFace (via `uniface`)          |
| Face recognition | ArcFace (via `uniface`)             |
| Database         | SQLite + SQLAlchemy                 |
| Validation       | Pydantic v2                         |
| Image processing | OpenCV                              |
| Frontend         | HTML/CSS/JS thuần (không cần build) |

---

## Tài liệu API tương tác

Sau khi khởi động server, truy cập:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **Postman Collection:** import file `endpoints.json`
