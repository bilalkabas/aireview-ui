import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
from collections import defaultdict
from .utils import METRICS, get_stats

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

def cliffs_delta(lst1, lst2):
    """
    Calculate Cliff's Delta effect size.
    lst1, lst2: lists of scores.
    """
    m, n = len(lst1), len(lst2)
    lst2 = sorted(lst2)
    j = 0
    k = 0
    more = 0
    less = 0
    for x in sorted(lst1):
        while j < n and lst2[j] < x: j += 1
        while k < n and lst2[k] <= x: k += 1
        less += j
        more += n - k
    if m * n == 0: return 0
    return (more - less) / (m * n)

def compute_metric_stats(data):
    """
    1. Metric score statistics (Mean +/- Std)
    """
    scores = pd.DataFrame(data['scores'])
    if scores.empty:
        raise ValueError("No evaluation scores found. Please check data directory path and JSON content.")
    
    # 1a. Overall Human vs AI (averaging across metrics)
    # We first average metrics for each review, then average those? Or just average all numbers?
    # "Averaging across all metrics" usually means pool all metric scores.
    human_scores = scores[scores['is_human'] == True]['score']
    ai_scores = scores[scores['is_human'] == False]['score']
    
    overall_stats = {
        'human': get_stats(human_scores),
        'ai': get_stats(ai_scores)
    }
    
    # 1b. Overall Human vs AI per metric
    per_metric_overall = {}
    for m in METRICS:
        h = scores[(scores['is_human'] == True) & (scores['metric'] == m)]['score']
        a = scores[(scores['is_human'] == False) & (scores['metric'] == m)]['score']
        per_metric_overall[m] = {
            'human': get_stats(h),
            'ai': get_stats(a)
        }
        
    # 1c. Average Human vs Each AI Model per metric
    # "Average human" means we use the global human baseline for comparison? Or per-model subset?
    # Usually global baseline.
    per_metric_model = defaultdict(dict)
    models = data['models']
    
    for m in METRICS:
        # Human baseline for this metric
        h_stats = per_metric_overall[m]['human']
        per_metric_model[m]['human'] = h_stats
        
        for mod in models:
            a = scores[(scores['model'] == mod) & (scores['metric'] == m)]['score']
            per_metric_model[m][mod] = get_stats(a)
            
    return {
        'overall': overall_stats,
        'per_metric_overall': per_metric_overall,
        'per_metric_model': per_metric_model
    }

def perform_tests(group1, group2, paired_g1=None, paired_g2=None):
    """
    Runs MWU, Levene, Cliff's Delta (on group1/group2 independent)
    and Wilcoxon (on paired_g1/paired_g2 if provided).
    """
    res = {}
    
    # Independent Tests
    try:
        _, mwu_p = stats.mannwhitneyu(group1, group2, alternative='two-sided')
        res['mwu_p'] = mwu_p
    except: res['mwu_p'] = np.nan
        
    try:
        _, lev_p = stats.levene(group1, group2, center='median')
        res['levene_p'] = lev_p
    except: res['levene_p'] = np.nan
    
    res['cliffs_delta'] = cliffs_delta(group1, group2)
    
    # Paired Test
    if paired_g1 is not None and paired_g2 is not None and len(paired_g1) > 0:
        try:
            # check if all diffs are zero
            if np.allclose(paired_g1, paired_g2):
                res['wilcoxon_p'] = 1.0
            else:
                _, wx_p = stats.wilcoxon(paired_g1, paired_g2)
                res['wilcoxon_p'] = wx_p
        except: res['wilcoxon_p'] = np.nan
    else:
        res['wilcoxon_p'] = np.nan
        
    return res

