# AI Reviewer Evaluation Report
**Date:** Automated Analysis

## Introduction
This report presents a comprehensive evaluation of AI reviewers compared to human performance.

## Score Statistics

### Score Distributions
![Distribution of Review Scores (Human vs AI)](plots/human_vs_ai_boxplot.png)

![Average Score Profile: Human vs AI](plots/radar_human_vs_ai.png)

### Per-Evaluator Statistics
![Score Distribution by Evaluator](plots/evaluator_boxplot.png)

### Per-Evaluator per Metric Statistics
![Score Distribution: Evaluator per Metric](plots/evaluator_per_metric_boxplot.png)

## Statistical Significance Tests

### Methodology
We confirm performance differences using Mann-Whitney U (unpaired), Wilcoxon Signed-Rank (paired), and assess variance equality with Levene's Test. Effect size is measured by Cliff's Delta.

### Global Analysis (Human vs All AI)
| Metric           | MW U (p)   |   Wilcoxon (p) |   Levene (p) |   Cliff's Delta |
|:-----------------|:-----------|---------------:|-------------:|----------------:|
| Coverage         | 0.4727     |         0.2872 |       0.5537 |          -0.037 |
| Specificity      | 0.0148*    |         0.3177 |       0.6603 |           0.126 |
| Correctness      | 0.6081     |         0.6546 |       0.1543 |           0.027 |
| Constructiveness | 0.7601     |         0.9317 |       0.9859 |           0.016 |
| Stance           | 0.1758     |         0.2412 |       0.6084 |          -0.069 |

### Per-Model Analysis
![Performance Profile per AI Model](plots/radar_models.png)

#### Model: claude-sonnet-4-20250514
| Metric           |   MW U (p) |   Wilcoxon (p) |   Levene (p) |   Cliff's Delta |
|:-----------------|-----------:|---------------:|-------------:|----------------:|
| Coverage         |     0.978  |         0.9204 |       1      |          -0.002 |
| Specificity      |     0.1591 |         0.5735 |       0.7804 |           0.119 |
| Correctness      |     0.4857 |         0.612  |       0.2798 |           0.059 |
| Constructiveness |     0.3805 |         0.5026 |       0.9137 |           0.074 |
| Stance           |     0.4292 |         0.2853 |       0.4104 |          -0.066 |

#### Model: fudan
| Metric           |   MW U (p) |   Wilcoxon (p) |   Levene (p) |   Cliff's Delta |
|:-----------------|-----------:|---------------:|-------------:|----------------:|
| Coverage         |     0.5627 |         0.2158 |       0.3076 |          -0.049 |
| Specificity      |     0.1847 |         0.4504 |       0.452  |           0.112 |
| Correctness      |     0.7863 |         0.4491 |       0.756  |          -0.023 |
| Constructiveness |     0.9296 |         0.5149 |       0.9294 |          -0.007 |
| Stance           |     0.276  |         0.0673 |       0.4246 |          -0.091 |

#### Model: gpt-5-chat-latest
| Metric           |   MW U (p) |   Wilcoxon (p) |   Levene (p) |   Cliff's Delta |
|:-----------------|-----------:|---------------:|-------------:|----------------:|
| Coverage         |     0.8837 |         0.6992 |       0.9562 |          -0.012 |
| Specificity      |     0.1752 |         0.5455 |       0.9357 |           0.115 |
| Correctness      |     0.5446 |         0.4443 |       0.1362 |           0.051 |
| Constructiveness |     0.8546 |         0.9498 |       0.4333 |          -0.015 |
| Stance           |     0.6342 |         0.6469 |       0.9548 |          -0.04  |

#### Model: hkust-reviewer
| Metric           |   MW U (p) | Wilcoxon (p)   |   Levene (p) |   Cliff's Delta |
|:-----------------|-----------:|:---------------|-------------:|----------------:|
| Coverage         |     0.0503 | 0.0104*        |       0.8714 |          -0.165 |
| Specificity      |     0.5538 | 0.9490         |       0.6102 |           0.05  |
| Correctness      |     0.9494 | 0.6110         |       0.4044 |           0.005 |
| Constructiveness |     0.3369 | 0.1553         |       0.5075 |          -0.081 |
| Stance           |     0.4284 | 0.3116         |       0.4613 |          -0.067 |

