import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from math import pi
from pathlib import Path
from utils import METRICS
from metrics import compute_turing_tests

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
def plot_decision_analysis(stats, output_dir):
    """
    Generates plots for Accepted vs Rejected analysis.
    """
    out = Path(output_dir)
    # Ensure stats are populated
    if not stats or not stats.get('score_means'):
        print("No decision stats available for plotting.")
        return
        
    METRICS_SHORT = [m.capitalize()[:4] for m in METRICS]
    
    color_palette = ['#66c2a5', '#fc8d62'] # Pastel Green, Pastel Red
    
    # 1. Human Scores
    data_h = {}
    err_h = {}
    for m in METRICS:
        k = m.capitalize()
        data_h[k] = stats['score_means'][m]['Human']
        err_h[k] = stats['score_stds'][m]['Human']
    
    df_h = pd.DataFrame(data_h).T
    df_h_err = pd.DataFrame(err_h).T
    
    plt.figure()
    df_h.plot(kind='bar', color=color_palette, rot=45, figsize=(6,4), width=0.7, yerr=df_h_err, capsize=4)
    plt.title("Human Review Scores")
    plt.ylabel("Avg Score")
    plt.ylim(0, 5.5)
    plt.legend(title='')
    plt.xticks(rotation=45, ha='right')
    plt.savefig(out / 'decision_human_scores.png', bbox_inches='tight')
    plt.close()
    
    # 2. AI Scores
    data_a = {}
    err_a = {}
    for m in METRICS:
        k = m.capitalize()
        data_a[k] = stats['score_means'][m]['AI']
        err_a[k] = stats['score_stds'][m]['AI']
    
    df_a = pd.DataFrame(data_a).T
    df_a_err = pd.DataFrame(err_a).T
    
    plt.figure()
    df_a.plot(kind='bar', color=color_palette, rot=45, figsize=(6,4), width=0.7, yerr=df_a_err, capsize=4)
    plt.title("AI Review Scores")
    plt.ylabel("Avg Score")
    plt.ylim(0, 5.5)
    plt.legend(title='')
    plt.xticks(rotation=45, ha='right')
    plt.savefig(out / 'decision_ai_scores.png', bbox_inches='tight')
    plt.close()
    
    # 4. Turing Matrices
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    
    turing_data = stats['turing']
    for i, dec in enumerate(['Accept', 'Reject']):
        if dec not in turing_data: continue
            
        cm = np.array(turing_data[dec]['cm'])
        acc = turing_data[dec]['acc']
        
        # CM: 0=AI, 1=Human (Actual Rows, Predicted Cols)
        df_cm = pd.DataFrame(cm, index=['AI', 'Human'], columns=['AI', 'Human'])
        
        annot = df_cm.applymap(lambda x: str(x))
        cmap = 'Greens' if dec=='Accept' else 'Reds'
        
        sns.heatmap(df_cm, annot=annot, fmt='', cmap=cmap, cbar=False, ax=axes[i], 
                    annot_kws={"size": 16, "weight": "bold"}, square=True)
        
        axes[i].set_title(f"{dec} Papers\nAcc: {acc:.1%}", fontsize=14, fontweight='bold')
        axes[i].set_xlabel("Predicted", fontsize=12)
        axes[i].tick_params(labelsize=11)
        
    plt.tight_layout()
    plt.savefig(out / 'decision_turing_combined.png', bbox_inches='tight')
    plt.close()

    # 5. Detection Metrics
    det_metrics = ['accuracy', 'precision', 'recall', 'f1']
    data_det = []
    for m in det_metrics:
        k = 'acc' if m=='accuracy' else ('prec' if m=='precision' else ('rec' if m=='recall' else 'f1'))
        data_det.append({
            'Metric': m.capitalize().replace('F1', 'F1 Score'), 
            'Accept': turing_data['Accept'][k],
            'Reject': turing_data['Reject'][k]
        })
    df_det = pd.DataFrame(data_det).set_index('Metric')
    
    plt.figure()
    df_det.plot(kind='bar', color=color_palette, rot=0, figsize=(6,4), width=0.7)
    plt.title("AI Detection Metrics by Decision")
    plt.ylim(0, 1.0)
    plt.legend(title='')
    plt.savefig(out / 'decision_detection_metrics.png', bbox_inches='tight')
    plt.close()

    # 6. Distribution
    counts = stats['counts']
    df_counts = pd.DataFrame(counts).T
    order_c = ['Papers', 'Reviews', 'Human Reviews', 'AI Reviews', 'Scored Reviews']
    df_counts = df_counts.reindex(order_c)
    
    plt.figure()
    ax = df_counts.plot(kind='bar', color=color_palette, rot=0, figsize=(9,5), width=0.8)
    plt.title("Dataset Distribution")
    plt.ylabel("Count")
    
    for p in ax.patches:
        ax.annotate(str(int(p.get_height())), (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='center', xytext=(0, 5), textcoords='offset points', fontsize=9, fontweight='bold')
        
    plt.legend(title='')
    plt.xticks(rotation=0, fontsize=9)
    plt.savefig(out / 'decision_distribution.png', bbox_inches='tight')
    plt.close()

    # 7. Combined Figure
    fig = plt.figure(figsize=(18, 20))
    # Layout: 3 rows. 
    # Row 1: Human (0,0), AI (0,1)
    # Row 2: Detection (1,0), Distribution (1,1)
    # Row 3: Turing Combined (Using 2 subplots)
    gs = fig.add_gridspec(3, 2, height_ratios=[1, 0.8, 1], top=0.92) # adjust top for legend
    
    # R1: Scores
    # Shorten labels for combined plot
    short_map = {
        'Constructiveness': 'Constr.',
        'Correctness': 'Correct.',
        'Specificity': 'Specif.'
    }
    df_h_s = df_h.rename(index=short_map)
    df_a_s = df_a.rename(index=short_map)
    df_h_err_s = df_h_err.rename(index=short_map)
    df_a_err_s = df_a_err.rename(index=short_map)

    ax_h = fig.add_subplot(gs[0, 0])
    df_h_s.plot(kind='bar', color=color_palette, rot=0, width=0.7, yerr=df_h_err_s, capsize=4, ax=ax_h)
    ax_h.set_title("Human Review Scores", fontsize=16)
    ax_h.set_ylim(0, 5.5)
    ax_h.set_xlabel("")
    ax_h.get_legend().remove() # Start by removing default, we will add global
    plt.setp(ax_h.get_xticklabels(), ha="center", rotation=0, fontsize=12)
    
    # Get handles/labels for global legend
    handles, labels = ax_h.get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center', ncol=2, bbox_to_anchor=(0.5, 0.95), fontsize=14, frameon=False)
    
    ax_a = fig.add_subplot(gs[0, 1])
    df_a_s.plot(kind='bar', color=color_palette, rot=0, width=0.7, yerr=df_a_err_s, capsize=4, ax=ax_a)
    ax_a.set_title("AI Review Scores", fontsize=16)
    ax_a.set_ylim(0, 5.5)
    ax_a.set_xlabel("")
    ax_a.legend().remove()
    plt.setp(ax_a.get_xticklabels(), ha="center", rotation=0, fontsize=12)
    
    # R2: Metrics & Dist
    ax_det = fig.add_subplot(gs[1, 0])
    df_det.plot(kind='bar', color=color_palette, rot=0, width=0.7, ax=ax_det)
    ax_det.set_title("AI Detection Accuracy", fontsize=16)
    ax_det.set_ylim(0, 1.0)
    ax_det.legend().remove()
    
    ax_cnt = fig.add_subplot(gs[1, 1])
    df_counts.plot(kind='bar', color=color_palette, rot=0, width=0.8, ax=ax_cnt)
    ax_cnt.set_title("Dataset Distribution", fontsize=16)
    ax_cnt.legend().remove()
    for p in ax_cnt.patches:
        ax_cnt.annotate(str(int(p.get_height())), (p.get_x() + p.get_width() / 2., p.get_height()), 
                        ha='center', va='bottom', xytext=(0, 3), textcoords='offset points', fontsize=10, fontweight='bold')
    
    # R3: Turing CMs
    for i, dec in enumerate(['Accept', 'Reject']):
        if dec not in turing_data: continue
        ax_cm = fig.add_subplot(gs[2, i])
        
        cm = np.array(turing_data[dec]['cm'])
        acc = turing_data[dec]['acc']
        df_cm = pd.DataFrame(cm, index=['AI', 'Human'], columns=['AI', 'Human'])
        annot = df_cm.applymap(lambda x: str(x))
        cmap = 'Greens' if dec=='Accept' else 'Reds'
        
        sns.heatmap(df_cm, annot=annot, fmt='', cmap=cmap, cbar=False, ax=ax_cm, 
                    annot_kws={"size": 18, "weight": "bold"}, square=True)
        ax_cm.set_title(f"{dec} Papers CM (Acc: {acc:.1%})", fontsize=16)
        ax_cm.set_xlabel("Predicted Label", fontsize=14)
        ax_cm.set_ylabel("Actual Label", fontsize=14)
        ax_cm.tick_params(labelsize=14)
        
    plt.tight_layout()
    plt.savefig(out / 'decision_analysis_combined.png', bbox_inches='tight')
    plt.close()
