let currentCheckoutItems = [];
let currentCheckoutTotals = {
    subtotal: 0,
    shipping: 0,
    discount: 0,
    total: 0
};

document.addEventListener('DOMContentLoaded', function() {
    initializeCheckout();
    setupAddressSelect();
    setupPaymentMethods();
    setupCouponForm();
    setupModalActions();

    const placeOrderButton = document.getElementById('place-order-btn');
    if (placeOrderButton) {
        placeOrderButton.addEventListener('click', function(e) {
            e.preventDefault();
            if (!getCartItemsPayload().length) {
                const errorMsg = document.getElementById('checkout-error-msg');
                if (errorMsg) {
                    errorMsg.textContent = 'Your cart is empty. Please add items before placing an order.';
                    errorMsg.style.display = 'block';
                    errorMsg.scrollIntoView({ behavior: 'smooth', block: 'center' });
                } else {
                    alert('Your cart is empty. Please add items before placing an order.');
                }
                return;
            }
            if (validateCheckoutForm()) {
                showOrderPreview();
            }
        });
    }

    refreshOrderSummary();
});

function initializeCheckout() {
    renderSummaryItems([]);

    // Pre-enable the button immediately if localStorage already has items,
    // so a slow or failed server response never leaves the button stuck disabled.
    const preCartPayload = getCartItemsPayload();
    const placeOrderButtonInit = document.getElementById('place-order-btn');
    if (placeOrderButtonInit && preCartPayload.length > 0) {
        placeOrderButtonInit.disabled = false;
    }

    const shippingDistrictField = document.getElementById('shipping-district');
    if (shippingDistrictField) {
        syncDistrictFields('shipping', shippingDistrictField.value);
        shippingDistrictField.addEventListener('change', function() {
            syncDistrictFields('shipping', this.value);
            refreshOrderSummary();
        });
    }

}

function syncDistrictFields(type, districtValue) {
    const normalizedDistrict = districtValue || '';
    const cityField = document.getElementById(`${type}-city`);
    const stateField = document.getElementById(`${type}-state`);
    const districtField = document.getElementById(`${type}-district`);

    if (districtField && districtField.value !== normalizedDistrict) {
        districtField.value = normalizedDistrict;
    }

    if (cityField) {
        cityField.value = normalizedDistrict;
    }

    if (stateField) {
        stateField.value = normalizedDistrict;
    }
}

function getCartItemsPayload() {
    let cartItems = [];
    try {
        cartItems = JSON.parse(localStorage.getItem('cartItems')) || [];
        if (!Array.isArray(cartItems)) cartItems = [];
    } catch (e) {
        console.warn('Cart data in localStorage is corrupted, resetting.', e);
        localStorage.removeItem('cartItems');
        cartItems = [];
    }
    return cartItems
        .map(item => ({
            id: Number(item.id),
            quantity: Number(item.quantity || 1),
            color: (item.color || '').trim()
        }))
        .filter(item => Number.isFinite(item.id) && item.id > 0 && Number.isFinite(item.quantity) && item.quantity > 0);
}

function renderSummaryItems(items) {
    const summaryItemsContainer = document.querySelector('.summary-items');
    const placeOrderButton = document.getElementById('place-order-btn');

    if (!summaryItemsContainer) {
        return;
    }

    if (!items.length) {
        summaryItemsContainer.innerHTML = '<p>Your cart is empty.</p>';
        if (placeOrderButton) {
            placeOrderButton.disabled = true;
        }
        return;
    }

    if (placeOrderButton) {
        placeOrderButton.disabled = false;
    }

    summaryItemsContainer.innerHTML = '';
    items.forEach(item => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'summary-item';
        itemDiv.dataset.id = item.id;
        
        const imgDiv = document.createElement('div');
        imgDiv.className = 'item-image';
        const img = document.createElement('img');
        img.src = item.image;
        img.alt = item.name;
        imgDiv.appendChild(img);
        
        const detailsDiv = document.createElement('div');
        detailsDiv.className = 'item-details';
        
        const nameDiv = document.createElement('div');
        nameDiv.className = 'item-name';
        nameDiv.textContent = item.name;
        detailsDiv.appendChild(nameDiv);
        
        if (item.color) {
            const metaDiv = document.createElement('div');
            metaDiv.className = 'item-meta';
            metaDiv.textContent = `Color: ${item.color}`;
            detailsDiv.appendChild(metaDiv);
        }
        
        const priceDiv = document.createElement('div');
        priceDiv.className = 'item-price';
        priceDiv.textContent = formatCurrency(item.unit_price) + ' ';
        const qtySpan = document.createElement('span');
        qtySpan.className = 'item-quantity';
        qtySpan.textContent = `x ${item.quantity}`;
        priceDiv.appendChild(qtySpan);
        
        itemDiv.appendChild(imgDiv);
        itemDiv.appendChild(detailsDiv);
        summaryItemsContainer.appendChild(itemDiv);
    });
}

