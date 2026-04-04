document.addEventListener('DOMContentLoaded', function() {
    // Initialize form elements and event listeners
    initializeCheckout();
    
    // Set up address selection if user is authenticated
    setupAddressSelect();
    
    // Handle billing address toggle
    setupBillingAddressToggle();
    
    // Setup payment method toggles
    setupPaymentMethods();
    
    // Setup coupon application
    setupCouponForm();
    
    // Calculate initial order summary
    updateOrderSummary();
    
    // Setup place order button
    document.getElementById('place-order-btn').addEventListener('click', function(e) {
        e.preventDefault();
        if (validateCheckoutForm()) {
            showOrderPreview();
        }
    });
    
    // Setup modal actions
    setupModalActions();
});

// Initialize checkout page
function initializeCheckout() {
    // Load cart items from localStorage
    loadCartItems();
    
    // Add event listeners for quantity changes
    document.querySelectorAll('.item-quantity-input').forEach(input => {
        input.addEventListener('change', function() {
            updateOrderSummary();
        });
    });
    
    // Add event listener for shipping state changes
    const shippingStateField = document.getElementById('shipping-state');
    if (shippingStateField) {
        shippingStateField.addEventListener('change', function() {
            updateOrderSummary();
        });
    }
}

// Load cart items from localStorage
function loadCartItems() {
    const cartItems = JSON.parse(localStorage.getItem('cartItems')) || [];
    const summaryItemsContainer = document.querySelector('.summary-items');
    
    if (summaryItemsContainer) {
        if (cartItems.length === 0) {
            summaryItemsContainer.innerHTML = '<p>Your cart is empty.</p>';
            document.getElementById('place-order-btn').disabled = true;
            return;
        }
        
        let itemsHTML = '';
        cartItems.forEach(item => {
            itemsHTML += `
                <div class="summary-item" data-id="${item.id}">
                    <div class="item-image">
                        <img src="${item.image}" alt="${item.name}">
                    </div>
                    <div class="item-details">
                        <div class="item-name">${item.name}</div>
                        <div class="item-price">$${item.price} <span class="item-quantity">× ${item.quantity}</span></div>
                    </div>
                </div>
            `;
        });
        
        summaryItemsContainer.innerHTML = itemsHTML;
    }
}

// Setup saved address selection for logged in users
function setupAddressSelect() {
    const shippingAddressSelect = document.getElementById('shipping-address-select');
    const billingAddressSelect = document.getElementById('billing-address-select');
    
    if (shippingAddressSelect) {
        shippingAddressSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            if (selectedOption.value !== '') {
                // Fill in shipping address fields based on selected saved address
                const addressData = JSON.parse(selectedOption.dataset.address || '{}');
                fillAddressFields('shipping', addressData);
            }
        });
    }
    
    if (billingAddressSelect) {
        billingAddressSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            if (selectedOption.value !== '') {
                // Fill in billing address fields based on selected saved address
                const addressData = JSON.parse(selectedOption.dataset.address || '{}');
                fillAddressFields('billing', addressData);
            }
        });
    }
}

// Fill address fields based on selected saved address
function fillAddressFields(type, addressData) {
    const prefix = type === 'shipping' ? 'shipping-' : 'billing-';
    
    document.getElementById(`${prefix}address-line1`).value = addressData.address_line1 || '';
    document.getElementById(`${prefix}address-line2`).value = addressData.address_line2 || '';
    document.getElementById(`${prefix}city`).value = addressData.city || '';
    document.getElementById(`${prefix}state`).value = addressData.state || '';
    document.getElementById(`${prefix}postal-code`).value = addressData.postal_code || '';
    document.getElementById(`${prefix}country`).value = addressData.country || '';
}

// Setup billing address toggle
function setupBillingAddressToggle() {
    const sameBillingCheckbox = document.getElementById('same-billing-address');
    const billingAddressSection = document.getElementById('billing-address-section');
    
    if (sameBillingCheckbox && billingAddressSection) {
        sameBillingCheckbox.addEventListener('change', function() {
            billingAddressSection.style.display = this.checked ? 'none' : 'block';
        });
        
        // Initialize based on initial checkbox state
        billingAddressSection.style.display = sameBillingCheckbox.checked ? 'none' : 'block';
    }
}

