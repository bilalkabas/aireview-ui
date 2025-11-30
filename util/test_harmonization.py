"""
Test script to validate harmonization data.
Checks that each review has exactly one harmonized text.
"""

import json
import os
import sys
from typing import List, Dict, Any

# Load environment variables (optional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not required for this script

# Configuration
INPUT_FILE = os.environ.get("HARMONIZATION_INPUT_FILE", "reviews/evaluation-data-all-venues.json")


class ValidationResult:
    """Stores validation results for reporting."""
    
    def __init__(self):
        self.total_papers = 0
        self.total_reviews = 0
        self.reviews_with_no_harmonization = []
        self.reviews_with_multiple_harmonizations = []
        self.reviews_with_exactly_one = 0
        
    def add_no_harmonization(self, paper_idx: int, paper_title: str, review_idx: int):
        """Record a review with no harmonization."""
        self.reviews_with_no_harmonization.append({
            "paper_idx": paper_idx,
            "paper_title": paper_title,
            "review_idx": review_idx
        })
    
    def add_multiple_harmonizations(self, paper_idx: int, paper_title: str, review_idx: int, count: int):
        """Record a review with multiple harmonizations."""
        self.reviews_with_multiple_harmonizations.append({
            "paper_idx": paper_idx,
            "paper_title": paper_title,
            "review_idx": review_idx,
            "harmonization_count": count
        })
    
    def is_valid(self) -> bool:
        """Check if all reviews have exactly one harmonization."""
        return (len(self.reviews_with_no_harmonization) == 0 and 
                len(self.reviews_with_multiple_harmonizations) == 0)
    
    def print_report(self):
        """Print a detailed validation report."""
        print("\n" + "=" * 70)
        print("📋 HARMONIZATION VALIDATION REPORT")
        print("=" * 70)
        print(f"Total papers: {self.total_papers}")
        print(f"Total reviews: {self.total_reviews}")
        print(f"Reviews with exactly 1 harmonization: {self.reviews_with_exactly_one}")
        print(f"Reviews with NO harmonization: {len(self.reviews_with_no_harmonization)}")
        print(f"Reviews with MULTIPLE harmonizations: {len(self.reviews_with_multiple_harmonizations)}")
        print("=" * 70)
        
        # Details for reviews with no harmonization
        if self.reviews_with_no_harmonization:
            print("\n⚠️  REVIEWS WITH NO HARMONIZATION:")
            print("-" * 70)
            for item in self.reviews_with_no_harmonization[:10]:  # Show first 10
                print(f"  Paper {item['paper_idx'] + 1}: {item['paper_title'][:60]}...")
                print(f"    → Review {item['review_idx'] + 1}: NO harmonization found")
            if len(self.reviews_with_no_harmonization) > 10:
                print(f"  ... and {len(self.reviews_with_no_harmonization) - 10} more")
        
        # Details for reviews with multiple harmonizations
        if self.reviews_with_multiple_harmonizations:
            print("\n⚠️  REVIEWS WITH MULTIPLE HARMONIZATIONS:")
            print("-" * 70)
            for item in self.reviews_with_multiple_harmonizations[:10]:  # Show first 10
                print(f"  Paper {item['paper_idx'] + 1}: {item['paper_title'][:60]}...")
                print(f"    → Review {item['review_idx'] + 1}: {item['harmonization_count']} harmonizations found")
            if len(self.reviews_with_multiple_harmonizations) > 10:
                print(f"  ... and {len(self.reviews_with_multiple_harmonizations) - 10} more")
        
        # Final verdict
        print("\n" + "=" * 70)
        if self.is_valid():
            print("✅ VALIDATION PASSED: All reviews have exactly one harmonization!")
        else:
            print("❌ VALIDATION FAILED: Some reviews have incorrect harmonization counts")
        print("=" * 70 + "\n")


def validate_harmonization(file_path: str) -> ValidationResult:
    """
    Validate that each review has exactly one harmonized text.
    
    Args:
        file_path: Path to the JSON file to validate
        
    Returns:
        ValidationResult object with detailed results
    """
    result = ValidationResult()
    
    print(f"\n📖 Loading harmonization data from: {file_path}")
    
    # Load the data
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            papers = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: File not found: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in file: {e}")
        sys.exit(1)
    
    result.total_papers = len(papers)
    print(f"   Loaded {len(papers)} papers\n")
    
    # Validate each review
    for paper_idx, paper in enumerate(papers):
        title = paper.get("title", "Unknown")
        reviews = paper.get("reviews", [])
        
        for review_idx, review in enumerate(reviews):
            result.total_reviews += 1
            
            harmonization = review.get("harmonization", [])
            harmonization_count = len(harmonization)
            
            if harmonization_count == 0:
                result.add_no_harmonization(paper_idx, title, review_idx)
            elif harmonization_count == 1:
                result.reviews_with_exactly_one += 1
            else:
                result.add_multiple_harmonizations(paper_idx, title, review_idx, harmonization_count)
    
    return result


def main():
    """Main entry point for the validation script."""
    print("\n🔍 Harmonization Validation Test")
    print(f"File: {INPUT_FILE}")
    
    # Run validation
    result = validate_harmonization(INPUT_FILE)
    
    # Print report
    result.print_report()
    
    # Exit with appropriate code
    sys.exit(0 if result.is_valid() else 1)


if __name__ == "__main__":
    main()
