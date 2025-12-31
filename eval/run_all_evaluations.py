import subprocess
import sys
from pathlib import Path

def run():
    modes = ['none', 'evaluator', 'evaluator_metric', 'evaluator_metric_target']
    # base_dir is eval/. Parent is root.
    base_dir = Path(__file__).parent
    root_dir = base_dir.parent
    
    for mode in modes:
        print(f"\n{'='*50}")
        print(f"Running evaluation for normalization: {mode}")
        print(f"{'='*50}\n")
        
        try:
            # Run LaTeX Report Generation
            print(f"Generating LaTeX report for {mode}...")
            cmd_tex = [sys.executable, "-m", "eval.create_report", "--normalization", mode]
            subprocess.run(cmd_tex, cwd=root_dir, check=True)
            
            # Run Markdown Report Generation
            print(f"Generating Markdown report for {mode}...")
            cmd_md = [sys.executable, "-m", "eval.create_report_md", "--normalization", mode]
            subprocess.run(cmd_md, cwd=root_dir, check=True)
            
            print(f"Successfully completed {mode}.")
            
        except subprocess.CalledProcessError as e:
            print(f"Error running evaluation for {mode}: {e}")
            sys.exit(1)

if __name__ == "__main__":
    run()
