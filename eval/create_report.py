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
    from metrics import compute_metric_stats, compute_statistical_tests, compute_agreement, compute_turing_tests, compute_decision_stats, NumpyEncoder
    from create_plots import generate_plots, plot_decision_analysis
except ImportError:
    from .utils import load_data, METRICS
    from .metrics import compute_metric_stats, compute_statistical_tests, compute_agreement, compute_turing_tests, compute_decision_stats, NumpyEncoder
    from .create_plots import generate_plots, plot_decision_analysis

def format_p_value(val):
    if pd.isna(val): return "-"
    stars = ""
    if val < 0.001: stars = "^{***}"
    elif val < 0.01: stars = "^{**}"
    elif val < 0.05: stars = "^{*}"
    return f"${val:.4f}{stars}$"

def format_delta(val):
    if pd.isna(val): return "-"
    return f"{val:+.3f}"

def create_latex_table(df, caption, label):
    return f"""
\\begin{{table}}[H]
\\centering
\\caption{{{caption}}}
\\label{{{label}}}
{df.to_latex(index=False, float_format="%.3f", escape=False)}
\\end{{table}}
"""

def generate_latex_content(stats, sig_tests, agreement, turing_tests, models, decision_stats):
    latex = r"""\documentclass{article}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{caption}
\usepackage{float}
\usepackage{geometry}
\geometry{a4paper, margin=1in}
\usepackage{hyperref}
\hypersetup{colorlinks=true, linkcolor=blue, linktoc=all}

\title{AI Reviewer Evaluation Report}
\author{Automated Analysis}
\date{\today}

\begin{document}
\maketitle
\tableofcontents
\newpage

\section{Introduction}
This report presents a comprehensive evaluation of AI reviewers compared to human performance.

\section{Score Statistics}

\subsection{Score Distributions}
\begin{figure}[H]
    \centering
    \includegraphics[width=0.8\textwidth]{plots/human_vs_ai_boxplot.png}
    \caption{Distribution of Review Scores (Human vs AI).}
\end{figure}

\begin{figure}[H]
    \centering
    \includegraphics[width=0.6\textwidth]{plots/radar_human_vs_ai.png}
    \caption{Average Score Profile: Human vs AI.}
\end{figure}

\subsection{Per-Evaluator Statistics}
\begin{figure}[H]
    \centering
    \includegraphics[width=0.9\textwidth]{plots/evaluator_boxplot.png}
    \caption{Score Distribution by Evaluator.}
\end{figure}

\subsection{Per-Evaluator per Metric Statistics}
\begin{figure}[H]
    \centering
    \includegraphics[width=1.0\textwidth]{plots/evaluator_per_metric_boxplot.png}
    \caption{Score Distribution: Evaluator per Metric.}
\end{figure}

\section{Statistical Significance Tests}

\subsection{Methodology}
We confirm performance differences using Mann-Whitney U (unpaired), Wilcoxon Signed-Rank (paired), and assess variance equality with Levene's Test. Effect size is measured by Cliff's Delta.

\subsection{Global Analysis (Human vs All AI)}
"""
    # Create DataFrame for Global Sig Tests
    global_rows = []
    agg_res = sig_tests['aggregated']
    for m in METRICS:
        r = agg_res.get(m, {})
        global_rows.append({
            'Metric': m.capitalize(),
            'MW U ($p$)': format_p_value(r.get('mwu_p')),
            'Wilcoxon ($p$)': format_p_value(r.get('wilcoxon_p')),
            'Levene ($p$)': format_p_value(r.get('levene_p')),
            'Cliff\'s $\delta$': format_delta(r.get('cliffs_delta'))
        })
    df_global = pd.DataFrame(global_rows)
    latex += create_latex_table(df_global, "Statistical Significance (Overall)", "tab:sig_global")

    latex += r"""
\subsection{Per-Model Analysis}
\begin{figure}[H]
    \centering
    \includegraphics[width=0.7\textwidth]{plots/radar_models.png}
    \caption{Performance Profile per AI Model.}
\end{figure}
"""

    # Per Model Tables
    model_res = sig_tests['per_model']
    for mod in models:
        latex += f"\\subsubsection{{Model: {mod}}}\n"
        m_rows = []
        for m in METRICS:
            r = model_res.get(mod, {}).get(m, {})
            m_rows.append({
                'Metric': m.capitalize(),
                'MW U ($p$)': format_p_value(r.get('mwu_p')),
                'Wilcoxon ($p$)': format_p_value(r.get('wilcoxon_p')),
                'Levene ($p$)': format_p_value(r.get('levene_p')),
                'Cliff\'s $\delta$': format_delta(r.get('cliffs_delta'))
            })
        df_mod = pd.DataFrame(m_rows)
        latex += create_latex_table(df_mod, f"Significance: Human vs {mod}", f"tab:sig_{mod}")

    latex += r"""

\section{Turing Test Analysis (AI Detection)}
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
        latex += create_latex_table(df_tur, "Turing Test Performance Metrics", "tab:tur_metrics")

    # Overall CM Image
    if overall:
        latex += r"""
