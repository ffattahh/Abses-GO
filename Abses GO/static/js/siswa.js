// siswa.js - Updated with localStorage support
let html5QrcodeScanner = null;

// Initialize attendance data if not exists
function initializeAttendanceData() {
    if (!localStorage.getItem('attendanceData')) {
        localStorage.setItem('attendanceData', JSON.stringify([]));
    }
}

// Cek apakah user sudah login
document.addEventListener("DOMContentLoaded", function() {
    const nis = sessionStorage.getItem('userSession');
    console.log("NIS dari session:", nis);
    const nama = sessionStorage.getItem('namaSiswa');
    const role = sessionStorage.getItem('userRole');

    if (!nis || role !== 'siswa') {
        alert('Session tidak valid, silakan login ulang.');
        window.location.href = '/login';
        return;
    }

    // tampilkan nama di header
    document.getElementById('namaSiswa').innerText = nama + " (" + nis + ")";

    // muat riwayat absensi
    loadRiwayatAbsensi(nis);
});

function loadRiwayatAbsensi() {
    const nis = sessionStorage.getItem('userSession'); // Ambil NIS dari session

    if (!nis) {
        console.error("NIS tidak ditemukan di sessionStorage");
        renderRiwayatAbsensi([]); // tampilkan kosong
        return;
    }

    fetch(`/api/history/${nis}`)
        .then(response => response.json())
        .then(data => {
            if (Array.isArray(data)) {
                renderRiwayatAbsensi(data);
            } else if (data.data) {
                // Jika API mengembalikan format { success, data: [...] }
                renderRiwayatAbsensi(data.data);
            } else {
                console.warn("Format API tidak sesuai, data:", data);
                renderRiwayatAbsensi([]);
            }
        })
        .catch(error => {
            console.error('Gagal mengambil riwayat:', error);
            renderRiwayatAbsensi([]);
        });
}

function tampilkanRiwayat(data) {
    const container = document.getElementById('riwayatTabel');
    container.innerHTML = '';

    if (!data || data.length === 0) {
        container.innerHTML = '<tr><td colspan="3">Belum ada riwayat absensi</td></tr>';
        return;
    }

    data.forEach(item => {
        const row = `
            <tr>
                <td>${item.tanggal}</td>
                <td>${item.jam}</td>
                <td>${item.status}</td>
            </tr>`;
        container.innerHTML += row;
    });
}

