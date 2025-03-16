/**
 * Product page functionality
 * Handles star rating selection and other interactive elements
 */

document.addEventListener("DOMContentLoaded", function() {
    // Star rating functionality
    initStarRating();
    
    // Order button functionality
    initOrderButton();
});

/**
 * Initialize the star rating system
 */
function initStarRating() {
    const starButtons = document.querySelectorAll(".star-btn");
    const ratingInput = document.getElementById("selected-rating");
    
    if (!starButtons.length || !ratingInput) return;

    starButtons.forEach((button, index) => {
        button.addEventListener("click", function() {
            let selectedValue = this.getAttribute("data-value");
            ratingInput.value = selectedValue;

            // Remove the 'selected' class from all stars
            starButtons.forEach(btn => btn.classList.remove("selected"));

            // Add the 'selected' class to the clicked star and all stars to its right (lower index)
            for (let i = 0; i <= index; i++) {
                starButtons[i].classList.add("selected");
            }
        });
    });
}

/**
 * Initialize the order button functionality
 */
function initOrderButton() {
    const orderButton = document.querySelector(".order-button");
    
    if (!orderButton) return;
    
    orderButton.addEventListener("click", function() {
        // In a real implementation, this would add the product to the cart
        // or redirect to a checkout page
        alert("Product added to cart!");
        
        // Animation feedback
        this.classList.add("clicked");
        setTimeout(() => {
            this.classList.remove("clicked");
        }, 300);
    });
} 