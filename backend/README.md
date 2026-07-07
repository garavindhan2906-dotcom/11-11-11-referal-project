# 11:11:11 Reseller Platform — Backend API

FastAPI + MySQL backend for the 11:11:11 Manifestation Perfume Reseller Platform by EVOXU PVT LTD.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 |
| Database | MySQL |
| Auth | JWT (python-jose) |
| Passwords | Bcrypt (passlib) |
| QR Codes | qrcode + Pillow |
| Server | Uvicorn |

---

## Project Structure

```
backend/
├── app/
│   ├── config.py              # Settings from .env
│   ├── database/
│   │   └── connection.py      # Engine, SessionLocal, Base, get_db
│   ├── models/
│   │   ├── retailer.py
│   │   ├── customer.py
│   │   ├── order.py
│   │   ├── scan.py
│   │   ├── whatsapp_click.py
│   │   └── payout.py
│   ├── schemas/
│   │   ├── retailer.py
│   │   ├── order.py
│   │   ├── scan.py
│   │   └── payout.py
│   ├── auth/
│   │   ├── jwt_handler.py     # create_access_token, verify_token
│   │   └── dependencies.py    # get_current_retailer
│   ├── services/
│   │   ├── qr_service.py      # QR code generation
│   │   ├── whatsapp_service.py
│   │   └── commission_service.py
│   ├── utils/
│   │   └── helpers.py         # Code generators
│   └── routes/
│       ├── auth.py
│       ├── retailer.py
│       ├── orders.py
│       ├── tracking.py
│       └── admin.py
├── uploads/
│   └── qrcodes/               # Generated QR PNG files
├── main.py
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup Instructions

### Step 1 — Prerequisites

Make sure you have installed:
- Python 3.12: https://python.org
- MySQL 8.0+: https://dev.mysql.com/downloads/

### Step 2 — Create MySQL Database

Open MySQL and run:

```sql
CREATE DATABASE evoxu_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Step 3 — Clone / Navigate to Backend Folder

```bash
cd "e:\Bhupan Format\backend"
```

### Step 4 — Create Virtual Environment

```bash
python -m venv venv
```

Activate it:

Windows:
```bash
venv\Scripts\activate
```

Mac/Linux:
```bash
source venv/bin/activate
```

### Step 5 — Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 6 — Configure Environment

```bash
copy .env.example .env
```

Edit `.env`:

```env
DATABASE_URL=mysql+pymysql://root:yourpassword@localhost:3306/evoxu_db
SECRET_KEY=generate-a-long-random-string-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
BASE_URL=https://11-11-11.shop
ADMIN_SECRET_KEY=your-admin-secret-key
```

Generate a secure SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Step 7 — Run the Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API is now running at: http://localhost:8000

Interactive docs: http://localhost:8000/docs

---

## API Reference

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Register new retailer |
| POST | `/api/auth/login` | Login + get JWT token |
| POST | `/api/auth/logout` | Logout (client-side) |

**Register body:**
```json
{
  "shop_name": "Priya Wellness Store",
  "owner_name": "Priya Sharma",
  "email": "priya@example.com",
  "phone": "9999999999",
  "password": "securepass123"
}
```

**Login body:**
```json
{
  "email": "priya@example.com",
  "password": "securepass123"
}
```

---

### Retailer (requires Bearer token)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/dashboard` | Dashboard stats |
| GET | `/api/retailer/profile` | Retailer profile |
| GET | `/api/retailer/qr` | QR code + referral link |
| GET | `/api/retailer/whatsapp-link` | WhatsApp share URL |

**Authorization header:**
```
Authorization: Bearer <your_token>
```

**Dashboard response:**
```json
{
  "total_scans": 120,
  "qr_scans": 80,
  "whatsapp_clicks": 55,
  "total_orders": 15,
  "total_sales": 45000.0,
  "total_commission": 4500.0
}
```

---

### Orders

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/api/orders` | Place order (public) | None |
| GET | `/api/orders` | My orders | Bearer |
| GET | `/api/commissions` | Commission history | Bearer |

**Place order body:**
```json
{
  "customer_name": "John Doe",
  "customer_email": "john@example.com",
  "customer_phone": "9888888888",
  "referral_code": "PS001",
  "order_amount": 2500
}
```

---

### Tracking (public)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/track-scan` | Track QR / link scan |
| POST | `/api/track-whatsapp-click` | Track WhatsApp click |

**Track scan body:**
```json
{
  "referral_code": "PS001",
  "source": "qr",
  "visitor_id": "optional-uuid"
}
```
Source values: `qr` | `whatsapp` | `website`

---

### Payouts (requires Bearer token)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/payout-request` | Request payout |
| GET | `/api/payouts` | My payout history |

**Request payout body:**
```json
{ "amount": 1000.0 }
```

---

### Admin (requires X-Admin-Key header)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/admin/dashboard` | Platform overview |
| GET | `/api/admin/retailers` | All retailers |
| GET | `/api/admin/orders` | All orders |
| GET | `/api/admin/payouts` | All payout requests |
| PUT | `/api/admin/retailers/{id}/toggle` | Activate/deactivate retailer |
| PUT | `/api/admin/retailers/{id}/commission` | Update commission % |
| PUT | `/api/admin/orders/{order_number}/status` | Update order status |
| PUT | `/api/admin/payouts/{id}/approve` | Approve payout |
| PUT | `/api/admin/payouts/{id}/mark-paid` | Mark payout as paid |

**Admin header:**
```
X-Admin-Key: your-admin-secret-key
```

---

## Business Logic

### Retailer Code Generation

Owner name "Priya Sharma", sequence 1 → `PS001`
Owner name "Ravi Kumar", sequence 2 → `RK002`

### Commission Calculation

```
commission = (order_amount × commission_percentage) / 100
```

Default commission: 10%
Example: ₹2,500 order → ₹250 commission

### QR Code

Generated automatically on registration.
Saved at: `uploads/qrcodes/PS001.png`
Served at: `http://localhost:8000/uploads/qrcodes/PS001.png`

---

## Connecting to the Frontend

In your HTML login page, update the API base URL:

```javascript
const API_BASE = "http://localhost:8000";

// Login
const res = await fetch(`${API_BASE}/api/auth/login`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email, password })
});
const data = await res.json();
localStorage.setItem("token", data.access_token);

// Dashboard
const dash = await fetch(`${API_BASE}/api/dashboard`, {
  headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
});
```

---

## Common Issues

**MySQL connection refused**
Make sure MySQL is running and the credentials in `.env` are correct.

**ModuleNotFoundError**
Make sure your virtual environment is activated before running.

**QR image not found**
The `uploads/qrcodes/` directory is created automatically on startup.

**401 Unauthorized**
Token expired or missing. Log in again to get a new token.
