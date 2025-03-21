/**
 * Shop page functionality
 * Handles filtering, sorting, and product interactions with URL-based filtering
 */

document.addEventListener("DOMContentLoaded", function() {
    // Initialize all components
    initPriceRange();
    initFilters();
    initProductInteractions();
    initNewsletter();
    initSubcategoryToggles();
    
    // Initialize URL parameters from current URL
    initFromURL();
    
    // Check if we're on search page and add 'data-id' attributes if missing
    ensureProductIds();
});

// Ensure all product items have data-id attributes
function ensureProductIds() {
    let missingIdCount = 0;
    let fixedCount = 0;
    
    document.querySelectorAll('.product-item').forEach((item, index) => {
        // Skip if already has data-id
        if (item.getAttribute('data-id')) {
            return;
        }
        
        missingIdCount++;
        let id = null;
        
        // Try to get ID from various sources
        const possibleIdSources = [
            // From item's own ID
            () => item.id && item.id.match(/\d+$/) ? item.id.match(/\d+$/)[0] : null,
            // From data attributes
            () => item.getAttribute('data-product-id'),
            // From links to the product
            () => {
                const link = item.querySelector('a.add-to-cart, a.view-details');
                if (link && link.href) {
                    const match = link.href.match(/\/product\/[\w-]+\-(\d+)\/?$/);
                    return match ? match[1] : null;
                }
                return null;
            },
            // Last resort: use index + timestamp for a unique ID
            () => `temp-${index}-${Date.now()}`
        ];
        
        // Try each source in order until we find an ID
        for (const getIdFunc of possibleIdSources) {
            id = getIdFunc();
            if (id) {
                break;
            }
        }
        
        if (id) {
            item.setAttribute('data-id', id);
            fixedCount++;
        }
    });
    
    console.log(`Fixed ${fixedCount}/${missingIdCount} missing product IDs`);
}

function initFromURL() {
    const urlParams = new URLSearchParams(window.location.search);
    
    // Set price range from URL
    const minPrice = urlParams.get('min_price');
    const maxPrice = urlParams.get('max_price');
    if (minPrice) document.getElementById('priceMin').value = minPrice;
    if (maxPrice) document.getElementById('priceMax').value = maxPrice;
    
    // Set category filters from URL
    const category = urlParams.get('category');
    if (category) {
        const categoryCheckbox = document.querySelector(`.category-checkbox[value="${category}"]`);
        if (categoryCheckbox) categoryCheckbox.checked = true;
    }
    
    // Set stock filter from URL
    const stock = urlParams.get('stock');
    if (stock) {
        const stockRadio = document.querySelector(`input[name="stock"][value="${stock}"]`);
        if (stockRadio) stockRadio.checked = true;
    }
    
    // Set sort from URL
    const sort = urlParams.get('sort');
    if (sort) {
        document.getElementById('sortFilter').value = sort;
    }
    
    // Set special offers from URL
    const discount = urlParams.get('discount');
    const featured = urlParams.get('featured');
    if (discount === 'true') document.getElementById('discountFilter').checked = true;
    if (featured === 'true') document.getElementById('featuredFilter').checked = true;
    
    // Set search query from URL
    const query = urlParams.get('q');
    if (query) {
        document.getElementById('searchInput').value = query;
    }
}

