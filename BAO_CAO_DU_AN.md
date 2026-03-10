# BÁO CÁO DỰ ÁN: HỆ THỐNG ĐIỂM DANH BẰNG KHUÔN MẶT

## 1. Tổng quan hệ thống
chay du an python -m uvicorn app.main:app --reload

### 1.1 Mục tiêu
Xây dựng hệ thống điểm danh tự động bằng nhận dạng khuôn mặt, cho phép:
- Đăng ký khuôn mặt sinh viên vào hệ thống (Enroll)
- Điểm danh tự động bằng cách chụp ảnh lớp học (Attendance)
- Quản lý lớp, sinh viên, và lịch sử điểm danh

### 1.2 Công nghệ sử dụng

| Thành phần           | Công nghệ               | Mô tả                                                        |
| -------------------- | ----------------------- | ------------------------------------------------------------ |
| Backend API          | **FastAPI** (Python)    | REST API xử lý đăng ký và điểm danh                          |
| Phát hiện khuôn mặt  | **RetinaFace**          | Deep learning model, phát hiện nhiều khuôn mặt trong 1 ảnh   |
| Trích xuất đặc trưng | **ArcFace**             | Deep learning model, chuyển khuôn mặt thành vector 512 chiều |
| Cơ sở dữ liệu        | **SQLite + SQLAlchemy** | Lưu trữ thông tin sinh viên, embedding, phiên điểm danh      |
| Xử lý ảnh            | **OpenCV**              | Decode ảnh, đánh giá chất lượng                              |
| Thư viện             | **uniface**             | Wrapper cho RetinaFace + ArcFace                             |

