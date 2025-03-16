document.addEventListener("DOMContentLoaded", function () {
    console.log("I Want More Admin Panel Loaded!");

    // Example: Toggle class on navbar click
    const navbar = document.querySelector(".iwm-admin-navbar");
    navbar.addEventListener("click", () => {
        navbar.classList.toggle("active");
    });

    // Example: Alert on successful login
    if (window.location.pathname.includes("/admin/login/")) {
        setTimeout(() => alert("Welcome to I Want More Admin!"), 500);
    }
});
