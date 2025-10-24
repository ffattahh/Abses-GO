// guru.js - Final Version with complete attendance management
let qrTimer;
let countdownTimer;
const BASE_URL = window.location.origin;

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
        const riwayatSection = document.getElementById('riwayatSection');
        if (riwayatSection && riwayatSection.style.display === 'block') {
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
    
    // Use QRCode library if available
    if (typeof QRCode !== 'undefined' && QRCode.toCanvas) {
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
        return;
    }

    // Fallback: manual draw
    showQRPlaceholder();
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

function generateAllQR() {
    fetch('/generate-qr')
        .then(res => res.json())
        .then(data => {
            alert(data.message);
            loadQRCodeGallery();
        });
}

function loadQRCodeGallery() {
    fetch('/api/get-all-siswa')
        .then(res => res.json())
        .then(data => {
            const gallery = document.getElementById('qrGallery');
            gallery.innerHTML = '';
            data.forEach(siswa => {
                gallery.innerHTML += `
                    <div class="qr-item">
                        <p>${siswa.Nama} (${siswa.NIS})</p>
                        <img src="/static/qr/${siswa.NIS}.png" width="150">
                    </div>
                `;
            });
        });
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

function refreshToken() {
  fetch(`${BASE_URL}/generate-qr-token`) // Panggil endpoint yang kita buat
    .then(res => res.json())
    .then(data => {
      const token = data && data.token ? data.token : null;
      if (!token) {
        console.warn('Token tidak diterima dari server');
        return;
      }
      
      console.log('GURU SIDE - Token diterima dari server:', token);

      const qrcodeContainer = document.getElementById('qrcode');
      if (qrcodeContainer) qrcodeContainer.innerHTML = '';

      if (typeof QRCode !== 'undefined' && qrcodeContainer) {
        try {
          new QRCode(qrcodeContainer, {
            text: token,
            width: 256,
            height: 256,
          });
          console.log('GURU SIDE - QR Code berhasil dibuat dengan token di atas.');
        } catch (err) {
          console.error('Gagal membuat QR di container qrcode:', err);
        }
      }
    })
    .catch(err => console.error('Gagal mengambil token baru:', err));
}

// start token refresh if endpoint present
try {
  setInterval(refreshToken, 30000);
  // initial call but only if endpoint available would respond; it's fine to call
  refreshToken();
} catch (e) {
  console.warn('refreshToken scheduling failed:', e);
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
      const today = new Date().toLocaleDateString('id-ID');
      const todayData = attendanceData.filter(item => {
          const itemDate = item && item.tanggal ? new Date(item.tanggal).toLocaleDateString('id-ID') : '';
          return itemDate === today;
      });
      const countElement = document.getElementById('todayCount');
      if (countElement) countElement.textContent = todayData.length;
  } catch (error) {
      console.error('Error loadTodayStats:', error);
      const el = document.getElementById('todayCount');
      if (el) el.textContent = '0';
  }
}

// ================== HISTORY ==================
function showRiwayatGuru() {
    const barcodeSection = document.getElementById('barcodeSection');
    const riwayatSection = document.getElementById('riwayatSection');
    if (barcodeSection) barcodeSection.style.display = 'none';
    if (riwayatSection) riwayatSection.style.display = 'block';

    const today = new Date().toLocaleDateString('id-ID');
    const dateEl = document.getElementById('todayDate');
    if (dateEl) dateEl.textContent = `Tanggal: ${today}`;

    loadTodayHistory();
}

function loadTodayHistory() {
    // Ambil data langsung dari API, bukan localStorage
    fetch('/api/history-guru-today')
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(result => {
            if (result && result.success && Array.isArray(result.data)) {
                // Simpan ke localStorage untuk keperluan offline/export
                localStorage.setItem('attendanceData', JSON.stringify(result.data));

                // Filter hanya data hari ini
                const todayISO = new Date().toISOString().split('T')[0];
                const todayData = result.data.filter(item => {
                    const itemDate = item && item.tanggal ? new Date(item.tanggal).toISOString().split('T')[0] : null;
                    return itemDate === todayISO;
                });

                // Tampilkan
                displayHistoryData(todayData);
            } else {
                console.warn("Format API tidak valid atau kosong:", result);
                displayHistoryData([]);
            }
        })
        .catch(error => {
            console.error("❌ Gagal mengambil data absensi:", error);
            displayHistoryData([]);
            showToast('error', 'Gagal memuat data absensi');
        });
}

function displayHistoryData(data) {
    const tbody = document.getElementById('todayHistory');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:20px;">Belum ada yang absen hari ini</td></tr>';
        return;
    }

    data.forEach((item, index) => {
        const nama = item && (item.nama_siswa || item.nama) ? (item.nama_siswa || item.nama) : 'Tidak diketahui';
        const waktu = item && (item.waktu || item.waktu_hadir) ? (item.waktu || item.waktu_hadir) : '-';
        const tanggal = item && (item.tanggal || item.tanggal_hadir) ? (item.tanggal || item.tanggal_hadir) : '-';

        const row = `
        <tr>
        <td>${index + 1}</td>
        <td>${item && item.nis ? item.nis : '-'}</td>
        <td>${nama}</td>
        <td>${item && item.jurusan ? item.jurusan : '-'}</td>
        <td>${item && item.kelas ? item.kelas : '-'}</td>
        <td>${tanggal}</td>
        <td>${waktu}</td>
        </tr>
        `;
        tbody.innerHTML += row;
    });

    console.log("Displayed history data count:", data.length);
}

