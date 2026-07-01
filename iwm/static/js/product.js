document.addEventListener('DOMContentLoaded', function () {
    const wishlistBtn = document.querySelector('.wishlist-btn');
    const productId   = wishlistBtn?.dataset.productId;
    const productName = wishlistBtn?.dataset.productName;
    const productPrice = parseFloat(wishlistBtn?.dataset.productPrice);
    let   productImage = wishlistBtn?.dataset.productImage;

    const quantityInput      = document.getElementById('quantity');
    const minusBtn           = document.querySelector('.qty-btn.minus');
    const plusBtn            = document.querySelector('.qty-btn.plus');
    const addToCartBtn       = document.getElementById('addToCartBtn');
    const orderNowBtn        = document.getElementById('orderNowBtn');
    const thumbnails         = document.querySelectorAll('.thumbnail');
    const mainImage          = document.getElementById('mainImage');
    const colorImageTriggers = document.querySelectorAll('.color-image-trigger');
    const requiresColor      = document.querySelector('.color-choice-list')?.dataset.requiresColor === 'true';
    let   selectedColor      = colorImageTriggers.length === 1 ? (colorImageTriggers[0].dataset.colorName || '') : '';

    // ── Image gallery ─────────────────────────────────────────────────────────
    function setActiveImage(url) {
        if (!mainImage || !url) return;
        mainImage.src = url;
        productImage  = url;
        thumbnails.forEach(t => {
            const src = t.dataset.imageUrl || t.querySelector('img')?.src;
            t.classList.toggle('active', src === url);
        });
    }

    function setActiveColor(activeTrigger) {
        colorImageTriggers.forEach(t => t.classList.toggle('active', t === activeTrigger));
    }

    thumbnails.forEach(t => t.addEventListener('click', function () {
        setActiveImage(this.dataset.imageUrl || this.querySelector('img')?.src);
    }));

    colorImageTriggers.forEach(trigger => trigger.addEventListener('click', function () {
        selectedColor = this.dataset.colorName || '';
        setActiveImage(this.dataset.imageUrl);
        setActiveColor(this);
    }));

    if (selectedColor) {
        Array.from(colorImageTriggers).find(t => t.dataset.colorName === selectedColor)?.classList.add('active');
    }

    // ── Toast (uses #toast element on product page) ───────────────────────────
    function showToast(message) {
        const toast = document.getElementById('toast');
        if (!toast) return;
        toast.textContent = message;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 3000);
    }

    // ── Wishlist ──────────────────────────────────────────────────────────────
    function syncWishlistButton(isInWishlist) {
        if (!wishlistBtn) return;
        wishlistBtn.classList.toggle('active', isInWishlist);
        const icon = wishlistBtn.querySelector('i');
        if (icon) {
            icon.classList.toggle('fas', isInWishlist);
            icon.classList.toggle('far', !isInWishlist);
        }
    }

    function checkWishlistStatus() {
        const wishlist = JSON.parse(localStorage.getItem('wishlistItems')) || [];
        syncWishlistButton(wishlist.some(item => item.id == productId));
    }

    wishlistBtn?.addEventListener('click', function () {
        const wishlist = JSON.parse(localStorage.getItem('wishlistItems')) || [];
        const idx = wishlist.findIndex(item => item.id == productId);
        if (idx !== -1) {
            wishlist.splice(idx, 1);
            syncWishlistButton(false);
            showToast('Removed from wishlist');
        } else {
            wishlist.push({ id: productId, name: productName, price: productPrice, image: productImage });
            syncWishlistButton(true);
            showToast('Added to wishlist');
        }
        localStorage.setItem('wishlistItems', JSON.stringify(wishlist));
        if (typeof updateWishlistCount === 'function') updateWishlistCount();
    });

    // ── Quantity ──────────────────────────────────────────────────────────────
    minusBtn?.addEventListener('click', function () {
        const v = parseInt(quantityInput.value);
        if (v > 1) quantityInput.value = v - 1;
    });

    plusBtn?.addEventListener('click', function () {
        const v = parseInt(quantityInput.value);
        const max = parseInt(quantityInput.max);
        if (v < max) quantityInput.value = v + 1;
    });

    // ── Cart ──────────────────────────────────────────────────────────────────
    function getValidatedSelection() {
        if (requiresColor && !selectedColor) { showToast('Please select a color first'); return null; }
        return { color: selectedColor, image: mainImage?.src || productImage };
    }

    function addProductToCart({ redirectToCart = false } = {}) {
        const selection = getValidatedSelection();
        if (!selection) return;

        const cart     = JSON.parse(localStorage.getItem('cartItems')) || [];
        const quantity = parseInt(quantityInput.value);
        const idx      = cart.findIndex(item => item.id == productId && (item.color || '') === selection.color);

        if (idx !== -1) {
            cart[idx].quantity += quantity;
            showToast('Updated cart quantity');
        } else {
            cart.push({ id: productId, name: productName, price: productPrice, image: selection.image, color: selection.color, quantity });
            showToast('Added to cart');
        }

        localStorage.setItem('cartItems', JSON.stringify(cart));
        if (typeof updateCartCount === 'function') updateCartCount();
        if (redirectToCart) window.location.href = '/cart/';
    }

    addToCartBtn?.addEventListener('click', () => addProductToCart());
    orderNowBtn?.addEventListener('click', () => addProductToCart({ redirectToCart: true }));

    // ── Init ──────────────────────────────────────────────────────────────────
    checkWishlistStatus();
});
