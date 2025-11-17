from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import mysql.connector
from mysql.connector import pooling, Error
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import qrcode
import uuid
import io
from openpyxl import Workbook

# ========================================
# DATABASE CONFIGURATION & FUNCTIONS
# ========================================

DB_CONFIG = {
    'host': 'http://absesgo.mysql.pythonanywhere-services.com',
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
    cur.execute(
        "INSERT INTO qr_token (token, waktu_buat, waktu_expired, status) VALUES (%s, %s, %s, 'aktif')",
        (token, datetime.now(), expires_dt)
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

    # Insert data absensi
    now = datetime.now()
    cur.execute("""
        INSERT INTO absensi (id_siswa, waktu_absen, token_qr, status, nama_siswa, jurusan, kelas)
        VALUES (%s, %s, %s, 'hadir', %s, %s, %s)
    """, (id_siswa, now, token_qr, siswa['nama_siswa'], siswa['jurusan'], siswa['kelas']))

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
app.secret_key = "change_this_secret_key_to_random_string"

# Konfigurasi folder untuk menyimpan QR codes
OUT_DIR = os.path.join('static', 'qrcodes')
os.makedirs(OUT_DIR, exist_ok=True)

# Token TTL (Time To Live) - 5 menit
TOKEN_TTL_SECONDS = 300

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
    """Proses login guru"""
    username = request.form.get('username')
    password = request.form.get('password')
    guru = get_guru_by_username(username)
    
    if not guru or guru['password'] != password:
        return "Login gagal: username/password salah", 401
    
    session.clear()
    session['guru'] = guru['username']
    session['nama_guru'] = guru['nama_guru']
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
    """Generate QR token untuk absensi"""
    if 'guru' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    # Generate token unik
    token = str(uuid.uuid4())
    expires_dt = datetime.now() + timedelta(seconds=TOKEN_TTL_SECONDS)
    
    # Simpan token ke database
    insert_qr_token(token, expires_dt)
    
    # Generate QR code
    filename = f"token_{datetime.now().strftime('%Y%m%d%H%M%S')}_{token[:8]}.png"
    filepath = os.path.join(OUT_DIR, filename)
    img = qrcode.make(token)
    img.save(filepath)
    
    return jsonify({
        'status': 'success',
        'token': token,
        'qr_url': url_for('static', filename=f"qrcodes/{filename}"),
        'expires_in': TOKEN_TTL_SECONDS
    })

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
    
    # Cek waktu kadaluarsa
    if datetime.now() > row['waktu_expired']:
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
    """API untuk mendapatkan data absensi terbaru"""
    try:
        absensi_list = get_all_absensi()
        
        # Format datetime ke string
        for item in absensi_list:
            if isinstance(item.get('waktu_absen'), datetime):
                item['waktu_absen'] = item['waktu_absen'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({
            'success': True,
            'data': absensi_list
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/absensi/filter', methods=['GET'])
def api_filter_absensi():
    """API untuk filter data absensi berdasarkan kelas, jurusan, dan bulan"""
    try:
        kelas = request.args.get('kelas')
        jurusan = request.args.get('jurusan')
        bulan = request.args.get('bulan')  # format: YYYY-MM

        conn = connect_db()
        cur = conn.cursor(dictionary=True)

        query = """
            SELECT s.nis, s.nama_siswa, s.kelas, s.jurusan, a.waktu_absen
            FROM absensi a
            JOIN siswa s ON a.id_siswa = s.id_siswa
            WHERE 1=1
        """
        params = []

        # Filter kelas
        if kelas:
            query += " AND s.kelas LIKE %s"
            params.append(f"{kelas}%")

        # Filter jurusan
        if jurusan:
            query += " AND s.jurusan = %s"
            params.append(jurusan)

        # Filter bulan
        if bulan:
            start_date = datetime.strptime(bulan + "-01", "%Y-%m-%d")
            if start_date.month == 12:
                end_date = start_date.replace(year=start_date.year + 1, month=1)
            else:
                end_date = start_date.replace(month=start_date.month + 1)
            query += " AND a.waktu_absen >= %s AND a.waktu_absen < %s"
            params.extend([start_date, end_date])

        query += " ORDER BY a.waktu_absen DESC"
        cur.execute(query, params)
        data = cur.fetchall()
        cur.close()
        conn.close()

        # Format waktu
        for d in data:
            if isinstance(d['waktu_absen'], datetime):
                d['waktu_absen'] = d['waktu_absen'].strftime("%Y-%m-%d %H:%M:%S")

        return jsonify({'success': True, 'data': data})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ========================================
# EXPORT EXCEL
# ========================================

@app.route('/export_absensi', methods=['GET'])
def export_absensi():
    """Export riwayat absensi ke file Excel (.xlsx)"""
    if 'guru' not in session:
        return redirect(url_for('index'))

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    kelas = request.args.get('kelas')
    jurusan = request.args.get('jurusan')
    bulan = request.args.get('bulan')

    absensi_list = get_all_absensi()

    # Filter data
    def in_filter(item):
        dt = item.get('waktu_absen')
        if isinstance(dt, str):
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                try:
                    dt = datetime.strptime(dt, fmt)
                    break
                except:
                    pass

        # Filter tanggal rentang
        if start_date:
            sd = datetime.strptime(start_date, '%Y-%m-%d')
            if dt < sd:
                return False
        if end_date:
            ed = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
            if dt > ed:
                return False

        # Filter bulan
        if bulan:
            try:
                year, month = bulan.split('-')
                if dt.year != int(year) or dt.month != int(month):
                    return False
            except:
                pass

        # Filter kelas
        if kelas and str(item.get('kelas', '')).lower() != kelas.lower():
            return False

        # Filter jurusan
        if jurusan and str(item.get('jurusan', '')).lower() != jurusan.lower():
            return False

        return True

    filtered_absen = [it for it in absensi_list if in_filter(it)]

    # Buat workbook Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Riwayat Absensi"

    headers = ['ID Absen', 'NIS', 'Nama Siswa', 'Kelas', 'Jurusan', 'Waktu Absen', 'Keterangan']
    ws.append(headers)

    for item in filtered_absen:
        ws.append([
            item.get('id_absen') or item.get('id') or '',
            item.get('nis') or '',
            item.get('nama_siswa') or item.get('nama') or '',
            item.get('kelas') or '',
            item.get('jurusan') or '',
            str(item.get('waktu_absen')),
            item.get('keterangan') or item.get('status') or ''
        ])

    # Auto-adjust column width
    for column_cells in ws.columns:
        length = max(len(str(cell.value)) for cell in column_cells)
        ws.column_dimensions[column_cells[0].column_letter].width = min(length + 2, 50)

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)

    filename = f"absensi_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
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
pass
