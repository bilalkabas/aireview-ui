import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from math import pi
from pathlib import Path
from .utils import METRICS
from .metrics import compute_turing_tests

def plot_confusion_matrix(cm_dict, title, filename):
    """
    Plots a 2x2 Confusion Matrix heatmap.
    Rows: Actual (AI, Human)
    Cols: Predicted (AI, Human)
    """
    # Matrix layout:
    #               Pred AI      Pred Human
    # Actual AI        TP           FN
    # Actual Human     FP           TN
    
    matrix = [
        [cm_dict['TP'], cm_dict['FN']],
        [cm_dict['FP'], cm_dict['TN']]
    ]
    
    df_cm = pd.DataFrame(matrix, index=['AI', 'Human'], columns=['AI', 'Human'])
    
    # Create Labels with percentages
    total = df_cm.sum().sum()
    annot_labels = df_cm.map(lambda v: f"{v}\n({v/total*100:.1f}%)" if total > 0 else f"{v}")
    
    plt.figure(figsize=(6, 5))
    sns.heatmap(df_cm, annot=annot_labels, fmt='', cmap='Blues', cbar=False, annot_kws={"size": 22})
    plt.title(title, fontsize=20)
    plt.ylabel("Actual Label", fontsize=18, fontweight='bold')
    plt.xlabel("Predicted Label", fontsize=18, fontweight='bold')
    plt.xticks(fontsize=20)
    plt.yticks(fontsize=20, rotation=90, va='center')
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()

def plot_combined_cms(per_eval_res, filename):
    """
    Plots all evaluator CMs in a single grid figure.
    """
    evaluators = sorted(per_eval_res.keys())
    n = len(evaluators)
    if n == 0: return

    cols = 3
    rows = (n + cols - 1) // cols
    
    # Increase fig size for layout
    fig, axes = plt.subplots(rows, cols, figsize=(cols*6, rows*6))
    axes = axes.flatten() if n > 1 else [axes]
    
    for i, ev in enumerate(evaluators):
        cm = per_eval_res[ev]
        # Layout: AI first
        matrix = [[cm['TP'], cm['FN']], [cm['FP'], cm['TN']]]
        
        df_cm = pd.DataFrame(matrix, index=['AI', 'Human'], columns=['AI', 'Human'])
        
        # Labels
        total = df_cm.sum().sum()
        annot_labels = df_cm.map(lambda v: f"{v}\n({v/total*100:.0f}%)" if total > 0 else f"{v}")
        
        sns.heatmap(df_cm, annot=annot_labels, fmt='', cmap='Blues', cbar=False, ax=axes[i], annot_kws={"size": 24})
        axes[i].set_title(ev, fontsize=24)
        axes[i].set_ylabel("Actual Label", fontsize=20, fontweight='bold')
        axes[i].set_xlabel("Predicted Label", fontsize=20, fontweight='bold')
        axes[i].tick_params(axis='both', which='major', labelsize=22)
        axes[i].set_yticklabels(axes[i].get_yticklabels(), rotation=90, va='center')
        
    # Hide empty subplots
    for j in range(n, len(axes)):
        axes[j].axis('off')
        
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()

def create_radar_chart(data_dict, title, filename):
    """
    data_dict: {'Label': {'metric': mean_score, ...}}
    """
    categories = [m.capitalize() for m in METRICS]
    N = len(categories)
    
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1] # Close the loop
    
    plt.figure(figsize=(8, 8))
    ax = plt.subplot(111, polar=True)
    
    # Draw one axe per variable + add labels
    plt.xticks(angles[:-1], categories, color='grey', size=10)
    
    # Draw ylabels
    ax.set_rlabel_position(0)
    plt.yticks([1, 2, 3, 4, 5], ["1","2","3","4","5"], color="grey", size=7)
    plt.ylim(0, 5.5)
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']
    
    for i, (label, metrics_data) in enumerate(data_dict.items()):
        values = [metrics_data.get(m, 0) for m in METRICS]
        values += values[:1] # Close the loop
        
        color = colors[i % len(colors)]
        ax.plot(angles, values, linewidth=2, linestyle='solid', label=label, color=color)
        ax.fill(angles, values, color=color, alpha=0.1)
    
    plt.title(title, size=15, y=1.1)
    plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()

def generate_plots(data, output_dir):
    """
    Generates all plots from the loaded data.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    scores_df = pd.DataFrame(data['scores'])
    
    # 1. Box Plot: Human vs AI (Aggregated)
    if not scores_df.empty:
        plt.figure(figsize=(10, 6))
        # Create a column 'Reviewer Type' for plot
        scores_df['Reviewer Type'] = scores_df['is_human'].apply(lambda x: 'Human' if x else 'AI')
        
        sns.boxplot(data=scores_df, x='metric', y='score', hue='Reviewer Type', 
                    palette={'Human': '#1f77b4', 'AI': '#ff7f0e'})
        plt.title('Score Distribution: Human vs AI')
        plt.ylabel('Score')
        plt.xlabel('Metric')
        plt.grid(axis='y', linestyle='--', alpha=0.3)
        plt.savefig(output_dir / "human_vs_ai_boxplot.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. Box Plot: Per Evaluator
        plt.figure(figsize=(12, 6))
        sns.boxplot(data=scores_df, x='evaluator', y='score', palette='Set2')
        plt.title('Score Distribution by Evaluator')
        plt.xticks(rotation=45)
        plt.grid(axis='y', linestyle='--', alpha=0.3)
        plt.savefig(output_dir / "evaluator_boxplot.png", dpi=300, bbox_inches='tight')
        plt.close()

        # 2.3: Per Evaluator Per Metric Box Plot
        plt.figure(figsize=(16, 8))
        sns.boxplot(data=scores_df, x='metric', y='score', hue='evaluator', palette='Set3')
        plt.title('Score Distribution per Metric by Evaluator')
        plt.xticks(rotation=45)
        plt.legend(title='Evaluator', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(axis='y', linestyle='--', alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / "evaluator_per_metric_boxplot.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 3. Radar Chart: Human vs AI (Mean)
        human_means = scores_df[scores_df['is_human'] == True].groupby('metric')['score'].mean().to_dict()
        ai_means = scores_df[scores_df['is_human'] == False].groupby('metric')['score'].mean().to_dict()
        
        radar_data = {
            'Human': human_means,
            'AI (Avg)': ai_means
        }
        create_radar_chart(radar_data, 'Average Score Profile: Human vs AI', output_dir / "radar_human_vs_ai.png")
        
        # 4. Radar Chart: Per Model
        model_radar_data = {'Human': human_means}
        models = data['models']
        for m in models:
            m_means = scores_df[scores_df['model'] == m].groupby('metric')['score'].mean().to_dict()
            model_radar_data[m] = m_means
            
        create_radar_chart(model_radar_data, 'Score Profile per Model', output_dir / "radar_models.png")
    
    # 5. Turing Test Confusion Matrices
    turing_tests = compute_turing_tests(data)
    
    # Overall
    if turing_tests['overall']:
        plot_confusion_matrix(turing_tests['overall'], 'Overall Confusion Matrix (AI Detection)', output_dir / "turing_cm_overall.png")
        
    # Per Evaluator (Combined)
    if turing_tests['per_evaluator']:
        plot_combined_cms(turing_tests['per_evaluator'], output_dir / "turing_cm_evaluators_combined.png")
        
    print(f"Plots saved to {output_dir}")