// Holds the full player list from the API -> kept in memory so filtering
// and sorting never need to re-fetch. Just slice and dice allPlayers.

let allPlayers = [];

// Kick everything off once the DOM is ready. Hits the Flask backend,
// grabs the scored player list, and renders it. If the backend is down
// or the fetch fails, logs the error so debugging isn't a nightmare.
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('/api/players');
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        allPlayers = await response.json();
        console.log('Players loaded successfully: ', allPlayers);
        renderPlayers(allPlayers);
    } catch (error) {
        console.error('failed to fetch players', error)
    }
});

// Thresholds were tuned manually after running the model — 50+ consistently
// flagged players with real bust signals (age, low FPPG, high TD rate).
// Below 40 tended to be legitimate studs. The middle band is the grey zone
// where context matters most.
function getRiskLevel(score) {
    if (score >= 50) return { label: 'High Risk', class: 'risk-high', color: '#ff3b3b' };
    if (score >= 40) return { label: 'Medium Risk', class: 'risk-medium', color: '#e2e60d' };
    return { label: 'Low Risk', class: 'risk-low', color: '#2ecc71' };
}

// Builds the leaderboard from scratch on every call —> clears the container,
// updates the results count, then loops through and stamps out a card per player.
// Rookies get a different card layout since they have no bust score,
// just a manually assigned bust risk and a note about their situation.
// Veterans get the full card with tooltip breakdown of all 6 scoring inputs.
function renderPlayers(players) {
    const element = document.getElementById('player-container');
    element.innerHTML = '';
    document.getElementById('results-count').textContent = `Showing ${players.length} players`; // ← MOVE HERE

    players.forEach((player, index) => {
        const card = document.createElement('div');
        card.className = 'player-card';

        if (player.data_flag === 'rookie') {
            card.style.setProperty('--risk-color', '#5b8cff');
            card.innerHTML = `
                <div class="rank">${index + 1}</div>
                <img src="${player.headshot || ''}" alt="${player.display_name}" onerror="this.src='silhouette.png'">
                <div class="player-info">
                    <div class="player-name">${player.display_name}</div>
                    <div class="player-meta">${player.position} · ${player.team} · ADP ${player.adp}</div>
                </div>
                <span class="risk-badge risk-rookie">Rookie</span>
                <div class="bust-score">
                    <div class="score-number" style="color:#5b8cff">${player.bust_risk}</div>
                    <div class="score-label">Bust Risk</div>
                </div>
                <div class="rookie-note">${player.note || ''}</div>
            `;
        } else {
            const risk = getRiskLevel(player.bust_score);
            card.style.setProperty('--risk-color', risk.color);
            card.innerHTML = `
                <div class="rank">${index + 1}</div>
                <img src="${player.headshot || ''}" alt="${player.name}" onerror="this.src='silhouette.png'">
                <div class="player-info">
                    <div class="player-name">${player.name}</div>
                    <div class="player-meta">${player.position} · ${player.team} · ADP ${player.adp}</div>
                </div>
                <span class="risk-badge ${risk.class}">${risk.label}</span>
                <div class="bust-score">
                    <div class="score-number" style="color:${risk.color}">${player.bust_score.toFixed(1)}</div>
                    <div class="score-label">Bust Score</div>
                    <div class="tooltip">
                        🏈 Age: ${player.score_age}<br>
                        🏥 Injury: ${player.score_injury}<br>
                        🎯 TD Regression: ${player.score_td}<br>
                        📊 Role Share: ${player.score_role}<br>
                        📈 ADP vs Finish: ${player.score_adp}<br>
                        ⚡ FPPG: ${player.score_fppg}
                    </div>
                </div>
                <div class="fppg">
                    <div class="fppg-number">${player.FPPG ? player.FPPG.toFixed(2) : 'N/A'}</div>
                    <div class="fppg-label">FPPG</div>
                </div>
            `;
        }
        element.append(card);
    });
}

// Runs every time a filter or search changes. Always works off the full
// allPlayers list so filters stack cleanly without losing data.
// Name search handles both veterans (player.name) and rookies (player.display_name)
// since the two groups store names under different keys.
function filterAndSort() {
    let position = document.getElementById('position-filter').value;
    let sort = document.getElementById('sort-filter').value;
    let search = document.getElementById('search-bar').value.toLowerCase();

    let filtered = allPlayers;

    if (position !== 'All') {
        filtered = filtered.filter(player => player.position === position);
    }

    if (search) {
        filtered = filtered.filter(player => {
            const name = (player.name || player.display_name || '').toLowerCase();
            return name.includes(search);
        });
    }

    if (sort === 'bust_score') {
        filtered.sort((a, b) => (b.bust_score || 0) - (a.bust_score || 0));
    } else if (sort === 'adp') {
        filtered.sort((a, b) => a.adp - b.adp);
    } else if (sort === 'name') {
        filtered.sort((a, b) => (a.name || a.display_name).localeCompare(b.name || b.display_name));
    }

    renderPlayers(filtered);
}

document.getElementById('position-filter').addEventListener('change', filterAndSort);
document.getElementById('sort-filter').addEventListener('change', filterAndSort);
document.getElementById('search-bar').addEventListener('input', filterAndSort);