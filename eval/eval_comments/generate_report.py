import json
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    input_file = 'evaluator_notes.json'
    output_file = 'evaluator_notes_report.md'
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, 'r') as f:
        data = json.load(f)
        
    # Simplify data for LLM context window
    simplified_data = []
    for item in data:
        # Use 'actual_source' as defined by user update
        source = item.get('actual_source')
        if not source:
            source = item.get('source', 'unknown') # Fallback
            
        simplified_data.append({
            "evaluator": item.get('evaluator'),
            "review_source": source,
            "comment": item.get('comment'),
            # "paper": item.get('paper_title') # Optional, include if needed for context
        })
        
    print(f"Preparing to analyze {len(simplified_data)} comments...")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found.")
        return
        
    client = OpenAI(api_key=api_key)
    
    prompt = f"""
    You are an expert data analyst. You have a dataset of {len(simplified_data)} comments made by human evaluators assessing the quality of peer reviews.
    
    **Metadata Key:**
    - `evaluator`: The name of the person writing the comment.
    - `review_source`: The origin of the review being evaluated (e.g., "human", "ai/gpt-5...", "ai/claude...").
    - `comment`: The feedback text provided by the evaluator.
    
    **Dataset:**
    {json.dumps(simplified_data, indent=2)}
    
    **Task:**
    Write a **Comprehensive Markdown Report** analyzing these evaluator notes.
    
    **Report Structure:**
    1. **Executive Summary**: Brief overview of the key findings.
    2. **Descriptive Statistics**:
       - Total number of comments.
       - Distribution of comments by Evaluator.
       - Distribution of comments by Review Source (Group into "Human" vs "AI" and optionally specific models).
    3. **Thematic Analysis**:
       - Categorize the comments into main themes (e.g., "Superficiality", "Hallucination", "Tone", "Specificity", "Factual Errors").
       - Provide counts and examples for each theme.
    4. **Comparative Analysis (Crucial)**:
       - **Human vs. AI**: How do the complaints/comments differ when the source is Human vs AI? 
         - Are AI reviews more likely to be called "generic" or "superficial"?
         - Are Human reviews more likely to have "tone" issues or "brevity"?
       - **Model Comparison**: If applicable, note any differences between AI models (e.g. GPT vs Claude).
    5. **Evaluator Analysis**:
       - Briefly note if certain evaluators focus on specific issues (e.g. "Evaluator X focuses heavily on formatting").
    6. **Conclusion**: Summarize the implications for using AI in peer review based on this qualitative feedback.
    
    Output the full report in Markdown format.
    """
    
    print("Sending request to LLM (gpt-5.2)...")
    try:
        response = client.chat.completions.create(
            model="gpt-5.2",
            messages=[
                {"role": "system", "content": "You are a detailed and insightful data analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        
        report_content = response.choices[0].message.content
        
        with open(output_file, 'w') as f:
            f.write(report_content)
            
        print(f"Analysis complete. Report saved to {output_file}")
        
    except Exception as e:
        print(f"Error during LLM processing: {e}")

if __name__ == "__main__":
    main()
