from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import mysql.connector
from mysql.connector import pooling, Error
from flask_cors import CORS
from datetime import datetime, timedelta
import pytz
import os
import qrcode
import uuid
import io
import secrets
from openpyxl import Workbook

# ========================================
# TIMEZONE CONFIGURATION - WIB
# ========================================
WIB = pytz.timezone('Asia/Jakarta')

def get_current_time_wib():
    """Fungsi untuk mendapatkan waktu sekarang dalam timezone WIB"""
    return datetime.now(WIB)

# ========================================
# DATABASE CONFIGURATION & FUNCTIONS
# ========================================

DB_CONFIG = {
    'host': 'absesgo.mysql.pythonanywhere-services.com',
    'user': 'absesgo',
    'password': 'passwordapa',
    'database': 'absesgo$absensi_qr'
}

def connect_db():
    """Fungsi untuk membuat koneksi database"""
    return mysql.connector.connect(**DB_CONFIG)

def get_db_connection():
    """Fungsi alternatif untuk koneksi database (untuk API CRUD)"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# ========================================
# DATABASE FUNCTIONS - GURU
# ========================================

def get_guru_by_username(username):
    """Ambil data guru berdasarkan username"""
    conn = connect_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM guru WHERE username=%s LIMIT 1", (username,))
    r = cur.fetchone()
    cur.close()
    conn.close()
    return r

# ========================================
# DATABASE FUNCTIONS - SISWA
# ========================================

def get_siswa_by_username(username):
    """Ambil data siswa berdasarkan username"""
    conn = connect_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM siswa WHERE username=%s LIMIT 1", (username,))
    r = cur.fetchone()
    cur.close()
    conn.close()
    return r

def get_siswa_by_id(id_siswa):
    """Ambil data siswa berdasarkan ID"""
    conn = connect_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM siswa WHERE id_siswa=%s LIMIT 1", (id_siswa,))
    r = cur.fetchone()
    cur.close()
    conn.close()
    return r

# ========================================
# DATABASE FUNCTIONS - QR TOKEN
# ========================================

def insert_qr_token(token, expires_dt):
    """Insert token QR baru ke database"""
    conn = connect_db()
    cur = conn.cursor()
    waktu_buat_wib = get_current_time_wib()
    cur.execute(
        "INSERT INTO qr_token (token, waktu_buat, waktu_expired, status) VALUES (%s, %s, %s, 'aktif')",
        (token, waktu_buat_wib, expires_dt)
    )
    conn.commit()
    cur.close()
    conn.close()

def verify_token(token):
    """Verifikasi token QR, mengembalikan baris token jika aktif"""
    conn = connect_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM qr_token WHERE token=%s AND status='aktif' LIMIT 1", (token,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def expire_token(token):
    """Expire token QR"""
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("UPDATE qr_token SET status='expired' WHERE token=%s", (token,))
    conn.commit()
    cur.close()
    conn.close()

# ========================================
# DATABASE FUNCTIONS - ABSENSI
# ========================================

def insert_absen_by_id(id_siswa, token_qr):
    """Insert data absensi siswa"""
    conn = connect_db()
    cur = conn.cursor(dictionary=True)

    # Cek duplikat absensi hari ini
    cur.execute("SELECT id_absen FROM absensi WHERE id_siswa=%s AND DATE(waktu_absen)=CURDATE()", (id_siswa,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return False

    # Ambil data siswa (nama, jurusan, kelas)
    cur.execute("SELECT nama_siswa, jurusan, kelas FROM siswa WHERE id_siswa=%s", (id_siswa,))
    siswa = cur.fetchone()
    if not siswa:
        cur.close()
        conn.close()
        return False

    # ✅ GUNAKAN WAKTU WIB
    waktu_absen_wib = get_current_time_wib()
    
    # Insert data absensi
    cur.execute("""
        INSERT INTO absensi (id_siswa, waktu_absen, token_qr, status, nama_siswa, jurusan, kelas)
        VALUES (%s, %s, %s, 'hadir', %s, %s, %s)
    """, (id_siswa, waktu_absen_wib, token_qr, siswa['nama_siswa'], siswa['jurusan'], siswa['kelas']))

    conn.commit()
    cur.close()
    conn.close()
    return True

def get_absensi_by_id_siswa(id_siswa):
    """Ambil riwayat absensi berdasarkan ID siswa"""
    conn = connect_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT a.*, s.nama_siswa, s.nis
        FROM absensi a
        JOIN siswa s ON a.id_siswa = s.id_siswa
        WHERE a.id_siswa=%s
        ORDER BY a.waktu_absen DESC
    """, (id_siswa,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_all_absensi():
    """Ambil semua data absensi"""
    conn = connect_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT a.*, s.nama_siswa, s.nis
        FROM absensi a
        JOIN siswa s ON a.id_siswa = s.id_siswa
        ORDER BY a.waktu_absen DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# ========================================
# FLASK APPLICATION
# ========================================

app = Flask(__name__)
CORS(app)

app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SECRET_KEY'] = 'random_secret_key'

# Konfigurasi folder untuk menyimpan QR codes (gunakan path absolut)
OUT_DIR = os.path.join(app.root_path, 'static', 'qrcodes')
os.makedirs(OUT_DIR, exist_ok=True)

# Token TTL (Time To Live) - 5 menit
TOKEN_TTL_SECONDS = 300

# ========================================
# LAZY IMPORTS (Import saat dibutuhkan)
# ========================================

def lazy_import_qrcode():
    """Import qrcode hanya saat dibutuhkan"""
    try:
        import qrcode
        return qrcode
    except ImportError:
        print("⚠️ qrcode module not installed")
        return None

def lazy_import_openpyxl():
    """Import openpyxl hanya saat dibutuhkan"""
    try:
        from openpyxl import Workbook
        return Workbook
    except ImportError:
        print("⚠️ openpyxl module not installed")
        return None

# ========================================
# ROUTES - HALAMAN UTAMA
# ========================================

@app.route('/')
def index():
    """Halaman login utama"""
    role = request.args.get('role', 'guru')
    return render_template('index.html', role=role)

# ========================================
# ROUTES - GURU
# ========================================

@app.route('/login_guru', methods=['POST'])
def login_guru():
    username = request.form.get('username')
    password = request.form.get('password')
    guru = get_guru_by_username(username)

    if not guru or guru['password'] != password:
        return "Login gagal: username/password salah", 401

    session.clear()
    session['guru'] = guru['username']
    session['nama_guru'] = guru['nama_guru']
    session['role'] = 'guru'
    return redirect(url_for('guru_dashboard'))

@app.route('/guru')
def guru_dashboard():
    """Dashboard guru"""
    if 'guru' not in session:
        return redirect(url_for('index'))

    absensi = get_all_absensi()
    return render_template('guru.html', nama=session.get('nama_guru'), absensi=absensi)

@app.route('/generate_token', methods=['POST'])
def generate_token():
    try:
        if 'role' not in session or session['role'] != 'guru':
            return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

        token = secrets.token_urlsafe(32)
        
        # ✅ GUNAKAN WAKTU WIB
        waktu_sekarang_wib = get_current_time_wib()
        expires_at = waktu_sekarang_wib + timedelta(seconds=TOKEN_TTL_SECONDS)

        # Insert token ke database
        insert_qr_token(token, expires_at)

        # Lazy import qrcode
        qrcode_module = lazy_import_qrcode()
        if not qrcode_module:
            return jsonify({'status': 'error', 'message': 'QR code module not available'}), 500

        # Generate QR Code
        qr = qrcode_module.QRCode(
            version=1,
            error_correction=qrcode_module.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(token)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Simpan file ke static/qrcodes (absolute path)
        timestamp = waktu_sekarang_wib.strftime('%Y%m%d_%H%M%S')
        filename = f"token_{timestamp}.png"
        filepath = os.path.join(OUT_DIR, filename)

        os.makedirs(OUT_DIR, exist_ok=True)
        img.save(filepath)

        print("[DEBUG] Saved QR file:", filepath)
        print("[DEBUG] Exists?", os.path.exists(filepath), "Readable?", os.access(filepath, os.R_OK))

        qr_url = url_for('static', filename=f'qrcodes/{filename}')

        return jsonify({
            'status': 'success',
            'token': token,
            'qr_url': qr_url,
            'expires_in': TOKEN_TTL_SECONDS
        })

    except Exception as e:
        import traceback
        print("=" * 80)
        print("ERROR in /generate_token:")
        print(traceback.format_exc())
        print("=" * 80)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/qrcodes/<filename>')
def serve_qr(filename):
    filepath = os.path.join(OUT_DIR, filename)

    # Cek apakah file ada
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        return "QR Code not found", 404

    # Cek apakah bisa dibaca
    if not os.access(filepath, os.R_OK):
        print(f"[ERROR] Permission denied: {filepath}")
        return "Access denied", 403

    try:
        return send_file(filepath, mimetype='image/png')
    except Exception as e:
        print(f"[ERROR] Failed to serve QR: {e}")
        return "Internal Server Error", 500

# ========================================
# ROUTES - SISWA
# ========================================

@app.route('/login_siswa', methods=['POST'])
def login_siswa():
    """Proses login siswa"""
    username = request.form.get('username')
    password = request.form.get('password')
    siswa = get_siswa_by_username(username)

    if not siswa or siswa['password'] != password:
        return "Login gagal: username/password salah", 401

    session.clear()
    session['id_siswa'] = siswa['id_siswa']
    session['username'] = siswa['username']
    session['nama_siswa'] = siswa['nama_siswa']
    return redirect(url_for('siswa_dashboard'))

@app.route('/siswa')
def siswa_dashboard():
    """Dashboard siswa"""
    if 'id_siswa' not in session:
        return redirect(url_for('index'))

    id_s = session['id_siswa']
    history = get_absensi_by_id_siswa(id_s)
    return render_template('siswa.html', nama=session.get('nama_siswa'), history=history)

@app.route('/scan_token', methods=['POST'])
def scan_token():
    """Proses scan token QR untuk absensi"""
    if 'id_siswa' not in session:
        return jsonify({'status': 'error', 'message': 'Siswa belum login'}), 401

    data = request.get_json() or {}
    token = data.get('token')

    if not token:
        return jsonify({'status': 'error', 'message': 'Token kosong'}), 400

    # Verifikasi token
    row = verify_token(token)
    if not row:
        return jsonify({'status': 'error', 'message': 'Token tidak valid atau sudah expired'}), 400

    # ✅ CEK WAKTU KADALUARSA DENGAN WIB
    waktu_sekarang_wib = get_current_time_wib()
    
    # Konversi waktu_expired dari database ke WIB jika belum
    waktu_expired = row['waktu_expired']
    if waktu_expired.tzinfo is None:
        waktu_expired = WIB.localize(waktu_expired)
    
    if waktu_sekarang_wib > waktu_expired:
        return jsonify({'status': 'error', 'message': 'Token sudah kadaluarsa'}), 400

    # Insert absensi
    success = insert_absen_by_id(session['id_siswa'], token)
    if success:
        return jsonify({'status': 'success', 'message': 'Absensi berhasil tercatat'})
    else:
        return jsonify({'status': 'warning', 'message': 'Anda sudah absen hari ini'})


# ========================================
# API - ABSENSI
# ========================================
@app.route('/api/absensi', methods=['GET'])
def api_get_absensi():
    """API data absensi"""
    try:
        data = get_all_absensi()

        for row in data:
            if isinstance(row.get('waktu_absen'), datetime):
                row['waktu_absen'] = row['waktu_absen'].strftime('%Y-%m-%d %H:%M:%S')

        return jsonify({'success': True, 'data': data}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ========================================
# EXPORT EXCEL
# ========================================

@app.route('/export_absensi', methods=['GET'])
def export_absensi():
    """Export riwayat absensi ke file Excel (.xlsx) """
    if 'guru' not in session:
        return redirect(url_for('index'))

    # Ambil parameter filter
    kelas = request.args.get('kelas', '')
    jurusan = request.args.get('jurusan', '')
    bulan = request.args.get('bulan', '')

    conn = connect_db()
    cur = conn.cursor(dictionary=True)

    # Query yang sama dengan API filter
    query = """
        SELECT a.*, s.nis, s.nama_siswa, s.kelas, s.jurusan
        FROM absensi a
        JOIN siswa s ON a.id_siswa = s.id_siswa
        WHERE 1=1
    """
    params = []

    query += " ORDER BY a.waktu_absen DESC"

    cur.execute(query, params)
    absensi_list = cur.fetchall()
    cur.close()
    conn.close()

    # Buat workbook Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Riwayat Absensi"

    headers = ['ID Absen', 'NIS', 'Nama Siswa', 'Kelas', 'Jurusan', 'Waktu Absen', 'Status']
    ws.append(headers)

    for item in absensi_list:
        # Format waktu
        waktu_absen = item.get('waktu_absen')
        if isinstance(waktu_absen, datetime):
            waktu_absen = waktu_absen.strftime('%Y-%m-%d %H:%M:%S')
        else:
            waktu_absen = str(waktu_absen)

        ws.append([
            item.get('id_absen', ''),
            item.get('nis', ''),
            item.get('nama_siswa', ''),
            item.get('kelas', ''),
            item.get('jurusan', ''),
            waktu_absen,
            item.get('status', 'hadir')
        ])

    # Auto-adjust column width
    for column_cells in ws.columns:
        length = max(len(str(cell.value)) for cell in column_cells)
        ws.column_dimensions[column_cells[0].column_letter].width = min(length + 2, 50)

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)

    # ✅ GUNAKAN WAKTU WIB UNTUK FILENAME
    filename = f"absensi{get_current_time_wib().strftime('%Y%m%d%H%M%S')}.xlsx"

    return send_file(
        bio,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
# ========================================
# API CRUD - SISWA
# ========================================

@app.route('/api/siswa', methods=['GET'])
def api_get_siswa():
    """API GET - Ambil semua data siswa"""
    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({
                'success': False,
                'message': 'Koneksi database gagal'
            }), 500

        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM siswa ORDER BY id_siswa ASC")
        data = cursor.fetchall()

        cursor.close()
        connection.close()

        return jsonify({
            'success': True,
            'data': data
        }), 200

    except Error as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/siswa', methods=['POST'])
def api_add_siswa():
    """API POST - Tambah siswa baru"""
    try:
        data = request.get_json()

        username = data.get('username', '')
        password = data.get('password', '')
        nis = data.get('nis', '')
        nama_siswa = data.get('nama_siswa', '')
        jurusan = data.get('jurusan', '')
        kelas = data.get('kelas', '')

        # Validasi data
        if not username or not password or not nis or not nama_siswa:
            return jsonify({
                'success': False,
                'message': 'Data tidak lengkap. Username, password, NIS, dan nama siswa wajib diisi.'
            }), 400

        connection = get_db_connection()
        if connection is None:
            return jsonify({
                'success': False,
                'message': 'Koneksi database gagal'
            }), 500

        cursor = connection.cursor()
        query = """
            INSERT INTO siswa (username, password, nis, nama_siswa, jurusan, kelas)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = (username, password, nis, nama_siswa, jurusan, kelas)

        cursor.execute(query, values)
        connection.commit()

        last_id = cursor.lastrowid

        cursor.close()
        connection.close()

        return jsonify({
            'success': True,
            'message': 'Siswa berhasil ditambahkan',
            'id': last_id
        }), 201

    except Error as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/siswa/<int:id_siswa>', methods=['GET'])
def api_get_siswa_by_id(id_siswa):
    """API GET - Ambil satu data siswa berdasarkan ID"""
    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({
                'success': False,
                'message': 'Koneksi database gagal'
            }), 500

        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM siswa WHERE id_siswa=%s", (id_siswa,))
        data = cursor.fetchone()

        cursor.close()
        connection.close()

        if data is None:
            return jsonify({
                'success': False,
                'message': 'Siswa tidak ditemukan'
            }), 404

        return jsonify({
            'success': True,
            'data': data
        }), 200

    except Error as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/siswa/<int:id_siswa>', methods=['PUT'])
def api_update_siswa(id_siswa):
    """API PUT - Update data siswa"""
    try:
        data = request.get_json()

        username = data.get('username', '')
        password = data.get('password', '')
        nis = data.get('nis', '')
        nama_siswa = data.get('nama_siswa', '')
        jurusan = data.get('jurusan', '')
        kelas = data.get('kelas', '')

        # Validasi data
        if not username or not password or not nis or not nama_siswa:
            return jsonify({
                'success': False,
                'message': 'Data tidak lengkap. Username, password, NIS, dan nama siswa wajib diisi.'
            }), 400

        connection = get_db_connection()
        if connection is None:
            return jsonify({
                'success': False,
                'message': 'Koneksi database gagal'
            }), 500

        cursor = connection.cursor()
        query = """
            UPDATE siswa
            SET username=%s, password=%s, nis=%s, nama_siswa=%s, jurusan=%s, kelas=%s
            WHERE id_siswa=%s
        """
        values = (username, password, nis, nama_siswa, jurusan, kelas, id_siswa)

        cursor.execute(query, values)
        connection.commit()

        if cursor.rowcount == 0:
            cursor.close()
            connection.close()
            return jsonify({
                'success': False,
                'message': 'Siswa tidak ditemukan'
            }), 404

        cursor.close()
        connection.close()

        return jsonify({
            'success': True,
            'message': 'Data siswa berhasil diupdate'
        }), 200

    except Error as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/siswa/<int:id_siswa>', methods=['DELETE'])
def api_delete_siswa(id_siswa):
    """API DELETE - Hapus siswa"""
    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({
                'success': False,
                'message': 'Koneksi database gagal'
            }), 500

        cursor = connection.cursor()
        query = "DELETE FROM siswa WHERE id_siswa=%s"

        cursor.execute(query, (id_siswa,))
        connection.commit()

        if cursor.rowcount == 0:
            cursor.close()
            connection.close()
            return jsonify({
                'success': False,
                'message': 'Siswa tidak ditemukan'
            }), 404

        cursor.close()
        connection.close()

        return jsonify({
            'success': True,
            'message': 'Siswa berhasil dihapus'
        }), 200

    except Error as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

# ========================================
# LOGOUT
# ========================================

@app.route('/logout')
def logout():
    """Logout dan clear session"""
    session.clear()
    return redirect(url_for('index'))

# ========================================
# RUN APPLICATION
# ========================================

if __name__ == '__main__':
    # Jalankan aplikasi tanpa SSL, di semua interface
    # Akses dari perangkat lain di LAN: http://[IP_ADDRESS]:5000
    app.run(host='0.0.0.0', port=5000, debug=True)
