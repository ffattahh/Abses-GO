import mysql.connector
from datetime import date, datetime 

def connect_db(dbsekolah):
    """Menghubungkan ke database berdasarkan nama yang diberikan."""
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database=dbsekolah
        )
        return conn
    except mysql.connector.Error as err:
        print(f"[DATABASE] ❌ Gagal koneksi ke {dbsekolah}: {err}")
        return None

# --- FUNGSI ABSENSI ---

# --- PERUBAHAN DIMULAI DI SINI ---
def insert_absen(nis, nama, jurusan, kelas):
    """Memasukkan data absensi siswa, dengan pengecekan duplikat dan pencatatan waktu."""
    conn = connect_db("dbsekolah")
    if not conn:
        return False

    cursor = conn.cursor()
    
    # 1. Dapatkan tanggal DAN waktu saat ini
    now = datetime.now()
    today_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")

    try:
        # Pengecekan duplikat untuk siswa yang sama di tanggal yang sama
        cursor.execute("SELECT id FROM absensi WHERE nis=%s AND tanggal_hadir=%s", (nis, today_date))
        if cursor.fetchone():
            print(f"[DATABASE] ⚠️ Siswa dengan NIS {nis} sudah absen hari ini.")
            conn.close()
            return False # Mengembalikan False jika sudah ada

        # 2. Ubah SQL INSERT untuk menyertakan kolom 'waktu_hadir'
        sql = "INSERT INTO absensi (nis, nama, jurusan, kelas, tanggal_hadir, waktu_hadir) VALUES (%s, %s, %s, %s, %s, %s)"
        
        # 3. Tambahkan 'current_time' ke dalam data yang akan dieksekusi
        values = (nis, nama, jurusan, kelas, today_date, current_time)
        
        cursor.execute(sql, values)
        conn.commit()
        
        print(f"[DATABASE] ✅ Absen untuk siswa NIS {nis} berhasil disimpan.")
        return True # Mengembalikan True jika berhasil

    except mysql.connector.Error as err:
        print(f"[DATABASE] ❌ Gagal INSERT absen: {err}")
        conn.rollback() # Batalkan perubahan jika terjadi error
        return False # Mengembalikan False jika gagal

    finally:
        # Pastikan koneksi selalu ditutup
        if conn.is_connected():
            cursor.close()
            conn.close()
# --- AKHIR PERUBAHAN ---


def get_today_absen():
    """Mengambil semua data absensi untuk hari ini."""
    conn = connect_db("dbsekolah")
    if not conn: return []

    cursor = conn.cursor(dictionary=True)
    today = date.today().strftime("%Y-%m-%d")
    query = "SELECT * FROM absensi WHERE tanggal_hadir=%s ORDER BY waktu_hadir DESC"
    cursor.execute(query, (today,))
    result = cursor.fetchall()
    conn.close()
    return result

def get_all_absen():
    """Mengambil SEMUA riwayat absensi dari database untuk ditampilkan ke guru."""
    conn = connect_db("dbsekolah")
    if not conn: return []
    
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM absensi ORDER BY tanggal_hadir DESC, id DESC"
    cursor.execute(query)
    result = cursor.fetchall()
    conn.close()
    return result

def get_absen_by_nis(nis):
    """Mengambil semua riwayat absensi untuk SATU siswa berdasarkan NIS."""
    conn = connect_db("dbsekolah")
    if not conn: return []

    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM absensi WHERE nis=%s ORDER BY tanggal_hadir DESC, id DESC"
    cursor.execute(query, (nis,))
    result = cursor.fetchall()
    conn.close()
    return result

# --- FUNGSI SISWA ---

def get_siswa(username, password):
    """Mencari data siswa berdasarkan username dan password untuk login."""
    conn = connect_db("dbsekolah")
    if not conn: return None

    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM siswa WHERE Username = %s AND Password = %s"
    cursor.execute(query, (username, password))
    result = cursor.fetchone()
    conn.close()
    return result
    
def get_siswa_by_nis(nis):
    """Mencari data siswa berdasarkan NIS."""
    conn = connect_db("dbsekolah")
    if not conn: return None

    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM siswa WHERE NIS = %s"
    cursor.execute(query, (nis,))
    result = cursor.fetchone()
    conn.close()
    return result

# --- FUNGSI GURU ---

def get_guru(username, password):
    """Mencari data guru berdasarkan username dan password untuk login."""
    conn = connect_db("dbsekolah")
    if not conn: return None
    
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM guru WHERE Username = %s AND Password = %s"
    cursor.execute(query, (username, password))
    result = cursor.fetchone()
    conn.close()
    return result