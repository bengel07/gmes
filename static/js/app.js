// GmesPay Frontend JavaScript
const API_URL = window.location.origin;

// Auth check
function checkAuth() {
    const token = localStorage.getItem('token');
    const protectedPages = ['/dashboard', '/wallet', '/cards', '/transfer', '/profile'];
    const currentPage = window.location.pathname;

    if (!token && protectedPages.includes(currentPage)) {
        window.location.href = '/login';
    }

    if (token && (currentPage === '/login' || currentPage === '/register')) {
        window.location.href = '/dashboard';
    }
}

// Format currency
function formatCurrency(amount, currency = 'HTG') {
    return new Intl.NumberFormat('fr-HT', {
        style: 'currency',
        currency: currency === 'HTG' ? 'USD' : currency,
        minimumFractionDigits: 2
    }).format(amount);
}

// Show toast notification
function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.style.position = 'fixed';
        container.style.bottom = '20px';
        container.style.right = '20px';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    document.getElementById('toastContainer').appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();

    toast.addEventListener('hidden.bs.toast', () => toast.remove());
}

// Loading spinner
function showLoading(show, elementId) {
    const element = document.getElementById(elementId);
    if (show) {
        element.innerHTML = '<div class="text-center"><div class="spinner-border text-primary"></div></div>';
    }
}

// Run auth check on page load
document.addEventListener('DOMContentLoaded', checkAuth);