#### Model: rpi
| Metric           | MW U (p)   |   Wilcoxon (p) |   Levene (p) |   Cliff's Delta |
|:-----------------|:-----------|---------------:|-------------:|----------------:|
| Coverage         | 0.1428     |         0.5453 |       0.5192 |           0.123 |
| Specificity      | 0.0224*    |         0.1919 |       0.6972 |           0.193 |
| Correctness      | 0.9494     |         0.7463 |       0.8985 |           0.005 |
| Constructiveness | 0.5533     |         0.927  |       0.9648 |           0.05  |
| Stance           | 0.1941     |         0.2312 |       0.1507 |          -0.109 |

#### Model: stanford
| Metric           |   MW U (p) |   Wilcoxon (p) |   Levene (p) |   Cliff's Delta |
|:-----------------|-----------:|---------------:|-------------:|----------------:|
| Coverage         |     0.1656 |         0.1145 |       0.4615 |          -0.117 |
| Specificity      |     0.05   |         0.3699 |       0.1712 |           0.166 |
| Correctness      |     0.47   |         0.5009 |       0.1237 |           0.061 |
| Constructiveness |     0.3763 |         0.8481 |       0.676  |           0.074 |
| Stance           |     0.6072 |         0.4528 |       0.6338 |          -0.043 |

## Turing Test Analysis (AI Detection)
Evaluators were asked to guess if the review was written by AI or Human. We present the confusion matrices below.
| Evaluator   |   Accuracy |   Precision |   Recall |       F1 |
|:------------|-----------:|------------:|---------:|---------:|
| Bernhard    |   0.666667 |    0.666667 | 1        | 0.8      |
| Guang       |   0.377778 |    0.535714 | 0.5      | 0.517241 |
| Justin      |   0.6      |    0.657895 | 0.833333 | 0.735294 |
| Luping      |   0.477778 |    0.740741 | 0.333333 | 0.45977  |
| Tolga       |   0.477778 |    0.666667 | 0.433333 | 0.525253 |
| Yixuan      |   0.566667 |    0.769231 | 0.5      | 0.606061 |
| Overall     |   0.527778 |    0.66055  | 0.6      | 0.628821 |

![Overall Confusion Matrix (AI Detection)](plots/turing_cm_overall.png)

### Per-Evaluator Confusion Matrices
![Confusion Matrices per Evaluator](plots/turing_cm_evaluators_combined.png)

## Inter-Evaluator Agreement
Cohen's Kappa and Gwet's AC2 agreement between evaluators on review scores (discretized).

### Cohen's Kappa
| Evaluator   | Bernhard   | Guang   | Justin   | Luping   | Tolga   | Yixuan   |
|:------------|:-----------|:--------|:---------|:---------|:--------|:---------|
| Bernhard    | -          | 0.03    | -        | -0.01    | 0.05    | -        |
| Guang       | 0.03       | -       | -0.08    | -0.01    | -       | 0.26     |
| Justin      | -          | -0.08   | -        | -        | 0.13    | -0.06    |
| Luping      | -0.01      | -0.01   | -        | -        | -       | 0.24     |
| Tolga       | 0.05       | -       | 0.13     | -        | -       | 0.11     |
| Yixuan      | -          | 0.26    | -0.06    | 0.24     | 0.11    | -        |

