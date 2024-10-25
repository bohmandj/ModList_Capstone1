
// show loading screen shown after clicking buttons w/ class 'show-loading'
document.addEventListener('DOMContentLoaded', function () {
    const showLoadingButtons = document.querySelectorAll('.show-loading');
    const loadingContainer = document.getElementById('loading-container');

    showLoadingButtons.forEach(button => {
        button.addEventListener('click', function () {
            loadingContainer.style.display = 'flex';
        });
    });
});