function initPriceRange() {
    const minPriceSlider = document.getElementById('priceSliderMin');
    const maxPriceSlider = document.getElementById('priceSliderMax');
    const minPriceInput = document.getElementById('priceMin');
    const maxPriceInput = document.getElementById('priceMax');
    const minValue = document.querySelector('.price-min-value');
    const maxValue = document.querySelector('.price-max-value');
    const sliderRange = document.querySelector('.slider-range');
    const applyPriceButton = document.getElementById('applyPriceFilter');
    
    if (!minPriceSlider || !maxPriceSlider || !minPriceInput || !maxPriceInput) return;
    
    const minPrice = 0;
    const maxPrice = 10000;
    let currentMinPrice = parseInt(minPriceInput.value || minPrice);
    let currentMaxPrice = parseInt(maxPriceInput.value || maxPrice);
    
    // Set initial z-index
    minPriceSlider.style.zIndex = "5";
    maxPriceSlider.style.zIndex = "4";
    
    // Minimum distance between sliders (in price units)
    const minDistance = 100;
    
    function updatePriceRange() {
        const urlParams = new URLSearchParams(window.location.search);
        if (currentMinPrice > 0) urlParams.set('min_price', currentMinPrice);
        else urlParams.delete('min_price');
        
        if (currentMaxPrice < maxPrice) urlParams.set('max_price', currentMaxPrice);
        else urlParams.delete('max_price');
        
        updateURL(urlParams);
    }
    
    // Price slider event listeners - update visuals during sliding but don't trigger URL change
    minPriceSlider.addEventListener('input', function() {
        // Bring this slider to front when being used
        minPriceSlider.style.zIndex = "6";
        maxPriceSlider.style.zIndex = "4";
        
        // Enforce minimum distance from max slider
        const newValue = parseInt(this.value);
        currentMinPrice = Math.min(newValue, currentMaxPrice - minDistance);
        
        // Update slider position if constrained
        if (newValue !== currentMinPrice) {
            this.value = currentMinPrice;
        }
        
        // Update UI
        minPriceInput.value = currentMinPrice;
        minValue.textContent = '৳' + currentMinPrice.toLocaleString();
        updateSliderRange();
    });
    
    // Update URL only when slider interaction is complete
    minPriceSlider.addEventListener('change', function() {
        if (applyPriceButton) return; // If apply button exists, let the button handle URL updates
        updatePriceRange();
    });
    
    maxPriceSlider.addEventListener('input', function() {
        // Bring this slider to front when being used
        maxPriceSlider.style.zIndex = "6";
        minPriceSlider.style.zIndex = "4";
        
        // Enforce minimum distance from min slider
        const newValue = parseInt(this.value);
        currentMaxPrice = Math.max(newValue, currentMinPrice + minDistance);
        
        // Update slider position if constrained
        if (newValue !== currentMaxPrice) {
            this.value = currentMaxPrice;
        }
        
        // Update UI
        maxPriceInput.value = currentMaxPrice;
        maxValue.textContent = '৳' + currentMaxPrice.toLocaleString();
        updateSliderRange();
    });
    
    // Update URL only when slider interaction is complete
    maxPriceSlider.addEventListener('change', function() {
        if (applyPriceButton) return; // If apply button exists, let the button handle URL updates
        updatePriceRange();
    });
    
    // Price input event listeners
    minPriceInput.addEventListener('change', function() {
        const newValue = parseInt(this.value) || minPrice;
        currentMinPrice = Math.max(minPrice, Math.min(newValue, currentMaxPrice - minDistance));
        
        // Update all UI elements
        this.value = currentMinPrice;
        minPriceSlider.value = currentMinPrice;
        minValue.textContent = '৳' + currentMinPrice.toLocaleString();
        updateSliderRange();
        
        if (!applyPriceButton) updatePriceRange();
    });
    
    maxPriceInput.addEventListener('change', function() {
        const newValue = parseInt(this.value) || maxPrice;
        currentMaxPrice = Math.min(maxPrice, Math.max(newValue, currentMinPrice + minDistance));
        
        // Update all UI elements
        this.value = currentMaxPrice;
        maxPriceSlider.value = currentMaxPrice;
        maxValue.textContent = '৳' + currentMaxPrice.toLocaleString();
        updateSliderRange();
        
        if (!applyPriceButton) updatePriceRange();
    });
    
    // Apply price filter button
    if (applyPriceButton) {
        applyPriceButton.addEventListener('click', function() {
            updatePriceRange();
        });
    }
    
    function updateSliderRange() {
        if (!sliderRange) return;
        const minPercent = (currentMinPrice / maxPrice) * 100;
        const maxPercent = (currentMaxPrice / maxPrice) * 100;
        sliderRange.style.left = minPercent + '%';
        sliderRange.style.width = (maxPercent - minPercent) + '%';
    }
    
    // Initialize displays
    minValue.textContent = '৳' + currentMinPrice.toLocaleString();
    maxValue.textContent = '৳' + currentMaxPrice.toLocaleString();
    updateSliderRange();
    
    // Set initial slider values
    minPriceSlider.value = currentMinPrice;
    maxPriceSlider.value = currentMaxPrice;
}

