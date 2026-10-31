# Tanilink 🌾

Marketplace yang menghubungkan **petani langsung dengan pembeli** di Indonesia — tanpa perantara berlebih.

## Tech Stack
- **Backend**: Python 3.11+, FastAPI
- **Database**: PostgreSQL (SQLAlchemy 2.0 + Alembic)
- **Auth**: JWT (access + refresh token, revokable), bcrypt
- **Validasi**: Pydantic v2
- **Frontend (MVP)**: HTML/CSS/JS statis

---

## Cara Menjalankan

### 1. Prasyarat
- Python 3.11+
- PostgreSQL 14+ berjalan lokal

### 2. Clone & setup environment

```bash
git clone <repo-url>
cd tanilink
```

**Windows (PowerShell):**
```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

**Linux / Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Konfigurasi environment

```powershell
# Windows
copy .env.example .env
# Edit .env: isi DATABASE_URL dan SECRET_KEY
```

Generate `SECRET_KEY` yang aman:
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Buat database & jalankan migrasi

```powershell
# Buat database di PostgreSQL terlebih dahulu (via psql atau pgAdmin)
# createdb tanilink_db

# Jalankan migrasi Alembic
python -m alembic upgrade head
```

### 5. Jalankan server

```powershell
uvicorn app.main:app --reload
```

API tersedia di: http://localhost:8000  
Dokumentasi interaktif: http://localhost:8000/docs

---

## Struktur Folder

```
tanilink/
├── app/
│   ├── main.py              # Entry point FastAPI
│   ├── core/
│   │   ├── config.py        # Settings dari .env
│   │   ├── security.py      # JWT + bcrypt
│   │   └── dependencies.py  # get_db(), get_current_user()
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic v2 schemas
│   ├── routers/             # FastAPI routers (endpoint)
│   ├── services/            # Logika bisnis
│   └── db/
│       └── session.py       # Engine & SessionLocal
├── migrations/              # Alembic migrations
├── tests/                   # pytest
├── static/                  # Frontend HTML/CSS/JS
├── uploads/                 # File foto produk (lokal)
├── .env.example
├── requirements.txt
└── README.md
```

---

## Menjalankan Test

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## Endpoint Utama

| Method | Path | Deskripsi |
|--------|------|-----------|
| POST | `/auth/register` | Registrasi user baru |
| POST | `/auth/login` | Login, dapat access + refresh token |
| POST | `/auth/refresh` | Tukar refresh token dengan access token baru |
| POST | `/auth/logout` | Revoke refresh token |
| GET | `/products` | Daftar produk (filter: kategori, lokasi, harga) |
| POST | `/products` | Tambah produk (petani) |
| PUT | `/products/{id}` | Update produk (petani pemilik) |
| DELETE | `/products/{id}` | Hapus produk (petani pemilik) |
| GET | `/users/{id}/products` | Profil petani + produknya |
| POST | `/cart/items` | Tambah item ke keranjang |
| GET | `/cart` | Lihat keranjang |
| POST | `/orders` | Buat pesanan dari keranjang |
| GET | `/orders` | Riwayat pesanan |

---

## Konvensi Respons API

Semua respons mengikuti struktur konsisten:

```json
{
  "success": true,
  "data": { ... },
  "message": "OK"
}
```

Error:
```json
{
  "success": false,
  "data": null,
  "message": "Pesan error yang jelas"
}
```
