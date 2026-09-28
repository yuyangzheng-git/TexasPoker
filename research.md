# Research Framing

This project is a Texas Hold'em simulation platform with LLM-based agents, Monte Carlo equity estimation, and real-time decision visualization. I built it as a testbed for studying AI decision-making under uncertainty and comparing language-model reasoning with algorithmic baselines.

## Research Question

How do LLM-based poker agents compare with algorithmic (Monte Carlo + pot odds) baselines on decision quality, chip outcomes, and explainability under uncertainty?

### Sub-questions

1. Does LLM reasoning add measurable value over pure equity/pot-odds heuristics, or does it mainly add latency and cost?
2. How do invalid/fallback actions from LLMs affect long-run performance?
3. What prompting strategies change risk preference and action consistency?

## Testbed Components

| Component | File | Role |
|-----------|------|------|
| Game engine | `backend/game_engine.py` | Betting rounds, side pots, winner determination |
| Hand evaluation | `backend/hand_evaluator.py` | Best-5-of-7 scoring (C(7,5) enumeration) |
| Monte Carlo equity | `backend/monte_carlo_equity.py` | Win probability via simulation |
| LLM agent | `backend/llm_agent.py` | Prompt building, response parsing, fallback actions |
| Memory / profiling | `backend/agent_engine.py` | Opponent profiling, VPIP/PFR tracking |
| Benchmark harness | `scripts/benchmark.py` | Headless simulation, CSV export |

## Experiments

### Experiment 1: LLM agent vs Monte Carlo baseline

Compare LLM agent decisions against Monte Carlo equity estimates.

- Metrics: win rate, expected value (chips per hand), invalid action rate, latency, token cost
- Protocol: `python scripts/benchmark.py --seats llm,llm,llm,mc,mc,mc --hands 200 --seeds 42,43,44`

### Experiment 2: Prompting strategy comparison

Compare prompting strategies (e.g., different personas in `config/agent_personas.json`, temperature settings).

- Metrics: consistency (same state → same action), risk preference (aggression rate), strategic quality (chips per hand), explanation quality (thinking output)

### Experiment 3: LLM agent vs rule-based agent

- Metrics: chips won/lost, fold/call/raise distribution, long-run performance

Preliminary results (two algorithmic baselines only — not yet LLM decision quality)
are in [docs/benchmark-results.md](docs/benchmark-results.md).

## Metrics Definitions

- **Net chips per hand**: change in a seat's stack per hand; primary performance metric
- **Win rate**: share of pots won (note: can be high while losing chips — see results)
- **VPIP**: voluntary money in pot pre-flop = hands with a voluntary pre-flop
  call/raise/all-in / hands played (per-hand, not an all-street action ratio)
- **PFR**: pre-flop raise = hands with a pre-flop raise / hands played; an
  all-in counts only when it raises (stack above the call price), all-in calls do not
- **Invalid action rate**: LLM outputs that fail parsing/validation and require a fallback action
- **Latency & token cost**: recorded per decision by the benchmark harness
  (`avg_latency_ms`, `prompt_tokens`, `completion_tokens` in the CSV)

## Limitations

- LLM decisions are prompt-sensitive; personas in `config/agent_personas.json` are hand-written
- Monte Carlo equity ignores opponent ranges (uniform random opponents)
- Small hand counts have high variance; use ≥500 hands for stable estimates
- LLM latency and token cost make real-time LLM agents expensive
- Simulation results may not transfer to human games

## Running the Benchmark

```bash
# 100 手牌 × 3 种子，MC 基线 vs 随机对照；庄家轮转平衡位置，
# --rotate 按种子轮换初始排布，--require-position-coverage 校验位置覆盖
python scripts/benchmark.py --hands 100 --sims 500 --seeds 42,43,44 \
    --rotate --require-position-coverage --rebuy

# 加入 LLM 席位（需要 ANTHROPIC_API_KEY；初始化失败默认终止实验）
python scripts/benchmark.py --hands 100 --seeds 42,43,44 --rotate --rebuy \
    --seats llm,llm,llm,mc,mc,mc
```

Results are written to `data/benchmark_results.csv` (per-hand rows include
`position` and `dealer` so positional balance can be re-checked after the fact).