### 1.3 Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────┐
│                    FastAPI Server                    │
├──────────────┬──────────────┬───────────────────────┤
│  /enroll     │  /attendance │  /students, /classes  │
│  (Đăng ký)   │  (Điểm danh) │  (Quản lý)           │
├──────────────┴──────────────┴───────────────────────┤
│                   Core Engine                        │
│  ┌────────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │ RetinaFace │ │ ArcFace  │ │ Quality Gate      │  │
│  │ (Detect)   │ │(Embedding│ │ (Lọc chất lượng)  │  │
│  └────────────┘ └──────────┘ └───────────────────┘  │
├─────────────────────────────────────────────────────┤
│              SQLite Database                         │
│  classes | students | embeddings | sessions          │
└─────────────────────────────────────────────────────┘
```

---

## 2. CHỨC NĂNG ĐĂNG KÝ (Enroll)

### 2.1 Mô tả
Sinh viên đăng ký khuôn mặt bằng cách upload 1 hoặc nhiều ảnh chân dung. Hệ thống trích xuất đặc trưng khuôn mặt (embedding) và lưu vào cơ sở dữ liệu.

### 2.2 API Endpoint

```
POST /enroll/
Content-Type: multipart/form-data

Tham số:
  - class_id     (string, bắt buộc): Mã lớp (VD: "10A1")
  - student_id   (string, bắt buộc): Mã sinh viên (VD: "HS001")
  - student_name (string, bắt buộc): Tên sinh viên
  - images       (file[], bắt buộc): 1 hoặc nhiều ảnh chân dung
```

### 2.3 Quy trình xử lý (Pipeline)

```
Ảnh upload
    │
    ▼
[1] Decode ảnh (bytes → BGR numpy array)
    │
    ▼
[2] RetinaFace detect khuôn mặt
    │  → Trả về: bbox, confidence, landmarks (5 điểm mốc)
    │  → Nếu nhiều mặt: chọn mặt có confidence cao nhất
    │
    ▼
[3] ArcFace trích xuất embedding
    │  → Input: ảnh gốc + 5 landmarks
    │  → Output: vector 512 chiều (float32)
    │  → Embedding được normalize (||v|| = 1)
    │
    ▼
[4] Lưu vào Database
    │  → Bảng students: id, name, class_id
    │  → Bảng student_embeddings: vector (binary), dim=512
    │
    ▼
[5] Trả kết quả
    → {"ok": true, "embeddings_saved": 3}
```

### 2.4 Chi tiết kỹ thuật

**Tại sao lưu nhiều embedding cho 1 sinh viên?**
- Mỗi ảnh cho 1 embedding khác nhau (góc chụp, ánh sáng, biểu cảm)
- Khi điểm danh, so sánh với TẤT CẢ embedding → tăng tỷ lệ nhận đúng
- VD: Upload 3 ảnh → 3 embedding → điểm danh chỉ cần match 1 trong 3

**Normalize embedding:**
```python
emb = emb / (np.linalg.norm(emb) + 1e-9)
```
- Chia vector cho độ dài (L2 norm) để ||v|| = 1
- Sau khi normalize, cosine similarity = dot product (tính toán nhanh hơn)
- `+ 1e-9` là epsilon tránh chia cho 0

---

## 3. CHỨC NĂNG ĐIỂM DANH (Attendance)

### 3.1 Mô tả
Upload 1 hoặc nhiều ảnh chụp lớp học. Hệ thống phát hiện tất cả khuôn mặt, so sánh với gallery đã đăng ký, và trả về danh sách có mặt / vắng mặt.

### 3.2 API Endpoint

```
POST /attendance/
Content-Type: multipart/form-data

Tham số:
  - class_id  (string, bắt buộc): Mã lớp
  - images    (file[], bắt buộc): Ảnh chụp lớp học
  - threshold (float, mặc định 0.40): Ngưỡng nhận dạng
```

### 3.3 Quy trình xử lý (Pipeline)

```
Ảnh lớp học upload (có thể nhiều ảnh)
    │
    ▼
[1] Load Gallery
    │  → Lấy TẤT CẢ embedding của sinh viên trong lớp từ DB
    │  → Re-normalize mỗi vector để đảm bảo ||v|| = 1
    │  → VD: Lớp 30 sinh viên, mỗi người 3 ảnh → gallery 90 vectors
    │
    ▼
[2] Decode ảnh (bytes → BGR numpy array)
    │
    ▼
[3] RetinaFace detect TẤT CẢ khuôn mặt trong ảnh
    │  → VD: Ảnh chụp lớp → detect 25 khuôn mặt
    │
    ▼
[4] Quality Gate (Lọc chất lượng) — cho mỗi khuôn mặt
    │  ├─ Confidence ≥ 0.4? (model có chắc đây là mặt không?)
    │  ├─ Kích thước ≥ 20px? (mặt có đủ lớn không?)
    │  ├─ Blur score ≥ 3.0?  (mặt có quá mờ không?)
    │  └─ Có landmarks không? (cần 5 điểm mốc để tính embedding)
    │  → Nếu KHÔNG đạt → loại bỏ, ghi log lý do
    │  → Nếu ĐẠT → tiếp tục bước 5
    │
    ▼
[5] ArcFace trích xuất embedding cho mỗi khuôn mặt đạt chất lượng
    │  → Output: vector 512 chiều
    │
    ▼
[6] So sánh Cosine Similarity với Gallery
    │  → Tính similarity giữa face embedding và TẤT CẢ gallery vectors
    │  → Lấy gallery vector có similarity cao nhất
    │  → Nếu similarity ≥ threshold (0.40) → MATCHED (có mặt)
    │  → Nếu similarity < threshold → UNKNOWN (không nhận ra)
    │
    ▼
[7] Tổng hợp kết quả
    │  → present: danh sách sinh viên có mặt + score
    │  → absent: danh sách sinh viên vắng mặt
    │  → unknown_faces_count: số khuôn mặt không nhận ra
    │
    ▼
[8] Lưu phiên điểm danh vào DB + Trả kết quả
```

### 3.4 Chi tiết từng bước

#### Bước 4: Quality Gate — Lọc chất lượng khuôn mặt

Mục đích: Loại bỏ các khuôn mặt chất lượng kém trước khi tính embedding, tránh kết quả sai.

| Tiêu chí         | Ngưỡng                   | Ý nghĩa                                                       | Nếu không đạt                                      |
| ---------------- | ------------------------ | ------------------------------------------------------------- | -------------------------------------------------- |
| `min_conf = 0.4` | Confidence ≥ 40%         | Model RetinaFace tin rằng đây là mặt người với xác suất ≥ 40% | Có thể là vật thể khác bị nhận nhầm                |
| `min_face = 20`  | Kích thước ≥ 20px        | Khuôn mặt phải rộng và cao ≥ 20 pixel                         | Quá nhỏ → embedding không đủ chi tiết              |
| `min_blur = 3.0` | Laplacian variance ≥ 3.0 | Đo độ nét bằng Laplacian variance trên crop khuôn mặt         | Ảnh quá mờ (motion blur nặng) → embedding sai lệch |

**Về chỉ số Blur (Laplacian Variance):**

```python
def blur_score(bgr):
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()
```

- Laplacian tính đạo hàm bậc 2 → phát hiện cạnh (edge) trong ảnh
- Variance cao → nhiều cạnh rõ → ảnh NÉT
- Variance thấp → ít cạnh → ảnh MỜ

Giá trị thực tế trên crop khuôn mặt nhỏ (~100x100px):
```
Ảnh chân dung studio:    100 ~ 500
Ảnh webcam bình thường:  15 ~ 80
Ảnh phone hơi mờ:        5 ~ 15
Ảnh cực mờ (tay rung):   0.5 ~ 3
```

→ Ngưỡng `min_blur = 3.0` chỉ loại ảnh **cực kỳ mờ**, cho phép webcam/phone hoạt động bình thường. Lý do: **ArcFace đã được huấn luyện trên dữ liệu đa dạng**, nó vẫn trích xuất embedding khá chính xác từ ảnh hơi mờ. Việc lọc chất lượng quá khắt khe ở bước này không cần thiết vì đã có bước matching (cosine threshold) phía sau.

#### Bước 6: Cosine Similarity — So sánh khuôn mặt

**Công thức:**

$$\text{cosine\_similarity}(\vec{a}, \vec{b}) = \frac{\vec{a} \cdot \vec{b}}{||\vec{a}|| \times ||\vec{b}||}$$

Vì cả 2 vector đã được normalize (||v|| = 1), nên:

$$\text{cosine\_similarity} = \vec{a} \cdot \vec{b} = \sum_{i=1}^{512} a_i \times b_i$$

**Ý nghĩa giá trị:**

| Cosine Similarity | Ý nghĩa                                                 |
| ----------------- | ------------------------------------------------------- |
| 0.7 ~ 1.0         | Rất giống → chắc chắn cùng 1 người                      |
| 0.5 ~ 0.7         | Khá giống → có thể cùng người (khác ánh sáng, góc chụp) |
| 0.3 ~ 0.5         | Hơi giống → cần cân nhắc                                |
| 0.0 ~ 0.3         | Khác nhau → khác người                                  |

**Chọn ngưỡng threshold = 0.40:**

Trong điều kiện lý tưởng (cùng ánh sáng, cùng góc chụp), các paper khuyến nghị threshold 0.5-0.6. Tuy nhiên, trong thực tế hệ thống điểm danh:
- Ảnh đăng ký: chân dung chất lượng cao, ánh sáng tốt
- Ảnh điểm danh: webcam/điện thoại, ánh sáng phòng học không ổn định, có thể hơi mờ

Sự chênh lệch chất lượng ảnh giữa enroll và attendance làm cosine similarity giảm khoảng 0.1 – 0.2. Do đó threshold 0.40 trong thực tế tương đương 0.55 – 0.60 trong điều kiện test lý tưởng.

Threshold có thể tùy chỉnh qua tham số API:
- Lớp ít người (< 20): 0.35 – 0.40 (ưu tiên nhận đúng)
- Lớp nhiều người (> 30): 0.45 – 0.50 (ưu tiên tránh nhận nhầm)

#### Bước 7: Tổng hợp kết quả

```python
def update_present_best(present_best, matched, score):
    # Nếu 1 sinh viên match nhiều lần (nhiều ảnh), giữ score cao nhất
    prev = present_best.get(matched, 0.0)
    if score > prev:
        present_best[matched] = score
```

- Nếu 1 sinh viên xuất hiện trong nhiều ảnh → chỉ tính 1 lần, giữ điểm cao nhất
- `present` = tập hợp sinh viên đã match
- `absent` = `all_students - present`

---

## 4. CƠ SỞ DỮ LIỆU

### 4.1 Sơ đồ bảng (ERD)

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│   classes    │     │    students      │     │ student_embeddings  │
├──────────────┤     ├──────────────────┤     ├─────────────────────┤
│ id (PK)      │◄────│ class_id (FK)    │     │ id (PK, auto)       │
│ name         │     │ id (PK)          │◄────│ student_id (FK)     │
│ created_at   │     │ name             │     │ dim (512)           │
└──────────────┘     │ created_at       │     │ vector (BLOB)       │
                     └──────────────────┘     │ source              │
                                              │ created_at          │
                                              └─────────────────────┘

┌────────────────────────┐     ┌────────────────────┐
│  attendance_sessions   │     │ attendance_results │
├────────────────────────┤     ├────────────────────┤
│ id (PK, UUID)          │◄────│ session_id (FK)    │
│ class_id (FK)          │     │ student_id (FK)    │
│ created_at             │     │ status             │
│ threshold              │     │ best_score         │
│ images_count           │     │ created_at         │
│ unknown_faces_count    │     └────────────────────┘
│ note (JSON result)     │
└────────────────────────┘
```

### 4.2 Lưu trữ Embedding

- Embedding vector 512 chiều (float32) → 512 × 4 = **2048 bytes** / embedding
- Lưu dạng `BLOB` (binary) bằng `np.ndarray.tobytes()`
- Load về bằng `np.frombuffer(blob, dtype=np.float32)`
- Re-normalize sau khi load để đảm bảo ||v|| = 1

---

## 5. CÁC API KHÁC

### 5.1 Danh sách lớp
```
GET /classes/
→ Trả về: [{"class_id": "10A1", "name": "10A1", "created_at": "..."}]
```

### 5.2 Danh sách sinh viên trong lớp
```
GET /students/?class_id=10A1
→ Trả về: [{"student_id": "HS001", "name": "Nguyễn Văn A", ...}]
```

### 5.3 Lịch sử điểm danh
```
GET /attendance/sessions?class_id=10A1
→ Trả về danh sách phiên điểm danh: thời gian, số ảnh, threshold, ...

GET /attendance/sessions/{session_id}
→ Trả về chi tiết 1 phiên: danh sách present/absent, score, debug info
```

---

## 6. CẤU TRÚC THƯ MỤC DỰ ÁN

```
face-attendance-api/
├── app/
│   ├── main.py                  # Khởi tạo FastAPI, đăng ký router
│   ├── settings.py              # Cấu hình (DB URL, storage dir, ...)
│   ├── deps.py                  # Dependency injection (DB session)
│   │
│   ├── api/                     # REST API endpoints
│   │   ├── routes_enroll.py     # API đăng ký khuôn mặt
│   │   ├── routes_attendance.py # API điểm danh
│   │   ├── routes_students.py   # API quản lý sinh viên
│   │   └── routes_classes.py    # API quản lý lớp
│   │
│   ├── core/                    # Logic xử lý chính
│   │   ├── uniface_engine.py    # Wrapper RetinaFace + ArcFace
│   │   ├── quality.py           # Quality Gate (blur, confidence, size)
│   │   ├── matching.py          # Cosine similarity matching
│   │   └── attendance_logic.py  # Tổng hợp kết quả điểm danh
│   │
│   ├── db/                      # Database layer
│   │   ├── database.py          # SQLAlchemy engine + session
│   │   ├── models.py            # ORM models (classes, students, ...)
│   │   └── crud.py              # CRUD operations
│   │
│   ├── schemas/                 # Pydantic schemas (chưa dùng)
│   └── utils/                   # Tiện ích
│       └── image.py             # Decode ảnh upload → BGR
│
├── requirements.txt             # Danh sách thư viện
└── README.md
```

---

## 7. LUỒNG HOẠT ĐỘNG TỔNG THỂ

### 7.1 Luồng Đăng ký (Enroll)

```
Người dùng                        Server                         Database
    │                               │                               │
    │  POST /enroll/                │                               │
    │  (class_id, student_id,       │                               │
    │   student_name, images[])     │                               │
    │──────────────────────────────►│                               │
    │                               │  Decode ảnh                   │
    │                               │  RetinaFace detect            │
    │                               │  Chọn mặt confidence cao nhất │
    │                               │  ArcFace extract embedding    │
    │                               │  Normalize vector             │
    │                               │──────────────────────────────►│
    │                               │  INSERT class, student,       │
    │                               │  embedding (cho mỗi ảnh)      │
    │                               │◄──────────────────────────────│
    │  {"ok": true,                 │                               │
    │   "embeddings_saved": 3}      │                               │
    │◄──────────────────────────────│                               │
```

### 7.2 Luồng Điểm danh (Attendance)

```
Người dùng                        Server                         Database
    │                               │                               │
    │  POST /attendance/            │                               │
    │  (class_id, images[],         │                               │
    │   threshold=0.40)             │                               │
    │──────────────────────────────►│                               │
    │                               │──────────────────────────────►│
    │                               │  Load gallery embeddings      │
    │                               │  (all students in class)      │
    │                               │◄──────────────────────────────│
    │                               │                               │
    │                               │  Với mỗi ảnh:                 │
    │                               │    Decode ảnh                 │
    │                               │    RetinaFace detect ALL mặt  │
    │                               │    Với mỗi mặt:               │
    │                               │      Quality Gate check       │
    │                               │      ArcFace embedding        │
    │                               │      Cosine match vs gallery  │
    │                               │      → matched / unknown      │
    │                               │                               │
    │                               │  Tổng hợp present/absent      │
    │                               │──────────────────────────────►│
    │                               │  Lưu attendance_session       │
    │                               │◄──────────────────────────────│
    │  {"present": [...],           │                               │
    │   "absent": [...],            │                               │
    │   "unknown_faces_count": 2}   │                               │
    │◄──────────────────────────────│                               │
```

---

## 8. THỰC NGHIỆM VÀ ĐÁNH GIÁ

### 8.1 Bảng thực nghiệm chọn Threshold

*(Cần bổ sung số liệu thực tế khi test)*

| Threshold | Nhận đúng (TP) | Nhận nhầm (FP) | Bỏ sót (FN) | Nhận xét             |
| --------- | -------------- | -------------- | ----------- | -------------------- |
| 0.30      | ?/?            | ?              | ?           | Nhận nhầm nhiều      |
| 0.35      | ?/?            | ?              | ?           |                      |
| **0.40**  | ?/?            | ?              | ?           | **Giá trị mặc định** |
| 0.45      | ?/?            | ?              | ?           |                      |
| 0.50      | ?/?            | ?              | ?           |                      |
| 0.60      | ?/?            | ?              | ?           | Bỏ sót nhiều         |

### 8.2 Điều kiện test

- Số lượng sinh viên: ___
- Thiết bị chụp enroll: ___
- Thiết bị chụp attendance: ___
- Môi trường ánh sáng: ___

---

## 9. KẾT LUẬN

Hệ thống điểm danh bằng khuôn mặt sử dụng pipeline 2 giai đoạn:
1. **RetinaFace** phát hiện và định vị khuôn mặt trong ảnh
2. **ArcFace** trích xuất đặc trưng 512 chiều và so sánh cosine similarity

Hệ thống hoạt động với 3 lớp bảo vệ:
- **Quality Gate**: Loại ảnh chất lượng cực kém (mờ nặng, mặt quá nhỏ)
- **Cosine threshold**: Chỉ chấp nhận match khi similarity đủ cao
- **Admin tunable**: Threshold có thể tùy chỉnh qua API cho từng lớp/bối cảnh

Giá trị mặc định (threshold=0.40, min_blur=3.0) được chọn để cân bằng giữa **độ nhạy** (không bỏ sót sinh viên) và **độ chính xác** (không nhận nhầm), phù hợp với điều kiện thực tế phòng học (webcam, ánh sáng không ổn định).
