import argparse
import sys
import os
import json
import pandas as pd
from pathlib import Path

# Adjust path to enable imports if run as script
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from utils import load_data, METRICS
    from metrics import compute_metric_stats, compute_statistical_tests, compute_kappa, compute_turing_tests, NumpyEncoder
    from create_plots import generate_plots
except ImportError:
    from .utils import load_data, METRICS
    from .metrics import compute_metric_stats, compute_statistical_tests, compute_kappa, compute_turing_tests, NumpyEncoder
    from .create_plots import generate_plots

def format_p_value(val):
    if pd.isna(val): return "-"
    stars = ""
    if val < 0.001: stars = "***"
    elif val < 0.01: stars = "**"
    elif val < 0.05: stars = "*"
    return f"{val:.4f}{stars}"

def format_delta(val):
    if pd.isna(val): return "-"
    return f"{val:+.3f}"

def generate_markdown_content(stats, sig_tests, kappa_matrix, turing_tests, models):
    md = """# AI Reviewer Evaluation Report
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
"""
    # Create DataFrame for Global Sig Tests
    global_rows = []
    agg_res = sig_tests['aggregated']
    for m in METRICS:
        r = agg_res.get(m, {})
        global_rows.append({
            'Metric': m.capitalize(),
            'MW U (p)': format_p_value(r.get('mwu_p')),
            'Wilcoxon (p)': format_p_value(r.get('wilcoxon_p')),
            'Levene (p)': format_p_value(r.get('levene_p')),
            'Cliff\'s Delta': format_delta(r.get('cliffs_delta'))
        })
    df_global = pd.DataFrame(global_rows)
    md += df_global.to_markdown(index=False)
    md += "\n\n"

    md += "### Per-Model Analysis\n"
    md += "![Performance Profile per AI Model](plots/radar_models.png)\n\n"

    # Per Model Tables
    model_res = sig_tests['per_model']
    for mod in models:
        md += f"#### Model: {mod}\n"
        m_rows = []
        for m in METRICS:
            r = model_res.get(mod, {}).get(m, {})
            m_rows.append({
                'Metric': m.capitalize(),
                'MW U (p)': format_p_value(r.get('mwu_p')),
                'Wilcoxon (p)': format_p_value(r.get('wilcoxon_p')),
                'Levene (p)': format_p_value(r.get('levene_p')),
                'Cliff\'s Delta': format_delta(r.get('cliffs_delta'))
            })
        df_mod = pd.DataFrame(m_rows)
        md += df_mod.to_markdown(index=False)
        md += "\n\n"

    md += """## Turing Test Analysis (AI Detection)
Evaluators were asked to guess if the review was written by AI or Human. We present the confusion matrices below.
"""
    # 1. Performance Table
    tur_rows = []
    per_eval = turing_tests.get('per_evaluator', {})
    
    # Per Evaluator rows
    for ev in sorted(per_eval.keys()):
        stats = per_eval[ev]
        r = {'Evaluator': ev}
        for k in ['Accuracy', 'Precision', 'Recall', 'F1']:
            r[k] = stats.get(k, 0)
        tur_rows.append(r)
        
    # Overall row
    overall = turing_tests.get('overall', {})
    if overall:
        r = {'Evaluator': 'Overall'}
        for k in ['Accuracy', 'Precision', 'Recall', 'F1']:
            r[k] = overall.get(k, 0)
        tur_rows.append(r)
        
    if tur_rows:
        df_tur = pd.DataFrame(tur_rows)
        cols = ['Evaluator', 'Accuracy', 'Precision', 'Recall', 'F1']
        df_tur = df_tur[cols] # Reorder
        md += df_tur.to_markdown(index=False)
        md += "\n\n"

    # Overall CM Image
    if overall:
        md += "![Overall Confusion Matrix (AI Detection)](plots/turing_cm_overall.png)\n\n"
    else:
        md += "\nNo Turing Test data found.\n"
        
    md += "### Per-Evaluator Confusion Matrices\n"
    tur_eval = turing_tests.get('per_evaluator', {})
    if tur_eval:
        md += "![Confusion Matrices per Evaluator](plots/turing_cm_evaluators_combined.png)\n\n"
    else:
        md += "\nNo Per-Evaluator data found.\n"

    md += """## Inter-Evaluator Agreement
Cohen's Kappa agreement between evaluators on review scores (discretized).
"""
    # Create Kappa Table (Matrix)
    df_kappa = pd.DataFrame.from_dict(kappa_matrix)
    # Format NaN
    df_kappa = df_kappa.map(lambda x: f"{x:.2f}" if not pd.isna(x) else "-")
    # Reset index to include evaluator names
    df_kappa.reset_index(inplace=True)
    df_kappa.rename(columns={'index': 'Evaluator'}, inplace=True)
    
    md += df_kappa.to_markdown(index=False)
    md += "\n\n"

    md += """# Appendix: Guide to Interpretations

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
"""
    return md

def main():
    default_data_dir = Path(__file__).parent / 'data'
    default_output_dir = Path(__file__).parent / 'report_output'

    parser = argparse.ArgumentParser(description="Generate AI Review Evaluation Report (Markdown)")
    parser.add_argument('--data_dir', type=str, default=str(default_data_dir), help='Path to data directory')
    parser.add_argument('--output_dir', type=str, default=str(default_output_dir), help='Output directory')
    parser.add_argument('--normalization', type=str, default='none', choices=['none', 'evaluator', 'evaluator_metric', 'evaluator_metric_target'], help='Normalization method')
    args = parser.parse_args()
    
    output_path = Path(args.output_dir) / f"norm_{args.normalization}"
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Loading Data from {args.data_dir}...")
    try:
        data = load_data(args.data_dir, args.normalization)
    except FileNotFoundError:
        print(f"Error: Data directory '{args.data_dir}' not found.")
        return

    print("Computing Metrics...")
    stats = compute_metric_stats(data)
    sig_tests = compute_statistical_tests(data)
    turing_tests = compute_turing_tests(data)
    kappa_matrix = compute_kappa(data)
    
    print("Generating Plots...")
    generate_plots(data, output_path / 'plots')
    
    # Save Metrics JSON
    final_output = {
        'statistics': stats,
        'significance': sig_tests,
        'agreement': kappa_matrix,
        'turing': turing_tests
    }
    with open(output_path / 'metrics.json', 'w') as f:
        json.dump(final_output, f, indent=2, cls=NumpyEncoder)
    print(f"Metrics saved to {output_path / 'metrics.json'}")
    
    print("Generating Markdown Report...")
    md_content = generate_markdown_content(stats, sig_tests, kappa_matrix, turing_tests, data['models'])
    
    md_file = output_path / 'report.md'
    with open(md_file, 'w') as f:
        f.write(md_content)
        
    print(f"Report generated at: {md_file}")

if __name__ == "__main__":
    main()
