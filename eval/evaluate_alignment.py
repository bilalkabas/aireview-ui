import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
from rouge_score import rouge_scorer
import sacrebleu
from dotenv import load_dotenv
import nltk
from tqdm import tqdm

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

load_dotenv()

# Setup OpenAI
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    api_key = os.environ.get("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

SCORING_MODEL = "gpt-5.2" 
EMBEDDING_MODEL = "text-embedding-3-large"

# Define Prompt Template Globally
SCORING_PROMPT_TEMPLATE = """
You are an expert reviewer evaluator.
Compare the Original Review and the Harmonized Review below.
The Harmonized Review is a rewriting of the Original.

Assess semantic alignment on two axes:
1. Correctness (1-5): Is the information factually preserving the original? 5 = Perfect preservation.
2. Coverage (1-5): Does it cover all key points from the original? 5 = covers everything.

Original Review:
{original}

Harmonized Review:
{harmonized}

Return a JSON object with keys "correctness" and "coverage" (integers 1-5).
"""

def get_embedding(text):
    text = text.replace("\n", " ")
    if not text.strip():
        return np.zeros(3072) 
    res = client.embeddings.create(input=[text], model=EMBEDDING_MODEL)
    return res.data[0].embedding

def get_llm_score(original, harmonized):
    prompt = SCORING_PROMPT_TEMPLATE.format(original=original, harmonized=harmonized)
    
    try:
        response = client.chat.completions.create(
            model=SCORING_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"Error in LLM scoring: {e}")
        return {"correctness": 0, "coverage": 0}

def compute_metrics(original, harmonized):
    # 1. LLM Score
    llm_scores = get_llm_score(original, harmonized)
    
    # 2. Embedding Cosine Similarity
    emb_orig = get_embedding(original)
    emb_harm = get_embedding(harmonized)
    
    if len(emb_orig) > 0 and len(emb_harm) > 0:
        cos_sim = cosine_similarity([emb_orig], [emb_harm])[0][0]
    else:
        cos_sim = 0.0
    
    # 3. ROUGE
    scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
    rouge_scores = scorer.score(original, harmonized)
    rouge_l = rouge_scores['rougeL'].fmeasure
    
    # 4. BLEU
    bleu = sacrebleu.sentence_bleu(harmonized, [original]).score
    
    return {
        "correctness": llm_scores.get('correctness', 0),
        "coverage": llm_scores.get('coverage', 0),
        "cosine_similarity": cos_sim,
        "rouge_l": rouge_l,
        "bleu": bleu
    }

def plot_distributions(df, output_dir):
    plot_dir = output_dir / 'plots'
    plot_dir.mkdir(exist_ok=True)
    
    sns.set_theme(style="whitegrid")
    
    # Define Metric Groups
    groups = {
        'llm': {
            'metrics': ['correctness', 'coverage'],
            'title': 'LLM Evaluation (1-5)',
            'file_suffix': 'llm'
        },
        'cosine': {
            'metrics': ['cosine_similarity'],
            'title': 'Cosine Similarity (0-1)',
            'file_suffix': 'cosine'
        },
        'rouge': {
            'metrics': ['rouge_l'],
            'title': 'ROUGE-L Score (0-1)',
            'file_suffix': 'rouge'
        },
        'bleu': {
            'metrics': ['bleu'],
            'title': 'BLEU Score (0-100)',
            'file_suffix': 'bleu'
        }
    }
    
    for key, group in groups.items():
        metrics_list = group['metrics']
        title_base = group['title']
        suffix = group['file_suffix']
        
        # 1. Overall Mean + Variance (Bar Plot)
        plt.figure(figsize=(8 if len(metrics_list)==1 else 10, 6))
        df_melt = df.melt(id_vars=['reviewer_type', 'model'], value_vars=metrics_list, var_name='Metric', value_name='Score')
        
        sns.barplot(data=df_melt, x='Metric', y='Score', hue='reviewer_type', errorbar='sd', capsize=.1, alpha=0.8)
        
        plt.title(f"{title_base}: Human vs AI (Mean ± Std Dev)")
        plt.tight_layout()
        plt.savefig(plot_dir / f'overall_{suffix}.png')
        plt.close()
        
        # 2. Per Model Breakdown (Bar Plot) - Only AI
        df_ai = df[df['reviewer_type'] == 'AI']
        if not df_ai.empty:
            plt.figure(figsize=(10 if len(metrics_list)==1 else 12, 6))
            df_ai_melt = df_ai.melt(id_vars=['model'], value_vars=metrics_list, var_name='Metric', value_name='Score')
            
            sns.barplot(data=df_ai_melt, x='Metric', y='Score', hue='model', errorbar='sd', capsize=.1, alpha=0.9)
            
            plt.title(f"{title_base}: AI Models (Mean ± Std Dev)")
            if len(metrics_list) > 1:
                plt.xticks(rotation=45)
            # Move legend outside
            plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.tight_layout()
            plt.savefig(plot_dir / f'ai_models_{suffix}.png')
            plt.close()

def generate_md_report(df, output_dir):
    metrics = ["correctness", "coverage", "cosine_similarity", "rouge_l", "bleu"]
    
    # 1. Overall Statistics (Transposed)
    stats = df.groupby('reviewer_type')[metrics].agg(['mean', 'std'])
    
    stacked = stats.stack(level=0, future_stack=True) 
    transposed = stacked.unstack(level=0)
    
    transposed.columns = transposed.columns.swaplevel(0, 1)
    transposed.sort_index(axis=1, inplace=True)
    
    transposed.columns = [f"{col[0]} ({col[1].capitalize()})" for col in transposed.columns]
    
    md = "# Harmonization Alignment Evaluation\n\n"
    md += "This report evaluates the semantic alignment between original reviews and their harmonized versions.\n\n"
    
    md += "## Methodology\n"
    md += "We used a multi-tiered approach:\n"
    md += f"1. **LLM Eval ({SCORING_MODEL})**: Scored Correctness and Coverage (1-5).\n"
    md += f"2. **Embedding Similarity**: Cosine similarity using `{EMBEDDING_MODEL}`.\n"
    md += "3. **ROUGE-L**: Measures longest common subsequence overlap.\n"
    md += "4. **BLEU**: Measures n-gram overlap precision.\n\n"
    
    md += "## Scoring Prompt\n"
    md += "The following prompt was used for LLM evaluation:\n\n"
    md += "```text\n"
    md += SCORING_PROMPT_TEMPLATE
    md += "\n```\n\n"
    
    md += "## Overall Statistics\n"
    md += "Mean and Standard Deviation for each metric.\n\n"
    md += transposed.to_markdown(floatfmt=".3f")
    md += "\n\n"
    
    md += "### Visualizations (Overall)\n"
    md += "#### LLM Scores (1-5)\n![LLM Overall](plots/overall_llm.png)\n\n"
    md += "#### Cosine Similarity (0-1)\n![Cosine Overall](plots/overall_cosine.png)\n\n"
    md += "#### ROUGE-L (0-1)\n![ROUGE Overall](plots/overall_rouge.png)\n\n"
    md += "#### BLEU (0-100)\n![BLEU Overall](plots/overall_bleu.png)\n\n"
    
    md += "## AI Model Performance\n"
    
    # Per Model Table (Transposed)
    df_ai = df[df['reviewer_type'] == 'AI']
    if not df_ai.empty:
        stats_ai = df_ai.groupby('model')[metrics].mean()
        stats_ai_T = stats_ai.T
        
        md += stats_ai_T.to_markdown(floatfmt=".3f")
        md += "\n\n"
    
    md += "### Visualizations (By Model)\n"
    md += "#### LLM Scores (1-5)\n![LLM AI Models](plots/ai_models_llm.png)\n\n"
    md += "#### Cosine Similarity (0-1)\n![Cosine AI Models](plots/ai_models_cosine.png)\n\n"
    md += "#### ROUGE-L (0-1)\n![ROUGE AI Models](plots/ai_models_rouge.png)\n\n"
    md += "#### BLEU (0-100)\n![BLEU AI Models](plots/ai_models_bleu.png)\n\n"
    
    report_path = output_dir / 'alignment_report.md'
    with open(report_path, 'w') as f:
        f.write(md)
    print(f"Report generated at {report_path}")

def main():
    output_dir = Path(__file__).parent / 'alignment_evaluation'
    output_dir.mkdir(exist_ok=True)
    csv_path = output_dir / 'alignment_results.csv'
    
    # Check for existing results
    if csv_path.exists():
        print(f"Loading existing results from {csv_path}...")
        df = pd.read_csv(csv_path)
    else:
        # File Loading Logic
        data_file = Path(__file__).parent.parent / 'reviews' / 'evaluation-data-all-venues.json'
        
        if not data_file.exists():
            print(f"Error: {data_file} not found.")
            return

        files = [data_file]
        
        results = []
        print(f"Starting alignment evaluation on {data_file}...")
        
        for fpath in files:
            evaluator_name = "Combined" 
            print(f"Processing {data_file.name}...")
            
            with open(fpath, 'r') as f:
                papers = json.load(f)
                
            # Count total reviews
            total_reviews = sum(len(p.get('reviews', [])) for p in papers)
            
            with tqdm(total=total_reviews, desc="Evaluating", unit="review") as pbar:
                for paper in papers:
                    for review in paper.get('reviews', []):
                        original_text = review.get('text', '')
                        harm_list = review.get('harmonization', [])
                        
                        if not original_text or not harm_list:
                            pbar.update(1)
                            continue
                            
                        harmonized_text = harm_list[0].get('text', '')
                        if not harmonized_text:
                            pbar.update(1)
                            continue
                        
                        # Metadata
                        is_human = (review.get('reviewer') == 'human')
                        reviewer_type = 'Human' if is_human else 'AI'
                        if not is_human:
                            model_name = review.get('reviewer').replace('ai/', '')
                        else:
                            model_name = 'Human'
                        
                        try:
                            metrics = compute_metrics(original_text, harmonized_text)
                            
                            record = {
                                "evaluator": evaluator_name,
                                "reviewer_type": reviewer_type,
                                "model": model_name,
                                **metrics
                            }
                            results.append(record)
                            
                        except Exception as e:
                            print(f"Failed review: {e}")
                        
                        pbar.update(1)

        if not results:
            print("No reviews processed. Check data keys.")
            return

        # Save Results
        df = pd.DataFrame(results)
        df.to_csv(csv_path, index=False)
        print(f"Results saved to {csv_path}")
    
    # Generate Plots
    print("Generating Plots...")
    plot_distributions(df, output_dir)
    
    # Generate Report
    print("Generating Report...")
    generate_md_report(df, output_dir)

if __name__ == "__main__":
    main()
