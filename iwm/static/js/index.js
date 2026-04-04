document.addEventListener("DOMContentLoaded", () => {
    const slider = document.querySelector("#mainSlider");
    if (!slider) return;

    const slides = slider.querySelectorAll(".slide");
    const prevBtn = slider.querySelector(".prev");
    const nextBtn = slider.querySelector(".next");
    const dotsContainer = slider.querySelector(".dots-container");
    const dots = slider.querySelectorAll(".dot");

    let index = 0;
    let interval;
    const total = slides.length;

    if (total === 0) return;

    // Initialize slider - activate first slide
    function initSlider() {
        // Make sure first slide is active
        slides.forEach((slide, i) => {
            slide.classList.toggle("active", i === 0);
        });
        
        // Create/update dots if needed
        if (dots.length === 0) {
            createDots();
        }
        
        // Update dots
        updateDots();
        
        // Start auto sliding
        startAuto();
    }

    // Create dots if they don't exist
    function createDots() {
        dotsContainer.innerHTML = '';
        slides.forEach((_, i) => {
            const dot = document.createElement("button");
            dot.className = "dot";
            dot.setAttribute("data-slide", i);
            dot.setAttribute("aria-label", `Go to slide ${i + 1}`);
            
            dot.addEventListener("click", () => {
                index = i;
                updateSlider();
                restartAuto();
            });
            
            if (i === 0) dot.classList.add("active");
            dotsContainer.appendChild(dot);
        });
    }

    function updateSlider() {
        // Update slides
        slides.forEach((slide, i) => {
            slide.classList.toggle("active", i === index);
        });
        
        // Update dots
        updateDots();
    }

    function updateDots() {
        dots.forEach((dot, i) => {
            dot.classList.toggle("active", i === index);
        });
    }

    function nextSlide() {
        index = (index + 1) % total;
        updateSlider();
    }

    function prevSlide() {
        index = (index - 1 + total) % total;
        updateSlider();
    }

    // Event listeners
    nextBtn?.addEventListener("click", () => {
        nextSlide();
        restartAuto();
    });

    prevBtn?.addEventListener("click", () => {
        prevSlide();
        restartAuto();
    });

    // Dot navigation
    dots.forEach((dot, i) => {
        dot.addEventListener("click", () => {
            index = i;
            updateSlider();
            restartAuto();
        });
    });

    // Auto sliding functionality
    function startAuto() {
        stopAuto();
        interval = setInterval(nextSlide, 4000);
    }

    function stopAuto() {
        if (interval) {
            clearInterval(interval);
            interval = null;
        }
    }

    function restartAuto() {
        stopAuto();
        startAuto();
    }

    // Pause on hover
    slider.addEventListener("mouseenter", stopAuto);
    slider.addEventListener("mouseleave", startAuto);

    // Touch swipe support
    let touchStartX = 0;
    let touchEndX = 0;

    slider.addEventListener("touchstart", e => {
        touchStartX = e.touches[0].clientX;
    }, { passive: true });

    slider.addEventListener("touchend", e => {
        touchEndX = e.changedTouches[0].clientX;
        handleSwipe();
        restartAuto();
    }, { passive: true });

    // Mouse-based swipe for desktop
    slider.addEventListener("mousedown", e => {
        touchStartX = e.clientX;
    });

    slider.addEventListener("mouseup", e => {
        touchEndX = e.clientX;
        handleSwipe();
        restartAuto();
    });

    function handleSwipe() {
        const diff = touchStartX - touchEndX;

        if (Math.abs(diff) > 50) { // Minimum swipe distance
            if (diff > 0) {
                nextSlide(); // Swipe left - next slide
            } else {
                prevSlide(); // Swipe right - prev slide
            }
        }
    }

    // Initialize the slider
    initSlider();
});