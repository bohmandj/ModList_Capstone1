
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

    let popularGameCardIndex = 10; // 10 most popular games' cards already shown

    document.getElementById('load-more').addEventListener('click', function () {
        // Btn functionality to display more popular games below the starting 
        // 10 games every time the #load-more btn is clicked

        const gameCardSection = document.querySelector('.game-section');

        for (let i = 0; i < 10 && popularGameCardIndex < games.length; i++, popularGameCardIndex++) {
            const game = games[popularGameCardIndex];

            const newGameCard = document.createElement('li');
            newGameCard.classList.add('game-card');
            newGameCard.innerHTML = `
            <a class="game-img" href="/games/${game.domain_name}" style="background-image: url(https://staticdelivery.nexusmods.com/Images/games/4_3/tile_${game.id}.jpg);" alt="${game.name} cover image" title="Open ${game.name} page on ModList">
            </a>
            <a class="nexus-btn-container" href="https://www.nexusmods.com/${game.domain_name}" target="_blank" rel="noopener noreferrer" title="Open ${game.name} on Nexus to search all mods in a new tab.">
                <img class="nexus-btn" src="https://raw.githubusercontent.com/github/explore/781dbc058383a2ee8259ebbab057292f16172d5e/topics/nexus-mods/nexus-mods.png">
            </a>
            <a class="game-title" href="/games/${game.domain_name}" title="Open ${game.name} page on ModList">
                <span>${game.name}</span>
            </a>
        `;
            gameCardSection.appendChild(newGameCard);
        }

        if (popularGameCardIndex >= games.length) {
            this.style.display = 'none';
        }
    });
});