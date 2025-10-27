# database.py
import mysql.connector
from datetime import datetime
from mysql.connector import pooling

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'absensi_qr',
    'auth_plugin': 'mysql_native_password'
}

connection_pool = pooling.MySQLConnectionPool(pool_name="mypool",
                                              pool_size=10,)

def connect_db():
    return mysql.connector.connect(**DB_CONFIG)

# GURU
def get_guru_by_username(username):
    conn = connect_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM guru WHERE username=%s LIMIT 1", (username,))
    r = cur.fetchone()
    cur.close(); conn.close()
    return r

# SISWA
def get_siswa_by_username(username):
    conn = connect_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM siswa WHERE username=%s LIMIT 1", (username,))
    r = cur.fetchone()
    cur.close(); conn.close()
    return r

def get_siswa_by_id(id_siswa):
    conn = connect_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM siswa WHERE id_siswa=%s LIMIT 1", (id_siswa,))
    r = cur.fetchone()
    cur.close(); conn.close()
    return r

# TOKEN QR
def insert_qr_token(token, expires_dt):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO qr_token (token, waktu_buat, waktu_expired, status) VALUES (%s, %s, %s, 'aktif')",
        (token, datetime.now(), expires_dt)
    )
    conn.commit()
    cur.close(); conn.close()

def verify_token(token):
    """
    Mengembalikan baris token jika aktif. Caller harus memeriksa waktu_expired.
    """
    conn = connect_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM qr_token WHERE token=%s AND status='aktif' LIMIT 1", (token,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row

def expire_token(token):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("UPDATE qr_token SET status='expired' WHERE token=%s", (token,))
    conn.commit()
    cur.close(); conn.close()

# ABSENSI
def insert_absen_by_id(id_siswa, token_qr):
    conn = connect_db()
    cur = conn.cursor(dictionary=True)

    # Cek duplikat hari ini
    cur.execute("SELECT id_absen FROM absensi WHERE id_siswa=%s AND DATE(waktu_absen)=CURDATE()", (id_siswa,))
    if cur.fetchone():
        cur.close(); conn.close()
        return False

    # Ambil data siswa (nama, jurusan, kelas)
    cur.execute("SELECT nama_siswa, jurusan, kelas FROM siswa WHERE id_siswa=%s", (id_siswa,))
    siswa = cur.fetchone()
    if not siswa:
        cur.close(); conn.close()
        return False

    # Insert data absensi
    now = datetime.now()
    cur.execute("""
        INSERT INTO absensi (id_siswa, waktu_absen, token_qr, status, nama_siswa, jurusan, kelas)
        VALUES (%s, %s, %s, 'hadir', %s, %s, %s)
    """, (id_siswa, now, token_qr, siswa['nama_siswa'], siswa['jurusan'], siswa['kelas']))

    conn.commit()
    cur.close(); conn.close()
    return True

def get_absensi_by_id_siswa(id_siswa):
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
    cur.close(); conn.close()
    return rows

def get_all_absensi():
    conn = connect_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT a.*, s.nama_siswa, s.nis
        FROM absensi a
        JOIN siswa s ON a.id_siswa = s.id_siswa
        ORDER BY a.waktu_absen DESC
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows