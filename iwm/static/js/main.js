const moreSmall = document.getElementById('moreSmall');
const smallDropdown = document.querySelector("#more-link-small .dropdown-menu");
const moreLink = document.getElementById('more-link');
const moreLinkToggle = document.getElementById('moreLinkToggle');
const search = document.getElementById('search');
const innerHeader = document.getElementById('i-h');
const searchBtn = document.getElementById('searchToggle');
const searchInput = document.getElementById("sea");
const clearBtn = document.getElementById("clear-btn");
const suggestionsContainer = document.getElementById('suggestions');
const orderLinks = document.querySelector('.order_links');
const storeToggle = document.getElementById('store');

function setSearchOpen(isOpen) {
    if (!search || !innerHeader || !searchBtn) return;

    search.style.display = isOpen ? 'flex' : 'none';
    innerHeader.style.display = isOpen ? 'none' : 'flex';
    searchBtn.setAttribute('aria-expanded', String(isOpen));

    if (isOpen && searchInput) {
        searchInput.focus();
    }
}

function setToggleState(button, expanded) {
    if (button) {
        button.setAttribute('aria-expanded', String(expanded));
    }
}

setSearchOpen(false);

if (searchBtn) {
    searchBtn.addEventListener("click", (event) => {
        event.stopPropagation();
        setSearchOpen(search.style.display !== 'flex');
    });
}

if (moreSmall && smallDropdown) {
    moreSmall.addEventListener("click", () => {
        const isOpen = smallDropdown.style.display === 'block';
        smallDropdown.style.display = isOpen ? 'none' : 'block';
        setToggleState(moreSmall, !isOpen);
    });
}

if (moreLink && moreLinkToggle) {
    moreLinkToggle.addEventListener("click", (event) => {
        event.stopPropagation();
        const isOpen = moreLink.classList.toggle('open');
        setToggleState(moreLinkToggle, isOpen);
    });
}

if (storeToggle && orderLinks) {
    storeToggle.addEventListener("click", (event) => {
        event.stopPropagation();
        const isOpen = orderLinks.classList.toggle('open');
        setToggleState(storeToggle, isOpen);
    });
}

document.addEventListener("click", (event) => {
    if (search && search.style.display === 'flex' && !search.contains(event.target) && !searchBtn?.contains(event.target)) {
        setSearchOpen(false);
    }

    if (moreLink && !moreLink.contains(event.target)) {
        moreLink.classList.remove('open');
        setToggleState(moreLinkToggle, false);
    }

    if (smallDropdown && moreSmall && !moreSmall.contains(event.target) && !smallDropdown.contains(event.target)) {
        smallDropdown.style.display = 'none';
        setToggleState(moreSmall, false);
    }

    if (orderLinks && !orderLinks.contains(event.target)) {
        orderLinks.classList.remove('open');
        setToggleState(storeToggle, false);
    }
});

document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") {
        return;
    }

    setSearchOpen(false);

    if (moreLink) {
        moreLink.classList.remove('open');
        setToggleState(moreLinkToggle, false);
    }

    if (smallDropdown) {
        smallDropdown.style.display = 'none';
        setToggleState(moreSmall, false);
    }

    if (orderLinks) {
        orderLinks.classList.remove('open');
        setToggleState(storeToggle, false);
    }
});

if (searchInput && clearBtn) {
    searchInput.addEventListener("input", function() {
        clearBtn.style.display = this.value ? "block" : "none";
    });

    clearBtn.addEventListener("click", function() {
        searchInput.value = "";
        clearBtn.style.display = "none";
        searchInput.focus();
    });
}

 

document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("sea");
    const suggestionsContainer = document.getElementById("suggestions");

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
      suggestionsContainer.innerHTML = '';
      const loadingDiv = document.createElement('div');
      loadingDiv.className = 'empty-suggestions';
      loadingDiv.textContent = 'Searching...';
      suggestionsContainer.appendChild(loadingDiv);
      suggestionsContainer.classList.add("active");

      fetch(`/autocomplete/?q=${encodeURIComponent(query)}`)
        .then((response) => response.json())
        .then((data) => {
          if (data.length === 0) {
            suggestionsContainer.innerHTML = '';
            const emptyDiv = document.createElement('div');
            emptyDiv.className = 'empty-suggestions';
            emptyDiv.textContent = `No results found for "${query}"`;
            suggestionsContainer.appendChild(emptyDiv);
            return;
          }

          suggestionsContainer.innerHTML = '';
          data.forEach((item) => {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'suggestion-item';
            const a = document.createElement('a');
            a.href = item.url;
            
            const icon = document.createElement('i');
            if (item.type === "product") {
                icon.className = 'fas fa-tag';
            } else if (item.type === "category") {
                icon.className = 'fas fa-folder';
            } else if (item.type === "tag") {
                icon.className = 'fas fa-hashtag';
            }
            a.appendChild(icon);
            
            const contentDiv = document.createElement('div');
            contentDiv.style.width = '100%';
            
            const nameSpan = document.createElement('span');
            const lowerName = (item.name || '').toLowerCase();
            const lowerQuery = (query || '').toLowerCase();
            const matchIndex = lowerName.indexOf(lowerQuery);
            
            if (matchIndex >= 0 && query.length > 0) {
                const before = item.name.substring(0, matchIndex);
                const match = item.name.substring(matchIndex, matchIndex + query.length);
                const after = item.name.substring(matchIndex + query.length);
                
                nameSpan.appendChild(document.createTextNode(before));
                const strong = document.createElement('strong');
                strong.style.color = 'var(--btn-bg)';
                strong.textContent = match;
                nameSpan.appendChild(strong);
                nameSpan.appendChild(document.createTextNode(after));
            } else {
                nameSpan.textContent = item.name;
            }
            
            contentDiv.appendChild(nameSpan);
            
            if (item.type === "product") {
              const formattedPrice = new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'BDT',
                minimumFractionDigits: 0
              }).format(item.price);
              
              const detailsDiv = document.createElement('div');
              detailsDiv.style.display = 'flex';
              detailsDiv.style.justifyContent = 'space-between';
              detailsDiv.style.fontSize = '12px';
              detailsDiv.style.color = '#666';
              detailsDiv.style.marginTop = '3px';
              
              const catSpan = document.createElement('span');
              catSpan.textContent = item.category;
              
              const priceSpan = document.createElement('span');
              priceSpan.style.color = 'var(--btn-bg)';
              priceSpan.style.fontWeight = '500';
              priceSpan.textContent = formattedPrice;
              
              detailsDiv.appendChild(catSpan);
              detailsDiv.appendChild(priceSpan);
              contentDiv.appendChild(detailsDiv);
            }
            
            a.appendChild(contentDiv);
            itemDiv.appendChild(a);
            suggestionsContainer.appendChild(itemDiv);
          });
        })
        .catch((error) => {
          console.error("Error fetching suggestions:", error);
          suggestionsContainer.innerHTML = '';
          const errorDiv = document.createElement('div');
          errorDiv.className = 'empty-suggestions';
          errorDiv.textContent = 'Error loading suggestions';
          suggestionsContainer.appendChild(errorDiv);
        });
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
            const selectedItem = suggestionsContainer.querySelector('.suggestion-item.selected');
            if (selectedItem) {
                window.location.href = selectedItem.querySelector('a').getAttribute('href');
            } else {
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

});

