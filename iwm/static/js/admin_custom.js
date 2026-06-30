/* ==========================================================
   IWantMore Admin — Shared JavaScript (AH8)
   Loaded globally via UNFOLD["SCRIPTS"] in settings.py.
   ========================================================== */

document.addEventListener('DOMContentLoaded', function () {
    /* AH8: Clear Cache confirmation intercept
       Intercepts any sidebar link whose href contains "/clear-cache/"
       and shows a browser confirm dialog before allowing navigation. */
    document.querySelectorAll('a[href*="/clear-cache/"]').forEach(function (link) {
        link.addEventListener('click', function (e) {
            var confirmed = window.confirm(
                '\u26a0\ufe0f  Clear the full site cache?\n\n' +
                'This will flush all cached data immediately. ' +
                'The site may be briefly slower while caches rebuild.\n\n' +
                'This action cannot be undone.'
            );
            if (!confirmed) {
                e.preventDefault();
            }
        });
    });
});
