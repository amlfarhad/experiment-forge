# experiment-forge — Statistical Experimentation Platform

Most A/B testing tutorials teach you to run a t-test and check if p < 0.05. In production at FAANG-scale, that's about 10% of the work. The other 90% is everything this project covers: knowing when your experiment is broken, reducing the sample you need, stopping early without lying to yourself, and making decisions when you have multiple metrics.

This platform implements the techniques that power experimentation at Microsoft, Netflix, Meta, and Google — with simulations that **prove** why each technique matters.

## What Makes This Different

| Technique | What It Does | Why It Matters | Where It's Used |
|-----------|-------------|----------------|-----------------|
| **CUPED** | Reduces metric variance using pre-experiment data | 40-50% fewer users needed for same statistical power | Microsoft, Netflix, Meta |
| **Sequential Testing** | Valid p-values at any point during the experiment | Stop experiments early without inflating false positives | Optimizely, Netflix |
| **Peeking Simulation** | Proves that naive continuous monitoring gives ~26% FPR | Understanding this is table stakes for DS interviews | Every mature platform |
| **SRM Detection** | Catches broken randomization before you analyze | The #1 experiment diagnostic — catches pipeline bugs | Microsoft, Google |
| **Multi-Armed Bandits** | Adaptively routes traffic to winning variants | Minimizes user exposure to worse experiences | Google, Spotify |
| **Bayesian A/B Testing** | Answers "P(B > A)?" instead of "P(data \| no effect)?" | More intuitive, no peeking problem, natural stopping | Netflix, Spotify |
| **Delta Method** | Correct variance for ratio metrics (revenue/session) | Naive SE is wrong for ratio metrics — delta method fixes it | Uber, Airbnb |

## Simulations That Prove Understanding

### The Peeking Problem
```
$ python -m simulations.peeking_sim

With 20 peeks at α=0.05:
  Fixed-horizon FPR: 4.8% (expected 5.0%)
  Peeking FPR:       26.1% (inflated 5.2x)

  Peeking inflates false positives by 5.2x!
```

### CUPED Variance Reduction
```
$ python -m simulations.cuped_sim

With pre/post correlation of 0.7:
  Standard power: 62.4%
  CUPED power:    91.2% (+28.8%)
  Effective sample multiplier: 2.0x

  CUPED makes 5,000 users as powerful as 10,000 users without CUPED.
```

### SRM Detection Across Scenarios
```
$ python -m simulations.srm_sim

  clean_50_50                | detection_rate=  0.1%
  slight_imbalance (50.5%)   | detection_rate= 12.3%
  moderate_imbalance (52%)   | detection_rate= 99.8%
  severe_imbalance (55%)     | detection_rate=100.0%
```

## Modules

### Core (`core/`)
- **`experiment.py`** — Continuous metrics (Welch's t-test), proportions (z-test), ratio metrics (delta method)
- **`power_analysis.py`** — Sample size calculation, power curves, MDE estimation
- **`sequential.py`** — Group sequential testing with O'Brien-Fleming and Pocock alpha spending
- **`multiple_testing.py`** — Bonferroni, Holm-Bonferroni, Benjamini-Hochberg (FDR)

### Variance Reduction (`variance_reduction/`)
- **`cuped.py`** — CUPED implementation with experiment-level analysis
- **`stratification.py`** — Stratified estimation for heterogeneous populations

### Advanced (`advanced/`)
- **`bandits.py`** — Epsilon-Greedy, UCB1, Thompson Sampling with regret simulation
- **`bayesian.py`** — Bayesian A/B testing for proportions and continuous metrics
- **`interference.py`** — Network spillover detection and interference simulation

### Simulations (`simulations/`)
- **`peeking_sim.py`** — Proves peeking inflates FPR to ~26%
- **`cuped_sim.py`** — Demonstrates 40-50% variance reduction with correlated covariates
- **`srm_sim.py`** — SRM detection sensitivity across imbalance levels

## Quick Start

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run all demonstrations
python pipeline.py

# Run individual simulations
python -m simulations.peeking_sim
python -m simulations.cuped_sim
python -m simulations.srm_sim
```

## Testing

```bash
pytest tests/ -v
```

## Project Structure

```
experiment-forge/
├── pipeline.py                         # Run all demos
├── core/
│   ├── experiment.py                   # t-test, z-test, delta method
│   ├── power_analysis.py               # Sample size & power curves
│   ├── sequential.py                   # Group sequential testing
│   └── multiple_testing.py             # Bonferroni, BH, Holm
├── variance_reduction/
│   ├── cuped.py                        # CUPED implementation
│   └── stratification.py              # Stratified estimation
├── advanced/
│   ├── bandits.py                      # ε-Greedy, UCB1, Thompson Sampling
│   ├── bayesian.py                     # Bayesian A/B testing
│   └── interference.py                # Network spillover detection
├── simulations/
│   ├── peeking_sim.py                  # Peeking problem proof
│   ├── cuped_sim.py                    # CUPED benefit demonstration
│   └── srm_sim.py                      # SRM detection sensitivity
└── tests/
    ├── test_experiment.py
    ├── test_cuped.py
    ├── test_bandits.py
    └── test_sequential.py
```

## References

- Deng et al., 2013 — *Improving the Sensitivity of Online Controlled Experiments by Utilizing Pre-Experiment Data* (CUPED, Microsoft)
- Johari et al., 2017 — *Peeking at A/B Tests* (Always-valid inference)
- Fabijan et al., 2019 — *Diagnosing Sample Ratio Mismatch in Online Controlled Experiments* (SRM, Microsoft)
- Chapelle et al., 2011 — *An Empirical Evaluation of Thompson Sampling* (Bandits)
- Kohavi et al., 2020 — *Trustworthy Online Controlled Experiments* (A/B Testing Bible)