function initFilters() {
    const searchInput = document.getElementById('searchInput');
    const allCategoriesCheckbox = document.getElementById('allCategories');
    const categoryCheckboxes = document.querySelectorAll('.category-checkbox');
    const stockRadios = document.querySelectorAll('input[name="stock"]');
    const sortFilter = document.getElementById('sortFilter');
    const discountFilter = document.getElementById('discountFilter');
    const featuredFilter = document.getElementById('featuredFilter');
    const resetAllButton = document.getElementById('resetAllFilters');
    
    // Search input handler with debounce
    let searchTimeout;
    if (searchInput) {
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            const urlParams = new URLSearchParams(window.location.search);
            if (this.value.trim()) {
                urlParams.set('q', this.value.trim());
            } else {
                urlParams.delete('q');
            }
            updateURL(urlParams);
        }, 500);
    });
    }
    
    // All Categories checkbox handler
    if (allCategoriesCheckbox) {
        allCategoriesCheckbox.addEventListener('change', function() {
            if (this.checked) {
                // Uncheck all other category checkboxes
                categoryCheckboxes.forEach(checkbox => {
                    checkbox.checked = false;
                });
                
                // Update URL parameter
                const urlParams = new URLSearchParams(window.location.search);
                urlParams.delete('category');
                updateURL(urlParams);
            } else {
                // Don't allow unchecking - if user tries to uncheck, keep it checked
                this.checked = true;
            }
        });
    }
    
    // Category filter handler - radio button-like behavior
    categoryCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const urlParams = new URLSearchParams(window.location.search);
            
            if (this.checked) {
                // Uncheck "All Categories" checkbox
                if (allCategoriesCheckbox) {
                    allCategoriesCheckbox.checked = false;
                }
                
                // Uncheck all other category checkboxes
                categoryCheckboxes.forEach(cb => {
                    if (cb !== this) {
                        cb.checked = false;
                    }
                });
                
                // Set URL parameter
                urlParams.set('category', this.value);
            } else {
                // If unchecked, check the "All Categories" checkbox
                if (allCategoriesCheckbox) {
                    allCategoriesCheckbox.checked = true;
                }
                
                // Remove URL parameter
                urlParams.delete('category');
            }
            
            updateURL(urlParams);
        });
    });
    
    // Stock filter handler
    stockRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            const urlParams = new URLSearchParams(window.location.search);
            if (this.value !== 'all') {
                urlParams.set('stock', this.value);
            } else {
                urlParams.delete('stock');
            }
            updateURL(urlParams);
        });
    });
    
    // Sort filter handler
    if (sortFilter) {
    sortFilter.addEventListener('change', function() {
        const urlParams = new URLSearchParams(window.location.search);
        if (this.value !== 'newest') {
            urlParams.set('sort', this.value);
        } else {
            urlParams.delete('sort');
        }
        updateURL(urlParams);
    });
    }
    
    // Special offers handlers
    if (discountFilter) {
    discountFilter.addEventListener('change', function() {
        const urlParams = new URLSearchParams(window.location.search);
        if (this.checked) {
            urlParams.set('discount', 'true');
        } else {
            urlParams.delete('discount');
        }
        updateURL(urlParams);
    });
    }
    
    if (featuredFilter) {
    featuredFilter.addEventListener('change', function() {
        const urlParams = new URLSearchParams(window.location.search);
        if (this.checked) {
            urlParams.set('featured', 'true');
        } else {
            urlParams.delete('featured');
        }
        updateURL(urlParams);
    });
    }
    
    // Reset all filters
    if (resetAllButton) {
    resetAllButton.addEventListener('click', function() {
        window.location.href = '/search/';
    });
    }
}

function updateURL(urlParams) {
    // Determine if we're on /shop or /search route
    const currentPath = window.location.pathname;
    const basePath = currentPath.includes('/shop') ? '/shop/' : '/search/';
    
    const newURL = `${basePath}?${urlParams.toString()}`;
    window.history.pushState({}, '', newURL);
    fetchProducts(newURL);
}

