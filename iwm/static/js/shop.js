/**
 * Shop page functionality
 * Handles filtering, sorting, and product interactions with URL-based filtering
 */

document.addEventListener("DOMContentLoaded", function() {
    // Initialize all components
    initPriceRange();
    initFilters();
    initSubcategoryToggles();
    
    // Initialize URL parameters from current URL
    initFromURL();
    
    // Check if we're on search page and add 'data-id' attributes if missing
    ensureProductIds();
    
    // Update cart and wishlist count badges
    updateWishlistCount();
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
    // Set color filter from URL
    const color = urlParams.get('color');
    if (color) {
        const colorRadio = document.querySelector(`.color-options input[value="${color}"]`);
        if (colorRadio) colorRadio.checked = true;
    }

    // Set size filter from URL
    const size = urlParams.get('size');
    if (size) {
        const sizeSelect = document.querySelector('.size-filter select');
        if (sizeSelect) sizeSelect.value = size;
    }

    // Set brand filter from URL
    const brand = urlParams.get('brand');
    if (brand) {
        const brandSelect = document.querySelector('.brand-filter select');
        if (brandSelect) brandSelect.value = brand;
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
    const colorFilters = document.querySelectorAll(".color-options input[type='radio']");
    const sizeFilter = document.querySelector(".size-filter select");
    const brandFilter = document.querySelector(".brand-filter select");
    
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
    
    colorFilters.forEach((color) => {
        color.addEventListener("change", function () {
            const urlParams = new URLSearchParams(window.location.search);
            urlParams.set("color", this.value);
            updateURL(urlParams);
        });
    });

    // Handle size selection
    if (sizeFilter) {
        sizeFilter.addEventListener("change", function () {
            const urlParams = new URLSearchParams(window.location.search);
            if (this.value !== "all") {
                urlParams.set("size", this.value);
            } else {
                urlParams.delete("size");
            }
            updateURL(urlParams);
        });
    }

    // Handle brand selection
    if (brandFilter) {
        brandFilter.addEventListener("change", function () {
            const urlParams = new URLSearchParams(window.location.search);
            if (this.value !== "all") {
                urlParams.set("brand", this.value);
            } else {
                urlParams.delete("brand");
            }
            updateURL(urlParams);
        });}

    // Reset all filters
    if (resetAllButton) {
    resetAllButton.addEventListener('click', function() {
        window.location.href = '/search/';
    });
    }
}

function updateURL(urlParams) {
    let currentPath = window.location.pathname;

    // Ensure we always redirect to /search/ when filters are applied
    if (currentPath.startsWith('/shop/')) {
        currentPath = currentPath.replace('/shop/', '/search/');
    } else if (!currentPath.startsWith('/search/')) {
        currentPath = '/search/'; // Default to /search/ if not already there
    }

    const newURL = `${currentPath}?${urlParams.toString()}`;
    window.history.pushState({}, '', newURL);
    
    // Call fetchProducts if you have AJAX-based content update
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
