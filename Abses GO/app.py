from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import os
from datetime import date, datetime, timedelta
import socket
import ssl
from werkzeug.serving import make_ssl_devcert
from database import connect_db, insert_absen, get_siswa, get_guru, get_today_absen, get_siswa_by_nis, get_absen_by_nis, get_all_absen

app = Flask(__name__)

DATA_FILE = 'data/absensi.json'
CERT_FILE = 'cert.pem'
KEY_FILE = 'key.pem'

# Pastikan folder data ada
os.makedirs('data', exist_ok=True)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump([], f)

# Helper functions
def load_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_local_ip():
    """Mendapatkan IP address lokal"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def create_ssl_cert():
    """Membuat SSL certificate untuk HTTPS"""
    try:
        # Gunakan werkzeug untuk membuat dev certificate
        make_ssl_devcert('ssl_cert', host=get_local_ip())
        
        # Rename files
        if os.path.exists('ssl_cert.crt') and os.path.exists('ssl_cert.key'):
            os.rename('ssl_cert.crt', CERT_FILE)
            os.rename('ssl_cert.key', KEY_FILE)
            print("✅ SSL Certificate berhasil dibuat!")
            return True
            
    except Exception as e:
        print(f"❌ Error creating SSL cert dengan werkzeug: {e}")
        
    # Fallback: Buat manual dengan OpenSSL jika ada
    try:
        import subprocess
        local_ip = get_local_ip()
        
        # Buat config file untuk certificate
        config_content = f"""[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
C = ID
ST = Java
L = Jakarta
O = Absensi App
CN = {local_ip}

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
IP.1 = 127.0.0.1
IP.2 = {local_ip}
"""
        
        with open('ssl.conf', 'w') as f:
            f.write(config_content)
        
        # Generate key dan certificate
        subprocess.run([
            'openssl', 'req', '-x509', '-newkey', 'rsa:4096', 
            '-keyout', KEY_FILE, '-out', CERT_FILE,
            '-days', '365', '-nodes', '-config', 'ssl.conf'
        ], check=True, capture_output=True)
        
        # Cleanup
        if os.path.exists('ssl.conf'):
            os.remove('ssl.conf')
            
        print("✅ SSL Certificate berhasil dibuat dengan OpenSSL!")
        return True
        
    except subprocess.CalledProcessError:
        print("❌ OpenSSL tidak ditemukan")
    except Exception as e:
        print(f"❌ Error creating SSL cert dengan OpenSSL: {e}")
    
    # Fallback terakhir: Manual creation
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import ipaddress
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Create certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "ID"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Java"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Jakarta"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Absensi App"),
            x509.NameAttribute(NameOID.COMMON_NAME, local_ip),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                x509.IPAddress(ipaddress.IPv4Address(local_ip)),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        # Write certificate
        with open(CERT_FILE, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        # Write private key
        with open(KEY_FILE, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        print("✅ SSL Certificate berhasil dibuat dengan cryptography!")
        return True
        
    except ImportError:
        print("❌ Install dependencies: pip install cryptography")
    except Exception as e:
        print(f"❌ Error creating SSL cert dengan cryptography: {e}")
    
    return False

# Force HTTPS redirect
@app.before_request
def force_https():
    # Skip redirect untuk localhost dalam development
    if request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https':
        return
    
    # Jika bukan localhost dan tidak HTTPS, redirect ke HTTPS
    if not request.host.startswith('127.0.0.1') and not request.host.startswith('localhost'):
        if not request.is_secure:
            return redirect(request.url.replace('http://', 'https://'))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/siswa')
def siswa():
    return render_template('siswa.html')

@app.route('/guru')
def halaman_guru():
    # Pastikan guru sudah login (tambahkan logika session check Anda di sini)
    # if 'guru_id' not in session:
    #     return redirect(url_for('login_guru'))

    # Panggil fungsi untuk mendapatkan data absen hari ini
    data_absen_hari_ini = get_today_absen()
    
    # Render template dengan data yang sudah diambil
    return render_template('guru.html', daftar_absen=data_absen_hari_ini)

def guru():
    return render_template('guru.html')

@app.route('/api/history', methods=['GET'])
def get_history():
    data = load_data()
    return jsonify(data)

@app.route('/api/history-today', methods=['GET'])
def get_today_history():
    try:
        # Ambil data absensi hari ini dari database
        today_data = get_today_absen()
        return jsonify(today_data), 200
    except Exception as e:
        print(f"[ERROR] Gagal ambil history today: {e}")
        return jsonify({"success": False, "message": "Gagal mengambil data absensi hari ini"}), 500

@app.route('/api/history/<nis>', methods=['GET'])
def get_history_by_nis(nis):
    try:
        # 1. Ambil data dari database
        history_data = get_absen_by_nis(nis)
        
        # 2. Lakukan konversi objek tanggal/waktu menjadi string
        for row in history_data:
            for key, value in row.items():
                if isinstance(value, (datetime, date)):
                    row[key] = value.isoformat()

        # 3. Kirim data yang sudah aman untuk JSON
        return jsonify({
            "success": True,
            "data": history_data
        }), 200
    except Exception as e:
        print(f"[ERROR] Gagal ambil history untuk NIS {nis}: {e}")
        return jsonify({"success": False, "message": f"Gagal mengambil riwayat untuk NIS {nis}"}), 500

# GANTI FUNGSI scan_absen ANDA DENGAN VERSI INI
@app.route('/scan-absen', methods=['POST'])
def scan_absen():
    # --- Print untuk Debugging ---
    print("\n======================================")
    print("✅ Endpoint /scan-absen BERHASIL diakses!")
    print(f" Waktu: {datetime.now()}")
    print(f" Data form mentah yang diterima: {request.form}")
    # -----------------------------

    nis = request.form.get('nis')
    print(f" MENCARI DATA UNTUK NIS: {nis}")

    if not nis:
        print("❌ GAGAL: NIS tidak ada dalam data yang dikirim.")
        print("======================================\n")
        return jsonify({'status': 'error', 'message': 'NIS tidak ditemukan dalam permintaan.'}), 400

    siswa = get_siswa_by_nis(nis)
    print(f" Hasil pencarian siswa di database: {siswa}")
    
    if not siswa:
        print(f"❌ GAGAL: Siswa dengan NIS {nis} tidak terdaftar di database.")
        print("======================================\n")
        return jsonify({'status': 'error', 'message': f'Siswa dengan NIS {nis} tidak terdaftar.'}), 404

    try:
        print(" MEMANGGIL fungsi insert_absen...")
        berhasil = insert_absen(
            nis=siswa['nis'], 
            nama=siswa['nama'], 
            jurusan=siswa['jurusan'], 
            kelas=siswa['kelas']
        )
        print(f" Hasil dari insert_absen: {berhasil}")
        
        if berhasil:
            print("🎉 SUKSES: Data berhasil dimasukkan ke database.")
            print("======================================\n")
            return jsonify({'status': 'success', 'message': f"Absensi untuk {siswa['Nama']} berhasil."}), 200
        else:
            print("⚠️ GAGAL: Siswa kemungkinan sudah absen hari ini (insert_absen mengembalikan False).")
            print("======================================\n")
            return jsonify({'status': 'conflict', 'message': f"{siswa['Nama']} sudah tercatat absen hari ini."}), 409

    except Exception as e:
        print(f"🔥 TERJADI ERROR KRITIS: {str(e)}")
        print("======================================\n")
        return jsonify({'status': 'error', 'message': 'Terjadi kesalahan pada server.'}), 500

@app.route('/api/login-siswa', methods=['POST'])
def login_siswa():
    try:
        username = request.json.get('username')
        password = request.json.get('password')

        if not username or not password:
            return jsonify({"error": "Username dan password wajib diisi"}), 400

        siswa = get_siswa(username, password)  # Ambil dari database

        if siswa:
            return jsonify({
                "success": True,
                "message": "Login siswa berhasil",
                "user": siswa['Username'] if 'Username' in siswa else siswa['nis']
            })
        else:
            return jsonify({"error": "Username atau password salah"}), 401
    except Exception as e:
        return jsonify({"error": f"Terjadi kesalahan saat login: {str(e)}"}), 500

@app.route('/api/login-guru', methods=['POST'])
def login_guru():
    try:
        username = request.json.get('username')
        password = request.json.get('password')

        if not username or not password:
            return jsonify({"error": "Username dan password wajib diisi"}), 400

        guru = get_guru(username, password)  # Ambil dari database

        if guru:
            return jsonify({
                "success": True,
                "message": "Login guru berhasil",
                "user": guru['Username']
            })
        else:
            return jsonify({"error": "Username atau password salah"}), 401
    except Exception as e:
        return jsonify({"error": f"Terjadi kesalahan saat login: {str(e)}"}), 500
    
@app.route('/api/history-guru', methods=['GET'])
def get_history_guru():
    try:
        # 1. Ambil data dari database (hasilnya berisi objek tanggal)
        all_data = get_all_absen()

        # 2. Lakukan konversi objek tanggal/waktu menjadi string
        for row in all_data:
            for key, value in row.items():
                if isinstance(value, (datetime, date)):
                    row[key] = value.isoformat() # Mengubah ke format string standar (YYYY-MM-DDTHH:MM:SS)

        # 3. Kirim data yang sudah aman untuk JSON
        return jsonify({
            "success": True,
            "count": len(all_data),
            "data": all_data
        }), 200
    except Exception as e:
        print(f"[ERROR] Gagal ambil history guru: {e}")
        return jsonify({"success": False, "message": "Gagal mengambil data riwayat"}), 500

@app.route('/api/history-guru-today', methods=['GET'])
def get_history_guru_today():
    try:
        data = get_today_absen()
        return jsonify({
            "success": True,
            "count": len(data),
            "data": data
        }), 200
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"success": False, "message": "Gagal ambil data"}), 500
    
def get_all_absen():
    """Ambil SEMUA absensi siswa dari database"""
    conn = connect_db("dbsekolah")
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)
    # Urutkan berdasarkan tanggal dan ID terbaru agar data baru muncul di atas
    query = "SELECT * FROM absensi ORDER BY tanggal_hadir DESC, id DESC"
    print(f"[DEBUG] Query get_all_absen: {query}")
    cursor.execute(query)
    result = cursor.fetchall()
    conn.close()
    return result

def get_absen_by_nis(nis):
    """Ambil semua absensi untuk satu siswa berdasarkan NIS"""
    conn = connect_db("dbsekolah")
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM absensi WHERE nis=%s ORDER BY tanggal_hadir DESC, id DESC"
    print(f"[DEBUG] Query get_absen_by_nis: {query} | {nis}")
    cursor.execute(query, (nis,))
    result = cursor.fetchall()
    conn.close()
    return result

if __name__ == '__main__':
    # Server HTTP sederhana untuk dihubungkan dengan Ngrok
    # Pastikan tidak ada 'ssl_context' di sini.
    app.run(port=5000, debug=True)