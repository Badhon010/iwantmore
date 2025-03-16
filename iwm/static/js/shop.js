/**
 * Shop page functionality
 * Handles filtering, sorting, and product interactions
 */

document.addEventListener("DOMContentLoaded", function() {
    // Initialize filters
    initFilters();
    
    // Initialize product interactions
    initProductInteractions();
});

/**
 * Initialize filtering and sorting functionality
 */
function initFilters() {
    const categoryFilter = document.getElementById('categoryFilter');
    const sortFilter = document.getElementById('sortFilter');
    const searchInput = document.getElementById('searchInput');
    const activeFilters = document.getElementById('activeFilters');
    const productGrid = document.getElementById('productGrid');
    
    // Track active filters
    const activeFilterState = {
        category: 'all',
        sort: 'newest',
        search: ''
    };
    
    // Category filter change event
    if (categoryFilter) {
        categoryFilter.addEventListener('change', function() {
            activeFilterState.category = this.value;
            updateActiveFilters();
            applyFilters();
        });
    }
    
    // Sort filter change event
    if (sortFilter) {
        sortFilter.addEventListener('change', function() {
            activeFilterState.sort = this.value;
            updateActiveFilters();
            applyFilters();
        });
    }
    
    // Search input event
    if (searchInput) {
        // Debounce search to avoid too many filter operations while typing
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
    
    /**
     * Update the active filters display
     */
    function updateActiveFilters() {
        if (!activeFilters) return;
        
        activeFilters.innerHTML = '';
        
        // Add category filter tag if not "all"
        if (activeFilterState.category !== 'all') {
            const categoryName = categoryFilter.options[categoryFilter.selectedIndex].text;
            addFilterTag('Category: ' + categoryName, () => {
                categoryFilter.value = 'all';
                activeFilterState.category = 'all';
                updateActiveFilters();
                applyFilters();
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
        activeFilters.style.display = activeFilters.children.length > 0 ? 'flex' : 'none';
    }
    
    /**
     * Add a filter tag to the active filters area
     */
    function addFilterTag(text, removeCallback) {
        const tag = document.createElement('div');
        tag.className = 'filter-tag';
        tag.innerHTML = `
            ${text}
            <span class="remove-filter">&times;</span>
        `;
        
        tag.querySelector('.remove-filter').addEventListener('click', removeCallback);
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
            // Apply category filter
            const categoryMatch = activeFilterState.category === 'all' || 
                                  product.dataset.category === activeFilterState.category;
            
            // Apply search filter
            let searchMatch = true;
            if (activeFilterState.search) {
                const productName = product.querySelector('.product-name').textContent.toLowerCase();
                const productCategory = product.querySelector('.product-category')?.textContent.toLowerCase() || '';
                searchMatch = productName.includes(activeFilterState.search) || 
                              productCategory.includes(activeFilterState.search);
            }
            
            // Show or hide product based on filters
            if (categoryMatch && searchMatch) {
                product.style.display = '';
                visibleCount++;
            } else {
                product.style.display = 'none';
            }
        });
        
        // Apply sorting
        sortProducts(activeFilterState.sort);
        
        // Show no results message if needed
        const noProductsContainer = document.querySelector('.no-products');
        if (noProductsContainer) {
            if (visibleCount === 0) {
                if (!productGrid.querySelector('.no-results-message')) {
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
                const noResults = productGrid.querySelector('.no-results-message');
                if (noResults) {
                    noResults.remove();
                }
            }
        }
    }
    
    /**
     * Sort products based on selected sort option
     */
    function sortProducts(sortOption) {
        if (!productGrid) return;
        
        const products = Array.from(productGrid.querySelectorAll('.product-item'));
        
        products.sort((a, b) => {
            // Get the relevant data for sorting
            const aPrice = parseFloat(a.querySelector('.product-price').textContent.trim().replace('৳', ''));
            const bPrice = parseFloat(b.querySelector('.product-price').textContent.trim().replace('৳', ''));
            
            switch (sortOption) {
                case 'price-low':
                    return aPrice - bPrice;
                case 'price-high':
                    return bPrice - aPrice;
                case 'rating':
                    const aRating = a.querySelectorAll('.star i.fas.fa-star').length;
                    const bRating = b.querySelectorAll('.star i.fas.fa-star').length;
                    return bRating - aRating;
                default: // newest or any other (use data-id or just keep original order)
                    return 0;
            }
        });
        
        // Re-append in sorted order
        products.forEach(product => {
            productGrid.appendChild(product);
        });
    }
    
    /**
     * Reset all filters to default state
     */
    function resetAllFilters() {
        if (categoryFilter) categoryFilter.value = 'all';
        if (sortFilter) sortFilter.value = 'newest';
        if (searchInput) searchInput.value = '';
        
        activeFilterState.category = 'all';
        activeFilterState.sort = 'newest';
        activeFilterState.search = '';
        
        updateActiveFilters();
        applyFilters();
    }
    
    // Initial setup
    updateActiveFilters();
}

/**
 * Initialize product interactions (add to cart, wishlist, etc.)
 */
function initProductInteractions() {
    // Add to cart button event
    const addToCartButtons = document.querySelectorAll('.add-to-cart');
    addToCartButtons.forEach(button => {
      button.addEventListener('click', function() {
            const productId = this.dataset.productId;
            addToCart(productId);
            
            // Visual feedback
            this.classList.add('added');
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-check"></i> Added';
            
            setTimeout(() => {
                this.classList.remove('added');
                this.innerHTML = originalText;
            }, 1500);
      });
    });
    
    // Quick action buttons
    const quickActionButtons = document.querySelectorAll('.quick-action-btn');
    quickActionButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.stopPropagation(); // Prevent event bubbling
            
            const action = this.getAttribute('title');
            if (action === 'Add to wishlist') {
                // Toggle heart icon
                const icon = this.querySelector('i');
                if (icon.classList.contains('far')) {
                    icon.classList.replace('far', 'fas');
                    this.style.color = '#ff6b6b';
                } else {
                    icon.classList.replace('fas', 'far');
                    this.style.color = '';
                }
            } else if (action === 'Quick view') {
                // Show quick view modal (to be implemented)
                alert('Quick view not implemented yet');
            }
    });
  });
}

/**
 * Add a product to the cart
 */
function addToCart(productId) {
    console.log('Adding product to cart:', productId);
    // In a real implementation, this would make an AJAX request to add the product to the cart
    // For now, we'll just show an alert
    // alert('Product added to cart!');
    
    // Update cart icon (example implementation)
    const cartIcon = document.querySelector('#cart i');
    if (cartIcon) {
        cartIcon.classList.add('pulse');
        setTimeout(() => {
            cartIcon.classList.remove('pulse');
        }, 1000);
    }
}
  