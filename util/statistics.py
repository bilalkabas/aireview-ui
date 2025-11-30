#!/usr/bin/env python3
"""
Statistics and visualization script for paper review data.
Generates histograms of paper decisions overall and per evaluator.
"""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict
import matplotlib.pyplot as plt


def load_json(file_path):
    """Load JSON data from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {file_path}: {e}")
        sys.exit(1)


def collect_decision_statistics(data):
    """
    Collect statistics about paper decisions overall and per evaluator.

    Args:
        data: List of paper objects

    Returns:
        tuple: (overall_decisions, per_evaluator_decisions)
    """
    overall_decisions = []
    per_evaluator_decisions = defaultdict(list)

    for paper in data:
        decision = paper.get('decision').lower()
        evaluators = paper.get('evaluators', [])

        if decision:
            overall_decisions.append(decision)

            # Add this decision to each evaluator's list
            for evaluator in evaluators:
                per_evaluator_decisions[evaluator].append(decision)

    return overall_decisions, dict(per_evaluator_decisions)


def collect_model_statistics(data):
    """
    Collect statistics about how many papers each AI model has reviewed.

    Args:
        data: List of paper objects

    Returns:
        dict: Mapping of model names to number of papers reviewed
    """
    model_paper_counts = defaultdict(set)  # Use set to avoid counting same paper multiple times

    for paper_idx, paper in enumerate(data):
        reviews = paper.get('reviews', [])

        for review in reviews:
            reviewer = review.get('reviewer', '')

            # Check if this is an AI review
            if reviewer.startswith('ai/'):
                # Extract model name (remove "ai/" prefix)
                model_name = reviewer[3:]  # Remove "ai/" prefix
                model_paper_counts[model_name].add(paper_idx)

    # Convert sets to counts
    model_counts = {model: len(papers) for model, papers in model_paper_counts.items()}

    return model_counts


def plot_overall_histogram(decisions, output_path=None):
    """
    Plot histogram of all paper decisions.

    Args:
        decisions: List of decision strings
        output_path: Optional path to save the figure
    """
    decision_counts = Counter(decisions)

    # Sort by count descending
    sorted_decisions = sorted(decision_counts.items(), key=lambda x: x[1], reverse=True)
    labels = [d[0] for d in sorted_decisions]
    counts = [d[1] for d in sorted_decisions]

    # Create figure
    plt.figure(figsize=(12, 6))
    bars = plt.bar(range(len(labels)), counts, color='steelblue', alpha=0.8, edgecolor='black')

    # Customize plot
    plt.xlabel('Decision', fontsize=12, fontweight='bold')
    plt.ylabel('Number of Papers', fontsize=12, fontweight='bold')
    plt.title(f'Distribution of Paper Decisions (Total: {len(decisions)})',
              fontsize=14, fontweight='bold')
    plt.xticks(range(len(labels)), labels, rotation=45, ha='right')
    plt.grid(axis='y', alpha=0.3, linestyle='--')

    # Add value labels on bars
    total = sum(counts)
    for bar, count in zip(bars, counts):
        percentage = (count / total * 100) if total > 0 else 0
        label = f'{count}\n({percentage:.1f}%)'
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                label, ha='center', va='bottom', fontsize=9, fontweight='bold')

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved overall histogram to {output_path}")
    else:
        plt.show()

    plt.close()


def plot_per_evaluator_histograms(per_evaluator_decisions, output_dir=None):
    """
    Plot histograms for each evaluator's decisions.

    Args:
        per_evaluator_decisions: Dict mapping evaluator names to lists of decisions
        output_dir: Optional directory to save the figures
    """
    # Sort evaluators by number of papers reviewed
    sorted_evaluators = sorted(per_evaluator_decisions.items(),
                               key=lambda x: len(x[1]), reverse=True)

    # Calculate grid dimensions
    n_evaluators = len(sorted_evaluators)
    n_cols = min(3, n_evaluators)
    n_rows = (n_evaluators + n_cols - 1) // n_cols

    # Create subplots
    _, axes = plt.subplots(n_rows, n_cols, figsize=(6*n_cols, 5*n_rows))

    # Flatten axes array for easier iteration
    if n_evaluators == 1:
        axes = [axes]
    else:
        axes = axes.flatten() if n_evaluators > 1 else [axes]

    # Plot each evaluator's histogram
    for idx, (evaluator, decisions) in enumerate(sorted_evaluators):
        ax = axes[idx]
        decision_counts = Counter(decisions)

        # Sort by count descending
        sorted_decisions = sorted(decision_counts.items(), key=lambda x: x[1], reverse=True)
        labels = [d[0] for d in sorted_decisions]
        counts = [d[1] for d in sorted_decisions]

        # Create bar plot
        bars = ax.bar(range(len(labels)), counts, color='coral', alpha=0.8, edgecolor='black')

        # Customize subplot
        ax.set_xlabel('Decision', fontsize=10, fontweight='bold')
        ax.set_ylabel('Number of Papers', fontsize=10, fontweight='bold')
        ax.set_title(f'{evaluator} (Total: {len(decisions)})',
                    fontsize=11, fontweight='bold')
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
        ax.grid(axis='y', alpha=0.3, linestyle='--')

        # Add value labels on bars
        total_eval = sum(counts)
        for bar, count in zip(bars, counts):
            percentage = (count / total_eval * 100) if total_eval > 0 else 0
            label = f'{count}\n({percentage:.1f}%)'
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                   label, ha='center', va='bottom', fontsize=8, fontweight='bold')

    # Hide empty subplots
    for idx in range(n_evaluators, len(axes)):
        axes[idx].set_visible(False)

    plt.suptitle('Paper Decisions by Evaluator', fontsize=16, fontweight='bold', y=1.0)
    plt.tight_layout()

    if output_dir:
        output_path = Path(output_dir) / 'per_evaluator_decisions.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved per-evaluator histogram to {output_path}")
    else:
        plt.show()

    plt.close()


def plot_model_coverage(model_counts, output_path=None):
    """
    Plot bar chart showing how many papers each AI model has reviewed.

    Args:
        model_counts: Dict mapping model names to number of papers reviewed
        output_path: Optional path to save the figure
    """
    if not model_counts:
        print("Warning: No model data to plot")
        return

    # Sort models by number of papers (descending)
    sorted_models = sorted(model_counts.items(), key=lambda x: x[1], reverse=True)
    model_names = [m[0] for m in sorted_models]
    paper_counts = [m[1] for m in sorted_models]

    # Create figure
    plt.figure(figsize=(12, 6))
    bars = plt.bar(range(len(model_names)), paper_counts, color='mediumseagreen', alpha=0.8, edgecolor='black')

    # Customize plot
    plt.xlabel('AI Model', fontsize=12, fontweight='bold')
    plt.ylabel('Number of Papers Reviewed', fontsize=12, fontweight='bold')
    plt.title('Papers Reviewed per AI Model', fontsize=14, fontweight='bold')
    plt.xticks(range(len(model_names)), model_names, rotation=45, ha='right')
    plt.grid(axis='y', alpha=0.3, linestyle='--')

    # Add value labels on bars
    for bar, count in zip(bars, paper_counts):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                str(count), ha='center', va='bottom', fontsize=10, fontweight='bold')

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved model coverage plot to {output_path}")
    else:
        plt.show()

    plt.close()


def print_statistics(overall_decisions, per_evaluator_decisions, model_counts=None):
    """Print detailed statistics about decisions and models."""
    print("\n" + "="*70)
    print("OVERALL STATISTICS")
    print("="*70)

    overall_counts = Counter(overall_decisions)
    total = len(overall_decisions)

    print(f"\nTotal papers with decisions: {total}")
    print("\nDecision breakdown:")
    for decision, count in sorted(overall_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total * 100) if total > 0 else 0
        print(f"  {decision:.<50} {count:>4} ({percentage:>5.1f}%)")

    print("\n" + "="*70)
    print("PER-EVALUATOR STATISTICS")
    print("="*70)

    # Sort evaluators by number of papers
    sorted_evaluators = sorted(per_evaluator_decisions.items(),
                               key=lambda x: len(x[1]), reverse=True)

    for evaluator, decisions in sorted_evaluators:
        decision_counts = Counter(decisions)
        total_eval = len(decisions)

        print(f"\n{evaluator} (Total: {total_eval} papers)")
        print("-" * 70)
        for decision, count in sorted(decision_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_eval * 100) if total_eval > 0 else 0
            print(f"  {decision:.<50} {count:>4} ({percentage:>5.1f}%)")

    # Print model statistics if provided
    if model_counts:
        print("\n" + "="*70)
        print("AI MODEL STATISTICS")
        print("="*70)

        # Sort models by number of papers
        sorted_models = sorted(model_counts.items(), key=lambda x: x[1], reverse=True)

        print(f"\nTotal AI models: {len(sorted_models)}")
        print("\nPapers reviewed per model:")
        for model, count in sorted_models:
            print(f"  {model:.<50} {count:>4} papers")


def main():
    # Define file paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_path = project_root / 'reviews' / 'evaluation-data-all-venues.json'
    output_dir = project_root / 'statistics_output'

    # Create output directory
    output_dir.mkdir(exist_ok=True)

    print(f"Loading data from {data_path}...")
    data = load_json(data_path)

    print("Collecting statistics...")
    overall_decisions, per_evaluator_decisions = collect_decision_statistics(data)
    model_counts = collect_model_statistics(data)

    # Print statistics
    print_statistics(overall_decisions, per_evaluator_decisions, model_counts)

    # Generate plots
    print("\n" + "="*70)
    print("GENERATING PLOTS")
    print("="*70 + "\n")

    if overall_decisions:
        plot_overall_histogram(overall_decisions,
                              output_dir / 'overall_decisions.png')
    else:
        print("Warning: No decisions found in data")

    if per_evaluator_decisions:
        plot_per_evaluator_histograms(per_evaluator_decisions, output_dir)
    else:
        print("Warning: No per-evaluator decisions found in data")

    if model_counts:
        plot_model_coverage(model_counts,
                           output_dir / 'model_coverage.png')
    else:
        print("Warning: No AI model data found")

    print(f"\n Done! All plots saved to {output_dir}/")


if __name__ == '__main__':
    main()
