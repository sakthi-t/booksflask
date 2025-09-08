// Main JavaScript file for BooksCart

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Search form enhancement
    const searchForm = document.querySelector('form[action*="books"]');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            const searchInput = searchForm.querySelector('input[name="search"]');
            if (searchInput.value.trim() === '') {
                e.preventDefault();
                searchInput.focus();
            }
        });
    }

   // Add loading state to buttons WITHOUT preventing form submission
document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function() {
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Loading...';
            submitBtn.disabled = true;
        }
    });
});


// Utility functions
function showAlert(message, type = 'info') {
    const alertContainer = document.createElement('div');
    alertContainer.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertContainer, container.firstChild);
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        const alert = alertContainer.querySelector('.alert');
        const bsAlert = new bootstrap.Alert(alert);
        bsAlert.close();
    }, 5000);
}

// Form validation helpers
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function validatePassword(password) {
    return password.length >= 6;
}

// Cart functions (placeholder for future implementation)
function addToCart(bookId, quantity = 1) {
    // TODO: Implement add to cart functionality
    showAlert('Added to cart!', 'success');
}

function addToWishlist(bookId) {
    // TODO: Implement add to wishlist functionality
    showAlert('Added to wishlist!', 'success');
}
