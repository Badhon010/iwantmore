// ── Top-level element references (needed by synchronous event handlers) ──────
const moreSmall      = document.getElementById('moreSmall');
const smallDropdown  = document.querySelector("#more-link-small .dropdown-menu");
const moreLink       = document.getElementById('more-link');
const moreLinkToggle = document.getElementById('moreLinkToggle');
const search         = document.getElementById('search');
const innerHeader    = document.getElementById('i-h');
const searchBtn      = document.getElementById('searchToggle');
const searchInput    = document.getElementById('sea');
const clearBtn       = document.getElementById('clear-btn');
const suggestionsContainer = document.getElementById('suggestions');
const orderLinks     = document.querySelector('.order_links');
const storeToggle    = document.getElementById('store');

// ── Utilities ─────────────────────────────────────────────────────────────────
function debounce(fn, delay) {
    let t;
    return function (...args) {
        clearTimeout(t);
        t = setTimeout(() => fn.apply(this, args), delay);
    };
}

function setToggleState(btn, expanded) {
    btn?.setAttribute('aria-expanded', String(expanded));
}

// ── Search panel ──────────────────────────────────────────────────────────────
function setSearchOpen(isOpen) {
    if (!search || !innerHeader || !searchBtn) return;
    search.style.display     = isOpen ? 'flex' : 'none';
    innerHeader.style.display = isOpen ? 'none' : 'flex';
    setToggleState(searchBtn, isOpen);
    if (isOpen && searchInput) searchInput.focus();
}

setSearchOpen(false);

searchBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    setSearchOpen(search.style.display !== 'flex');
});

if (searchInput && clearBtn) {
    searchInput.addEventListener('input', function () {
        clearBtn.style.display = this.value ? 'block' : 'none';
    });
    clearBtn.addEventListener('click', function () {
        searchInput.value = '';
        clearBtn.style.display = 'none';
        searchInput.focus();
        suggestionsContainer?.classList.remove('active');
    });
}

// ── Dropdowns ─────────────────────────────────────────────────────────────────
moreSmall?.addEventListener('click', () => {
    const isOpen = smallDropdown.style.display === 'block';
    smallDropdown.style.display = isOpen ? 'none' : 'block';
    setToggleState(moreSmall, !isOpen);
});

moreLinkToggle?.addEventListener('click', (e) => {
    e.stopPropagation();
    const isOpen = moreLink.classList.toggle('open');
    setToggleState(moreLinkToggle, isOpen);
});

storeToggle?.addEventListener('click', (e) => {
    e.stopPropagation();
    const isOpen = orderLinks.classList.toggle('open');
    setToggleState(storeToggle, isOpen);
});

// ── Global click / Escape — close all overlays ────────────────────────────────
document.addEventListener('click', (e) => {
    if (search?.style.display === 'flex' && !search.contains(e.target) && !searchBtn?.contains(e.target)) {
        setSearchOpen(false);
    }
    if (moreLink && !moreLink.contains(e.target)) {
        moreLink.classList.remove('open');
        setToggleState(moreLinkToggle, false);
    }
    if (smallDropdown && moreSmall && !moreSmall.contains(e.target) && !smallDropdown.contains(e.target)) {
        smallDropdown.style.display = 'none';
        setToggleState(moreSmall, false);
    }
    if (orderLinks && !orderLinks.contains(e.target)) {
        orderLinks.classList.remove('open');
        setToggleState(storeToggle, false);
    }
    if (searchInput && suggestionsContainer && !searchInput.contains(e.target) && !suggestionsContainer.contains(e.target)) {
        suggestionsContainer.classList.remove('active');
    }
});

document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    setSearchOpen(false);
    moreLink?.classList.remove('open');
    setToggleState(moreLinkToggle, false);
    if (smallDropdown) { smallDropdown.style.display = 'none'; setToggleState(moreSmall, false); }
    orderLinks?.classList.remove('open');
    setToggleState(storeToggle, false);
    suggestionsContainer?.classList.remove('active');
});

