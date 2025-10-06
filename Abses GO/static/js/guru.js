// guru.js - Final Version with complete attendance management
let qrTimer;
let countdownTimer;

// ================== INIT LOCALSTORAGE ==================
function initializeAttendanceData() {
    if (!localStorage.getItem('attendanceData')) {
        localStorage.setItem('attendanceData', JSON.stringify([]));
    }
}

// ================== PAGE LOAD ==================
document.addEventListener('DOMContentLoaded', function() {
    const userSession = sessionStorage.getItem('userSession');
    const userRole = sessionStorage.getItem('userRole');
    
    if (!userSession || userRole !== 'guru') {
        window.location.href = '/';
        return;
    }
    
    initializeAttendanceData();
    
    // Wait QRCode library
    setTimeout(() => {
        initializeGuru();
    }, 100);
});

// ================== DASHBOARD INIT ==================
function initializeGuru() {
    console.log('Initializing guru dashboard...');
    
    generateQRCode();
    startCountdown();
    updateClock();
    loadTodayStats();
    
    // Update clock
    setInterval(updateClock, 1000);
    
    // Refresh QR every 30s
    qrTimer = setInterval(() => {
        generateQRCode();
        startCountdown();
    }, 30000);
    
    // Refresh data every 5s
    setInterval(() => {
        loadTodayStats();
        if (document.getElementById('riwayatSection').style.display === 'block') {
            loadTodayHistory();
        }
    }, 5000);
}

// ================== QR CODE ==================
function generateQRCode() {
    const canvas = document.getElementById('barcodeCanvas');
    if (!canvas) return;
    
    if (typeof QRCode === 'undefined') {
        showQRPlaceholder();
        return;
    }
    
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    const timestamp = Date.now();
    const randomId = Math.random().toString(36).substring(2, 15);
    const qrData = `ABSENSI-${timestamp}-${randomId}`;
    
    QRCode.toCanvas(canvas, qrData, {
        width: 256,
        height: 256,
        margin: 2,
        color: { dark: '#000000', light: '#FFFFFF' },
        errorCorrectionLevel: 'M'
    }, function (error) {
        if (error) {
            console.error('Error QR:', error);
            showToast('error', 'Gagal membuat QR Code');
            showQRPlaceholder();
        } else {
            console.log('QR Code berhasil dibuat:', qrData);
        }
    });
}

function showQRPlaceholder() {
    const canvas = document.getElementById('barcodeCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    canvas.width = 256;
    canvas.height = 256;
    ctx.fillStyle = '#f0f0f0';
    ctx.fillRect(0, 0, 256, 256);
    ctx.fillStyle = '#666';
    ctx.font = '16px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('QR Code Loading...', 128, 128);
}

// ================== COUNTDOWN ==================
function startCountdown() {
    let seconds = 30;
    const countdownElement = document.getElementById('countdown');
    if (countdownTimer) clearInterval(countdownTimer);
    
    countdownTimer = setInterval(() => {
        seconds--;
        if (countdownElement) {
            countdownElement.textContent = seconds;
            if (seconds <= 5) {
                countdownElement.style.color = '#e74c3c';
                countdownElement.style.fontWeight = 'bold';
            } else if (seconds <= 10) {
                countdownElement.style.color = '#f39c12';
            } else {
                countdownElement.style.color = '#2c3e50';
                countdownElement.style.fontWeight = 'normal';
            }
        }
        if (seconds <= 0) {
            clearInterval(countdownTimer);
            seconds = 30;
        }
    }, 1000);
}

// ================== CLOCK ==================
function updateClock() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const clockElement = document.getElementById('currentTime');
    if (clockElement) clockElement.textContent = timeString;
}

// ================== STATS ==================
function loadTodayStats() {
    try {
        const attendanceData = JSON.parse(localStorage.getItem('attendanceData') || '[]');
        const today = new Date().toDateString();
        const todayData = attendanceData.filter(record => new Date(record.timestamp).toDateString() === today);
        const countElement = document.getElementById('todayCount');
        if (countElement) countElement.textContent = todayData.length;
    } catch (error) {
        console.error('Error loadTodayStats:', error);
        document.getElementById('todayCount').textContent = '0';
    }
}