\begin{figure}[H]
    \centering
    \includegraphics[width=0.5\textwidth]{plots/turing_cm_overall.png}
    \caption{Overall Confusion Matrix (AI Detection).}
\end{figure}
"""
    else:
        latex += "\nNo Turing Test data found.\n"
        
    latex += r"\subsection{Per-Evaluator Confusion Matrices}"
    tur_eval = turing_tests.get('per_evaluator', {})
    if tur_eval:
        latex += r"""
\begin{figure}[H]
    \centering
    \includegraphics[width=0.85\textwidth]{plots/turing_cm_evaluators_combined.png}
    \caption{Confusion Matrices per Evaluator.}
\end{figure}
"""
    else:
        latex += "\nNo Per-Evaluator data found.\n"

    latex += r"""
\section{Inter-Evaluator Agreement}
Cohen's Kappa and Gwet's AC2 agreement between evaluators on review scores (discretized).

\subsection{Cohen's Kappa}
"""
    # Create Kappa Table (Matrix)
    if 'cohen_kappa' in agreement:
        df_kappa = pd.DataFrame.from_dict(agreement['cohen_kappa'])
        # Format NaN
        df_kappa = df_kappa.map(lambda x: f"{x:.2f}" if not pd.isna(x) else "-")
        # Reset index to include evaluator names
        df_kappa.reset_index(inplace=True)
        df_kappa.rename(columns={'index': 'Evaluator'}, inplace=True)
        latex += create_latex_table(df_kappa, "Pairwise Cohen's Kappa Agreement", "tab:kappa")
    
    latex += r"""
\subsection{Gwet's AC2}
Gwet's AC2 is often more robust to marginal imbalance and ordinal data.
"""
    if 'gwet_ac2' in agreement:
        df_ac2 = pd.DataFrame.from_dict(agreement['gwet_ac2'])
        # Format NaN
        df_ac2 = df_ac2.map(lambda x: f"{x:.2f}" if not pd.isna(x) else "-")
        # Reset index
        df_ac2.reset_index(inplace=True)
        df_ac2.rename(columns={'index': 'Evaluator'}, inplace=True)
        latex += create_latex_table(df_ac2, "Pairwise Gwet's AC2 Agreement", "tab:ac2")

    latex += r"""
\section{Breakdown wrt Accepted versus Rejected Papers}
Analysis of review characteristics based on the final decision (Accept vs Reject).

\begin{figure}[H]
    \centering
    \begin{minipage}{0.48\textwidth}
        \centering
        \includegraphics[width=\linewidth]{plots/decision_human_scores.png}
        \caption{Human Scores (Accept/Reject)}
    \end{minipage}\hfill
    \begin{minipage}{0.48\textwidth}
        \centering
        \includegraphics[width=\linewidth]{plots/decision_ai_scores.png}
        \caption{AI Scores (Accept/Reject)}
    \end{minipage}
\end{figure}



\begin{figure}[H]
    \centering
    \includegraphics[width=1.0\textwidth]{plots/decision_turing_combined.png}
    \caption{Turing Test Confusion Matrices (Accept/Reject)}
\end{figure}

\begin{figure}[H]
    \centering
    \begin{minipage}{0.48\textwidth}
        \centering
        \includegraphics[width=\linewidth]{plots/decision_detection_metrics.png}
        \caption{AI Detection Metrics}
    \end{minipage}\hfill
    \begin{minipage}{0.48\textwidth}
        \centering
        \includegraphics[width=\linewidth]{plots/decision_distribution.png}
        \caption{Dataset Distribution}
    \end{minipage}
\end{figure}
"""

    latex += r"""
\appendix
\newpage
\section{Appendix: Guide to Interpretations}

\subsection{Interpreting Box Plots}
The box plots in this report visualize the distribution of review scores.
\begin{itemize}
    \item \textbf{Box}: Represents the Interquartile Range (IQR), spanning from the 25th percentile ($Q1$) to the 75th percentile ($Q3$). It contains the middle 50\% of the data.
    \item \textbf{Median}: The line inside the box marks the median score (50th percentile).
    \item \textbf{Whiskers}: Extend from the box to the most extreme data points that are not considered outliers. Typically, this is $1.5 \times IQR$.
    \item \textbf{Empty Circles (Outliers)}: Points lying beyond the whiskers are plotted individually as empty circles. These represent outlier scores that are unusually high or low compared to the rest of the distribution.
\end{itemize}

\subsection{Statistical Methodology Details}
This section explains the intuition and computation behind the statistical tests used.

\subsubsection{Mann-Whitney U Test}
\textbf{Intuition}: A non-parametric test for independent samples (e.g., Human vs AI scores across different papers). It assesses whether one group's values are stochastically larger than the other's. It does not assume a normal distribution.
\textbf{Computation}: All observations are ranked together. The sum of ranks for each group is calculated. The $U$ statistic is derived from these rank sums, comparing the number of times a value from one group precedes a value from the other.

\subsubsection{Wilcoxon Signed-Rank Test}
\textbf{Intuition}: A non-parametric paired test used for per-model comparisons where we have matched scores (Human and AI reviewing the \textit{same} paper). It tests if the distribution of differences is symmetric about zero.
\textbf{Computation}: Differences between paired scores ($d_i = x_{human} - x_{ai}$) are calculated. Absolute differences $|d_i|$ are ranked. Ranks are signed according to the sign of $d_i$. The test statistic $W$ is the sum of positive ranks.

\subsubsection{Levene's Test}
\textbf{Intuition}: Tests the null hypothesis that the variances (spread) of the two groups are equal (Homogeneity of Variance).
\textbf{Computation}: It performs an Analysis of Variance (ANOVA) on the absolute deviations of scores from their group means (or medians). A significant $p$-value suggests the groups have different consistency levels.

\subsubsection{Cliff's Delta ($\delta$)}
\textbf{Intuition}: An effect size measure quantifying the magnitude of difference between two groups. It represents the probability that a randomly selected value from one group is greater than one from the other, minus the reverse probability. values range from -1 to +1.
\textbf{Computation}:
\[ \delta = \frac{\#(x_H > x_A) - \#(x_H < x_A)}{n_H \times n_A} \]
where $x_H$ and $x_A$ are scores from Human and AI groups respectively. 
Interpretation: $|\delta| < 0.147$ (Negligible), $< 0.33$ (Small), $< 0.474$ (Medium), else (Large).

\subsubsection{Cohen's Kappa ($\kappa$)}
\textbf{Intuition}: Measures inter-rater agreement for categorical items, correcting for agreement occurring by chance.
\textbf{Computation}:
\[ \kappa = \frac{p_o - p_e}{1 - p_e} \]
where $p_o$ is the relative observed agreement, and $p_e$ is the hypothetical probability of chance agreement based on marginal frequencies.

\end{document}
"""
    return latex

def main():
    # Resolve default data_dir relative to this script location
    # script is in eval/create_report.py. parent is eval. parent.parent is root.
    # script is in eval/create_report.py. parent is eval.
    default_data_dir = Path(__file__).parent / 'data'
    default_output_dir = Path(__file__).parent / 'report_output'

    parser = argparse.ArgumentParser(description="Generate AI Review Evaluation Report")
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
    agreement_res = compute_agreement(data) # Changed from kappa_matrix
    decision_stats = compute_decision_stats(data) # Compute Accepted/Rejected stats
    
    print("Generating Plots...")
    generate_plots(data, output_path / 'plots')
    plot_decision_analysis(decision_stats, output_path / 'plots') # Generate new plots
    
    # Save Metrics JSON
    final_output = {
        'statistics': stats,
        'significance': sig_tests,
        'agreement': agreement_res,
        'turing': turing_tests
    }
    with open(output_path / 'metrics.json', 'w') as f:
        json.dump(final_output, f, indent=2, cls=NumpyEncoder)
    print(f"Metrics saved to {output_path / 'metrics.json'}")
    
    print("Generating Report...")
    latex_content = generate_latex_content(stats, sig_tests, agreement_res, turing_tests, data['models'], decision_stats)
    
    tex_file = output_path / 'report.tex'
    with open(tex_file, 'w') as f:
        f.write(latex_content)
        
    print(f"Report generated at: {tex_file}")

if __name__ == "__main__":
    main()