// ── Badge helpers (global — called from item_cart.js, product.js, checkout.js) ─
function updateCartCount() {
    const badges = document.querySelectorAll('.cart-count');
    if (!badges.length) return;
    const cart  = JSON.parse(localStorage.getItem('cartItems')) || [];
    const total = cart.reduce((sum, item) => sum + (parseInt(item.quantity) || 1), 0);
    badges.forEach(b => {
        b.textContent = total > 0 ? total : '';
        b.setAttribute('data-count', total);
    });
}

function updateWishlistCount() {
    const badges = document.querySelectorAll('.wishlist-count');
    if (!badges.length) return;
    const items = JSON.parse(localStorage.getItem('wishlistItems')) || [];
    badges.forEach(b => {
        b.textContent = items.length > 0 ? items.length : '';
        b.setAttribute('data-count', items.length);
    });
}

function updateOrderCount() {
    const badges = document.querySelectorAll('.order-count');
    if (!badges.length) return;

    const isLoggedIn = document.body.classList.contains('logged-in');
    if (!isLoggedIn) {
        badges.forEach(b => { b.textContent = ''; b.setAttribute('data-count', 0); b.style.display = 'none'; });
        return;
    }

    fetch('/api/order-count/')
        .then(r => r.ok ? r.json() : null)
        .then(data => {
            const count = parseInt(data?.count || 0);
            badges.forEach(b => {
                if (count > 0) {
                    b.textContent = count;
                    b.setAttribute('data-count', count);
                    b.style.display = '';
                } else {
                    b.textContent = '';
                    b.setAttribute('data-count', 0);
                    b.style.display = 'none';
                }
            });
        })
        .catch(() => {
            badges.forEach(b => { b.textContent = ''; b.setAttribute('data-count', 0); b.style.display = 'none'; });
        });
}

// Used by wishlist.html template
function addToCart(productId, productName, productPrice, productImage, quantity = 1) {
    const cart = JSON.parse(localStorage.getItem('cartItems')) || [];
    const idx  = cart.findIndex(item => item.id == productId);
    if (idx !== -1) {
        cart[idx].quantity += quantity;
    } else {
        cart.push({ id: productId, name: productName, price: productPrice, image: productImage, quantity });
    }
    localStorage.setItem('cartItems', JSON.stringify(cart));
    updateCartCount();
    const cartIcon = document.querySelector('.cart i');
    if (cartIcon) {
        cartIcon.classList.add('pulse');
        setTimeout(() => cartIcon.classList.remove('pulse'), 500);
    }
    return cart;
}

