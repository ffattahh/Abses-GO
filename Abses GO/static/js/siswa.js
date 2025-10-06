// siswa.js - Updated with localStorage support
let html5QrcodeScanner = null;

// Initialize attendance data if not exists
function initializeAttendanceData() {
    if (!localStorage.getItem('attendanceData')) {
        localStorage.setItem('attendanceData', JSON.stringify([]));
    }
}

// Cek apakah user sudah login
document.addEventListener('DOMContentLoaded', function() {
    const userSession = sessionStorage.getItem('userSession');
    const userRole = sessionStorage.getItem('userRole');
    
    if (!userSession || userRole !== 'siswa') {
        window.location.href = '/';
        return;
    }
    
    initializeAttendanceData();
    initializeScanner();
});

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

function onScanSuccess(decodedText, decodedResult) {
    console.log('QR Code scanned:', decodedText);
    
    // Validate QR code format (should start with ABSENSI-)
    if (!decodedText.startsWith('ABSENSI-')) {
        showToast('error', 'QR Code tidak valid untuk absensi');
        return;
    }
    
    // Process scan result
    document.getElementById('scanResult').innerHTML = `
        <div class="scan-success">
            <i class="fas fa-check-circle"></i>
            <p>Scan berhasil: ${decodedText}</p>
        </div>
    `;
    
    // Get current user name from session
    const currentUser = sessionStorage.getItem('userSession');
    
    // Submit absensi with current user name
    submitAbsensi(currentUser, decodedText);
}

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