function fetchProducts(url) {
    fetch(url)
        .then(response => response.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            
            // Update product grid
            const newProductGrid = doc.querySelector('.product-grid');
            const currentProductGrid = document.querySelector('.product-grid');
            if (newProductGrid && currentProductGrid) {
                currentProductGrid.innerHTML = newProductGrid.innerHTML;
                
                // Ensure product IDs are set after AJAX update
                ensureProductIds();
            }
            
            // Update product count
            const newProductCount = doc.querySelector('#productCount');
            const currentProductCount = document.querySelector('#productCount');
            if (newProductCount && currentProductCount) {
                currentProductCount.textContent = newProductCount.textContent;
            }
            
            // Update active filters
            const newActiveFilters = doc.querySelector('#activeFilters');
            const currentActiveFilters = document.querySelector('#activeFilters');
            if (newActiveFilters && currentActiveFilters) {
                currentActiveFilters.innerHTML = newActiveFilters.innerHTML;
            }
            
            // Reinitialize product interactions for the new content
            initProductInteractions();
        })
        .catch(error => console.error('Error fetching products:', error));
}

function initSubcategoryToggles() {
    // Get all toggle elements
    const toggles = document.querySelectorAll('.toggle-subcategory');
    
    // Add click event to each toggle
    toggles.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            e.stopPropagation(); // Prevent event bubbling to parent
            
            // Toggle active class for the icon rotation
            this.classList.toggle('active');
            
            // Find the parent category item
            const categoryItem = this.closest('.category-item');
            
            // Find the subcategory wrapper to toggle
            const subcategoryWrapper = categoryItem.querySelector('.subcategory-wrapper');
            
            // Toggle display of subcategory wrapper with animation
            if (subcategoryWrapper.style.display === 'flex' || getComputedStyle(subcategoryWrapper).display === 'flex') {
                // Slide up animation
                const height = subcategoryWrapper.scrollHeight;
                subcategoryWrapper.style.height = height + 'px';
                
                // Trigger reflow
                subcategoryWrapper.offsetHeight;
                
                // Start transition
                subcategoryWrapper.style.height = '0';
                subcategoryWrapper.style.opacity = '0';
                subcategoryWrapper.style.marginBottom = '0';
                subcategoryWrapper.style.transform = 'translateY(-10px)';
                
                setTimeout(() => {
                    subcategoryWrapper.style.display = 'none';
                    // Reset the parent category style
                    categoryItem.querySelector('.category').style.borderRadius = '12px';
                }, 300);
            } else {
                // Change the parent category border radius
                categoryItem.querySelector('.category').style.borderRadius = '12px 12px 0 0';
                
                // Slide down animation
                subcategoryWrapper.style.display = 'flex';
                subcategoryWrapper.style.height = '0';
                subcategoryWrapper.style.opacity = '0';
                subcategoryWrapper.style.marginBottom = '10px';
                subcategoryWrapper.style.transform = 'translateY(-10px)';
                
                // Trigger reflow
                subcategoryWrapper.offsetHeight;
                
                // Start transition
                const height = subcategoryWrapper.scrollHeight;
                subcategoryWrapper.style.height = height + 'px';
                subcategoryWrapper.style.opacity = '1';
                subcategoryWrapper.style.marginBottom = '10px';
                subcategoryWrapper.style.transform = 'translateY(0)';
                
                setTimeout(() => {
                    subcategoryWrapper.style.height = 'auto';
                }, 300);
            }
        });
    });
    
    // Add click event to the whole category div as well
    const categories = document.querySelectorAll('.category');
    categories.forEach(category => {
        category.addEventListener('click', function() {
            // Trigger click on the toggle icon
            const toggle = this.querySelector('.toggle-subcategory');
            if (toggle) {
                toggle.click();
            }
        });
    });
}

/**
 * Initialize product interactions (quick view, wishlist, etc.)
 */
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

/**
 * Initialize newsletter subscription
 */
function initNewsletter() {
    const newsletterForm = document.getElementById('newsletterForm');
    
    if (newsletterForm) {
        newsletterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const emailInput = this.querySelector('input[type="email"]');
            const email = emailInput.value.trim();
            
            if (email) {
                // In a real scenario, this would submit to the server
                // For now, just show a success message
                emailInput.value = '';
                
                // Show success message
                const toast = document.createElement('div');
                toast.className = 'toast show';
                toast.textContent = 'Thank you for subscribing to our newsletter!';
                document.body.appendChild(toast);
                
                setTimeout(() => {
                    toast.className = 'toast';
                    setTimeout(() => {
                        toast.remove();
                    }, 300);
                }, 3000);
        }
    });
}
}