// 🔹 Fungsi ambil semua riwayat absensi dari backend
function fetchGuruHistoryAll() {
  console.log("🔄 Mengambil seluruh data absensi siswa...");

  fetch('https://192.168.18.76:5000/api/history-guru-all') // ✅ gunakan IP server Flask
    .then(res => res.json())
    .then(result => {
      if (result.success) {
        console.log("✅ Data absensi dari server:", result.data);
        displayGuruHistoryAll(result.data, result.count);
      } else {
        console.error("❌ Gagal:", result.message);
        document.getElementById('guruAllHistory').innerHTML =
          `<tr><td colspan="7" style="text-align:center; color:red;">${result.message}</td></tr>`;
      }
    })
    .catch(err => {
      console.error("🚨 Error fetch:", err);
      document.getElementById('guruAllHistory').innerHTML =
        `<tr><td colspan="7" style="text-align:center; color:red;">Gagal memuat data.</td></tr>`;
    });
}

function displayGuruHistoryAll(data, totalCount) {
  const tbody = document.getElementById('guruAllHistory');
  const total = document.getElementById('guruTotalAll');

  if (!data || data.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;">Belum ada data absensi.</td></tr>`;
    total.textContent = "Total seluruh data absensi: 0";
    return;
  }

  let rows = '';
  data.forEach((item, i) => {
    rows += `
      <tr>
        <td>${i + 1}</td>
        <td>${item.nis}</td>
        <td>${item.nama}</td>
        <td>${item.jurusan}</td>
        <td>${item.kelas}</td>
        <td>${item.tanggal_hadir}</td>
        <td>${item.waktu_hadir}</td>
      </tr>`;
  });
  tbody.innerHTML = rows;
  total.textContent = `Total seluruh data absensi: ${totalCount}`;
}

document.addEventListener('DOMContentLoaded', () => {
  fetchGuruHistoryAll(); // tampilkan semua riwayat saat halaman dibuka
});

document.addEventListener('DOMContentLoaded', () => {
  // Pastikan user role
  const userSession = sessionStorage.getItem('userSession');
  const userRole = sessionStorage.getItem('userRole');
  if (!userSession || userRole !== 'guru') {
      window.location.href = '/';
      return;
  }

  // Inisialisasi data & dashboard
  initializeAttendanceData();
  initializeGuru();

  // Tampilkan data riwayat
  fetchGuruHistoryAll();
});

// ================== ACTION BUTTONS ==================
function showBarcode() {
    const bs = document.getElementById('barcodeSection');
    const rs = document.getElementById('riwayatSection');
    if (bs) bs.style.display = 'block';
    if (rs) rs.style.display = 'none';
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
        csvContent += `${index + 1},"${item.nama_siswa || item.nama || ''}","${item.tanggal || ''}","${item.waktu || ''}","${item.status || ''}"\n`;
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
        alert(`Found ${parsedData.length} records:\n\n` + parsedData.map(r => `${r.nama_siswa || r.nama} - ${r.tanggal} ${r.waktu}`).join('\n'));
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

// ================== LEGACY / UTILITY ==================
// Bungkus fetch yang sebelumnya berjalan "liar" ke fungsi sehingga tidak auto dijalankan
function loadHistoryGuru() {
    fetch(`${BASE_URL}/api/history`, { credentials: 'include' })
        .then(response => response.json())
        .then(result => {
            console.log("Data dari API (loadHistoryGuru):", result); // debug

            // struktur API mungkin berbeda, cek property
            const data = (result && (result.data || result.results || result)) ? (result.data || result.results || result) : [];

            // Simpan ke localStorage
            localStorage.setItem('attendanceData', JSON.stringify(data));

            const tableBody = document.getElementById('history-table-body');
            if (!tableBody) return;

            tableBody.innerHTML = "";

            data.forEach((item, index) => {
                const row = `
                    <tr>
                        <td>${index + 1}</td>
                        <td>${item.nis || '-'}</td>
                        <td>${item.nama || '-'}</td>
                        <td>${item.jurusan || '-'}</td>
                        <td>${item.kelas || '-'}</td>
                        <td>${item.tanggal_hadir || item.tanggal || '-'}</td>
                        <td>${item.waktu_hadir || item.waktu || '-'}</td>
                    </tr>
                `;
                tableBody.innerHTML += row;
            });
        })
        .catch(error => {
            console.error("Error loadHistoryGuru:", error);
            // jangan alert di produksi, cukup log
        });
}

// ================== ON LOAD ==================
window.addEventListener('load', function() {
    if (document.getElementById('barcodeCanvas')) generateQRCode();
});
