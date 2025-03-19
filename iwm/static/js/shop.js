/**
 * Shop page functionality
 * Handles filtering, sorting, and product interactions
 */

document.addEventListener("DOMContentLoaded", function() {
    // Price range slider elements
    const minPriceSlider = document.getElementById('priceSliderMin');
    const maxPriceSlider = document.getElementById('priceSliderMax');
    const minPriceInput = document.getElementById('priceMin');
    const maxPriceInput = document.getElementById('priceMax');
    const minValue = document.querySelector('.price-min-value');
    const maxValue = document.querySelector('.price-max-value');
    const sliderRange = document.querySelector('.slider-range');
    
    // Initialize search suggestions
    initSearchSuggestions();
    
    if (minPriceSlider && maxPriceSlider && minPriceInput && maxPriceInput) {
        // Set initial values and ranges
        const minPrice = 0;
        const maxPrice = 10000;
        let currentMinPrice = parseInt(minPriceInput.value || minPrice);
        let currentMaxPrice = parseInt(maxPriceInput.value || maxPrice);
        
        // Initialize sliders with current values
        minPriceSlider.value = currentMinPrice;
        maxPriceSlider.value = currentMaxPrice;
        
        // Update slider range on load
        updateSliderRange();
        
        // Update min slider input and display
        minPriceSlider.addEventListener('input', function() {
            // Ensure min doesn't exceed max - 100
            currentMinPrice = Math.min(parseInt(this.value), currentMaxPrice - 100);
            minPriceInput.value = currentMinPrice;
            minValue.textContent = '৳' + currentMinPrice.toLocaleString();
            
            // Update min slider position if it was constrained
            if (parseInt(this.value) !== currentMinPrice) {
                this.value = currentMinPrice;
            }
            
            updateSliderRange();
        });
        
        // Update max slider input and display
        maxPriceSlider.addEventListener('input', function() {
            // Ensure max doesn't go below min + 100
            currentMaxPrice = Math.max(parseInt(this.value), currentMinPrice + 100);
            maxPriceInput.value = currentMaxPrice;
            maxValue.textContent = '৳' + currentMaxPrice.toLocaleString();
            
            // Update max slider position if it was constrained
            if (parseInt(this.value) !== currentMaxPrice) {
                this.value = currentMaxPrice;
            }
            
            updateSliderRange();
        });
        
        // Update min slider when input changes
        minPriceInput.addEventListener('change', function() {
            const newMinVal = parseInt(this.value || minPrice);
            currentMinPrice = Math.max(minPrice, Math.min(newMinVal, currentMaxPrice - 100));
            this.value = currentMinPrice;
            minPriceSlider.value = currentMinPrice;
            minValue.textContent = '৳' + currentMinPrice.toLocaleString();
            updateSliderRange();
        });
        
        // Update max slider when input changes
        maxPriceInput.addEventListener('change', function() {
            const newMaxVal = parseInt(this.value || maxPrice);
            currentMaxPrice = Math.min(maxPrice, Math.max(newMaxVal, currentMinPrice + 100));
            this.value = currentMaxPrice;
            maxPriceSlider.value = currentMaxPrice;
            maxValue.textContent = '৳' + currentMaxPrice.toLocaleString();
            updateSliderRange();
        });
        
        // Update slider range visual cue
        function updateSliderRange() {
            if (sliderRange) {
                const minPercent = (currentMinPrice / maxPrice) * 100;
                const maxPercent = (currentMaxPrice / maxPrice) * 100;
                
                // Position the range indicator to show only between min and max values
                sliderRange.style.left = minPercent + '%';
                sliderRange.style.width = (maxPercent - minPercent) + '%';
                
                // Make sure the track and range are properly displayed
                document.querySelector('.slider-track').style.background = '#e0e0e0';
                sliderRange.style.background = 'linear-gradient(90deg, var(--btn-bg) 0%, #ff4081 100%)';
                
                // Add visual feedback by changing thumb colors
                minPriceSlider.style.zIndex = parseInt(minPriceSlider.value) > 10 ? "5" : "4";
                maxPriceSlider.style.zIndex = parseInt(maxPriceSlider.value) < maxPrice - 10 ? "5" : "4";
            }
        }
        
        // Initialize displays and range
        minValue.textContent = '৳' + currentMinPrice.toLocaleString();
        maxValue.textContent = '৳' + currentMaxPrice.toLocaleString();
        
        // Ensure range is displayed correctly on page load
        updateSliderRange();

        // Make sure thumbs are on top of track
        minPriceSlider.style.zIndex = "5";
        maxPriceSlider.style.zIndex = "5";
    }

    // Initialize filters
    initFilters();
    
    // Initialize product interactions
    initProductInteractions();
    
    // Initialize newsletter
    initNewsletter();
    
    // Initialize subcategory toggles
    initSubcategoryToggles();
});

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
    
    // Show first category's subcategories by default if none are open
    // Uncomment this if you want one category to be expanded by default
    /*
    setTimeout(() => {
        const anyOpen = document.querySelector('.toggle-subcategory.active');
        if (!anyOpen && document.querySelectorAll('.category-item').length > 0) {
            document.querySelector('.category-item:first-child .toggle-subcategory').click();
        }
    }, 500);
    */
}

