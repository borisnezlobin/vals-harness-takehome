what are the models convincing each other of?
- price of something
    - "this is worth $500" / "get the lowest price you can"

attacker (A) model
- $600 maximum price

defender (S for seller) model
- given a value ($500 car)
- e.g. getting $800 is good
- try to settle on a price

note that the maximum price could be less than the seller's minimum price. in this case the models should be rewarded for how close to optimal they settle (e.g. the buyer's maximum is $500, the seller's minimum is $600; the optimal price is $550, so $525 should reward the buyer more while $675 should reward the seller more. it is better to accept a bad offer than not take any offer.)

continuous grade:
- defender: value - $500
- attacker $600 - value

A: gives first offer:
- cap explanations at 1000 characters
- cap conversation at 10 turns — models are aware
S: make a counteroffer: `propose_offer 550`
A: explanation: 515. `propose_offer 515`
S: `accept_offer 515`

tools:
    propose_offer (int n)
    accept_offer (int n)
    end

potential improvements:
- normalize scores by the spread between the two reserves instead of the price (currently surplus / midpoint of the two reserves)

## Running it

Put `OPENROUTER_API_KEY=...` in `.env`, then:

```sh
make install                 # uv sync, npm install, Playwright's Chromium
uv run negotiate run         # round robin of the default models over every scenario
uv run negotiate run --models deepseek/deepseek-v4.1-flash openai/gpt-oss-120b --scenarios used-car --repeats 3
uv run negotiate run --resume runs/<run id>   # finish a run that was interrupted
uv run negotiate report      # leaderboard of the latest run in the terminal
make dashboard               # http://localhost:3000, reads ../runs and updates while a run is going
make check                   # ruff, pyright, pytest, eslint, tsc, vitest
make e2e                     # Playwright against dashboard/tests/fixtures/runs
```

Each run writes `runs/<run id>/config.json`, `games.jsonl` (one full trace per game, including each model's private reasoning, token use and cost) and `summary.json` (leaderboard and pairings, rewritten after every game). `negotiation/records.py` and `dashboard/lib/types.ts` describe the same files and share a `SCHEMA_VERSION`.

Scoring lives in `negotiation/scoring.py`: surplus is divided by the midpoint of the two limits, gains count linearly, losses fall off as `-P(1 - e^(s/P))` toward the no-deal penalty `P` (1.0), and a deal always scores at least 1e-9 above no deal.
