document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.cancel-btn').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            if (!confirm('Are you sure you want to cancel this order?')) {
                e.preventDefault();
            }
        });
    });
});
