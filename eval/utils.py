import json
import logging
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd

# Constants
METRICS = ['coverage', 'specificity', 'correctness', 'constructiveness', 'stance']

def clean_model_name(name):
    """
    Cleans model name by removing 'ai/' prefix if present.
    Example: 'ai/gpt-4-0613' -> 'gpt-4-0613'
    """
    if name.startswith('ai/'):
        return name[3:]
    return name

def get_stats(scores):
    """
    computes basic statistics (N, Min, Max, Mean, Std) for a list of scores.
    Returns a dictionary.
    """
    if len(scores) == 0: 
        return {'N': 0, 'Min': 0, 'Max': 0, 'Mean': 0, 'Std': 0}
    return {
        'N': len(scores),
        'Min': np.min(scores),
        'Max': np.max(scores),
        'Mean': np.mean(scores),
        'Std': np.std(scores)
    }

def normalize_score(score, min_val, max_val):
    """
    Min-max normalization to range [1, 5].
    """
    rng = max_val - min_val
    if rng == 0:
        rng = 1.0 # Avoid division by zero
    return (score - min_val) / rng * 4.0 + 1.0

def load_data(data_dir, normalization='none'):
    """
    Loads evaluation data from JSON files in the specified directory.
    
    Args:
        data_dir (str or Path): Path to directory containing 'evaluation-data-all-venues-*.json' files.
        normalization (str): 'none', 'evaluator', 'evaluator_metric', or 'evaluator_metric_target'.
        
    Returns:
        dict: A dictionary containing:
            - 'raw_reviews': List of all review objects with metadata.
            - 'scores': flat list of dicts {'evaluator', 'reviewer_type', 'model', 'metric', 'score', 'paper_title'}
            - 'evaluators': List of evaluator names.
            - 'models': List of AI model names.
    """
    data_dir = Path(data_dir)
    all_files = sorted(data_dir.glob('evaluation-data-all-venues-*.json'))
    
    # Pass 1: Collect stats for normalization if needed
    evaluator_stats = {} # {evaluator: {'min': x, 'max': y}}
    evaluator_metric_stats = defaultdict(dict) # {evaluator: {metric: {'min': x, 'max': y}}}
    
    if normalization != 'none':
        temp_scores_eval = defaultdict(list)
        temp_scores_eval_metric = defaultdict(lambda: defaultdict(list))
        
        for fpath in all_files:
            evaluator_name = fpath.stem.replace('evaluation-data-all-venues-', '').capitalize()
            with open(fpath, 'r') as f:
                papers = json.load(f)
                
            for paper in papers:
                for review in paper.get('reviews', []):
                    metrics = review.get('metrics', {})
                    for m in METRICS:
                        val = metrics.get(m, 0)
                        if val > 0:
                            if normalization == 'evaluator':
                                temp_scores_eval[evaluator_name].append(val)
                            elif normalization in ['evaluator_metric', 'evaluator_metric_target']:
                                temp_scores_eval_metric[evaluator_name][m].append(val)
        
        # Compute Min/Max
        if normalization == 'evaluator':
            for ev, vals in temp_scores_eval.items():
                evaluator_stats[ev] = {'min': min(vals), 'max': max(vals)}
        elif normalization == 'evaluator_metric':
            for ev, m_vals in temp_scores_eval_metric.items():
                for m, vals in m_vals.items():
                    evaluator_metric_stats[ev][m] = {'min': min(vals), 'max': max(vals)}
        elif normalization == 'evaluator_metric_target':
            for ev, m_vals in temp_scores_eval_metric.items():
                for m, vals in m_vals.items():
                    std = np.std(vals)
                    if std == 0: std = 1.0
                    evaluator_metric_stats[ev][m] = {'mean': np.mean(vals), 'std': std}

    # Pass 2: Collect and Normalize Data
    flat_scores = []
    confusion_data = []
    models = set()
    evaluators = set()
    raw_reviews = []
    
    for fpath in all_files:
        evaluator_name = fpath.stem.replace('evaluation-data-all-venues-', '').replace('.json', '').capitalize()
        evaluators.add(evaluator_name)
        
        with open(fpath, 'r') as f:
            papers = json.load(f)
            
        for paper in papers:
            title = paper.get('title', 'Unknown')
            decision = paper.get('decision', 'Unknown')
            for review in paper.get('reviews', []):
                reviewer_raw = review.get('reviewer', 'unknown')
                is_human = (reviewer_raw == 'human')
                model_name = clean_model_name(reviewer_raw)
                if not is_human:
                    models.add(model_name)
                
                review_obj = {
                    'evaluator': evaluator_name,
                    'paper_title': title,
                    'is_human': is_human,
                    'model': model_name,
                    'metrics': {},
                    'original': review
                }
                
                metrics = review.get('metrics', {})
                
                # Turing Test Data
                source_guess = metrics.get('source', '')
                if source_guess in ['human', 'ai']:
                    confusion_data.append({
                        'evaluator': evaluator_name,
                        'actual': 'human' if is_human else 'ai',
                        'predicted': source_guess,
                        'decision': decision
                    })

                for m in METRICS:
                    val = metrics.get(m, 0)
                    if val > 0:
                        # Apply Normalization
                        final_val = val
                        if normalization == 'evaluator':
                            stats = evaluator_stats.get(evaluator_name, {'min': 1, 'max': 5})
                            final_val = normalize_score(val, stats['min'], stats['max'])
                        elif normalization == 'evaluator_metric':
                            stats = evaluator_metric_stats.get(evaluator_name, {}).get(m, {'min': 1, 'max': 5})
                            final_val = normalize_score(val, stats['min'], stats['max'])
                        elif normalization == 'evaluator_metric_target':
                            stats = evaluator_metric_stats.get(evaluator_name, {}).get(m, {'mean': 2.5, 'std': 1.0})
                            z = (val - stats['mean']) / stats['std']
                            final_val = z * 1.0 + 2.5
                            final_val = max(1.0, min(5.0, final_val))
                        
                        review_obj['metrics'][m] = final_val
                        
                        flat_scores.append({
                            'evaluator': evaluator_name,
                            'paper_title': title,
                            'is_human': is_human,
                            'model': model_name,
                            'metric': m,
                            'score': final_val,
                            'decision': decision
                        })
                
                raw_reviews.append(review_obj)

    return {
        'scores': flat_scores, 
        'confusion_data': confusion_data,
        'raw_reviews': raw_reviews,
        'evaluators': sorted(list(evaluators)), 
        'models': sorted(list(models))
    }