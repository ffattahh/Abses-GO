import mysql.connector

try:
    conn = mysql.connector.connect(
        host="localhost",      # atau "127.0.0.1"
        user="root",           # default user XAMPP
        password="",           # default password XAMPP kosong
        database="dbguru"      # ganti sesuai nama database
    )
    if conn.is_connected():
        print("✅ Berhasil terkoneksi ke MySQL XAMPP!")
    else:
        print("❌ Gagal terkoneksi!")
except mysql.connector.Error as err:
    print(f"Error: {err}")
finally:
    if 'conn' in locals() and conn.is_connected():
        conn.close()