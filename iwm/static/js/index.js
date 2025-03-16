document.addEventListener("DOMContentLoaded", function () {
    const slides = document.querySelector(".slides");
    const slideImages = document.querySelectorAll(".slide");
    let index = 0;
    const totalSlides = slideImages.length;

    // Ensure slides container has enough width
    slides.style.width = `${totalSlides * 100}%`;
    slideImages.forEach(slide => {
        slide.style.width = `${100 / totalSlides}%`;
    });

    function nextSlide() {
        index = (index + 1) % totalSlides;
        updateSlider();
    }

    function updateSlider() {
        const offset = -index * 100;
        slides.style.transition = "transform 0.5s ease-in-out";
        slides.style.transform = `translateX(${offset}%)`;
    }

    setInterval(nextSlide, 3000); // Change slide every 3 seconds
});
