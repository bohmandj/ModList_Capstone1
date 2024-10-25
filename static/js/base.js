
document.addEventListener('DOMContentLoaded', function () {
    const showLoadingButtons = document.querySelectorAll('.show-loading');
    const loadingContainer = document.getElementById('loading-container');
    const scrollToTopButton = document.getElementById('scrollToTop');

    // Show loading screen on button click for route that could take time
    showLoadingButtons.forEach(button => {
        button.addEventListener('click', function () {
            loadingContainer.style.display = 'flex';
        });
    });

    // Show/hide scroll-to-top button based on scroll position
    window.addEventListener('scroll', function () {
        if (document.body.scrollTop > 200 || document.documentElement.scrollTop > 200) {
            if (window.innerWidth >= 768) { // Don't show scroll up btn on phones
                scrollToTopButton.style.display = "block";
            }
        } else {
            scrollToTopButton.style.display = "none";
        }
    });

    // Scroll to top when the button is clicked
    scrollToTopButton.addEventListener('click', function () {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
});