// main.js
document.addEventListener('DOMContentLoaded', function() {
    // Clear any existing session when loading main page
    sessionStorage.clear();
    showRoleSelection();
});

function selectRole(role) {
    if (role === 'siswa') {
        document.getElementById('roleSelection').style.display = 'none';
        document.getElementById('loginSectionSiswa').style.display = 'block';
        document.getElementById('loginSectionGuru').style.display = 'none';
    } else if (role === 'guru') {
        document.getElementById('roleSelection').style.display = 'none';
        document.getElementById('loginSectionSiswa').style.display = 'none';
        document.getElementById('loginSectionGuru').style.display = 'block';
    }
    
    // Clear any previous error messages
    clearErrors();
}

function showRoleSelection() {
    document.getElementById('roleSelection').style.display = 'block';
    document.getElementById('loginSectionSiswa').style.display = 'none';
    document.getElementById('loginSectionGuru').style.display = 'none';
    clearErrors();
}

function loginSiswa() {
    const username = document.getElementById('usernameSiswa').value.trim();
    const password = document.getElementById('passwordSiswa').value.trim();
    const errorDiv = document.getElementById('loginErrorSiswa');
    
    // Clear previous errors
    errorDiv.style.display = 'none';
    
    if (!username || !password) {
        showError('loginErrorSiswa', 'Username dan password tidak boleh kosong');
        return;
    }
    
    // Show loading state
    const loginBtn = event.target;
    const originalText = loginBtn.innerHTML;
    loginBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Login...';
    loginBtn.disabled = true;
    
    fetch('/api/login-siswa', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            username: username,
            password: password
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Set session
            sessionStorage.setItem('userSession', data.user); // NIS
            sessionStorage.setItem('userRole', 'siswa');
            sessionStorage.setItem('namaSiswa', data.nama);
            window.location.href = '/siswa';

            
            // Redirect to siswa page
            window.location.href = '/siswa';
        } else {
            showError('loginErrorSiswa', data.error || 'Login gagal');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showError('loginErrorSiswa', 'Terjadi kesalahan koneksi');
    })
    .finally(() => {
        // Restore button state
        loginBtn.innerHTML = originalText;
        loginBtn.disabled = false;
    });
}

function loginGuru() {
    const username = document.getElementById('usernameGuru').value.trim();
    const password = document.getElementById('passwordGuru').value.trim();
    const errorDiv = document.getElementById('loginErrorGuru');
    
    // Clear previous errors
    errorDiv.style.display = 'none';
    
    if (!username || !password) {
        showError('loginErrorGuru', 'Username dan password tidak boleh kosong');
        return;
    }
    
    // Show loading state
    const loginBtn = event.target;
    const originalText = loginBtn.innerHTML;
    loginBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Login...';
    loginBtn.disabled = true;
    
    fetch('/api/login-guru', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            username: username,
            password: password
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Set session
            sessionStorage.setItem('userSession', username);
            sessionStorage.setItem('userRole', 'guru');
            
            // Redirect to guru page
            window.location.href = '/guru';
        } else {
            showError('loginErrorGuru', data.error || 'Login gagal');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showError('loginErrorGuru', 'Terjadi kesalahan koneksi');
    })
    .finally(() => {
        // Restore button state
        loginBtn.innerHTML = originalText;
        loginBtn.disabled = false;
    });
}

function showError(elementId, message) {
    const errorDiv = document.getElementById(elementId);
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        
        // Auto hide after 5 seconds
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
    }
}

function clearErrors() {
    const errorElements = ['loginErrorSiswa', 'loginErrorGuru'];
    errorElements.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.style.display = 'none';
        }
    });
}

// Handle Enter key for forms
document.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        if (document.getElementById('loginSectionSiswa').style.display === 'block') {
            loginSiswa();
        } else if (document.getElementById('loginSectionGuru').style.display === 'block') {
            loginGuru();
        }
    }
});
