# Improvement Plan for RA Applications

## Current Status

This project is valuable because it combines LLM agents, game simulation, WebSocket interaction, poker decision logic, hand evaluation, and Monte Carlo equity estimation. It can be reframed as a research testbed for AI decision-making under uncertainty.

## Best Research Fit

- LLM agent decision-making
- Decision-making under uncertainty
- Explainable AI behavior
- Human-AI or AI-AI strategic interaction
- Baseline comparison between LLM agents and algorithmic agents

Best professor matches:

- Sam Kirshner
- Mary-Anne Williams
- Robert Kohn

## Main Issues

- The main visible README is frontend-oriented.
- The research motivation is not yet clear.
- There are no benchmark results comparing LLM agents with baselines.
- There are deployment archives committed in the repo, which may look messy.
- It is not obvious whether secrets or local config files have been checked.

## Highest Priority Improvements

1. Add a top-level README focused on the whole system, not only the frontend.
2. Add `research.md` explaining the project as an AI decision-making testbed.
3. Add experimental results comparing LLM agents with rule-based or Monte Carlo baselines.
4. Remove unnecessary committed archive files if they are not required.
5. Add clear test and run instructions.

## Suggested Experiments

Experiment 1:

- Compare LLM agent decisions against Monte Carlo equity estimates.
- Metrics: win rate, expected value, invalid action rate, latency, token cost.

Experiment 2:

- Compare different prompting strategies.
- Metrics: consistency, risk preference, strategic quality, explanation quality.

Experiment 3:

- Compare LLM agent vs rule-based agent.
- Metrics: chips won/lost, fold/call/raise distribution, long-run performance.

## Concrete Tasks

- Add `/docs/research-framing.md`.
- Add `/docs/benchmark-results.md`.
- Add a script that runs 100 simulated hands and exports results to CSV.
- Add plots or a table summarizing agent performance.
- Add a clear architecture section for backend, frontend, agent engine, and equity calculator.
- Confirm that `config/` has no private keys.

## Suggested README Pitch

Add this near the top:

> This project is a Texas Hold'em simulation platform with LLM-based agents, Monte Carlo equity estimation, and real-time decision visualization. I built it as a testbed for studying AI decision-making under uncertainty and comparing language-model reasoning with algorithmic baselines.

## RA Application Value

Current value: Medium-High

This can become a very strong research portfolio project after you add benchmark results.