function setupAddressSelect() {
    const shippingAddressSelect = document.getElementById('shipping-address-select');

    if (shippingAddressSelect) {
        shippingAddressSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            if (selectedOption.value !== '') {
                const addressData = JSON.parse(selectedOption.dataset.address || '{}');
                fillAddressFields('shipping', addressData);
                refreshOrderSummary();
            }
        });
    }

}

function fillAddressFields(type, addressData) {
    const prefix = type === 'shipping' ? 'shipping-' : 'billing-';
    const district = addressData.state || addressData.city || '';

    document.getElementById(`${prefix}address-line1`).value = addressData.address_line1 || '';
    const fullNameField = document.getElementById(`${prefix}full-name`);
    if (fullNameField) {
        fullNameField.value = addressData.full_name || '';
    }
    const locationDescriptionField = document.getElementById(`${prefix}location-description`);
    if (locationDescriptionField) {
        locationDescriptionField.value = addressData.address_line2 || '';
    }
    syncDistrictFields(type, district);
    document.getElementById(`${prefix}postal-code`).value = addressData.postal_code || '';
    document.getElementById(`${prefix}country`).value = addressData.country || '';
}

function setupPaymentMethods() {
    const paymentMethods = document.querySelectorAll('.payment-method input[type="radio"]');
    const paymentFields = document.querySelectorAll('.payment-fields');

    paymentMethods.forEach(method => {
        method.addEventListener('change', function() {
            paymentFields.forEach(field => {
                field.style.display = 'none';
            });

            const selectedPaymentFields = document.querySelector(`.${this.value}-fields`);
            if (selectedPaymentFields) {
                selectedPaymentFields.style.display = 'block';
            }
        });
    });

    const defaultMethod = document.querySelector('.payment-method input[type="radio"]:checked');
    if (defaultMethod) {
        const selectedPaymentFields = document.querySelector(`.${defaultMethod.value}-fields`);
        if (selectedPaymentFields) {
            selectedPaymentFields.style.display = 'block';
        }
    }
}

