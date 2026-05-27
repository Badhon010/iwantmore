document.addEventListener("DOMContentLoaded", () => {
    const slider = document.querySelector("#mainSlider");
    if (!slider) return;

    const slides = slider.querySelectorAll(".slide");
    const prevBtn = slider.querySelector(".prev");
    const nextBtn = slider.querySelector(".next");
    const dots = [...slider.querySelectorAll(".dot")];

    let index = 0;
    let interval;
    const total = slides.length;

    if (total === 0) return;

    function render() {
        slides.forEach((slide, i) => {
            slide.classList.toggle("active", i === index);
        });
        dots.forEach((dot, i) => {
            dot.classList.toggle("active", i === index);
        });
    }

    function goToSlide(nextIndex) {
        index = (nextIndex + total) % total;
        render();
    }

    function nextSlide() {
        goToSlide(index + 1);
    }

    function prevSlide() {
        goToSlide(index - 1);
    }

    nextBtn?.addEventListener("click", () => {
        nextSlide();
        restartAuto();
    });

    prevBtn?.addEventListener("click", () => {
        prevSlide();
        restartAuto();
    });

    dots.forEach((dot, i) => {
        dot.addEventListener("click", () => {
            goToSlide(i);
            restartAuto();
        });
    });

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

    slider.addEventListener("mouseenter", stopAuto);
    slider.addEventListener("mouseleave", startAuto);

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

        if (Math.abs(diff) > 50) {
            if (diff > 0) {
                nextSlide();
            } else {
                prevSlide();
            }
        }
    }

    render();
    startAuto();
});
