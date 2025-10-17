document.addEventListener('DOMContentLoaded', function() {
    // Get product data
    const wishlistBtn = document.querySelector('.wishlist-btn');
    const productId = wishlistBtn?.dataset.productId;
    const productName = wishlistBtn?.dataset.productName;
    const productPrice = parseFloat(wishlistBtn?.dataset.productPrice);
    const productImage = wishlistBtn?.dataset.productImage;
    
    // Quantity controls
    const quantityInput = document.getElementById('quantity');
    const minusBtn = document.querySelector('.qty-btn.minus');
    const plusBtn = document.querySelector('.qty-btn.plus');
    
    // Action buttons
    const addToCartBtn = document.getElementById('addToCartBtn');
    const orderNowBtn = document.getElementById('orderNowBtn');
    
    // Thumbnail images
    const thumbnails = document.querySelectorAll('.thumbnail');
    const mainImage = document.getElementById('mainImage');
    
    // ========================================
    // Thumbnail Image Switching
    // ========================================
    thumbnails.forEach(thumb => {
        thumb.addEventListener('click', function() {
            const imgSrc = this.querySelector('img').src;
            mainImage.src = imgSrc;
            
            thumbnails.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
        });
    });
    
    // ========================================
    // Wishlist Functionality
    // ========================================
    function checkWishlistStatus() {
        const wishlist = JSON.parse(localStorage.getItem('wishlistItems')) || [];
        const isInWishlist = wishlist.some(item => item.id == productId);
        
        if (isInWishlist) {
            wishlistBtn.classList.add('active');
            wishlistBtn.querySelector('i').classList.remove('far');
            wishlistBtn.querySelector('i').classList.add('fas');
        }
    }
    
    wishlistBtn?.addEventListener('click', function() {
        const wishlist = JSON.parse(localStorage.getItem('wishlistItems')) || [];
        const index = wishlist.findIndex(item => item.id == productId);
        
        if (index !== -1) {
            wishlist.splice(index, 1);
            this.classList.remove('active');
            this.querySelector('i').classList.remove('fas');
            this.querySelector('i').classList.add('far');
            showToast('Removed from wishlist');
        } else {
            wishlist.push({
                id: productId,
                name: productName,
                price: productPrice,
                image: productImage
            });
            this.classList.add('active');
            this.querySelector('i').classList.remove('far');
            this.querySelector('i').classList.add('fas');
            showToast('Added to wishlist');
        }
        
        localStorage.setItem('wishlistItems', JSON.stringify(wishlist));
    });
    
    // ========================================
    // Quantity Controls
    // ========================================
    minusBtn?.addEventListener('click', function() {
        const currentValue = parseInt(quantityInput.value);
        if (currentValue > 1) {
            quantityInput.value = currentValue - 1;
        }
    });
    
    plusBtn?.addEventListener('click', function() {
        const currentValue = parseInt(quantityInput.value);
        const maxValue = parseInt(quantityInput.max);
        if (currentValue < maxValue) {
            quantityInput.value = currentValue + 1;
        }
    });
    
    // ========================================
    // Add to Cart
    // ========================================
    addToCartBtn?.addEventListener('click', function() {
        const cart = JSON.parse(localStorage.getItem('cartItems')) || [];
        const quantity = parseInt(quantityInput.value);
        const index = cart.findIndex(item => item.id == productId);
        
        if (index !== -1) {
            cart[index].quantity += quantity;
            showToast(`Updated cart quantity`);
        } else {
            cart.push({
                id: productId,
                name: productName,
                price: productPrice,
                image: productImage,
                quantity: quantity
            });
            showToast('Added to cart');
        }
        
        localStorage.setItem('cartItems', JSON.stringify(cart));
    });
    
    // ========================================
    // Order Now
    // ========================================
    orderNowBtn?.addEventListener('click', function() {
        const cart = JSON.parse(localStorage.getItem('cartItems')) || [];
        const quantity = parseInt(quantityInput.value);
        const index = cart.findIndex(item => item.id == productId);
        
        if (index !== -1) {
            cart[index].quantity += quantity;
        } else {
            cart.push({
                id: productId,
                name: productName,
                price: productPrice,
                image: productImage,
                quantity: quantity
            });
        }
        
        localStorage.setItem('cartItems', JSON.stringify(cart));
        window.location.href = '/cart/';
    });
    
    // ========================================
    // Toast Notification
    // ========================================
    function showToast(message) {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
    
    // Initialize
    checkWishlistStatus();
});