function renderRiwayatAbsensi(data) {
    const tbody = document.getElementById("riwayat-absen");
    tbody.innerHTML = "";

    if (data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;">Belum ada data absensi</td></tr>`;
        return;
    }

    data.forEach((item, index) => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${index + 1}</td>
            <td>${item.tanggal}</td>
            <td>${item.waktu}</td>
            <td>${item.kelas}</td>
            <td>Hadir</td>
        `;
        tbody.appendChild(row);
    });
}

function initializeScanner() {
    try {
        html5QrcodeScanner = new Html5QrcodeScanner(
            "reader", 
            { 
                fps: 10, 
                qrbox: {width: 250, height: 250},
                showTorchButtonIfSupported: true,
                showZoomSliderIfSupported: true,
                defaultZoomValueIfSupported: 2,
                supportedScanTypes: [Html5QrcodeScanType.SCAN_TYPE_CAMERA]
            },
            false
        );
        html5QrcodeScanner.render(onScanSuccess, onScanFailure);
    } catch (error) {
        console.error('Error initializing scanner:', error);
        showToast('error', 'Gagal menginisialisasi scanner kamera');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    initializeScanner();
});

function kirimAbsensiKeServer() {
    // Ambil NIS langsung dari session agar tidak bisa dimanipulasi
    const nis = sessionStorage.getItem('userSession');
    console.log("NIS dikirim:", nis);  // Debug setelah nis diambil

    if (!nis) {
        alert("Session tidak ditemukan, silakan login ulang.");
        window.location.href = '/login';
        return;
    }

    fetch('/scan-absen', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nis: nis })
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message); // akan menampilkan pesan "Anda sudah absen hari ini"
        if (data.status === 'success') {
            loadRiwayatAbsensi(nis);
        }
    })
    .catch(error => {
        alert('Gagal menghubungi server.');
        console.error(error);
    });
}

scanner.onScan((content) => {
    // Misalnya QR berisi NIS siswa
    let nis = content;
    kirimAbsensiKeServer(nis);
});

function onScanSuccess(decodedText) {
    console.log("NIS terdeteksi:", decodedText);

    fetch('/scan-absen', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ nis: decodedText })
    })
    .then(res => res.json())
    .then(data => {
        alert(data.message);
    })
    .catch(err => console.error("Error scan:", err));
}

document.addEventListener('DOMContentLoaded', function() {
    let scanner = new Html5QrcodeScanner("qr-reader", { fps: 10, qrbox: 200 });
    scanner.render(onScanSuccess);
});

function onScanFailure(error) {
    // Handle scan failure silently
}

function submitAbsensi(namaSiswa, qrCode) {
    const now = new Date();
    const tanggal = now.toLocaleDateString('id-ID');
    const waktu = now.toLocaleTimeString('id-ID');
    
    let attendanceData = JSON.parse(localStorage.getItem('attendanceData') || '[]');
    const today = now.toDateString();
    const alreadyPresent = attendanceData.some(record => 
        record.nama_siswa === namaSiswa && 
        new Date(record.timestamp).toDateString() === today
    );
    
    if (alreadyPresent) {
        showToast('warning', 'Anda sudah melakukan absensi hari ini');
        return;
    }
    
    const newRecord = {
        id: Date.now(),
        nama_siswa: namaSiswa,
        tanggal: tanggal,
        waktu: waktu,
        timestamp: now.toISOString(),
        qr_code: qrCode,
        status: 'Hadir'
    };
    
    attendanceData.push(newRecord);
    localStorage.setItem('attendanceData', JSON.stringify(attendanceData));

    // ===============================
    // 🔥 Sinkronisasi ke data guru
    syncAbsensiToGuru(newRecord);
    // ===============================

    showToast('success', `Absensi berhasil dicatat untuk ${namaSiswa} pada ${waktu}`);
    
    setTimeout(() => {
        document.getElementById('scanResult').innerHTML = '';
    }, 3000);
}

// ===============================
// 🔥 Tambahan fungsi baru untuk guru
function syncAbsensiToGuru(record) {
    let attendanceDataGuru = JSON.parse(localStorage.getItem('attendanceDataGuru') || '[]');
    
    // Cek apakah siswa ini sudah absen hari ini di data guru
    const today = new Date(record.timestamp).toDateString();
    const alreadyPresentGuru = attendanceDataGuru.some(r => 
        r.nama_siswa === record.nama_siswa && 
        new Date(r.timestamp).toDateString() === today
    );
    
    if (!alreadyPresentGuru) {
        attendanceDataGuru.push(record);
        localStorage.setItem('attendanceDataGuru', JSON.stringify(attendanceDataGuru));
    }
}

function showManualAbsen() {
    document.getElementById('scanSection').style.display = 'none';
    document.getElementById('manualSection').style.display = 'block';
    
    if (html5QrcodeScanner) {
        html5QrcodeScanner.clear();
    }
}

function submitManualAbsen() {
    const nama = document.getElementById('namaManual').value.trim();
    if (!nama) {
        showToast('error', 'Nama tidak boleh kosong');
        return;
    }
    
    // Use current user from session, not manual input
    const currentUser = sessionStorage.getItem('userSession');
    const manualQrCode = `MANUAL-${Date.now()}`;
    
    submitAbsensi(currentUser, manualQrCode);
    
    // Clear input
    document.getElementById('namaManual').value = '';
}

function backToScan() {
    document.getElementById('scanSection').style.display = 'block';
    document.getElementById('manualSection').style.display = 'none';
    document.getElementById('historySection').style.display = 'none';
    
    // Restart scanner
    setTimeout(() => {
        initializeScanner();
    }, 500);
}

function showHistorySiswa() {
    document.getElementById('scanSection').style.display = 'none';
    document.getElementById('historySection').style.display = 'block';
    
    if (html5QrcodeScanner) {
        html5QrcodeScanner.clear();
    }
    
    loadHistorySiswa();
}

function loadHistorySiswa() {
    const currentUser = sessionStorage.getItem('userSession');
    const attendanceData = JSON.parse(localStorage.getItem('attendanceData') || '[]');
    
    // Filter data untuk user saat ini
    const userHistory = attendanceData.filter(item => item.nama_siswa === currentUser);
    
    // Sort by timestamp descending (newest first)
    userHistory.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    const tbody = document.querySelector('#historyTable tbody');
    tbody.innerHTML = '';
    
    if (userHistory.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 20px;">Belum ada riwayat absensi</td></tr>';
        return;
    }
    
    userHistory.forEach((item, index) => {
        const row = `
            <tr>
                <td>${index + 1}</td>
                <td>${item.nama_siswa}</td>
                <td>${item.tanggal}</td>
                <td>${item.waktu}</td>
            </tr>
        `;
        tbody.innerHTML += row;
    });
}

function logoutSiswa() {
    if (confirm('Apakah Anda yakin ingin logout?')) {
        if (html5QrcodeScanner) {
            html5QrcodeScanner.clear();
        }
        sessionStorage.removeItem('userSession');
        sessionStorage.removeItem('userRole');
        window.location.href = '/';
    }
}

function showToast(type, message) {
    const toast = document.getElementById('toast');
    if (!toast) {
        alert(message); // Fallback if toast element not found
        return;
    }
    
    const icon = toast.querySelector('.toast-icon');
    const messageSpan = toast.querySelector('.toast-message');
    
    // Set icon based on type
    let iconClass = 'fa-info-circle';
    if (type === 'success') iconClass = 'fa-check-circle';
    else if (type === 'error') iconClass = 'fa-exclamation-circle';
    else if (type === 'warning') iconClass = 'fa-exclamation-triangle';
    
    if (icon) icon.className = 'toast-icon fas ' + iconClass;
    if (messageSpan) messageSpan.textContent = message;
    
    // Set toast class
    toast.className = 'toast toast-' + type;
    toast.style.display = 'block';
    
    // Auto hide after 3 seconds
    setTimeout(() => {
        toast.style.display = 'none';
    }, 3000);
}

// Export function for debugging
function debugShowAttendanceData() {
    const data = localStorage.getItem('attendanceData');
    console.log('Current attendance data:', JSON.parse(data || '[]'));
    return JSON.parse(data || '[]');
}

// Clear all attendance data (for testing)
function clearAttendanceData() {
    if (confirm('Hapus semua data absensi? Ini tidak bisa dibatalkan!')) {
        localStorage.removeItem('attendanceData');
        initializeAttendanceData();
        showToast('success', 'Data absensi berhasil dihapus');
    }
}