function setupCouponForm() {
    const couponForm = document.getElementById('coupon-form');
    const couponCodeInput = document.getElementById('coupon-code');

    if (!couponForm) {
        return;
    }

    couponForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const couponCode = couponCodeInput.value.trim();
        if (couponCode === '') {
            displayCouponMessage('Please enter a coupon code', 'error');
            return;
        }

        const shippingState = document.getElementById('shipping-state')?.value || '';

        fetch('/apply-coupon/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCSRFToken()
            },
            body: `coupon_code=${encodeURIComponent(couponCode)}&shipping_state=${encodeURIComponent(shippingState)}&items_json=${encodeURIComponent(JSON.stringify(getCartItemsPayload()))}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displayCouponMessage(data.message, 'success');
                applyCheckoutSummary(data);
            } else {
                displayCouponMessage(data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            displayCouponMessage('Error applying coupon. Please try again.', 'error');
        });
    });
}

function displayCouponMessage(message, type) {
    const couponMessage = document.getElementById('coupon-message');
    if (couponMessage) {
        couponMessage.textContent = message;
        couponMessage.className = `coupon-message ${type}`;
        couponMessage.style.display = 'block';
    }
}

function formatCurrency(value) {
    return `৳${Number(value || 0).toFixed(2)}`;
}

function applyCheckoutSummary(data) {
    currentCheckoutItems = data.items || [];
    currentCheckoutTotals = data.totals || currentCheckoutTotals;

    renderSummaryItems(currentCheckoutItems);

    document.getElementById('subtotal-amount').textContent = formatCurrency(currentCheckoutTotals.subtotal);
    document.getElementById('shipping-amount').textContent = formatCurrency(currentCheckoutTotals.shipping);
    document.getElementById('total-amount').textContent = formatCurrency(currentCheckoutTotals.total);

    const discountElement = document.getElementById('discount-row');
    const discountAmountElement = document.getElementById('discount-amount');

    if (Number(currentCheckoutTotals.discount) > 0) {
        discountElement.style.display = 'flex';
        discountAmountElement.textContent = `-${formatCurrency(currentCheckoutTotals.discount)}`;
    } else {
        discountElement.style.display = 'none';
    }

    document.getElementById('order-subtotal').value = Number(currentCheckoutTotals.subtotal).toFixed(2);
    document.getElementById('order-shipping').value = Number(currentCheckoutTotals.shipping).toFixed(2);
    document.getElementById('order-discount').value = Number(currentCheckoutTotals.discount).toFixed(2);
    document.getElementById('order-total').value = Number(currentCheckoutTotals.total).toFixed(2);
}

function refreshOrderSummary(options = {}) {
    const cartPayload = getCartItemsPayload();
    if (!cartPayload.length) {
        currentCheckoutItems = [];
        currentCheckoutTotals = { subtotal: 0, shipping: 0, discount: 0, total: 0 };
        applyCheckoutSummary({ items: [], totals: currentCheckoutTotals });
        return Promise.resolve();
    }

    return fetch('/checkout-totals/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({
            items: cartPayload,
            shipping_state: document.getElementById('shipping-state')?.value || '',
            coupon_code: options.couponCode || '',
            clear_coupon: Boolean(options.clearCoupon)
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data && data.status === 'success') {
            applyCheckoutSummary(data);
        } else {
            // Server returned an error (e.g. product deleted/unavailable).
            // Re-enable the button so the user can still attempt to place the order;
            // the backend will do a final validation at submit time.
            const placeOrderBtn = document.getElementById('place-order-btn');
            if (placeOrderBtn && getCartItemsPayload().length > 0) {
                placeOrderBtn.disabled = false;
            }
        }
        return data;
    })
    .catch(error => {
        console.error('Error fetching checkout totals:', error);
        // Network / server error — re-enable button so the user is not stuck.
        const placeOrderBtn = document.getElementById('place-order-btn');
        if (placeOrderBtn && getCartItemsPayload().length > 0) {
            placeOrderBtn.disabled = false;
        }
        return null;
    });
}

function validateCheckoutForm() {
    let isValid = true;

    const fullName = document.getElementById('full-name').value.trim();
    const email = document.getElementById('email').value.trim();
    const phone = document.getElementById('phone').value.trim();

    if (fullName === '') {
        isValid = false;
        document.getElementById('full-name').classList.add('error');
    }

    if (email !== '' && !isValidEmail(email)) {
        isValid = false;
        document.getElementById('email').classList.add('error');
    }

    if (phone === '') {
        isValid = false;
        document.getElementById('phone').classList.add('error');
    }

    const shippingAddressLine1 = document.getElementById('shipping-address-line1').value.trim();
    const shippingDistrict = document.getElementById('shipping-district').value.trim();
    const shippingCountry = document.getElementById('shipping-country').value.trim();
    const shippingLocationDescription = document.getElementById('shipping-location-description').value.trim();

    if (shippingAddressLine1 === '') {
        isValid = false;
        document.getElementById('shipping-address-line1').classList.add('error');
    }

    if (shippingDistrict === '') {
        isValid = false;
        document.getElementById('shipping-district').classList.add('error');
    }

    if (shippingLocationDescription === '') {
        isValid = false;
        document.getElementById('shipping-location-description').classList.add('error');
    }

    if (shippingCountry === '') {
        isValid = false;
        document.getElementById('shipping-country').classList.add('error');
    }

    if (!isValid) {
        const errorMsg = document.getElementById('checkout-error-msg');
        if (errorMsg) {
            errorMsg.style.display = 'block';
            errorMsg.textContent = 'Please fill in all required fields highlighted below.';
        }
        const firstError = document.querySelector('.error');
        if (firstError) {
            firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    } else {
        const errorMsg = document.getElementById('checkout-error-msg');
        if (errorMsg) errorMsg.style.display = 'none';
    }

    return isValid;
}

function showOrderPreview() {
    try {
        const fullName = document.getElementById('full-name').value;
        const email = document.getElementById('email').value;
        const phone = document.getElementById('phone').value;

        document.getElementById('preview-name').textContent = fullName;
        document.getElementById('preview-email').textContent = email;
        document.getElementById('preview-phone').textContent = phone;

        const shippingAddressLine1 = document.getElementById('shipping-address-line1').value;
        const shippingDistrict = document.getElementById('shipping-district').value;
        const shippingLocationDescription = document.getElementById('shipping-location-description').value;
        const shippingCountry = document.getElementById('shipping-country').value;

        const container = document.getElementById('preview-shipping-address');
        container.innerHTML = '';
        
        container.appendChild(document.createTextNode(fullName));
        container.appendChild(document.createElement('br'));
        container.appendChild(document.createTextNode(shippingAddressLine1));
        
        if (shippingDistrict) {
            container.appendChild(document.createElement('br'));
            container.appendChild(document.createTextNode(`District: ${shippingDistrict}`));
        }
        if (shippingLocationDescription) {
            container.appendChild(document.createElement('br'));
            container.appendChild(document.createTextNode(shippingLocationDescription));
        }
        container.appendChild(document.createElement('br'));
        container.appendChild(document.createTextNode(shippingCountry));

        const paymentMethodRadio = document.querySelector('.payment-method input[type="radio"]:checked');
        const paymentContainer = document.getElementById('preview-payment-method');
        paymentContainer.innerHTML = '';
        if (paymentMethodRadio) {
            const labelEl = paymentMethodRadio.closest('.payment-method') &&
                            paymentMethodRadio.closest('.payment-method').querySelector('.payment-label');
            const paymentMethodLabel = labelEl ? labelEl.textContent.trim() : paymentMethodRadio.value;
            paymentContainer.appendChild(document.createTextNode(paymentMethodLabel));
            paymentContainer.appendChild(document.createElement('br'));
        }
        paymentContainer.appendChild(document.createTextNode('Our team will call you to confirm payment and delivery details.'));

        const orderItemsContainer = document.getElementById('preview-order-items');
        orderItemsContainer.innerHTML = '';
        currentCheckoutItems.forEach(item => {
            const row = document.createElement('div');
            row.className = 'detail-row';
            
            const label = document.createElement('div');
            label.className = 'detail-label';
            label.textContent = `${item.name}${item.color ? ` (${item.color})` : ''} x ${item.quantity}`;
            
            const val = document.createElement('div');
            val.className = 'detail-value';
            val.textContent = formatCurrency(item.line_total);
            
            row.appendChild(label);
            row.appendChild(val);
            orderItemsContainer.appendChild(row);
        });

        const subtotal = Number(document.getElementById('order-subtotal').value || 0);
        const shipping = Number(document.getElementById('order-shipping').value || 0);
        const discount = Number(document.getElementById('order-discount').value || 0);
        const total = Number(document.getElementById('order-total').value || 0);

        document.getElementById('preview-subtotal').textContent = formatCurrency(subtotal);
        document.getElementById('preview-shipping').textContent = formatCurrency(shipping);

        const previewDiscountRow = document.getElementById('preview-discount-row');
        if (discount > 0) {
            previewDiscountRow.style.display = 'flex';
            document.getElementById('preview-discount').textContent = `-${formatCurrency(discount)}`;
        } else {
            previewDiscountRow.style.display = 'none';
        }

        document.getElementById('preview-total').textContent = formatCurrency(total);

        const modal = document.getElementById('order-preview-modal');
        modal.style.display = 'block';
    } catch (err) {
        console.error('Error showing order preview:', err);
        const errorMsg = document.getElementById('checkout-error-msg');
        if (errorMsg) {
            errorMsg.textContent = 'Something went wrong showing the order preview. Please refresh and try again.';
            errorMsg.style.display = 'block';
            errorMsg.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else {
            alert('Something went wrong. Please refresh the page and try again.');
        }
    }
}

function setupModalActions() {
    const modal = document.getElementById('order-preview-modal');
    const closeModal = document.getElementById('close-modal');
    const editOrderBtn = document.getElementById('edit-order-btn');
    const confirmOrderBtn = document.getElementById('confirm-order-btn');

    if (closeModal) {
        closeModal.addEventListener('click', function() {
            modal.style.display = 'none';
        });
    }

    if (editOrderBtn) {
        editOrderBtn.addEventListener('click', function() {
            modal.style.display = 'none';
        });
    }

    if (confirmOrderBtn) {
        confirmOrderBtn.addEventListener('click', function() {
            submitOrder();
        });
    }

    window.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
}

function submitOrder() {
    const personalInfo = {
        full_name: document.getElementById('full-name').value,
        email: document.getElementById('email').value,
        phone: document.getElementById('phone').value
    };

    const shippingAddress = {
        full_name: personalInfo.full_name,
        address_line1: document.getElementById('shipping-address-line1').value,
        address_line2: document.getElementById('shipping-location-description').value || '',
        city: document.getElementById('shipping-district')?.value || 'Dhaka',
        postal_code: document.getElementById('shipping-postal-code')?.value || '1000',
        state: document.getElementById('shipping-district')?.value || 'Dhaka',
        country: document.getElementById('shipping-country')?.value || 'Bangladesh'
    };

    const billingAddress = shippingAddress;

    const paymentMethod = document.querySelector('.payment-method input[type="radio"]:checked').value;
    const paymentDetails = {};

    const additionalNotes = document.getElementById('additional-notes').value;
    const orderData = {
        personal_info: personalInfo,
        shipping_address: shippingAddress,
        billing_address: billingAddress,
        same_billing_address: true,
        payment_method: paymentMethod,
        payment_details: paymentDetails,
        items: getCartItemsPayload(),
        additional_notes: additionalNotes,
        idempotency_key: getCheckoutIdempotencyKey()
    };

    document.getElementById('confirm-order-btn').disabled = true;
    document.getElementById('confirm-order-btn').textContent = 'Processing...';

    fetch('/place-order/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify(orderData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            localStorage.removeItem('cartItems');
            sessionStorage.removeItem('checkoutIdempotencyKey');

            if (typeof updateCartCount === 'function') {
                updateCartCount();
            }

            window.location.href = `/order-confirmation/?order_number=${data.order_number}`;
        } else {
            alert('Error: ' + data.message);
            document.getElementById('confirm-order-btn').disabled = false;
            document.getElementById('confirm-order-btn').textContent = 'Confirm Order';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while processing your order. Please try again.');
        document.getElementById('confirm-order-btn').disabled = false;
        document.getElementById('confirm-order-btn').textContent = 'Confirm Order';
    });
}

function getCSRFToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];

    return cookieValue || '';
}

function createIdempotencyKey() {
    if (window.crypto && typeof window.crypto.randomUUID === 'function') {
        return window.crypto.randomUUID();
    }

    return `checkout-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function getCheckoutIdempotencyKey() {
    const storageKey = 'checkoutIdempotencyKey';
    let idempotencyKey = sessionStorage.getItem(storageKey);

    if (!idempotencyKey) {
        idempotencyKey = createIdempotencyKey();
        sessionStorage.setItem(storageKey, idempotencyKey);
    }

    return idempotencyKey;
}

function isValidEmail(email) {
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailPattern.test(email);
}

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('input, select, textarea').forEach(function(el) {
        el.addEventListener('input', function() {
            this.classList.remove('error');
        });
        el.addEventListener('change', function() {
            this.classList.remove('error');
        });
    });
});
