document.addEventListener("DOMContentLoaded", function() {initProductInteractions()});
function initProductInteractions() {
    function showToast(message) {
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
    
    function createAddToCartAnimation(e) {
        const button = e.currentTarget;
        const rect = button.getBoundingClientRect();
        const startX = rect.left + rect.width / 2;
        const startY = rect.top + rect.height / 2;
        
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
        
        setTimeout(() => {
            element.style.transition = 'all 0.7s cubic-bezier(0.18, 0.89, 0.32, 1.28)';
            element.style.left = `${endX}px`;
            element.style.top = `${endY}px`;
            element.style.opacity = '0';
            element.style.transform = 'scale(0.5)';
        }, 10);
        
        setTimeout(() => {
            element.remove();
            
            const cartIcon = document.querySelector('.cart i');
            if (cartIcon) {
                cartIcon.classList.add('pulse');
                setTimeout(() => {
                    cartIcon.classList.remove('pulse');
                }, 500);
            }
        }, 700);
    }
    function toggleWishlistItem(productId, productName, productPrice, productImage, button) {
        const wishlistItems = JSON.parse(localStorage.getItem('wishlistItems')) || [];
        const existingItemIndex = wishlistItems.findIndex(item => item.id == productId);
        
        if (existingItemIndex !== -1) {
            wishlistItems.splice(existingItemIndex, 1);
            
            if (button) {
                button.classList.remove('active');
                const icon = button.querySelector('i');
                if (icon) {
                    icon.className = 'far fa-heart';
                }
            }
            
            updateProductHeartIcons(productId, false);
            showToast(`Removed "${productName}" from your wishlist`);
        } else {
            wishlistItems.push({
                id: productId,
                name: productName,
                price: productPrice,
                image: productImage
            });
            
            if (button) {
                button.classList.add('active');
                const icon = button.querySelector('i');
                if (icon) {
                    icon.className = 'fas fa-heart';
                    
                    icon.classList.add('pulse');
                    setTimeout(() => {
                        icon.classList.remove('pulse');
                    }, 500);
                }
            }
            
            updateProductHeartIcons(productId, true);
            showToast(`Added "${productName}" to your wishlist`);
        }
        
        localStorage.setItem('wishlistItems', JSON.stringify(wishlistItems));
        updateWishlistCount();
    }

    function updateProductHeartIcons(productId, isInWishlist) {
        document.querySelectorAll('.quick-action-btn[title="Add to wishlist"]').forEach(btn => {
            const productItem = btn.closest('.product-item');
            if (!productItem) return;
            
            const btnProductId = productItem.getAttribute('data-id');
            
            if (btnProductId == productId) {
                const icon = btn.querySelector('i');
                if (icon) {
                    icon.className = isInWishlist ? 'fas fa-heart' : 'far fa-heart';
                }
            }
        });
    }

    function updateWishlistUI() {
        const wishlistItems = JSON.parse(localStorage.getItem('wishlistItems')) || [];
        
        document.querySelectorAll('.quick-action-btn[title="Add to wishlist"]').forEach(btn => {
            const productItem = btn.closest('.product-item');
            if (!productItem) return;
            
            const productId = productItem.getAttribute('data-id');
            if (!productId) return;
            
            const icon = btn.querySelector('i');
            if (!icon) return;
            
            const isInWishlist = wishlistItems.some(item => item.id == productId);
            icon.className = isInWishlist ? 'fas fa-heart' : 'far fa-heart';
        });
    }
    
    document.addEventListener('click', function(e) {
        if (e.target.closest('.quick-action-btn') && e.target.closest('.quick-action-btn').title === 'Add to wishlist') {
            const btn = e.target.closest('.quick-action-btn');
            const productItem = btn.closest('.product-item');
            
            if (!productItem) {
                return;
            }
            
            let productId = productItem.getAttribute('data-id');
            if (!productId) {
                productId = productItem.id ? productItem.id.replace('product-', '') : null;
                if (productId) {
                    productItem.setAttribute('data-id', productId);
                }
            }
            
            let productName = '';
            const nameElement = productItem.querySelector('.product-name .name');
            if (nameElement) {
                productName = nameElement.textContent.trim();
            } else {
                const altNameElement = productItem.querySelector('h3.product-name') || 
                                       productItem.querySelector('.product-title') || 
                                       productItem.querySelector('h3');
                if (altNameElement) {
                    productName = altNameElement.textContent.trim();
                }
            }
            
            let productPrice = productItem.getAttribute('data-price');
            if (!productPrice) {
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
                const altImgElement = productItem.querySelector('img');
                if (altImgElement && altImgElement.src) {
                    productImage = altImgElement.src;
                }
            }
            
            if (!productId || !productName || !productPrice || !productImage) {
                return;
            }
            
            toggleWishlistItem(productId, productName, productPrice, productImage, btn);
        }
    });
    
    document.querySelectorAll('.add-to-cart').forEach(button => {
        button.addEventListener('click', function(e) {
            createAddToCartAnimation(e);
        });
    });
    
    updateWishlistUI();
}
