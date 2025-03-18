/**
 * Product page functionality
 * Handles star rating selection, image zoom, and other interactive elements
 */

document.addEventListener("DOMContentLoaded", function() {
    // Star rating functionality
    initStarRating();
    
    // Order button functionality
    initOrderButton();
    
    // Product image zoom effect
    initImageZoom();
    
    // Initialize quantity selector
    initQuantitySelector();
    
    // Animate elements on scroll
    initScrollAnimations();
});

/**
 * Initialize the star rating system
 */
function initStarRating() {
    const starButtons = document.querySelectorAll(".star-btn");
    const ratingInput = document.getElementById("selected-rating");
    
    if (!starButtons.length || !ratingInput) return;

    // Set initial stars to empty
    starButtons.forEach(btn => {
        btn.innerHTML = '<i class="far fa-star"></i>';
    });

    starButtons.forEach((button, index) => {
        button.addEventListener("click", function() {
            let selectedValue = this.getAttribute("data-value");
            ratingInput.value = selectedValue;

            // Remove the 'selected' class from all stars
            starButtons.forEach(btn => {
                btn.classList.remove("selected");
                btn.innerHTML = '<i class="far fa-star"></i>';
            });

            // Add the 'selected' class to the clicked star and all stars to its right (lower index)
            for (let i = 0; i <= 4-index; i++) { // 4-index because star buttons are in reverse order
                const starIndex = i;
                const btn = starButtons[starIndex];
                btn.classList.add("selected");
                btn.innerHTML = '<i class="fas fa-star"></i>';
            }
            
            // Add an animation to the stars
            animateStars();
        });
    });
}

/**
 * Add an animation to the selected stars
 */
function animateStars() {
    const selectedStars = document.querySelectorAll(".star-btn.selected");
    selectedStars.forEach((star, index) => {
        setTimeout(() => {
            star.classList.add('pop');
            setTimeout(() => {
                star.classList.remove('pop');
            }, 300);
        }, index * 50);
    });
}

/**
 * Initialize the order button functionality
 */
function initOrderButton() {
    const orderButton = document.querySelector(".order-button");
    
    if (!orderButton) return;
    
    orderButton.addEventListener("click", function() {
        // Add a ripple effect to the button
        const ripple = document.createElement('span');
        ripple.classList.add('ripple');
        this.appendChild(ripple);
        
        // Position the ripple where the user clicked
        const rect = this.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        ripple.style.width = ripple.style.height = `${size}px`;
        
        // Clean up the ripple element after animation
        setTimeout(() => {
            ripple.remove();
        }, 600);
        
        // Show a cart notification
        const cartIcon = document.querySelector('#cart i');
        if (cartIcon) {
            cartIcon.classList.add('pulse');
            setTimeout(() => {
                cartIcon.classList.remove('pulse');
            }, 1000);
        }
        
        // In a real implementation, this would add the product to the cart
        showNotification('Product added to cart!');
        
        // Animation feedback
        this.classList.add("clicked");
        setTimeout(() => {
            this.classList.remove("clicked");
        }, 300);
    });
}

/**
 * Show a notification to the user
 */
function showNotification(message) {
    // Check if a notification container already exists
    let notificationContainer = document.querySelector('.notification-container');
    
    if (!notificationContainer) {
        // Create a notification container if it doesn't exist
        notificationContainer = document.createElement('div');
        notificationContainer.className = 'notification-container';
        document.body.appendChild(notificationContainer);
    }
    
    // Create a new notification
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.innerHTML = `
        <div class="notification-icon">
            <i class="fas fa-check-circle"></i>
        </div>
        <div class="notification-message">${message}</div>
    `;
    
    // Add the notification to the container
    notificationContainer.appendChild(notification);
    
    // Trigger the animation
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // Remove the notification after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

/**
 * Initialize image zoom effect
 */
function initImageZoom() {
    const productImage = document.querySelector('.product-image img');
    if (!productImage) return;
    
    // Create a magnifier glass element
    const magnifier = document.createElement('div');
    magnifier.className = 'magnifier';
    document.querySelector('.product-image').appendChild(magnifier);
    
    productImage.addEventListener('mousemove', function(e) {
        // Get the position of the image
        const rect = this.getBoundingClientRect();
        
        // Calculate the position of the cursor relative to the image
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        // Calculate the position as a percentage
        const xPercent = x / rect.width * 100;
        const yPercent = y / rect.height * 100;
        
        // Position the magnifier
        magnifier.style.display = 'block';
        magnifier.style.left = `${x - magnifier.offsetWidth/2}px`;
        magnifier.style.top = `${y - magnifier.offsetHeight/2}px`;
        
        // Set the background image and position
        magnifier.style.backgroundImage = `url(${this.src})`;
        magnifier.style.backgroundPosition = `${xPercent}% ${yPercent}%`;
    });
    
    productImage.addEventListener('mouseleave', function() {
        magnifier.style.display = 'none';
    });
}

/**
 * Initialize quantity selector
 */
function initQuantitySelector() {
    // Insert quantity selector HTML after the stock info
    const stockInfo = document.querySelector('.product-info .stock');
    if (!stockInfo) return;
    
    const quantitySelector = document.createElement('div');
    quantitySelector.className = 'quantity-selector';
    quantitySelector.innerHTML = `
        <label for="quantity">Quantity:</label>
        <div class="quantity-controls">
            <button type="button" class="quantity-btn minus">-</button>
            <input type="number" id="quantity" name="quantity" value="1" min="1" max="99">
            <button type="button" class="quantity-btn plus">+</button>
        </div>
    `;
    
    stockInfo.insertAdjacentElement('afterend', quantitySelector);
    
    // Add event listeners to the quantity buttons
    const minusBtn = quantitySelector.querySelector('.minus');
    const plusBtn = quantitySelector.querySelector('.plus');
    const quantityInput = quantitySelector.querySelector('#quantity');
    
    minusBtn.addEventListener('click', function() {
        let currentValue = parseInt(quantityInput.value);
        if (currentValue > 1) {
            quantityInput.value = currentValue - 1;
        }
    });
    
    plusBtn.addEventListener('click', function() {
        let currentValue = parseInt(quantityInput.value);
        let maxValue = parseInt(quantityInput.getAttribute('max'));
        if (currentValue < maxValue) {
            quantityInput.value = currentValue + 1;
        }
    });
}

/**
 * Initialize scroll animations
 */
function initScrollAnimations() {
    const elementsToAnimate = document.querySelectorAll('.product-info h1, .product-info .description, .product-info .price, .order-button, .review-section, .existing-reviews');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fadeIn');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1
    });
    
    elementsToAnimate.forEach(element => {
        element.classList.add('animate');
        observer.observe(element);
    });
} 