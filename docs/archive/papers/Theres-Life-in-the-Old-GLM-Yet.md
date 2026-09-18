# There's Life in the Old GLM Yet!
## When a modern foundation model meets decades of actuarial tradition

Cillian Williamson, Scott Hawes, Jin Cui, Karol Gawlowski

> **Status: historical record — round-1 single-dataset study (TabPFN v2.0 era, eudirectlapse).** The eudirectlapse result is the disclosed exception to the 2026-08-06 verdict: on the canonical 6-dataset classification frontier, TabPFN is AUC #1 of 9 methods on all 6 datasets (master report §14.11). This paper's methods and round-1 findings are unchanged.

## The Surprising Question

When TabPFN emerged as a breakthrough in tabular machine learning, the hype was justified - zero hyperparameter tuning, minimal feature engineering and state of the art performance straight out of the box. The question seemed obvious: why would any actuary still use logistic regression?

We set out to answer this with genuine rigor, testing TabPFN v2.0 via API-based inference (without GPU). Using the eudirectlapse dataset (23,060 motor insurance policies, 13% lapse rate, 18 heterogeneous features across demographics, policy terms, premiums, and vehicles) we benchmarked TabPFN against not just GLM, but CatBoost, XGBoost and RandomForest. Modelling policyholder lapse rates is a typical task encountered by actuaries, often involving binary classification on imbalanced datasets with subtle behavioural-contractual interactions where interpretability matters as much as raw predictive power.

**Methodological Note:** All models were trained on identical 70:30 train/test splits with stratification (seed 45). Performance was evaluated on held-out test data using three complementary metrics: ROC AUC (Area Under the ROC Curve — how well the model ranks lapse cases above non-lapse cases; 0.5 = random, 1.0 = perfect), Brier score (mean squared difference between predicted probabilities and actual outcomes; lower is better), and F1 score (a balance of precision and recall, particularly useful for imbalanced datasets such as this one). Together these capture ranking ability, probability quality, and practical threshold performance. Data is publicly available via the CASdatasets package in R.

The results were somewhat surprising; TabPFN did not outperform on raw discrimination, and neither did the deep learning models.

## How TabPFN Works: The Foundation Model Approach

TabPFN — short for Tabular Prior-Data Fitted Network — is pre-trained on millions of synthetic tabular datasets to learn general prediction strategies. When applied to new data, it takes the entire training sample as context and produces predictions in a single forward pass, with no need for hyperparameter tuning or cross-validation. For practitioners, this means fast baseline results and considerably less manual feature engineering in early exploration. Success depends on whether the pre-training distribution aligns with the specific problem at hand. On well-structured insurance problems with known patterns, this advantage diminishes — and GLMs retain a strong position where effects are primarily additive and where interpretability is required for governance or regulatory purposes. On novel problems with complex interactions, TabPFN's pre-training has the potential to unlock hidden signal.

## What We Actually Discovered

Reflecting more deeply on our analysis reveals the reasons for the somewhat surprising results - simple, intuitive patterns dominate the signal for this particular dataset, so there is little need for more complex modelling:

- **Age effect:** Lapse rates declined sharply with policyholder age, from approximately 18% at age 25 to 8% at age 60. This reveals a monotonic trend perfectly suited to the structure of the GLM.
- **Payment frequency effect:** Premium payment frequency was a clear discriminator, with annual payments lapsing 40% more than monthly equivalents (21% vs 15%). This is a known behavioral pattern in retention economics.
- **Policy tenure, vehicle age and region** all showed smooth, additive effects with no significant interactions.

These patterns align with established actuarial knowledge: retention is driven primarily by demographic stability and contractual factors rather than complex interactions. This explains why simpler models sufficed.

On a problem as well-structured as this, the GLM matched TabPFN's discrimination ability (ROC AUC 0.599 vs 0.593). Both outperformed CatBoost (0.591), RandomForest (0.578), and XGBoost (0.551).

Why did tree-based models underperform? Tree ensembles excel at capturing non-linear interactions and threshold effects. Their poor performance here confirms our exploratory finding: our lapse dataset lacks complex interactions. When relationships are primarily monotonic and additive (as with age and payment frequency), ensemble methods offer no advantage; they add computational cost without predictive gain. This is an important insight for actuaries: not every problem requires sophisticated machinery. The 5-model comparison revealed an uncomfortable truth: when underlying relationships are primarily simple and additive, classical methods hold their own. Complex models do not help; they just add latency and opacity.

Is there potential for TabPFN to add value in this scenario? The answer is yes but in a subtle yet valuable way.

## The Calibration Insight