// ================== HISTORY ==================
function showRiwayatGuru() {
    document.getElementById('barcodeSection').style.display = 'none';
    document.getElementById('riwayatSection').style.display = 'block';
    const today = new Date().toLocaleDateString('id-ID', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    document.getElementById('todayDate').textContent = `Tanggal: ${today}`;
    loadTodayHistory();
}

function loadTodayHistory() {
    try {
        const attendanceData = JSON.parse(localStorage.getItem('attendanceData') || '[]');
        const today = new Date().toDateString();
        const todayData = attendanceData.filter(record => new Date(record.timestamp).toDateString() === today);
        todayData.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        displayHistoryData(todayData);
    } catch (error) {
        console.error('Error loadTodayHistory:', error);
        displayHistoryData([]);
    }
}

function displayHistoryData(data) {
    const tbody = document.getElementById('todayHistory');
    tbody.innerHTML = '';
    if (data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:20px;">Belum ada yang absen hari ini</td></tr>';
        return;
    }
    data.forEach((item, index) => {
        const row = `
            <tr>
                <td>${index + 1}</td>
                <td>${item.nama_siswa}</td>
                <td>${item.waktu}</td>
                <td><span class="status-hadir">${item.status || 'Hadir'}</span></td>
            </tr>
        `;
        tbody.innerHTML += row;
    });
}

// ================== ACTION BUTTONS ==================
function showBarcode() {
    document.getElementById('barcodeSection').style.display = 'block';
    document.getElementById('riwayatSection').style.display = 'none';
    generateQRCode();
    startCountdown();
    loadTodayStats();
}

function refreshQR() {
    generateQRCode();
    startCountdown();
    showToast('success', 'QR Code berhasil di-refresh');
}

function refreshHistory() {
    loadTodayHistory();
    loadTodayStats();
    showToast('success', 'Data berhasil di-refresh');
}

function exportToExcel() {
    const attendanceData = JSON.parse(localStorage.getItem('attendanceData') || '[]');
    if (attendanceData.length === 0) {
        showToast('warning', 'Tidak ada data untuk diekspor');
        return;
    }
    let csvContent = "No,Nama Siswa,Tanggal,Waktu,Status\n";
    attendanceData.forEach((item, index) => {
        csvContent += `${index + 1},"${item.nama_siswa}","${item.tanggal}","${item.waktu}","${item.status}"\n`;
    });
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `data_absensi_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('success', 'Data berhasil diekspor ke CSV');
}

function logoutGuru() {
    if (confirm('Apakah Anda yakin ingin logout?')) {
        if (qrTimer) clearInterval(qrTimer);
        if (countdownTimer) clearInterval(countdownTimer);
        sessionStorage.removeItem('userSession');
        sessionStorage.removeItem('userRole');
        showToast('success', 'Logout berhasil');
        setTimeout(() => { window.location.href = '/'; }, 1000);
    }
}

// ================== TOAST ==================
function showToast(type, message) {
    const toast = document.getElementById('toast');
    if (!toast) return console.log('Toast:', message);
    const icon = toast.querySelector('.toast-icon');
    const messageSpan = toast.querySelector('.toast-message');
    let iconClass = 'fa-info-circle';
    if (type === 'success') iconClass = 'fa-check-circle';
    else if (type === 'error') iconClass = 'fa-exclamation-circle';
    else if (type === 'warning') iconClass = 'fa-exclamation-triangle';
    if (icon) icon.className = 'toast-icon fas ' + iconClass;
    if (messageSpan) messageSpan.textContent = message;
    toast.className = 'toast toast-' + type;
    toast.style.display = 'block';
    setTimeout(() => { toast.style.display = 'none'; }, 3000);
}

// ================== DEBUG ==================
function debugShowAttendanceData() {
    const data = localStorage.getItem('attendanceData');
    const parsedData = JSON.parse(data || '[]');
    console.log('Current attendance data:', parsedData);
    if (parsedData.length > 0) {
        alert(`Found ${parsedData.length} records:\n\n` + parsedData.map(r => `${r.nama_siswa} - ${r.tanggal} ${r.waktu}`).join('\n'));
    } else {
        alert('No attendance data found in localStorage');
    }
    return parsedData;
}

function forceRefreshData() {
    loadTodayStats();
    loadTodayHistory();
    showToast('info', 'Data dipaksa refresh');
}

function clearAttendanceData() {
    if (confirm('Hapus semua data absensi?')) {
        localStorage.removeItem('attendanceData');
        initializeAttendanceData();
        loadTodayStats();
        loadTodayHistory();
        showToast('success', 'Data absensi berhasil dihapus');
    }
}

function debugGenerateQR() {
    generateQRCode();
}

// ================== ON LOAD ==================
window.addEventListener('load', function() {
    if (document.getElementById('barcodeCanvas')) generateQRCode();
});