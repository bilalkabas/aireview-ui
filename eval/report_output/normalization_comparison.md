# Normalization Effects Analysis

Comparison of statistical test results across different score normalization techniques.

## Effect on Cliff's Delta (Effect Size)
*   **Range**: -1 to +1
*   **Interpretation**: >0 means Human > AI. <0 means AI > Human.
*   **Magnitude**: |d| < 0.147 (Negligible), < 0.33 (Small), < 0.474 (Medium), else (Large).

|                  |   evaluator |   evaluator_metric |   evaluator_metric_target |   none |
|:-----------------|------------:|-------------------:|--------------------------:|-------:|
| coverage         |      -0.037 |             -0.053 |                    -0.042 | -0.018 |
| specificity      |       0.126 |              0.122 |                     0.133 |  0.117 |
| correctness      |       0.027 |              0.009 |                     0.036 |  0.036 |
| constructiveness |       0.016 |              0.020 |                     0.030 |  0.019 |
| stance           |      -0.069 |             -0.049 |                    -0.047 | -0.044 |

## Effect on Mann-Whitney U Test p-values (Independent)
*   **Interpretation**: p < 0.05 indicates a statistically significant difference in distributions.

|                  |   evaluator |   evaluator_metric |   evaluator_metric_target |   none |
|:-----------------|------------:|-------------------:|--------------------------:|-------:|
| coverage         |      0.4727 |             0.3066 |                    0.4257 | 0.7241 |
| specificity      |      0.0148 |             0.0177 |                    0.0117 | 0.0217 |
| correctness      |      0.6081 |             0.8575 |                    0.4954 | 0.4835 |
| constructiveness |      0.7601 |             0.6904 |                    0.5667 | 0.7039 |
| stance           |      0.1758 |             0.3405 |                    0.3668 | 0.3827 |

## Effect on Wilcoxon Signed-Rank Test p-values (Paired)
*   **Interpretation**: p < 0.05 indicates a significant difference on matched review pairs.

|                  |   evaluator |   evaluator_metric |   evaluator_metric_target |   none |
|:-----------------|------------:|-------------------:|--------------------------:|-------:|
| coverage         |      0.2872 |             0.1812 |                    0.3154 | 0.4175 |
| specificity      |      0.3177 |             0.2872 |                    0.3046 | 0.2737 |
| correctness      |      0.6546 |             0.3564 |                    0.6326 | 0.6623 |
| constructiveness |      0.9317 |             0.9165 |                    0.9367 | 0.9531 |
| stance           |      0.2412 |             0.2990 |                    0.3751 | 0.2572 |

## Effect on Levene's Test p-values (Variance Homogeneity)
*   **Interpretation**: p < 0.05 suggests variances are unequal between Human and AI scores.

|                  |   evaluator |   evaluator_metric |   evaluator_metric_target |   none |
|:-----------------|------------:|-------------------:|--------------------------:|-------:|
| coverage         |      0.5537 |             0.3899 |                    0.0888 | 0.8742 |
| specificity      |      0.6603 |             0.1653 |                    0.8810 | 0.5070 |
| correctness      |      0.1543 |             0.8690 |                    0.6067 | 0.1881 |
| constructiveness |      0.9859 |             0.5780 |                    0.9975 | 0.6165 |
| stance           |      0.6084 |             0.4229 |                    0.8857 | 0.7488 |

