// Orders.js - Handles order-related functionality

document.addEventListener('DOMContentLoaded', function() {
    // Update order count on page load
    updateOrderCount();
    
    // Add event listeners for any buttons that need them
    setupEventListeners();
});

/**
 * Sets up event listeners for order-related elements
 */
function setupEventListeners() {
    // Add event listeners for cancel buttons if they exist
    const cancelButtons = document.querySelectorAll('.cancel-btn');
    cancelButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to cancel this order?')) {
                e.preventDefault();
            }
        });
    });
}

/**
 * Updates the order count in the header
 * Gets the count from the server-side rendered data
 */
function updateOrderCount() {
    // Try to get order count from API endpoint
    fetch('/api/order-count/')
        .then(response => response.json())
        .then(data => {
            const orderCountElement = document.getElementById('order-count');
            if (orderCountElement) {
                orderCountElement.textContent = data.count;
            }
        })
        .catch(error => {
            console.error('Error fetching order count:', error);
            // Fallback: try to get from page data
            const orderCountElement = document.getElementById('order-count');
            if (orderCountElement && orderCountElement.dataset.count) {
                orderCountElement.textContent = orderCountElement.dataset.count;
            } else if (orderCountElement) {
                // Default to 0 if no data available
                orderCountElement.textContent = '0';
            }
        });
}