Probability calibration (i.e. how well predicted probabilities align with actual outcomes) matters to actuaries. Pricing models must estimate true lapse probabilities; reserving models must reflect actual frequencies. Without calibration, probabilities can systematically under/overestimate true outcomes. Raw TabPFN was overconfident (Brier score 0.1108), a known neural network trait. Brier score measures calibration quality as mean squared difference between predicted and observed outcomes (0 = perfect, 0.25 = worst). Post-hoc isotonic calibration — a technique that adjusts raw model scores to better-calibrated probabilities after training, without modifying the underlying model — improved this +0.87% to 0.1080, outperforming GLM's 0.1098. The practical meaning is direct: if a model assigns a probability of 0.20, roughly 20% of those cases should actually lapse. Without calibration, that alignment cannot be assumed. Recent enterprise-scale analysis confirms that temperature scaling and isotonic regression perform similarly on large datasets, with temperature scaling offering computational advantages.

## Why This Matters: The Real Value Proposition

TabPFN is not just about winning on raw accuracy. It is about three things:

- **Workflow Efficiency:** GLM required 8-12 hours of binning, grouping, testing interactions. This requires considerable domain knowledge and expert judgement from the analyst. TabPFN accepted raw data and delivered results in minutes. For quarterly pricing cycles or exploratory phases, this speed is material.
- **Probability Accuracy:** An improvement of 0.87% on the Brier score translates to $50K-$100K in reduced mispricing on a 100,000-policy portfolio. This additional (seemingly small) gain in precision can translate to a measurable financial impact.
- **Robustness:** TabPFN produced identical results on raw and cleaned data. GLM required actuarial judgment to stabilise. For resource-constrained firms, fewer decisions means fewer opportunities for error.

## The Trade-Offs Actuaries Care About

## How to Choose

The GLM shines when real-time predictions matter, the structure of the data is simpler and there is a need to demonstrate transparency to regulators and other stakeholders. TabPFN on the other hand has significant potential when probability accuracy is needed and to reveal potential interactions in the data. An optimal strategy for practitioners is simply to deploy both if resources allow.

## Study Limitations

This analysis focuses on a single motor insurance dataset with additive risk factors. This has several key limitations which may be addressed by further work in this area:

- Single domain: Motor insurance lapse may not generalise to life, health, or claims frequency with different interaction structures.
- Single geography: UK direct-channel only.
- Stable environment: Assumes historical patterns persist.
- Known problem: Policy Lapse is well-studied. Novel problems with unknown interactions may differ.
- Research transparency: Public data (CASdatasets). Fixed random seeds (seed=45). Results reproducible using scikit-learn, TabPFN v2.0 API, standard calibration libraries.

For a full step-by-step replication protocol (environment, run order, seeds, expected artifacts, and checks), see: docs/archive/archive/papers/APPENDIX_REPRODUCIBILITY.md.

## The Honest Conclusion

We entered this study expecting TabPFN to dominate. It did not. Two critical caveats emerge from our work:

- **Caveat #1:** We tested eudirectlapse (UK motor), which has additive risk factors. Complex problems (life underwriting, catastrophe modeling) might differ from this. Tree-based models underperformed here because this problem lacks interactions. In domains with genuine complexity, TabPFN could unlock signal that GLM's additive assumption misses.
- **Caveat #2:** We benchmarked TabPFN v2.0 via API (no GPU). v2.5 achieves improved in-context learning on tabular benchmarks with enhanced robustness to data distribution shift. Real-world domain adaptation shows that continued pre-training on actual insurance data further improves TabPFN performance. Local GPU would reduce 7.6s to approximately 0.2-0.5s, changing real-time calculus. The calibration advantage is robust while the inference speed comparison is API-specific.

## The Actual Finding

On the eudirectlapse problem (a prototypical actuarial challenge with straightforward, additive risk drivers) the simple structure that GLM exploits remains unbeaten for raw discrimination. TabPFN's foundation model architecture did not unlock any hidden signal because the signal was not hidden. It is visible in age, payment frequency and tenure. Actuaries have been solving this problem elegantly for decades.

Actuaries should still pay attention however. The calibration advantage is real and actionable. A 0.87% Brier improvement compounds into meaningful value. The potential for increased workflow efficiency is significant also: hours saved matter when under time pressure. TabPFN also deals robustly with raw data without the need for curation by hand.

The right method is highly application dependent. If speed and regulatory acceptance are key, the GLM wins. If probability accuracy and workflow simplicity are paramount, the edge offered by a calibrated TabPFN model is meaningful. Do not adopt TabPFN because it is trendy - adopt it when your specific problem needs what it offers. Conversely, do not dismiss GLM because it is decades old. On well-structured problems with interpretability requirements, it remains formidable.

The future of actuarial modelling is about understanding the genuine strengths of each tool and deploying them strategically. Test, measure, and decide based on the problem context rather than hype. There is still plenty of life in the old GLM yet - and room for TabPFN where it excels.

## Summary Comparison Table

| Dimension | GLM | TabPFN |
|---|---:|---:|
| Discrimination (AUC) | 0.599 | 0.593 |
| Calibration (Brier) | 0.1098 | 0.1080 (best) |
| Interpretability | Coefficients | Black box |
| Inference speed | 0.01s | 7.6s (API) |
| Feature engineering | Required | None |
