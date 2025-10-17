document.addEventListener("DOMContentLoaded", function() {initProductInteractions()});
function initProductInteractions() {
    console.log('Initializing product interactions on ' + window.location.pathname);
    
    // Debug info
    const productItems = document.querySelectorAll('.product-item');
    console.log(`Found ${productItems.length} product items on the page`);
    
    // Check for required elements
    const heartButtons = document.querySelectorAll('.quick-action-btn[title="Add to wishlist"]');
    console.log(`Found ${heartButtons.length} wishlist buttons`);
    
    // Check data-id attributes
    const missingIds = Array.from(productItems).filter(item => !item.getAttribute('data-id')).length;
    console.log(`Products missing data-id: ${missingIds}`);
    
    // Function to check if a product is in the wishlist
    function isInWishlist(productId) {
        const wishlistItems = JSON.parse(localStorage.getItem('wishlistItems')) || [];
        return wishlistItems.some(item => item.id == productId);
    }
    
    // Function to show toast notifications
    function showToast(message) {
        // Create notification container if it doesn't exist
        if (!document.querySelector('.notification-container')) {
            const container = document.createElement('div');
            container.className = 'notification-container';
            document.body.appendChild(container);
        }
        
        const container = document.querySelector('.notification-container');
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.innerHTML = `
            <i class="notification-icon ${message.includes('Added') ? 'fas fa-check-circle' : 'fas fa-info-circle'}"></i>
            <span class="notification-message">${message}</span>
        `;
        
        container.appendChild(notification);
        
        // Show notification with animation
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);
        
        // Remove notification after 3 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 3000);
    }
    
    // Function to create an animation for adding products to cart
    function createAddToCartAnimation(e) {
        const button = e.currentTarget;
        const rect = button.getBoundingClientRect();
        const startX = rect.left + rect.width / 2;
        const startY = rect.top + rect.height / 2;
        
        // Get the cart icon position
        const cartIcon = document.querySelector('.cart');
        if (!cartIcon) return;
        
        const cartRect = cartIcon.getBoundingClientRect();
        const endX = cartRect.left + cartRect.width / 2;
        const endY = cartRect.top + cartRect.height / 2;
        
        // Create the animation element
        const element = document.createElement('div');
        element.className = 'moving-product';
        element.style.width = '20px';
        element.style.height = '20px';
        element.style.position = 'fixed';
        element.style.left = `${startX}px`;
        element.style.top = `${startY}px`;
        element.style.zIndex = '9999';
        element.style.pointerEvents = 'none';
        document.body.appendChild(element);
        
        // Set up animation
        setTimeout(() => {
            element.style.transition = 'all 0.7s cubic-bezier(0.18, 0.89, 0.32, 1.28)';
            element.style.left = `${endX}px`;
            element.style.top = `${endY}px`;
            element.style.opacity = '0';
            element.style.transform = 'scale(0.5)';
        }, 10);
        
        // Remove the element after animation completes
                setTimeout(() => {
            element.remove();
            
            // Add a pulse animation to the cart icon
            const cartIcon = document.querySelector('.cart i');
            if (cartIcon) {
                cartIcon.classList.add('pulse');
                    setTimeout(() => {
                    cartIcon.classList.remove('pulse');
                }, 500);
            }
        }, 700);
    }
    
    
    // Function to toggle item in wishlist
    function toggleWishlistItem(productId, productName, productPrice, productImage, button) {
        // Get existing wishlist items or initialize empty array
        const wishlistItems = JSON.parse(localStorage.getItem('wishlistItems')) || [];
        
        // Check if product already in wishlist
        const existingItemIndex = wishlistItems.findIndex(item => item.id == productId);
        
        if (existingItemIndex !== -1) {
            // Remove from wishlist if already present
            wishlistItems.splice(existingItemIndex, 1);
            
            // Update button appearance
            if (button) {
                button.classList.remove('active');
                const icon = button.querySelector('i');
                if (icon) {
                    icon.className = 'far fa-heart';
                }
            }
            
            // Update heart icons for this product in the grid
            updateProductHeartIcons(productId, false);
            
            showToast(`Removed "${productName}" from your wishlist`);
        } else {
            // Add new item to wishlist
            wishlistItems.push({
                id: productId,
                name: productName,
                price: productPrice,
                image: productImage
            });
            
            // Update button appearance
            if (button) {
                button.classList.add('active');
                const icon = button.querySelector('i');
                if (icon) {
                    icon.className = 'fas fa-heart';
                    
                    // Add pulse animation
                    icon.classList.add('pulse');
                    setTimeout(() => {
                        icon.classList.remove('pulse');
                    }, 500);
                }
            }
            
            // Update heart icons for this product in the grid
            updateProductHeartIcons(productId, true);
            
            showToast(`Added "${productName}" to your wishlist`);
        }
        
        // Save updated wishlist
        localStorage.setItem('wishlistItems', JSON.stringify(wishlistItems));
        
        // Update wishlist count badge
        updateWishlistCount();
    }
    
    // Function to add item to cart
    function addToCart(productId, productName, productPrice, productImage, quantity) {
        // Get existing cart items or initialize empty array
        const cartItems = JSON.parse(localStorage.getItem('cartItems')) || [];
        
        // Check if product already in cart
        const existingItemIndex = cartItems.findIndex(item => item.id == productId);
        
        if (existingItemIndex !== -1) {
            // Update quantity if already in cart
            cartItems[existingItemIndex].quantity += quantity;
        } else {
            // Add new item to cart
            cartItems.push({
                id: productId,
                name: productName,
                price: productPrice,
                image: productImage,
                quantity: quantity
            });
        }
        
        // Save updated cart
        localStorage.setItem('cartItems', JSON.stringify(cartItems));
        
        // Update cart count
        updateCartCount();
        
        // Update cart count if there's a cart counter element
        const cartCount = document.querySelector('.cart-count');
        if (cartCount) {
            const totalItems = cartItems.reduce((total, item) => total + item.quantity, 0);
            cartCount.textContent = totalItems;
            
            // Show the count if it was hidden
            cartCount.style.display = totalItems > 0 ? 'flex' : 'none';
        }
    }
    
    // Function to update all heart icons for a specific product
    function updateProductHeartIcons(productId, isInWishlist) {
        // Update quick action buttons in the grid
        document.querySelectorAll('.quick-action-btn[title="Add to wishlist"]').forEach(btn => {
            const productItem = btn.closest('.product-item');
            if (!productItem) return;
            
            const btnProductId = productItem.getAttribute('data-id');
            
            if (btnProductId == productId) {
                const icon = btn.querySelector('i');
                if (icon) {
                    if (isInWishlist) {
                        icon.className = 'fas fa-heart';
                } else {
                        icon.className = 'far fa-heart';
                    }
                }
        }
    });
}

    // Function to update all wishlist buttons based on localStorage
    function updateWishlistUI() {
        const wishlistItems = JSON.parse(localStorage.getItem('wishlistItems')) || [];
        
        // Update all wishlist buttons in the grid
        document.querySelectorAll('.quick-action-btn[title="Add to wishlist"]').forEach(btn => {
            const productItem = btn.closest('.product-item');
            if (!productItem) return;
            
            const productId = productItem.getAttribute('data-id');
            if (!productId) return;
            
            const icon = btn.querySelector('i');
            if (!icon) return;
            
            // Check if this product is in the wishlist
            const isInWishlist = wishlistItems.some(item => item.id == productId);
            
            if (isInWishlist) {
                icon.className = 'fas fa-heart';
            } else {
                icon.className = 'far fa-heart';
            }
        });
    }
    
    // Handle wishlist button clicks
    document.addEventListener('click', function(e) {
        // Handle wishlist quick action button
        if (e.target.closest('.quick-action-btn') && e.target.closest('.quick-action-btn').title === 'Add to wishlist') {
            const btn = e.target.closest('.quick-action-btn');
            const productItem = btn.closest('.product-item');
            
            if (!productItem) {
                console.error('Cannot find parent product item');
                return;
            }
            
            // Get product details with fallbacks
            let productId = productItem.getAttribute('data-id');
            // If no data-id, try to get it from the DOM structure
            if (!productId) {
                productId = productItem.id ? productItem.id.replace('product-', '') : null;
                if (productId) {
                    // Save it for future use
                    productItem.setAttribute('data-id', productId);
                }
            }
            
            let productName = '';
            const nameElement = productItem.querySelector('.product-name .name');
            if (nameElement) {
                productName = nameElement.textContent.trim();
            } else {
                // Try alternative selectors
                const altNameElement = productItem.querySelector('h3.product-name') || 
                                       productItem.querySelector('.product-title') || 
                                       productItem.querySelector('h3');
                if (altNameElement) {
                    productName = altNameElement.textContent.trim();
                }
            }
            
            let productPrice = productItem.getAttribute('data-price');
            if (!productPrice) {
                // Try to get price from DOM
                const priceElement = productItem.querySelector('.current-price');
                if (priceElement) {
                    productPrice = priceElement.textContent.replace('৳', '').trim();
                }
            }
            
            let productImage = '';
            const imgElement = productItem.querySelector('.product-image');
            if (imgElement && imgElement.src) {
                productImage = imgElement.src;
            } else {
                // Try alternative image selector
                const altImgElement = productItem.querySelector('img');
                if (altImgElement && altImgElement.src) {
                    productImage = altImgElement.src;
                }
            }
            
            if (!productId || !productName || !productPrice || !productImage) {
                console.error('Missing product details for wishlist:', { 
                    productId, 
                    productName, 
                    productPrice, 
                    productImage,
                    element: productItem 
                });
                alert('Sorry, could not add this product to wishlist. Some product details are missing.');
                return;
            }
            
            // Toggle wishlist status
            toggleWishlistItem(productId, productName, productPrice, productImage, btn);
        }
    });
    
    // Add to cart buttons
    const addToCartButtons = document.querySelectorAll('.add-to-cart');
    addToCartButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Display an animation effect (the actual cart functionality will be handled by the link)
            createAddToCartAnimation(e);
        });
    });
    
    // Update wishlist UI on page load
    updateWishlistUI();
}