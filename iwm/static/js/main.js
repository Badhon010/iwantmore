const title = document.querySelector('.title');
const moreSmall = document.getElementById('moreSmall');
const smallDropdown = document.querySelector("#more-link-small .dropdown-menu");
const search = document.getElementById('search');
const seaBtn = document.getElementById('sea-btn');
const innerHeader = document.getElementById('i-h');
const searchBtn = document.getElementsByClassName('search-btn')[0];
const searchInput = document.getElementById("sea");
const clearBtn = document.getElementById("clear-btn");
const suggestionsContainer = document.getElementById('suggestions');


search.style.display = 'none';
let dropDown = false;

// Toggle the search bar on searchBtn click
searchBtn.addEventListener("click", (event) => {
    event.stopPropagation(); // Prevent the click from bubbling up
    if (search.style.display === 'flex') {
        // If already open, close it
        search.style.display = 'none';
        innerHeader.style.display = 'flex';
    } else {
        // Open search bar and hide header
        search.style.display = 'flex';
        innerHeader.style.display = 'none';
    }
});

// Toggle dropdown in the bottom nav
moreSmall.addEventListener("click", () => {
    dropDown = !dropDown;
    smallDropdown.style.display = dropDown ? 'block' : 'none';
});

// Extra: Close the search bar when clicking anywhere outside of it
document.addEventListener("click", (event) => {if (search.style.display === 'flex' && !search.contains(event.target)) {
    search.style.display = 'none';
    innerHeader.style.display = 'flex';
}});



searchInput.addEventListener("input", function() {
    clearBtn.style.display = this.value ? "block" : "none";
});

clearBtn.addEventListener("click", function() {
    searchInput.value = "";
    clearBtn.style.display = "none";
    searchInput.focus();
});

 

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
            <a href="${item.url}">
                ${icon}
                <div style="width: 100%;">
                  <span>${highlightMatch(item.name, query)}</span>
                  ${detailsHtml}
                </div>
              </a>
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
      return text.replace(regex, '<strong style="color: var(--btn-bg);">$1</strong>');
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