// ── DOMContentLoaded — autocomplete + badges + alerts ────────────────────────
document.addEventListener('DOMContentLoaded', function () {

    // Initial badge sync
    updateCartCount();
    updateWishlistCount();
    updateOrderCount();

    // ── Autocomplete ──────────────────────────────────────────────────────────
    if (!searchInput || !suggestionsContainer) return;

    let selectedIndex = -1;

    function buildSuggestionItem(item, query) {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'suggestion-item';

        const a = document.createElement('a');
        a.href = item.url;

        const iconMap = { product: 'fas fa-tag', category: 'fas fa-folder', tag: 'fas fa-hashtag' };
        const icon = document.createElement('i');
        icon.className = iconMap[item.type] || 'fas fa-tag';
        a.appendChild(icon);

        const contentDiv = document.createElement('div');
        contentDiv.style.width = '100%';

        const nameSpan = document.createElement('span');
        const lowerName  = (item.name  || '').toLowerCase();
        const lowerQuery = (query || '').toLowerCase();
        const matchIdx   = lowerName.indexOf(lowerQuery);

        if (matchIdx >= 0 && query.length > 0) {
            nameSpan.appendChild(document.createTextNode(item.name.substring(0, matchIdx)));
            const strong = document.createElement('strong');
            strong.style.color = 'var(--btn-bg)';
            strong.textContent = item.name.substring(matchIdx, matchIdx + query.length);
            nameSpan.appendChild(strong);
            nameSpan.appendChild(document.createTextNode(item.name.substring(matchIdx + query.length)));
        } else {
            nameSpan.textContent = item.name;
        }
        contentDiv.appendChild(nameSpan);

        if (item.type === 'product') {
            const price = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'BDT', minimumFractionDigits: 0 }).format(item.price);
            const detailsDiv = Object.assign(document.createElement('div'), {
                style: 'display:flex;justify-content:space-between;font-size:12px;color:#666;margin-top:3px'
            });
            const catSpan   = Object.assign(document.createElement('span'), { textContent: item.category });
            const priceSpan = Object.assign(document.createElement('span'), { textContent: price });
            priceSpan.style.cssText = 'color:var(--btn-bg);font-weight:500';
            detailsDiv.append(catSpan, priceSpan);
            contentDiv.appendChild(detailsDiv);
        }

        a.appendChild(contentDiv);
        itemDiv.appendChild(a);
        return itemDiv;
    }

    const fetchSuggestions = debounce(function () {
        const query = searchInput.value.trim();
        if (query.length < 2) { suggestionsContainer.classList.remove('active'); return; }

        suggestionsContainer.innerHTML = '';
        const loading = Object.assign(document.createElement('div'), { className: 'empty-suggestions', textContent: 'Searching...' });
        suggestionsContainer.appendChild(loading);
        suggestionsContainer.classList.add('active');

        fetch(`/autocomplete/?q=${encodeURIComponent(query)}`)
            .then(r => r.json())
            .then(data => {
                suggestionsContainer.innerHTML = '';
                if (!data.length) {
                    suggestionsContainer.appendChild(
                        Object.assign(document.createElement('div'), { className: 'empty-suggestions', textContent: `No results for "${query}"` })
                    );
                    return;
                }
                data.forEach(item => suggestionsContainer.appendChild(buildSuggestionItem(item, query)));
            })
            .catch(() => {
                suggestionsContainer.innerHTML = '';
                suggestionsContainer.appendChild(
                    Object.assign(document.createElement('div'), { className: 'empty-suggestions', textContent: 'Error loading suggestions' })
                );
            });
    }, 300);

    searchInput.addEventListener('input', fetchSuggestions);
    searchInput.addEventListener('focus', function () {
        if (this.value.trim().length >= 2) suggestionsContainer.classList.add('active');
    });

    searchInput.addEventListener('keydown', function (e) {
        if (!suggestionsContainer.classList.contains('active')) return;
        const items = suggestionsContainer.querySelectorAll('.suggestion-item');
        if (!items.length) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            items.forEach(i => i.classList.remove('selected'));
            selectedIndex = (selectedIndex + 1) % items.length;
            items[selectedIndex].classList.add('selected');
            items[selectedIndex].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            items.forEach(i => i.classList.remove('selected'));
            selectedIndex = (selectedIndex - 1 + items.length) % items.length;
            items[selectedIndex].classList.add('selected');
            items[selectedIndex].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        } else if (e.key === 'Enter') {
            e.preventDefault();
            const sel = suggestionsContainer.querySelector('.suggestion-item.selected');
            if (sel) window.location.href = sel.querySelector('a').getAttribute('href');
            else this.closest('form').submit();
        } else if (e.key === 'Escape') {
            suggestionsContainer.classList.remove('active');
            selectedIndex = -1;
        }
    });

    // ── Django alert auto-dismiss ─────────────────────────────────────────────
    function dismissAlert(alert) {
        alert.style.cssText += 'opacity:0;transform:translateY(-10px);transition:opacity .3s ease,transform .3s ease';
        setTimeout(() => alert.remove(), 300);
    }

    document.querySelectorAll('.alert .btn-close').forEach(btn => {
        btn.addEventListener('click', function () { dismissAlert(this.closest('.alert')); });
    });

    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => { if (alert?.parentNode) dismissAlert(alert); }, 5000);
    });
});
