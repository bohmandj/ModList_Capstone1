
document.addEventListener('DOMContentLoaded', function () {
    // Functionality for menu that shows game names alphabetically 
    // by letter at the bottom of the signed-in homepage
    const alphabetLetters = document.querySelectorAll('.alphabet-letter');
    const gameList = document.querySelector('.game-list');
    const games = JSON.parse(document.getElementById('games-data').textContent);

    alphabetLetters.forEach(letter => {
        letter.addEventListener('click', function () {
            const selectedLetter = this.getAttribute('data-letter');
            gameList.innerHTML = '';
            gameList.style.display = 'none';

            let filteredGames;
            if (selectedLetter === '#') {
                filteredGames = games.filter(game => /^[0-9!@#$%^&*()_+[\]{};':"\\|,.<>?`~]+/.test(game.name.charAt(0)));
            } else {
                filteredGames = games.filter(game => game.name.startsWith(selectedLetter));
            }

            if (filteredGames.length > 0) {
                filteredGames.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
                filteredGames.forEach(game => {
                    const gameNameItem = document.createElement('li');
                    gameNameItem.innerHTML = `<a href="${window.location.origin}/games/${game.domain_name}">${game.name}</a>`;
                    gameList.appendChild(gameNameItem);
                });
                gameList.style.display = 'grid';
            } else {
                const noGamesItem = document.createElement('li');
                noGamesItem.textContent = `No games that start with '${selectedLetter}' were found.`;
                gameList.appendChild(noGamesItem);
                gameList.style.display = 'grid';
            }
        });
    });
});