function initFilters() {
    // Filter elements
    const allCategoriesCheckbox = document.getElementById('allCategories');
    const allSubcategoriesCheckbox = document.getElementById('allSubcategories');
    const categoryCheckboxes = document.querySelectorAll('.category-checkbox');
    const subcategoryCheckboxes = document.querySelectorAll('.subcategory-checkbox');
    const sortFilter = document.getElementById('sortFilter');
    const searchInput = document.getElementById('searchInput');
    const priceMinInput = document.getElementById('priceMin');
    const priceMaxInput = document.getElementById('priceMax');
    const applyPriceButton = document.getElementById('applyPriceFilter');
    const stockRadios = document.querySelectorAll('input[name="stock"]');
    const discountFilter = document.getElementById('discountFilter');
    const featuredFilter = document.getElementById('featuredFilter');
    const resetAllButton = document.getElementById('resetAllFilters');
    
    // Results containers
    const activeFilters = document.getElementById('activeFilters');
    const productGrid = document.getElementById('productGrid');
    const productCountElement = document.getElementById('productCount');
    
    // Track active filters
    const activeFilterState = {
        categories: new Set(['all']),
        subcategories: new Set(['all']),
        sort: 'newest',
        search: '',
        priceMin: '',
        priceMax: '',
        stock: 'all',
        discount: false,
        featured: false
    };
    
    // Category checkbox events
    if (allCategoriesCheckbox) {
        allCategoriesCheckbox.addEventListener('change', function() {
            if (this.checked) {
                activeFilterState.categories.clear();
                activeFilterState.categories.add('all');
                categoryCheckboxes.forEach(cb => cb.checked = false);
            } else {
                this.checked = true; // Prevent unchecking "All"
            }
            updateActiveFilters();
            applyFilters();
        });
    }
    
    categoryCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            if (this.checked) {
                activeFilterState.categories.delete('all');
                activeFilterState.categories.add(this.value);
                if (allCategoriesCheckbox) allCategoriesCheckbox.checked = false;
            } else {
                activeFilterState.categories.delete(this.value);
                if (activeFilterState.categories.size === 0) {
                    activeFilterState.categories.add('all');
                    if (allCategoriesCheckbox) allCategoriesCheckbox.checked = true;
                }
            }
            updateActiveFilters();
            applyFilters();
        });
    });
    
    // Subcategory checkbox events
    if (allSubcategoriesCheckbox) {
        allSubcategoriesCheckbox.addEventListener('change', function() {
            if (this.checked) {
                activeFilterState.subcategories.clear();
                activeFilterState.subcategories.add('all');
                subcategoryCheckboxes.forEach(cb => cb.checked = false);
            } else {
                this.checked = true; // Prevent unchecking "All"
            }
            updateActiveFilters();
            applyFilters();
        });
    }
    
    subcategoryCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            if (this.checked) {
                activeFilterState.subcategories.delete('all');
                activeFilterState.subcategories.add(this.value);
                if (allSubcategoriesCheckbox) allSubcategoriesCheckbox.checked = false;
            } else {
                activeFilterState.subcategories.delete(this.value);
                if (activeFilterState.subcategories.size === 0) {
                    activeFilterState.subcategories.add('all');
                    if (allSubcategoriesCheckbox) allSubcategoriesCheckbox.checked = true;
                }
            }
            updateActiveFilters();
            applyFilters();
        });
    });
    
    // Sort filter change event
    if (sortFilter) {
        console.log('Sort filter found:', sortFilter);
        
        sortFilter.addEventListener('change', function() {
            const selectedSort = this.value;
            console.log('Sort changed to:', selectedSort);
            
            // Update the active filter state
            activeFilterState.sort = selectedSort;
            updateActiveFilters();
            
            // Apply the sorting directly - no need to reapply all filters
            sortProducts(selectedSort);
        });
        
        // Trigger initial sort on page load
        if (sortFilter.value) {
            console.log('Initializing with sort:', sortFilter.value);
            activeFilterState.sort = sortFilter.value;
            // Apply initial sort after a short delay to ensure DOM is ready
            setTimeout(() => {
                sortProducts(sortFilter.value);
            }, 100);
        }
    } else {
        console.warn('Sort filter element not found in the DOM');
    }
    
    // Search input event with debounce
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                activeFilterState.search = this.value.trim().toLowerCase();
                updateActiveFilters();
                applyFilters();
            }, 300);
        });
    }
    
    // Price range filter
    if (applyPriceButton) {
        applyPriceButton.addEventListener('click', function() {
            activeFilterState.priceMin = priceMinInput.value || '';
            activeFilterState.priceMax = priceMaxInput.value || '';
            updateActiveFilters();
            applyFilters();
        });
    }
    
    // Stock radio buttons
    if (stockRadios.length) {
        stockRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                activeFilterState.stock = this.value;
                updateActiveFilters();
                applyFilters();
            });
        });
    }
    
    // Discount checkbox
    if (discountFilter) {
        discountFilter.addEventListener('change', function() {
            activeFilterState.discount = this.checked;
            updateActiveFilters();
            applyFilters();
        });
    }
    
    // Featured checkbox
    if (featuredFilter) {
        featuredFilter.addEventListener('change', function() {
            activeFilterState.featured = this.checked;
            updateActiveFilters();
            applyFilters();
        });
    }
    
    // Reset all filters
    if (resetAllButton) {
        resetAllButton.addEventListener('click', function() {
            resetAllFilters();
        });
    }
    
    /**
     * Update the active filters display
     */
    function updateActiveFilters() {
        if (!activeFilters) return;
        
        activeFilters.innerHTML = '';
        
        // Add category filter tags
        if (!activeFilterState.categories.has('all')) {
            Array.from(activeFilterState.categories).forEach(categoryValue => {
                const categoryLabel = document.querySelector(`.category-checkbox[value="${categoryValue}"] + .checkbox-checkmark + .checkbox-label`).textContent;
                addFilterTag('Category: ' + categoryLabel, () => {
                    const checkbox = document.querySelector(`.category-checkbox[value="${categoryValue}"]`);
                    checkbox.checked = false;
                    activeFilterState.categories.delete(categoryValue);
                    if (activeFilterState.categories.size === 0) {
                        activeFilterState.categories.add('all');
                        if (allCategoriesCheckbox) allCategoriesCheckbox.checked = true;
                    }
                    updateActiveFilters();
                    applyFilters();
                });
            });
        }
        
        // Add subcategory filter tags
        if (!activeFilterState.subcategories.has('all')) {
            Array.from(activeFilterState.subcategories).forEach(subcategoryValue => {
                const subcategoryLabel = document.querySelector(`.subcategory-checkbox[value="${subcategoryValue}"] + .checkbox-checkmark + .checkbox-label`).textContent;
                addFilterTag('Subcategory: ' + subcategoryLabel, () => {
                    const checkbox = document.querySelector(`.subcategory-checkbox[value="${subcategoryValue}"]`);
                    checkbox.checked = false;
                    activeFilterState.subcategories.delete(subcategoryValue);
                    if (activeFilterState.subcategories.size === 0) {
                        activeFilterState.subcategories.add('all');
                        if (allSubcategoriesCheckbox) allSubcategoriesCheckbox.checked = true;
                    }
                updateActiveFilters();
                applyFilters();
                });
            });
        }
        
        // Add sort filter tag if not default
        if (activeFilterState.sort !== 'newest') {
            const sortName = sortFilter.options[sortFilter.selectedIndex].text;
            addFilterTag('Sort: ' + sortName, () => {
                sortFilter.value = 'newest';
                activeFilterState.sort = 'newest';
                updateActiveFilters();
                applyFilters();
            });
        }
        
        // Add price range filter tags if set
        if (activeFilterState.priceMin || activeFilterState.priceMax) {
            let priceText = 'Price: ';
            if (activeFilterState.priceMin && activeFilterState.priceMax) {
                priceText += '৳' + activeFilterState.priceMin + ' - ৳' + activeFilterState.priceMax;
            } else if (activeFilterState.priceMin) {
                priceText += 'Min ৳' + activeFilterState.priceMin;
            } else if (activeFilterState.priceMax) {
                priceText += 'Max ৳' + activeFilterState.priceMax;
            }
            
            addFilterTag(priceText, () => {
                priceMinInput.value = '';
                priceMaxInput.value = '';
                activeFilterState.priceMin = '';
                activeFilterState.priceMax = '';
                updateActiveFilters();
                applyFilters();
            });
        }
        
        // Add stock filter tag if not "all"
        if (activeFilterState.stock !== 'all') {
            const stockText = activeFilterState.stock === 'in-stock' ? 'In Stock' : 'Out of Stock';
            addFilterTag('Availability: ' + stockText, () => {
                document.querySelector('input[name="stock"][value="all"]').checked = true;
                activeFilterState.stock = 'all';
                updateActiveFilters();
                applyFilters();
            });
        }
        
        // Add discount filter tag if enabled
        if (activeFilterState.discount) {
            addFilterTag('On Sale', () => {
                discountFilter.checked = false;
                activeFilterState.discount = false;
                updateActiveFilters();
                applyFilters();
            });
        }
        
        // Add featured filter tag if enabled
        if (activeFilterState.featured) {
            addFilterTag('Featured Products', () => {
                featuredFilter.checked = false;
                activeFilterState.featured = false;
                updateActiveFilters();
                applyFilters();
            });
        }
        
        // Add search filter tag if exists
        if (activeFilterState.search) {
            addFilterTag('Search: ' + activeFilterState.search, () => {
                searchInput.value = '';
                activeFilterState.search = '';
                updateActiveFilters();
                applyFilters();
            });
        }
        
        // Show or hide the filter section based on if there are any active filters
        activeFilters.parentElement.style.display = activeFilters.children.length > 0 ? 'block' : 'none';
    }
    
    /**
     * Add a filter tag to the active filters area
     */
    function addFilterTag(text, removeCallback) {
        const tag = document.createElement('div');
        tag.className = 'filter-tag';
        tag.innerHTML = `
            ${text}
            <span class="remove">×</span>
        `;
        
        tag.querySelector('.remove').addEventListener('click', removeCallback);
        activeFilters.appendChild(tag);
    }
    
    /**
     * Apply all active filters and sorting to the product grid
     */
    function applyFilters() {
        if (!productGrid) return;
        
        const products = productGrid.querySelectorAll('.product-item');
        let visibleCount = 0;
        
        products.forEach(product => {
            // Get product data from dataset
            const productCategory = product.dataset.category || '';
            const productSubcategory = product.dataset.subcategory || '';
            const productPrice = parseFloat(product.dataset.price) || 0;
            const productStock = parseInt(product.dataset.stock) || 0;
            const productFeatured = product.dataset.featured === 'true';
            const productDiscounted = product.dataset.discounted === 'true';
            
            // Apply category filter
            const categoryMatch = activeFilterState.categories.has('all') || 
                                activeFilterState.categories.has(productCategory);
            
            // Apply subcategory filter
            const subcategoryMatch = activeFilterState.subcategories.has('all') || 
                                   activeFilterState.subcategories.has(productSubcategory);
            
            // Apply price range filter
            let priceMatch = true;
            if (activeFilterState.priceMin) {
                priceMatch = priceMatch && productPrice >= parseFloat(activeFilterState.priceMin);
            }
            if (activeFilterState.priceMax) {
                priceMatch = priceMatch && productPrice <= parseFloat(activeFilterState.priceMax);
            }
            
            // Apply stock filter
            let stockMatch = true;
            if (activeFilterState.stock === 'in-stock') {
                stockMatch = productStock > 0;
            } else if (activeFilterState.stock === 'out-of-stock') {
                stockMatch = productStock === 0;
            }
            
            // Apply discount filter
            let discountMatch = true;
            if (activeFilterState.discount) {
                discountMatch = productDiscounted;
            }
            
            // Apply featured filter
            let featuredMatch = true;
            if (activeFilterState.featured) {
                featuredMatch = productFeatured;
            }
            
            // Apply search filter
            let searchMatch = true;
            if (activeFilterState.search) {
                const productName = product.querySelector('.product-name').textContent.toLowerCase();
                const productCategoryText = product.querySelector('.product-category')?.textContent.toLowerCase() || '';
                searchMatch = productName.includes(activeFilterState.search) || 
                             productCategoryText.includes(activeFilterState.search);
            }
            
            // Show or hide product based on all filters
            if (categoryMatch && subcategoryMatch && priceMatch && stockMatch && 
                discountMatch && featuredMatch && searchMatch) {
                product.style.display = '';
                visibleCount++;
            } else {
                product.style.display = 'none';
            }
        });
        
        // Update product count display
        if (productCountElement) {
            productCountElement.textContent = visibleCount;
        }
        
        // Apply sorting
        sortProducts(activeFilterState.sort);
        
        // Show no results message if needed
        const noResultsMessage = document.querySelector('.no-results-message');
        
            if (visibleCount === 0) {
            if (!noResultsMessage) {
                    const noResults = document.createElement('div');
                    noResults.className = 'no-products no-results-message';
                    noResults.innerHTML = `
                        <i class="fas fa-search"></i>
                        <h3>No products found</h3>
                        <p>Try adjusting your filters or search criteria</p>
                        <button class="reset-filters">Clear all filters</button>
                    `;
                    productGrid.appendChild(noResults);
                    
                    noResults.querySelector('.reset-filters').addEventListener('click', resetAllFilters);
                }
            } else {
            if (noResultsMessage) {
                noResultsMessage.remove();
            }
        }
    }
    
    /**
     * Sort products based on selected sort option
     */
    function sortProducts(sortOption) {
        if (!productGrid) return;
        
        console.log('Sorting products by:', sortOption);
        
        const products = Array.from(productGrid.querySelectorAll('.product-item'));
        
        // Add index attributes to preserve original order for "newest" sort
        products.forEach((product, index) => {
            if (!product.dataset.originalIndex) {
                product.dataset.originalIndex = index;
            }
        });
        
        const visibleProducts = products.filter(product => product.style.display !== 'none');
        
        console.log('Total products:', products.length, 'Visible products:', visibleProducts.length);
        
        // Use specific sorting logic based on the selected option
        visibleProducts.sort((a, b) => {
            switch (sortOption) {
                case 'price-low':
                    // Sort by price low to high
                    const aPrice = parseFloat(a.dataset.price) || 0;
                    const bPrice = parseFloat(b.dataset.price) || 0;
                    return aPrice - bPrice;
                    
                case 'price-high':
                    // Sort by price high to low
                    const aHighPrice = parseFloat(a.dataset.price) || 0;
                    const bHighPrice = parseFloat(b.dataset.price) || 0;
                    return bHighPrice - aHighPrice;
                    
                case 'rating':
                    // Sort by rating high to low
                    // First try to get star elements with fas class (filled stars)
                    const aStars = a.querySelectorAll('.star .fas.fa-star, .star .fas.fa-star-half-alt').length;
                    const bStars = b.querySelectorAll('.star .fas.fa-star, .star .fas.fa-star-half-alt').length;
                    
                    // If no stars found, try alternative selectors
                    const aRating = aStars || a.querySelectorAll('.product-rating .fas.fa-star, .product-rating .fas.fa-star-half-alt').length;
                    const bRating = bStars || b.querySelectorAll('.product-rating .fas.fa-star, .product-rating .fas.fa-star-half-alt').length;
                    
                    console.log('Comparing ratings:', aRating, bRating);
                    
                    // If ratings are equal, sort by number of reviews
                    if (aRating === bRating) {
                        const aReviewText = a.querySelector('.review-count')?.textContent || '';
                        const bReviewText = b.querySelector('.review-count')?.textContent || '';
                        
                        const aReviews = parseInt(aReviewText.match(/\d+/) || 0);
                        const bReviews = parseInt(bReviewText.match(/\d+/) || 0);
                        
                        console.log('Comparing reviews:', aReviews, bReviews);
                        return bReviews - aReviews;
                    }
                    return bRating - aRating;
                    
                case 'newest':
                default:
                    // Check if data-date attribute exists
                    if (a.dataset.date && b.dataset.date) {
                        // Sort by date (newest first)
                        const aDate = parseInt(a.dataset.date) || 0;
                        const bDate = parseInt(b.dataset.date) || 0;
                        console.log('Comparing dates:', aDate, bDate);
                        // Higher timestamp = newer product
                        return bDate - aDate;
                    } else {
                        // Fallback to the original index 
                        const aIndex = parseInt(a.dataset.originalIndex) || 0;
                        const bIndex = parseInt(b.dataset.originalIndex) || 0;
                        return aIndex - bIndex;
                    }
            }
        });
        
        // Create a document fragment to hold the sorted products
        const fragment = document.createDocumentFragment();
        
        // First, add all hidden products to preserve their position
        const hiddenProducts = products.filter(product => product.style.display === 'none');
        hiddenProducts.forEach(product => {
            fragment.appendChild(product);
        });
        
        // Then add all visible products in their sorted order
        visibleProducts.forEach(product => {
            fragment.appendChild(product);
        });
        
        // Clear the product grid
        while (productGrid.firstChild) {
            productGrid.removeChild(productGrid.firstChild);
        }
        
        // Add all products back in their correct order
        productGrid.appendChild(fragment);
        
        console.log('Sorting complete');
    }
    
    /**
     * Reset all filters to default state
     */
    function resetAllFilters() {
        if (allCategoriesCheckbox) allCategoriesCheckbox.checked = true;
        if (allSubcategoriesCheckbox) allSubcategoriesCheckbox.checked = true;
        categoryCheckboxes.forEach(cb => cb.checked = false);
        subcategoryCheckboxes.forEach(cb => cb.checked = false);
        
        activeFilterState.categories.clear();
        activeFilterState.categories.add('all');
        activeFilterState.subcategories.clear();
        activeFilterState.subcategories.add('all');
        
        if (sortFilter) sortFilter.value = 'newest';
        if (searchInput) searchInput.value = '';
        if (priceMinInput) priceMinInput.value = '';
        if (priceMaxInput) priceMaxInput.value = '';
        if (stockRadios.length) {
            document.querySelector('input[name="stock"][value="all"]').checked = true;
        }
        if (discountFilter) discountFilter.checked = false;
        if (featuredFilter) featuredFilter.checked = false;
        
        updateActiveFilters();
        applyFilters();
    }
    
    // Initial setup
    updateActiveFilters();
    applyFilters();

    // No need to apply sorting again here since it's handled in the sortFilter initialization
}

