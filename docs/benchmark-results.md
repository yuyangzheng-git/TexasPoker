# Benchmark Results

> Status: **PRELIMINARY — do not cite as evidence of a "stable advantage".**
> These results compare two algorithmic baselines only. The LLM-agent comparison
> (the actual research question) still needs real API runs; see the LLM section
> below. Numbers are included to demonstrate the harness, not to claim a finding.

## What was measured

A headless simulation of 3 × `mc` seats (Monte Carlo equity + pot odds rule-based
baseline) vs 3 × `random` seats (uniform random over legal actions).

## Methodology

- Command:
  ```bash
  python scripts/benchmark.py --hands 100 --sims 500 --seeds 42,43,44 \
      --rotate --require-position-coverage --rebuy --csv data/benchmark_results.csv
  ```
- 100 hands × 3 random seeds = 300 hands total (900 seat-hands per condition)
- **Position balancing**: the dealer button advances every hand (engine-driven),
  so agents at fixed seats visit every position (BTN/SB/BB/UTG/MP/CO) over each
  orbit. `--rotate` rotates the *initial* agent→seat alignment per seed instead
  of shifting it every hand (the old per-hand shift cancelled the dealer
  rotation and pinned every agent to a single relative position — e.g. always
  CO — which mixed position effects into the estimate). Positions and the
  dealer seat are recorded per hand in the CSV, and the run verifies with
  `--require-position-coverage` that every strategy covered all six positions.
- `--rebuy` resets stacks each hand, isolating per-hand strategy from bankroll dynamics
- Blinds: SB 50 / BB 100; starting stack 10,000
- Monte Carlo: 500 simulations per decision (live app uses 5000)
- Since commit fixing `build_remaining_deck`: known cards are excluded from the
  simulation deck (47 cards with 5 known, verified by `tests/test_monte_carlo_deck.py`)

## Results

Per-seed net chips/hand (with `--rotate` alignment per seed):

| seed | MC baseline | Random control |
|------|------------|----------------|
| 42   | +102.3     | −102.3         |
| 43   | +506.8     | −506.8         |
| 44   | −181.2     | +181.2         |

| Metric | MC baseline | Random control |
|--------|------------|----------------|
| Net chips per hand (mean over 3 seeds) | **+142.7** | **−142.7** |
| 95% t-CI of the mean (df = 2) | ±859.0 | ±859.0 |
| Pots won | 7.4% | 26.8% |
| VPIP (pre-flop, per hand) | 0.19 | 0.72 |
| PFR (pre-flop, per hand) | 0.08 | 0.48 |
| Runtime LLM fallbacks | 0 (no LLM seats) | 0 |

### Metric definitions

- **VPIP**: fraction of hands where the seat voluntarily put money in pre-flop
  (call/raise/all-in pre-flop). Blinds do not count.
- **PFR**: fraction of hands where the seat raised pre-flop. A pre-flop all-in
  counts as a raise only when its stack exceeded the amount needed to call
  (all-in calls do not count). Both are per-hand pre-flop statistics, not
  all-street action ratios.
- **Net chips per hand**: mean change in the seat's stack per hand.
- **95% t-CI**: t_critical(df) × sample std across seeds / √n
  (t(2) = 4.303 with 3 seeds; NIST/SEMATECH e-Handbook 1.3.5.2). Per-seed
  values are shown explicitly rather than only the pooled mean.

### Observations (with caveats)

- With 3 seeds the 95% t-interval is ±859 chips/hand and includes zero: the
  point estimate (+142.7) is **not** statistically distinguishable from zero
  at this sample size. The earlier +567.6 estimate was inflated by the
  per-hand rotation bug (agents were pinned to fixed relative positions).
- The random control wins more pots (26.8%) yet loses chips on average: it
  chases weak hands to showdown. Winning more pots ≠ winning more chips.
- These runs exercise the harness and the corrected hand evaluator; they are
  **not** results about LLM decision quality.

## Reproduce

```bash
python scripts/benchmark.py --hands 100 --sims 500 --seeds 42,43,44 \
    --rotate --require-position-coverage --rebuy --csv data/benchmark_results.csv
```

CSV columns: seed, hand_id, player, requested_agent, actual_agent, position,
dealer, net_chips, won_pot, vpip_hand, pfr_hand, fold/check/call/raise/allin,
decisions, avg_latency_ms, fallback_count, fallback_reasons, prompt_tokens,
completion_tokens.

## LLM-agent runs (planned)

The research question — do LLM agents add value over the algorithmic baseline —
requires real LLM calls. Protocol:

```bash
export ANTHROPIC_API_KEY=...
pip install -r backend/requirements.txt
python scripts/benchmark.py --hands 200 --seeds 42,43,44 --rotate --rebuy \
    --seats llm,llm,llm,mc,mc,mc --csv data/benchmark_llm_results.csv
```

What to report for LLM seats (recorded automatically by the harness):

- `fallback_count` / `fallback_reasons`: LLM parse or API failures (timeout, api_error),
  and init-failure degradation (`--llm-fallback` marks seats `mc_fallback`)
- `avg_latency_ms`: decision latency
- `prompt_tokens` / `completion_tokens`: cost basis (token counts)
- `actual_agent`: `llm` vs `llm_fallback` vs `mc_fallback` per seat-hand

If LLM initialization fails, the run **aborts** by default (no silent
degradation); `--llm-fallback` explicitly opts into degrading to the MC baseline,
and the CSV records the init failure as the seat's `fallback_reason`.

## Known limitations

- 3 seeds is far below the ≥10 independent replications needed for a meaningful
  t-interval; report per-seed values and treat the CI as indicative
- MC equity assumes uniform random opponents (no range modeling)
- 500 simulations per decision adds Monte Carlo noise to the baseline's decisions
- Random control is deliberately weak; a rule-based (preflop chart) or
  algorithmic (REINFORCE/CFR) baseline would be a stronger comparison
