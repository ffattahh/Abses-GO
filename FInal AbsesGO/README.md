# 📘 AbsesGO - Sistem Absensi QR Code Berbasis Flask

AbsesGO adalah sistem absensi berbasis **Flask** yang menggunakan **QR Code** untuk mencatat kehadiran guru dan siswa.  
Guru dapat melakukan generate token QR untuk periode waktu tertentu, sedangkan siswa melakukan scan QR untuk mencatat kehadiran otomatis.  
Sistem ini terhubung dengan **database MySQL** dan menggunakan antarmuka modern bertema biru–cyan (`#3484FF` dan `#58D2FF`).

---

## 🚀 Fitur Utama

### 👩‍🏫 Dashboard Guru
- Generate QR Token dengan durasi 5 menit
- Menampilkan QR Code aktif
- Melihat riwayat absensi siswa

### 👨‍🎓 Dashboard Siswa
- Scan QR Code dari guru menggunakan kamera
- Pencatatan kehadiran otomatis ke database
- Melihat riwayat absensi pribadi

---

## 🛠️ Persiapan Sebelum Menjalankan

### 1️⃣ Clone Repository
```bash
git clone https://github.com/ffattahh/final-project.git
cd final-project

python -m venv venv
venv\Scripts\activate

pip install flask mysql-connector-python qrcode

python app.py
```

## Requirements
- Flask==3.0.3
- mysql-connector-python==9.0.0
- qrcode==7.4.2
- Pillow==10.4.0
- Werkzeug==3.0.3
- itsdangerous==2.2.0
- Jinja2==3.1.4
- MarkupSafe==2.1.5