def get_paired_data(data, model_filter=None):
    """
    Helper to align scores by (Paper Title) for Paired Tests (Wilcoxon).
    Returns dict: metric -> {'human': [], 'ai': []}
    """
    # Structure: paper -> evaluator -> {'human': score, 'ai': []}
    pairing = defaultdict(lambda: defaultdict(lambda: {'human': {}, 'ai': defaultdict(list)}))
    
    scores = data['scores']
    for s in scores:
        if s['metric'] not in METRICS: continue
        
        # Filter for specific model if requested
        if model_filter and (not s['is_human']) and (s['model'] != model_filter):
            continue
            
        paper = s['paper_title']
        ev = s['evaluator']
        metric = s['metric']
        val = s['score']
        
        if s['is_human']:
            pairing[paper][ev]['human'][metric] = val
        else:
            pairing[paper][ev]['ai'][metric].append(val)
            
    # Flatten to lists
    paired_lists = defaultdict(lambda: {'human': [], 'ai': []})
    
    for paper, ev_dict in pairing.items():
        for ev, d in ev_dict.items():
            for m in METRICS:
                h_val = d['human'].get(m)
                ai_vals = d['ai'].get(m)
                
                if h_val is not None and ai_vals:
                    # If multiple scores (e.g. multiple runs), take mean
                    paired_lists[m]['human'].append(h_val)
                    paired_lists[m]['ai'].append(np.mean(ai_vals))
                    
    return paired_lists

def compute_statistical_tests(data):
    """
    2. Metric score statistical tests (per metric)
    """
    results_agg = {}
    results_model = defaultdict(dict)
    
    scores = pd.DataFrame(data['scores'])
    
    # 2a. Aggregated AI
    paired_agg = get_paired_data(data, model_filter=None)
    
    for m in METRICS:
        h_scores = scores[(scores['is_human'] == True) & (scores['metric'] == m)]['score'].tolist()
        a_scores = scores[(scores['is_human'] == False) & (scores['metric'] == m)]['score'].tolist()
        
        p = paired_agg[m]
        res = perform_tests(h_scores, a_scores, p['human'], p['ai'])
        results_agg[m] = res
        
    # 2b. Per Model
    models = data['models']
    for mod in models:
        paired_mod = get_paired_data(data, model_filter=mod)
        for m in METRICS:
            h_scores = scores[(scores['is_human'] == True) & (scores['metric'] == m)]['score'].tolist()
            a_scores = scores[(scores['model'] == mod) & (scores['metric'] == m)]['score'].tolist()
            
            p = paired_mod[m]
            res = perform_tests(h_scores, a_scores, p['human'], p['ai'])
            results_model[mod][m] = res
            
    return {
        'aggregated': results_agg,
        'per_model': results_model
    }

def compute_kappa(data):
    """
    4. Evaluator agreement statistics (Cohen's Kappa).
    Pairwise evaluators, common (Paper, Reviewer Identity).
    """
    # Build map: (Paper, Reviewer_Type, Model) -> Evaluator -> {metric: score}
    # Actually, we agree on specific scores.
    # Key = (PaperTitle, ReviewerName/Type). But "ReviewerName" varies.
    # Simplify: (PaperTitle, is_human, model_name).
    
    # Map: key -> evaluator -> [scores across metrics]
    # We aggregate all metrics? "Average across all metrics and papers".
    # So we can just make a long list of scores for shared items.
    
    idx_map = defaultdict(dict) # key -> evaluator -> list of scores
    
    scores = pd.DataFrame(data['scores'])
    # Iterate
    for idx, row in scores.iterrows():
        # Key identifies the *object* being evaluated
        # Object = (Paper, ReviewerIdentity)
        # ReviewerIdentity = Human OR specific Model.
        key = (row['paper_title'], row['is_human'], row['model'], row['metric'])
        ev = row['evaluator']
        score = row['score']
        idx_map[key][ev] = score

    evaluators = data['evaluators']
    kappa_matrix = pd.DataFrame(index=evaluators, columns=evaluators, dtype=float)
    
    # For pair (E1, E2)
    for i in range(len(evaluators)):
        for j in range(i+1, len(evaluators)):
            e1 = evaluators[i]
            e2 = evaluators[j]
            
            list1 = []
            list2 = []
            
            for key, ev_map in idx_map.items():
                if e1 in ev_map and e2 in ev_map:
                    list1.append(ev_map[e1])
                    list2.append(ev_map[e2])
            
            # Compute Kappa if enough overlap
            # Since scores are continuous (normalized) or ordinal (1-5), Cohen's Kappa needs discrete classes.
            # If normalized, they are floats. We should round? Or use Intraclass Correlation?
            # Prompt says "Kappa". Standard is Cohen's for categorical. Weighted for ordinal.
            # If normalization means float 3.5, Kappa is undefined.
            # I will assume we convert to nearest integer 1-5 for Kappa calculation.
            
            if len(list1) > 5:
                # Discretize
                l1_int = np.round(list1).astype(int)
                l2_int = np.round(list2).astype(int)
                
                # Check range
                # scikit-learn cohen_kappa_score
                from sklearn.metrics import cohen_kappa_score
                k = cohen_kappa_score(l1_int, l2_int, weights='linear')
                kappa_matrix.at[e1, e2] = k
                kappa_matrix.at[e2, e1] = k
            else:
                kappa_matrix.at[e1, e2] = np.nan
                kappa_matrix.at[e2, e1] = np.nan

    return kappa_matrix.to_dict()

