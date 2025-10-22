import mysql.connector
from datetime import date, datetime 

def connect_db(dbsekolah):
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database=dbsekolah
        )
        print(f"✅ Koneksi ke {dbsekolah} berhasil!")
        return conn
    except Exception as e:
        print(f"❌ Gagal koneksi ke {dbsekolah}: {e}")
        return None

# --- FUNGSI ABSENSI ---

def insert_absen(nis, nama, jurusan, kelas):
    """Memasukkan data absensi siswa, dengan pengecekan duplikat dan pencatatan waktu."""
    conn = connect_db("dbsekolah")
    if not conn:
        return False

    cursor = conn.cursor()
    
    # ✅ Dapatkan waktu penuh sebagai DATETIME
    now = datetime.now()
    today_date = now.strftime("%Y-%m-%d")          # untuk tanggal_hadir
    full_datetime = now.strftime("%Y-%m-%d %H:%M:%S")  # untuk waktu_hadir (DATETIME)

    try:
        # Pengecekan duplikat: tetap pakai today_date
        cursor.execute("SELECT id FROM absensi WHERE nis=%s AND tanggal_hadir=%s", (nis, today_date))
        if cursor.fetchone():
            print(f"[DATABASE] ⚠️ Siswa dengan NIS {nis} sudah absen hari ini.")
            conn.close()
            return False

        # ✅ Kirim full_datetime ke kolom waktu_hadir
        sql = "INSERT INTO absensi (nis, nama, jurusan, kelas, tanggal_hadir, waktu_hadir) VALUES (%s, %s, %s, %s, %s, %s)"
        values = (nis, nama, jurusan, kelas, today_date, full_datetime)
        
        cursor.execute(sql, values)
        conn.commit()
        
        print(f"[DATABASE] ✅ Absen untuk siswa NIS {nis} berhasil disimpan.")
        return True

    except mysql.connector.Error as err:
        print(f"[DATABASE] ❌ Gagal INSERT absen: {err}")
        conn.rollback()
        return False

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

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
    """Ambil data siswa berdasarkan NIS."""
    conn = connect_db("dbsekolah")
    if not conn:
        return None

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM siswa WHERE NIS = %s", (nis,))
        result = cursor.fetchone()
        return result
    except Exception as e:
        print(f"Error ambil siswa: {e}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
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