### Gwet's AC2
Gwet's AC2 is often more robust to marginal imbalance and ordinal data.
| Evaluator   | Bernhard   | Guang   | Justin   | Luping   | Tolga   | Yixuan   |
|:------------|:-----------|:--------|:---------|:---------|:--------|:---------|
| Bernhard    | -          | -0.16   | -        | -0.37    | -0.05   | -        |
| Guang       | -0.16      | -       | -0.09    | -0.30    | -       | 0.26     |
| Justin      | -          | -0.09   | -        | -        | 0.07    | -0.15    |
| Luping      | -0.37      | -0.30   | -        | -        | -       | 0.18     |
| Tolga       | -0.05      | -       | 0.07     | -        | -       | 0.03     |
| Yixuan      | -          | 0.26    | -0.15    | 0.18     | 0.03    | -        |

## Breakdown wrt Accepted versus Rejected Papers
Analysis of review characteristics based on the final decision (Accept vs Reject).

### Scores and Differences

**Human Scores (Accept/Reject)**  
![Human Scores](plots/decision_human_scores.png)

**AI Scores (Accept/Reject)**  
![AI Scores](plots/decision_ai_scores.png)



### Turing Test Confusion Matrices
![Turing Test Confusion Matrices (Accept/Reject)](plots/decision_turing_combined.png)

### Additional Metrics
**AI Detection Metrics**  
![AI Detection Metrics](plots/decision_detection_metrics.png)

**Dataset Distribution**  
![Dataset Distribution](plots/decision_distribution.png)
# Appendix: Guide to Interpretations

## Interpreting Box Plots
The box plots in this report visualize the distribution of review scores.
* **Box**: Represents the Interquartile Range (IQR), spanning from the 25th percentile (Q1) to the 75th percentile (Q3). It contains the middle 50% of the data.
* **Median**: The line inside the box marks the median score (50th percentile).
* **Whiskers**: Extend from the box to the most extreme data points that are not considered outliers. Typically, this is 1.5 * IQR.
* **Empty Circles (Outliers)**: Points lying beyond the whiskers are plotted individually as empty circles. These represent outlier scores that are unusually high or low compared to the rest of the distribution.

## Statistical Methodology Details
This section explains the intuition and computation behind the statistical tests used.

### Mann-Whitney U Test
**Intuition**: A non-parametric test for independent samples (e.g., Human vs AI scores across different papers). It assesses whether one group's values are stochastically larger than the other's. It does not assume a normal distribution.
**Computation**: All observations are ranked together. The sum of ranks for each group is calculated. The U statistic is derived from these rank sums, comparing the number of times a value from one group precedes a value from the other.

### Wilcoxon Signed-Rank Test
**Intuition**: A non-parametric paired test used for per-model comparisons where we have matched scores (Human and AI reviewing the *same* paper). It tests if the distribution of differences is symmetric about zero.
**Computation**: Differences between paired scores (d_i = x_H - x_A) are calculated. Absolute differences |d_i| are ranked. Ranks are signed according to the sign of d_i. The test statistic W is the sum of positive ranks.

### Levene's Test
**Intuition**: Tests the null hypothesis that the variances (spread) of the two groups are equal (Homogeneity of Variance).
**Computation**: It performs an Analysis of Variance (ANOVA) on the absolute deviations of scores from their group means (or medians). A significant p-value suggests the groups have different consistency levels.

### Cliff's Delta
**Intuition**: An effect size measure quantifying the magnitude of difference between two groups. It represents the probability that a randomly selected value from one group is greater than one from the other, minus the reverse probability. values range from -1 to +1.
**Computation**:
delta = (#(x_H > x_A) - #(x_H < x_A)) / (n_H * n_A)
where x_H and x_A are scores from Human and AI groups respectively. 
Interpretation: |delta| < 0.147 (Negligible), < 0.33 (Small), < 0.474 (Medium), else (Large).

### Cohen's Kappa
**Intuition**: Measures inter-rater agreement for categorical items, correcting for agreement occurring by chance.
**Computation**:
kappa = (p_o - p_e) / (1 - p_e)
where p_o is the relative observed agreement, and p_e is the hypothetical probability of chance agreement based on marginal frequencies.

### Gwet's AC2
**Intuition**: An alternative to Cohen's Kappa specific for ordinal data and robust to marginal imbalance (paradoxes of Kappa). It estimates chance agreement based on average marginal probabilities.
