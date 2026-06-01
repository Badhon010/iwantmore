document.addEventListener('DOMContentLoaded', function() {
    // Get product data
    const wishlistBtn = document.querySelector('.wishlist-btn');
    const productId = wishlistBtn?.dataset.productId;
    const productName = wishlistBtn?.dataset.productName;
    const productPrice = parseFloat(wishlistBtn?.dataset.productPrice);
    let productImage = wishlistBtn?.dataset.productImage;
    
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
    const colorImageTriggers = document.querySelectorAll('.color-image-trigger');
    const requiresColor = document.querySelector('.color-choice-list')?.dataset.requiresColor === 'true';
    let selectedColor = colorImageTriggers.length === 1 ? (colorImageTriggers[0].dataset.colorName || '') : '';
    
    // ========================================
    // Thumbnail Image Switching
    // ========================================
    function setActiveImage(imageUrl) {
        if (!mainImage || !imageUrl) {
            return;
        }

        mainImage.src = imageUrl;
        productImage = imageUrl;
        thumbnails.forEach((thumb) => {
            const thumbUrl = thumb.dataset.imageUrl || thumb.querySelector('img')?.src;
            thumb.classList.toggle('active', thumbUrl === imageUrl);
        });
        colorImageTriggers.forEach((trigger) => {
            trigger.classList.toggle('active', trigger.dataset.imageUrl === imageUrl);
        });
    }

    thumbnails.forEach(thumb => {
        thumb.addEventListener('click', function() {
            const imgSrc = this.dataset.imageUrl || this.querySelector('img').src;
            if (this.dataset.colorName) {
                selectedColor = this.dataset.colorName;
            }
            setActiveImage(imgSrc);
        });
    });

    colorImageTriggers.forEach((trigger) => {
        trigger.addEventListener('click', function() {
            selectedColor = this.dataset.colorName || '';
            setActiveImage(this.dataset.imageUrl);
        });
    });

    if (selectedColor) {
        const initialColorTrigger = Array.from(colorImageTriggers).find((trigger) => trigger.dataset.colorName === selectedColor);
        initialColorTrigger?.classList.add('active');
    }
    
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
    function getValidatedCartSelection() {
        if (requiresColor && !selectedColor) {
            showToast('Please select a color first');
            return null;
        }

        return {
            color: selectedColor,
            image: mainImage?.src || productImage
        };
    }

    function addProductToCart({ redirectToCart = false } = {}) {
        const cart = JSON.parse(localStorage.getItem('cartItems')) || [];
        const quantity = parseInt(quantityInput.value);
        const selection = getValidatedCartSelection();

        if (!selection) {
            return;
        }

        const index = cart.findIndex(item => item.id == productId && (item.color || '') === selection.color);
        
        if (index !== -1) {
            cart[index].quantity += quantity;
            showToast(`Updated cart quantity`);
        } else {
            cart.push({
                id: productId,
                name: productName,
                price: productPrice,
                image: selection.image,
                color: selection.color,
                quantity: quantity
            });
            showToast('Added to cart');
        }
        
        localStorage.setItem('cartItems', JSON.stringify(cart));
        if (redirectToCart) {
            window.location.href = '/cart/';
        }
    }

    addToCartBtn?.addEventListener('click', function() {
        addProductToCart();
    });
    
    // ========================================
    // Order Now
    // ========================================
    orderNowBtn?.addEventListener('click', function() {
        addProductToCart({ redirectToCart: true });
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