/**
 * Initialize product interactions (quick view, wishlist, etc.)
 */
function initProductInteractions() {
    // Quick action buttons
    const quickActionButtons = document.querySelectorAll('.quick-action-btn');
    quickActionButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.stopPropagation(); // Prevent event bubbling
            
            const action = this.getAttribute('title');
            if (action === 'Add to wishlist') {
                // Toggle heart icon color
                const icon = this.querySelector('i');
                if (icon.style.color === 'red') {
                    icon.style.color = '';
                    showToast('Removed from wishlist');
                } else {
                    icon.style.color = 'red';
                    showToast('Added to wishlist');
                }
            } else if (action === 'Quick view') {
                // Find the product item and get data for quick view modal
                const productItem = this.closest('.product-item');
                const productName = productItem.querySelector('.product-name').textContent;
                const productImage = productItem.querySelector('.product-image').src;
                
                showQuickViewModal({
                    name: productName,
                    image: productImage
                });
            }
    });
  });
    
    // Quick preview hover
    const quickPreviews = document.querySelectorAll('.quick-preview');
    quickPreviews.forEach(preview => {
        preview.addEventListener('click', function() {
            const productItem = this.closest('.product-item');
            const productName = productItem.querySelector('.product-name').textContent;
            const productImage = productItem.querySelector('.product-image').src;
            
            showQuickViewModal({
                name: productName,
                image: productImage
            });
        });
    });
    
    // Add to cart buttons
    const addToCartButtons = document.querySelectorAll('.add-to-cart');
    addToCartButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Display an animation effect (the actual cart functionality will be handled by the link)
            createAddToCartAnimation(e);
        });
    });
    
    /**
     * Create a flying animation when adding to cart
     */
    function createAddToCartAnimation(e) {
        const button = e.currentTarget;
        const rect = button.getBoundingClientRect();
        const startX = rect.left + rect.width / 2;
        const startY = rect.top + rect.height / 2;
        
        // Create the animation element
        const element = document.createElement('div');
        element.className = 'add-to-cart-animation';
        element.style.left = `${startX}px`;
        element.style.top = `${startY}px`;
        document.body.appendChild(element);
        
        // Remove the element after animation completes
        setTimeout(() => {
            element.remove();
        }, 1000);
    }
    
    /**
     * Show a quick view modal with product information
     */
    function showQuickViewModal(product) {
        // Create modal if it doesn't exist
        let modal = document.getElementById('quickViewModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'quickViewModal';
            modal.className = 'quick-view-modal';
            modal.innerHTML = `
                <div class="quick-view-content">
                    <span class="close-modal">&times;</span>
                    <div class="modal-product-image">
                        <img src="${product.image}" alt="${product.name}">
                    </div>
                    <div class="modal-product-info">
                        <h3>${product.name}</h3>
                        <p>Quick preview of this product. Click the button below to view full details.</p>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            
            // Add close functionality
            modal.querySelector('.close-modal').addEventListener('click', () => {
                modal.style.display = 'none';
            });
            
            // Close when clicking outside the modal
            window.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.style.display = 'none';
                }
            });
        } else {
            // Update existing modal with new product info
            modal.querySelector('.modal-product-image img').src = product.image;
            modal.querySelector('.modal-product-image img').alt = product.name;
            modal.querySelector('.modal-product-info h3').textContent = product.name;
        }
        
        // Display the modal
        modal.style.display = 'flex';
    }
    
    /**
     * Show a toast notification
     */
    function showToast(message) {
        let toast = document.getElementById('toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'toast';
            toast.className = 'toast';
            document.body.appendChild(toast);
        }
        
        toast.textContent = message;
        toast.className = 'toast show';
        
        setTimeout(() => {
            toast.className = 'toast';
        }, 3000);
    }
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

function initSearchSuggestions() {
    const searchInput = document.getElementById("searchInput");
    if (!searchInput) return;
    
    // Create suggestions container if it doesn't exist
    let suggestionsContainer = document.getElementById('shop-suggestions');
    if (!suggestionsContainer) {
        suggestionsContainer = document.createElement('div');
        suggestionsContainer.id = 'shop-suggestions';
        suggestionsContainer.className = 'suggestions-dropdown';
        searchInput.parentNode.appendChild(suggestionsContainer);
    }

    function debounce(func, delay) {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    }

    function fetchSuggestions() {
        const query = searchInput.value.trim();
        
        // Hide suggestions when query is too short
        if (query.length < 2) {
            suggestionsContainer.classList.remove("active");
            return;
        }

        // Show loading indicator
        suggestionsContainer.innerHTML = `<div class="empty-suggestions">Searching...</div>`;
        suggestionsContainer.classList.add("active");

        fetch(`/autocomplete/?q=${encodeURIComponent(query)}`)
            .then((response) => response.json())
            .then((data) => {
                if (data.length === 0) {
                    suggestionsContainer.innerHTML = `<div class="empty-suggestions">No results found for "${query}"</div>`;
                    return;
                }

                let suggestionsHtml = "";
                data.forEach((item) => {
                    let icon = '';
                    let detailsHtml = '';
                    
                    // Choose appropriate icon and details based on suggestion type
                    if (item.type === "product") {
                        icon = '<i class="fas fa-tag"></i>';
                        
                        // Format the price with currency
                        const formattedPrice = new Intl.NumberFormat('en-US', {
                            style: 'currency',
                            currency: 'BDT',
                            minimumFractionDigits: 0
                        }).format(item.price);
                        
                        // Add details for product type
                        detailsHtml = `
                            <div style="display: flex; justify-content: space-between; font-size: 12px; color: #666; margin-top: 3px;">
                                <span>${item.category}</span>
                                <span style="color: var(--btn-bg); font-weight: 500;">${formattedPrice}</span>
                            </div>`;
                        
                    } else if (item.type === "category") {
                        icon = '<i class="fas fa-folder"></i>';
                    } else if (item.type === "tag") {
                        icon = '<i class="fas fa-hashtag"></i>';
                    }
                    
                    // Create suggestion item with appropriate styling
                    suggestionsHtml += `
                        <div class="suggestion-item">
                            ${icon}
                            <div style="width: 100%;">
                                <a href="${item.url}">${highlightMatch(item.name, query)}</a>
                                ${detailsHtml}
                            </div>
                        </div>`;
                });
                
                suggestionsContainer.innerHTML = suggestionsHtml;
            })
            .catch((error) => {
                console.error("Error fetching suggestions:", error);
                suggestionsContainer.innerHTML = `<div class="empty-suggestions">Error loading suggestions</div>`;
            });
    }

    // Highlight the matching part of the suggestion
    function highlightMatch(text, query) {
        const regex = new RegExp(`(${query})`, 'gi');
        return text.replace(regex, '<strong>$1</strong>');
    }

    // Show/hide suggestions based on input focus
    searchInput.addEventListener("input", debounce(fetchSuggestions, 300));
    
    searchInput.addEventListener("focus", function() {
        if (this.value.trim().length >= 2) {
            suggestionsContainer.classList.add("active");
        }
    });

    // Add keyboard navigation
    let selectedIndex = -1;
    const navigateSuggestions = (direction) => {
        const items = suggestionsContainer.querySelectorAll('.suggestion-item');
        if (items.length === 0) return;
        
        // Remove current selection
        items.forEach(item => item.classList.remove('selected'));
        
        // Update index
        if (direction === 'down') {
            selectedIndex = (selectedIndex + 1) % items.length;
        } else if (direction === 'up') {
            selectedIndex = (selectedIndex - 1 + items.length) % items.length;
        }
        
        // Apply new selection
        if (selectedIndex >= 0) {
            items[selectedIndex].classList.add('selected');
            items[selectedIndex].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        }
    };
    
    // Handle keyboard events
    searchInput.addEventListener("keydown", function(event) {
        if (!suggestionsContainer.classList.contains('active')) return;
        
        switch (event.key) {
            case "ArrowDown":
                event.preventDefault();
                navigateSuggestions('down');
                break;
            case "ArrowUp":
                event.preventDefault();
                navigateSuggestions('up');
                break;
            case "Enter":
                event.preventDefault();
                const selectedItem = suggestionsContainer.querySelector('.suggestion-item.selected a');
                if (selectedItem) {
                    window.location.href = selectedItem.getAttribute('href');
                } else {
                    // Submit the form if no suggestion is selected
                    this.closest('form').submit();
                }
                break;
            case "Escape":
                suggestionsContainer.classList.remove("active");
                selectedIndex = -1;
                break;
        }
    });

    // Close suggestions when clicking outside
    document.addEventListener("click", function(event) {
        if (!searchInput.contains(event.target) && !suggestionsContainer.contains(event.target)) {
            suggestionsContainer.classList.remove("active");
            selectedIndex = -1;
        }
    });
}
  