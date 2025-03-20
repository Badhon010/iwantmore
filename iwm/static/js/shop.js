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
});

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
    sortFilter.addEventListener('change', function() {
        const urlParams = new URLSearchParams(window.location.search);
        if (this.value !== 'newest') {
            urlParams.set('sort', this.value);
        } else {
            urlParams.delete('sort');
        }
        updateURL(urlParams);
    });
    
    // Special offers handlers
    discountFilter.addEventListener('change', function() {
        const urlParams = new URLSearchParams(window.location.search);
        if (this.checked) {
            urlParams.set('discount', 'true');
        } else {
            urlParams.delete('discount');
        }
        updateURL(urlParams);
    });
    
    featuredFilter.addEventListener('change', function() {
        const urlParams = new URLSearchParams(window.location.search);
        if (this.checked) {
            urlParams.set('featured', 'true');
        } else {
            urlParams.delete('featured');
        }
        updateURL(urlParams);
    });
    
    // Reset all filters
    resetAllButton.addEventListener('click', function() {
        window.location.href = '/search/';
    });
}

function updateURL(urlParams) {
    const newURL = `/search/?${urlParams.toString()}`;
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
  