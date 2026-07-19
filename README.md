# ⚽ World Cup Final Companion — Spain v Argentina

A second-screen PWA for today's final (3pm ET, MetLife Stadium). Live score, match stats,
event timeline, win probability, attack momentum, xG race, and a pass-the-phone
**"Call The Next Event"** prediction game with a leaderboard.

## Quick start (2 minutes)

```bash
cd worldcup-companion
python3 serve.py
# open http://localhost:8080
```

That's it — the ESPN feed needs no key. Score, stats, timeline, and win probability work immediately.

## Unlock momentum + xG (5 more minutes, worth it)

BALLDONTLIE's shot maps and attack momentum require their GOAT tier —
**there's a 48-hour free trial** (card required, cancel anytime, 5 req/min):

1. Create an account at https://app.balldontlie.io and start the FIFA World Cup GOAT trial.
2. Copy your API key, then:

```bash
export BDL_API_KEY="your-key-here"
python3 serve.py
```

The momentum and xG panels light up automatically. The proxy caches BDL responses 45s
and the app alternates calls, so you stay well under the trial's 5 req/min.

## Install as a PWA

In Chrome/Edge: address bar → Install icon. On iPhone: Share → Add to Home Screen.
Allow notifications when prompted to get goal alerts even when the tab is backgrounded.

## How it's wired

| Piece | Source | Key? |
|---|---|---|
| Score, clock, status | ESPN `scoreboard` (unofficial) | No |
| Team stats, odds, events | ESPN `summary?event=760517` | No |
| Attack momentum | BDL `/match_momentum` | GOAT trial |
| Shot-by-shot xG | BDL `/match_shots` | GOAT trial |
| Win probability | Pre-match: ESPN odds → implied. In-play: client-side Poisson model | No |

`serve.py` is a stdlib-only static server + API proxy: keeps your BDL key server-side,
sidesteps CORS, and caches responses (ESPN 12s, BDL 45s) so polling never hits rate limits.

## The prediction game

Each player types their name, picks what happens in the next 10 minutes
(goal +5, red card +8, yellow +3, sub +2, corner +1, "nothing" +4), and locks it in.
Correct calls score points and build 🔥 streaks; the leaderboard persists in
localStorage across refreshes. Pass the phone around — that's the fun part.

## Caveats

- ESPN's API is unofficial and can change without notice; the app fails soft (panels hide, no crashes).
- Event classification is text-based; a weird commentary phrasing can misfile an event.
- Win probability is a naive model for entertainment — not betting advice.
- Personal use only. Don't rebroadcast or resell licensed match data.

## If something breaks mid-match

- Blank score → check `http://localhost:8080/api/health`, then the browser console.
- Momentum/xG hint won't clear → key not exported in the same shell you ran `serve.py` from.
- BDL 429s → you're on the trial's 5 req/min; the proxy already backs off, just wait a minute.