document.addEventListener("DOMContentLoaded", function() {
    // Update cart and wishlist count badges when page loads
    updateCartCount();
    updateWishlistCount();
    updateOrderCount();
});

// Function to update cart count badge
function updateCartCount() {
    const cartItems = JSON.parse(localStorage.getItem('cartItems')) || [];
    const cartCountBadges = document.querySelectorAll('.cart-count');
    
    if (cartCountBadges.length === 0) return;
    
    const totalItems = cartItems.reduce((total, item) => total + (parseInt(item.quantity) || 1), 0);
    
    cartCountBadges.forEach(badge => {
        badge.textContent = totalItems > 0 ? totalItems : '';
        badge.setAttribute('data-count', totalItems);
    });
}

// Function to update wishlist count badge
function updateWishlistCount() {
    const wishlistItems = JSON.parse(localStorage.getItem('wishlistItems')) || [];
    const wishlistCountBadges = document.querySelectorAll('.wishlist-count');
    
    if (wishlistCountBadges.length === 0) return;
    
    const totalItems = wishlistItems.length;
    
    wishlistCountBadges.forEach(badge => {
        badge.textContent = totalItems > 0 ? totalItems : '';
        badge.setAttribute('data-count', totalItems);
    });
}
// Function to update order count badge
function updateOrderCount() {
    const orderCountBadges = document.querySelectorAll('.order-count');
    if (orderCountBadges.length === 0) return;

    const isLoggedIn = document.body.classList.contains('logged-in');

    if (!isLoggedIn) {
        // Hide badge for logged-out users
        orderCountBadges.forEach(badge => {
            badge.textContent = '';
            badge.setAttribute('data-count', 0);
            badge.style.display = 'none';
        });
        return;
    }

    fetch('/api/order-count/')
        .then(response => {
            if (!response.ok) {
                orderCountBadges.forEach(badge => {
                    badge.textContent = '';
                    badge.setAttribute('data-count', 0);
                    badge.style.display = 'none';
                });
                return null;
            }
            return response.json();
        })
        .then(data => {
            if (!data) return;
            const count = parseInt(data.count || '0');
            updateOrderBadges(count);
        })
        .catch(() => {
            orderCountBadges.forEach(badge => {
                badge.textContent = '';
                badge.setAttribute('data-count', 0);
                badge.style.display = 'none';
            });
        });

    function updateOrderBadges(count) {
        orderCountBadges.forEach(badge => {
            if (count > 0) {
                badge.textContent = count;
                badge.setAttribute('data-count', count);
                badge.style.display = ''; // show badge
            } else {
                badge.textContent = '';
                badge.setAttribute('data-count', 0);
                badge.style.display = 'none'; // hide badge
            }
        });
    }
}

// Function to add item to cart
function addToCart(productId, productName, productPrice, productImage, quantity = 1) {
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
    
    // Add pulse animation to cart icon
    const cartIcon = document.querySelector('.cart i');
    if (cartIcon) {
        cartIcon.classList.add('pulse');
        setTimeout(() => {
            cartIcon.classList.remove('pulse');
        }, 500);
    }
    
    return cartItems;
}

// Alert message handling
document.addEventListener('DOMContentLoaded', function() {
    // Find all close buttons in alert messages
    const closeButtons = document.querySelectorAll('.alert .btn-close');
    
    // Add click event listener to each close button
    closeButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Find the parent alert element
            const alert = this.closest('.alert');
            
            // Add the fade-out class
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            alert.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            
            // Remove the alert after animation completes
            setTimeout(function() {
                alert.remove();
            }, 300);
        });
    });
    
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(function() {
            if (alert && alert.parentNode) {
                alert.style.opacity = '0';
                alert.style.transform = 'translateY(-10px)';
                alert.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                
                setTimeout(function() {
                    if (alert && alert.parentNode) {
                        alert.remove();
                    }
                }, 300);
            }
        }, 5000);
    });
});