def calculate_cm_stats(entries):
    """
    Computes TP, TN, FP, FN, Accuracy for Turing Test.
    Positive Class = AI.
    TP: Actual AI, Predicted AI
    TN: Actual Human, Predicted Human
    FP: Actual Human, Predicted AI
    FN: Actual AI, Predicted Human
    """
    tp = tn = fp = fn = 0
    for e in entries:
        act = e['actual']
        pred = e['predicted']
        if act == 'ai' and pred == 'ai': tp += 1
        elif act == 'human' and pred == 'human': tn += 1
        elif act == 'human' and pred == 'ai': fp += 1
        elif act == 'ai' and pred == 'human': fn += 1
    
    total = tp + tn + fp + fn
    acc = (tp + tn) / total if total > 0 else 0
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        'TP': tp, 'TN': tn, 'FP': fp, 'FN': fn, 
        'Accuracy': acc, 'Precision': precision, 'Recall': recall, 'F1': f1,
        'Total': total
    }

def compute_turing_tests(data):
    """
    3. Turing tests (Confusion Matrices).
    """
    cm_data = data.get('confusion_data', [])
    if not cm_data:
        return {'overall': {}, 'per_evaluator': {}}
    
    # Overall
    overall_stats = calculate_cm_stats(cm_data)
    
    # Per Evaluator
    per_eval_res = {}
    evaluator_items = defaultdict(list)
    for e in cm_data:
        evaluator_items[e['evaluator']].append(e)
        
    for ev, items in evaluator_items.items():
        per_eval_res[ev] = calculate_cm_stats(items)
        
    return {'overall': overall_stats, 'per_evaluator': per_eval_res}

def run_all_metrics(data_dir, normalization='none', output_file='metrics.json'):
    from .utils import load_data
    
    print(f"Loading data from {data_dir} with normalization={normalization}...")
    data = load_data(data_dir, normalization)
    
    print("Computing Stats...")
    stats_res = compute_metric_stats(data)
    
    print("Computing Significance Tests...")
    sig_res = compute_statistical_tests(data)
    
    print("Computing Kappa...")
    kappa_res = compute_kappa(data)
    
    # Turing (skip if no data)
    turing_res = compute_turing_tests(data)
    
    final_output = {
        'statistics': stats_res,
        'significance': sig_res,
        'agreement': kappa_res,
        'turing': turing_res
    }
    
    with open(output_file, 'w') as f:
        json.dump(final_output, f, indent=2, cls=NumpyEncoder)
        
    return final_output


if __name__ == "__main__":
    data_dir = Path(__file__).parent / 'data'
    output_path = Path(__file__).parent / 'metrics.json'
    run_all_metrics(str(data_dir), output_file=str(output_path))