// Setup payment method toggles
function setupPaymentMethods() {
    const paymentMethods = document.querySelectorAll('.payment-method input[type="radio"]');
    const paymentFields = document.querySelectorAll('.payment-fields');
    
    paymentMethods.forEach(method => {
        method.addEventListener('change', function() {
            // Hide all payment fields first
            paymentFields.forEach(field => {
                field.style.display = 'none';
            });
            
            // Show the selected payment fields
            const selectedPaymentFields = document.querySelector(`.${this.value}-fields`);
            if (selectedPaymentFields) {
                selectedPaymentFields.style.display = 'block';
            }
        });
    });
    
    // Initialize based on default selected payment method
    const defaultMethod = document.querySelector('.payment-method input[type="radio"]:checked');
    if (defaultMethod) {
        const selectedPaymentFields = document.querySelector(`.${defaultMethod.value}-fields`);
        if (selectedPaymentFields) {
            selectedPaymentFields.style.display = 'block';
        }
    }
}

// Setup coupon form
function setupCouponForm() {
    const couponForm = document.getElementById('coupon-form');
    const couponCodeInput = document.getElementById('coupon-code');
    const couponMessage = document.getElementById('coupon-message');
    
    if (couponForm) {
        couponForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const couponCode = couponCodeInput.value.trim();
            if (couponCode === '') {
                displayCouponMessage('Please enter a coupon code', 'error');
                return;
            }
            
            // AJAX request to apply coupon
            fetch('/apply-coupon/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCSRFToken()
                },
                body: `coupon_code=${encodeURIComponent(couponCode)}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    displayCouponMessage(data.message, 'success');
                    
                    // Update order summary with discount
                    updateOrderSummary(data.discount, data.discount_type);
                } else {
                    displayCouponMessage(data.message, 'error');
                }
            })
            .catch(error => {
                displayCouponMessage('Error applying coupon. Please try again.', 'error');
                console.error('Error:', error);
            });
        });
    }
}

// Display coupon message
function displayCouponMessage(message, type) {
    const couponMessage = document.getElementById('coupon-message');
    if (couponMessage) {
        couponMessage.textContent = message;
        couponMessage.className = `coupon-message ${type}`;
        couponMessage.style.display = 'block';
    }
}

// Update order summary
function updateOrderSummary(discount = 0, discountType = 'fixed') {
    const cartItems = JSON.parse(localStorage.getItem('cartItems')) || [];
    let subtotal = 0;
    
    cartItems.forEach(item => {
        subtotal += parseFloat(item.price) * parseInt(item.quantity);
    });
    
    // Calculate shipping cost based on location
    let shippingCost = 0;
    if (subtotal > 0) {
        // Get shipping location
        const shippingState = document.getElementById('shipping-state')?.value || '';
        console.log("Shipping state:", shippingState); // Debug log
        // Check if location is in Dhaka Division
        if (shippingState.toLowerCase().includes('dhaka')) {
            shippingCost = 80; // Inside Dhaka Division: 80 taka
        } else {
            shippingCost = 150; // Outside Dhaka Division: 150 taka
        }
        console.log("Shipping cost set to:", shippingCost); // Debug log
    }
    
    // Apply discount if any
    let discountAmount = 0;
    if (discount > 0) {
        if (discountType === 'percentage') {
            discountAmount = subtotal * (discount / 100);
        } else {
            discountAmount = discount;
        }
    }
    
    // Calculate total
    const total = subtotal + shippingCost - discountAmount;
    
    // Update UI
    document.getElementById('subtotal-amount').textContent = `৳${subtotal.toFixed(2)}`;
    document.getElementById('shipping-amount').textContent = `৳${shippingCost.toFixed(2)}`;
    
    const discountElement = document.getElementById('discount-row');
    const discountAmountElement = document.getElementById('discount-amount');
    
    if (discountAmount > 0) {
        discountElement.style.display = 'flex';
        discountAmountElement.textContent = `-৳${discountAmount.toFixed(2)}`;
    } else {
        discountElement.style.display = 'none';
    }
    
    document.getElementById('total-amount').textContent = `৳${total.toFixed(2)}`;
    
    // Store values for order processing
    document.getElementById('order-subtotal').value = subtotal.toFixed(2);
    document.getElementById('order-shipping').value = shippingCost.toFixed(2);
    document.getElementById('order-discount').value = discountAmount.toFixed(2);
    document.getElementById('order-total').value = total.toFixed(2);
}

// Validate checkout form
function validateCheckoutForm() {
    let isValid = true;
    
    // Validate personal info
    const fullName = document.getElementById('full-name').value.trim();
    const email = document.getElementById('email').value.trim();
    const phone = document.getElementById('phone').value.trim();
    
    if (fullName === '') {
        isValid = false;
        document.getElementById('full-name').classList.add('error');
    }
    
    if (email === '' || !isValidEmail(email)) {
        isValid = false;
        document.getElementById('email').classList.add('error');
    }
    
    if (phone === '') {
        isValid = false;
        document.getElementById('phone').classList.add('error');
    }
    
    // Validate shipping address
    const shippingAddressLine1 = document.getElementById('shipping-address-line1').value.trim();
    const shippingCity = document.getElementById('shipping-city').value.trim();
    const shippingPostalCode = document.getElementById('shipping-postal-code').value.trim();
    const shippingState = document.getElementById('shipping-state').value.trim();
    const shippingCountry = document.getElementById('shipping-country').value.trim();
    
    if (shippingAddressLine1 === '') {
        isValid = false;
        document.getElementById('shipping-address-line1').classList.add('error');
    }
    
    if (shippingCity === '') {
        isValid = false;
        document.getElementById('shipping-city').classList.add('error');
    }
    
    if (shippingPostalCode === '') {
        isValid = false;
        document.getElementById('shipping-postal-code').classList.add('error');
    }
    
    if (shippingState === '') {
        isValid = false;
        document.getElementById('shipping-state').classList.add('error');
    }
    
    if (shippingCountry === '') {
        isValid = false;
        document.getElementById('shipping-country').classList.add('error');
    }
    
    // Validate billing address if different from shipping
    const sameBillingAddress = document.getElementById('same-billing-address').checked;
    
    if (!sameBillingAddress) {
        const billingFullName = document.getElementById('billing-full-name').value.trim();
        const billingAddressLine1 = document.getElementById('billing-address-line1').value.trim();
        const billingCity = document.getElementById('billing-city').value.trim();
        const billingPostalCode = document.getElementById('billing-postal-code').value.trim();
        const billingState = document.getElementById('billing-state').value.trim();
        const billingCountry = document.getElementById('billing-country').value.trim();
        
        if (billingFullName === '') {
            isValid = false;
            document.getElementById('billing-full-name').classList.add('error');
        }
        
        if (billingAddressLine1 === '') {
            isValid = false;
            document.getElementById('billing-address-line1').classList.add('error');
        }
        
        if (billingCity === '') {
            isValid = false;
            document.getElementById('billing-city').classList.add('error');
        }
        
        if (billingPostalCode === '') {
            isValid = false;
            document.getElementById('billing-postal-code').classList.add('error');
        }
        
        if (billingState === '') {
            isValid = false;
            document.getElementById('billing-state').classList.add('error');
        }
        
        if (billingCountry === '') {
            isValid = false;
            document.getElementById('billing-country').classList.add('error');
        }
    }
    
    // Validate payment fields
    const paymentMethod = document.querySelector('.payment-method input[type="radio"]:checked').value;
    
    if (paymentMethod === 'bkash') {
        const bkashNumber = document.getElementById('bkash-number').value.trim();
        if (bkashNumber === '') {
            isValid = false;
            document.getElementById('bkash-number').classList.add('error');
        }
    } else if (paymentMethod === 'nagad') {
        const nagadNumber = document.getElementById('nagad-number').value.trim();
        if (nagadNumber === '') {
            isValid = false;
            document.getElementById('nagad-number').classList.add('error');
        }
    }
    
    return isValid;
}

// Show order preview modal
function showOrderPreview() {
    // Get personal info
    const fullName = document.getElementById('full-name').value;
    const email = document.getElementById('email').value;
    const phone = document.getElementById('phone').value;
    
    // Update personal info in preview
    document.getElementById('preview-name').textContent = fullName;
    document.getElementById('preview-email').textContent = email;
    document.getElementById('preview-phone').textContent = phone;
    
    // Get address info and format for preview
    const shippingAddressLine1 = document.getElementById('shipping-address-line1').value;
    const shippingAddressLine2 = document.getElementById('shipping-address-line2').value;
    const shippingCity = document.getElementById('shipping-city').value;
    const shippingPostalCode = document.getElementById('shipping-postal-code').value;
    const shippingState = document.getElementById('shipping-state').value;
    const shippingCountry = document.getElementById('shipping-country').value;
    
    // Format shipping address
    let shippingAddressHTML = `${fullName}<br>${shippingAddressLine1}`;
    if (shippingAddressLine2) {
        shippingAddressHTML += `<br>${shippingAddressLine2}`;
    }
    shippingAddressHTML += `<br>${shippingCity}, ${shippingState} ${shippingPostalCode}<br>${shippingCountry}`;
    document.getElementById('preview-shipping-address').innerHTML = shippingAddressHTML;
    
    // Get payment method
    const paymentMethodRadio = document.querySelector('.payment-method input[type="radio"]:checked');
    const paymentMethodLabel = paymentMethodRadio.closest('.payment-method').querySelector('.payment-label').textContent.trim();
    
    // Format payment method info
    let paymentMethodHTML = paymentMethodLabel;
    if (paymentMethodRadio.value === 'bkash') {
        const bkashNumber = document.getElementById('bkash-number').value;
        if (bkashNumber) {
            paymentMethodHTML += `<br>bKash Number: ${bkashNumber}`;
        }
    } else if (paymentMethodRadio.value === 'nagad') {
        const nagadNumber = document.getElementById('nagad-number').value;
        if (nagadNumber) {
            paymentMethodHTML += `<br>Nagad Number: ${nagadNumber}`;
        }
    } else if (paymentMethodRadio.value === 'cash_on_delivery') {
        paymentMethodHTML += `<br>Cash on Delivery`;
    }
    document.getElementById('preview-payment-method').innerHTML = paymentMethodHTML;
    
    // Add cart items to preview
    const cartItems = JSON.parse(localStorage.getItem('cartItems')) || [];
    const orderItemsContainer = document.getElementById('preview-order-items');
    let itemsHTML = '';
    
    cartItems.forEach(item => {
        itemsHTML += `
            <div class="detail-row">
                <div class="detail-label">${item.name} × ${item.quantity}</div>
                <div class="detail-value">$${(parseFloat(item.price) * parseInt(item.quantity)).toFixed(2)}</div>
            </div>
        `;
    });
    
    orderItemsContainer.innerHTML = itemsHTML;
    
    // Update totals in preview
    const subtotal = document.getElementById('order-subtotal').value;
    const shipping = document.getElementById('order-shipping').value;
    const discount = document.getElementById('order-discount').value;
    const total = document.getElementById('order-total').value;
    
    document.getElementById('preview-subtotal').textContent = `$${subtotal}`;
    document.getElementById('preview-shipping').textContent = `$${shipping}`;
    
    const previewDiscountRow = document.getElementById('preview-discount-row');
    if (parseFloat(discount) > 0) {
        previewDiscountRow.style.display = 'flex';
        document.getElementById('preview-discount').textContent = `-$${discount}`;
    } else {
        previewDiscountRow.style.display = 'none';
    }
    
    document.getElementById('preview-total').textContent = `$${total}`;
    
    // Show modal
    const modal = document.getElementById('order-preview-modal');
    modal.style.display = 'block';
}

// Setup modal actions
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
            // Submit order via AJAX
            submitOrder();
        });
    }
    
    // Close modal when clicking outside
    window.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
}

// Submit order via AJAX
function submitOrder() {
    // Get personal information
    const personalInfo = {
        full_name: document.getElementById('full-name').value,
        email: document.getElementById('email').value,
        phone: document.getElementById('phone').value
    };
    
    // Get shipping address
    const shippingAddress = {
        full_name: personalInfo.full_name,
        address_line1: document.getElementById('shipping-address-line1').value,
        address_line2: document.getElementById('shipping-address-line2').value || '',
        city: document.getElementById('shipping-city').value,
        postal_code: document.getElementById('shipping-postal-code')?.value || '1000', // Default to Dhaka postal code
        state: document.getElementById('shipping-state')?.value || 'Dhaka', // Default to Dhaka
        country: document.getElementById('shipping-country')?.value || 'Bangladesh'
    };
    
    // Get billing address (if different)
    const sameBillingAddress = document.getElementById('same-billing-address').checked;
    let billingAddress = {};
    
    if (sameBillingAddress) {
        billingAddress = shippingAddress;
    } else {
        billingAddress = {
            full_name: document.getElementById('billing-full-name')?.value || personalInfo.full_name,
            address_line1: document.getElementById('billing-address-line1').value,
            address_line2: document.getElementById('billing-address-line2')?.value || '',
            city: document.getElementById('billing-city').value,
            postal_code: document.getElementById('billing-postal-code')?.value || '1000', // Default to Dhaka postal code
            state: document.getElementById('billing-state')?.value || 'Dhaka', // Default to Dhaka
            country: document.getElementById('billing-country')?.value || 'Bangladesh'
        };
    }
    
    // Get payment method
    const paymentMethod = document.querySelector('.payment-method input[type="radio"]:checked').value;
    let paymentDetails = {};
    
    if (paymentMethod === 'bkash') {
        paymentDetails = {
            sender_number: document.getElementById('bkash-number').value,
            transaction_id: document.getElementById('bkash-trx-id') ? document.getElementById('bkash-trx-id').value : ''
        };
    } else if (paymentMethod === 'nagad') {
        paymentDetails = {
            sender_number: document.getElementById('nagad-number').value,
            transaction_id: document.getElementById('nagad-trx-id') ? document.getElementById('nagad-trx-id').value : ''
        };
    } else if (paymentMethod === 'cash_on_delivery') {
        // For COD, we still collect delivery payment details
        paymentDetails = {
            delivery_payment_method: document.getElementById('cod-delivery-payment-method') ? document.getElementById('cod-delivery-payment-method').value : '',
            delivery_transaction_id: document.getElementById('cod-delivery-trx-id') ? document.getElementById('cod-delivery-trx-id').value : ''
        };
    }
    
    // Get additional notes
    const additionalNotes = document.getElementById('additional-notes').value;
    
    // Get cart items
    const cartItems = JSON.parse(localStorage.getItem('cartItems')) || [];
    
    // Get totals
    const totals = {
        subtotal: document.getElementById('order-subtotal').value,
        shipping: document.getElementById('order-shipping').value,
        discount: document.getElementById('order-discount').value,
        total: document.getElementById('order-total').value
    };
    
    // Prepare order data
    const orderData = {
        personal_info: personalInfo,
        shipping_address: shippingAddress,
        billing_address: billingAddress,
        same_billing_address: sameBillingAddress,
        payment_method: paymentMethod,
        payment_details: paymentDetails,
        items: cartItems,
        additional_notes: additionalNotes,
        totals: totals
    };
    
    // Disable confirm button to prevent multiple submissions
    document.getElementById('confirm-order-btn').disabled = true;
    document.getElementById('confirm-order-btn').textContent = 'Processing...';
    
    // Submit order via AJAX
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
            // Clear cart
            localStorage.removeItem('cartItems');
            
            // Update cart count in the header
            if (typeof updateCartCount === 'function') {
                updateCartCount();
            }
            
            // Redirect to order confirmation page
            window.location.href = `/order-confirmation/?order_id=${data.order_id}`;
        } else {
            alert('Error: ' + data.message);
            
            // Re-enable confirm button
            document.getElementById('confirm-order-btn').disabled = false;
            document.getElementById('confirm-order-btn').textContent = 'Confirm Order';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while processing your order. Please try again.');
        
        // Re-enable confirm button
        document.getElementById('confirm-order-btn').disabled = false;
        document.getElementById('confirm-order-btn').textContent = 'Confirm Order';
    });
}

// Helper function to get CSRF token
function getCSRFToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    
    return cookieValue || '';
}

// Helper function to validate email
function isValidEmail(email) {
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailPattern.test(email);
}