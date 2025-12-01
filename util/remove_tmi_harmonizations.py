"""
Remove harmonized texts containing TMI-related phrases.

This script removes harmonization entries that contain references to TMI
(Transactions on Medical Imaging) which may indicate the model was biased
by venue information.

Searches for:
- "TMI" (uppercase)
- "IEEE TMI" (uppercase)
- "transactions on medical imaging" (case-insensitive)
- "IEEE transactions on medical imaging" (case-insensitive)
"""

import json
import sys
import re
from typing import List, Dict, Any


def contains_tmi_reference(text: str) -> bool:
    """
    Check if text contains any TMI-related phrases.

    Args:
        text: The harmonized text to check

    Returns:
        True if text contains any TMI reference
    """
    if not text:
        return False

    # Check for "TMI" as a standalone word (with word boundaries)
    # This prevents matching words like "LTMIC" or "OPTIMIZED"
    if re.search(r'\bTMI\b', text):
        return True

    # Check for "IEEE TMI" with word boundaries
    if re.search(r'\bIEEE\s+TMI\b', text):
        return True

    # Check for case-insensitive matches with word boundaries
    if re.search(r'\btransactions\s+on\s+medical\s+imaging\b', text, re.IGNORECASE):
        return True
    if re.search(r'\bieee\s+transactions\s+on\s+medical\s+imaging\b', text, re.IGNORECASE):
        return True

    return False


def analyze_harmonizations(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze harmonizations and count TMI references.

    Args:
        data: List of paper dictionaries

    Returns:
        Dictionary with analysis statistics
    """
    stats = {
        'total_papers': len(data),
        'total_reviews': 0,
        'total_harmonizations': 0,
        'tmi_harmonizations': 0,
        'affected_papers': 0,
        'affected_reviews': 0,
        'examples': []  # Store examples for display
    }

    for paper in data:
        paper_has_tmi = False
        reviews = paper.get('reviews', [])
        stats['total_reviews'] += len(reviews)

        for review in reviews:
            review_has_tmi = False
            harmonizations = review.get('harmonization', [])

            if harmonizations:
                stats['total_harmonizations'] += len(harmonizations)

                for harm in harmonizations:
                    harm_text = harm.get('text', '')

                    if contains_tmi_reference(harm_text):
                        stats['tmi_harmonizations'] += 1
                        review_has_tmi = True
                        paper_has_tmi = True

                        # Store example (limit to 3)
                        if len(stats['examples']) < 3:
                            # Extract snippet around TMI reference
                            snippet = harm_text[:200] + '...' if len(harm_text) > 200 else harm_text
                            stats['examples'].append({
                                'paper': paper.get('title', 'Unknown')[:60],
                                'model': harm.get('model', 'Unknown'),
                                'snippet': snippet
                            })

            if review_has_tmi:
                stats['affected_reviews'] += 1

        if paper_has_tmi:
            stats['affected_papers'] += 1

    return stats


def remove_tmi_harmonizations(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove harmonization entries containing TMI references.

    Args:
        data: List of paper dictionaries

    Returns:
        Updated list with TMI harmonizations removed
    """
    for paper in data:
        for review in paper.get('reviews', []):
            harmonizations = review.get('harmonization', [])

            if harmonizations:
                # Filter out harmonizations containing TMI references
                filtered_harmonizations = [
                    harm for harm in harmonizations
                    if not contains_tmi_reference(harm.get('text', ''))
                ]

                review['harmonization'] = filtered_harmonizations

    return data


def print_statistics(stats: Dict[str, Any]):
    """Print analysis statistics."""
    print("\n" + "=" * 80)
    print("TMI HARMONIZATION ANALYSIS")
    print("=" * 80)
    print(f"Total papers:                    {stats['total_papers']}")
    print(f"Total reviews:                   {stats['total_reviews']}")
    print(f"Total harmonizations:            {stats['total_harmonizations']}")
    print(f"\nTMI harmonizations found:        {stats['tmi_harmonizations']}")
    print(f"Affected reviews:                {stats['affected_reviews']}")
    print(f"Affected papers:                 {stats['affected_papers']}")

    if stats['total_harmonizations'] > 0:
        percentage = (stats['tmi_harmonizations'] / stats['total_harmonizations']) * 100
        print(f"Percentage of harmonizations:    {percentage:.1f}%")

    # Show examples
    if stats['examples']:
        print(f"\n" + "-" * 80)
        print("EXAMPLES OF TMI REFERENCES:")
        print("-" * 80)
        for i, example in enumerate(stats['examples'], 1):
            print(f"\nExample {i}:")
            print(f"  Paper: {example['paper']}")
            print(f"  Model: {example['model']}")
            print(f"  Text:  {example['snippet']}")

    print("=" * 80)


def main():
    """Main entry point."""
    # Default input file
    input_file = "reviews/evaluation-data-all-venues.json"

    # Allow command line override
    if len(sys.argv) > 1:
        input_file = sys.argv[1]

    print(f"\n📖 Reading data from: {input_file}")

    # Load data
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: File not found: {input_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in file: {e}")
        sys.exit(1)

    print(f"   Loaded {len(data)} papers")

    # Analyze harmonizations
    print("\n🔍 Analyzing harmonizations for TMI references...")
    stats = analyze_harmonizations(data)

    # Print statistics
    print_statistics(stats)

    # Check if any TMI harmonizations found
    if stats['tmi_harmonizations'] == 0:
        print("\n✅ No TMI harmonizations found. Nothing to remove.")
        sys.exit(0)

    # Ask for confirmation
    print(f"\n⚠️  WARNING: This will REMOVE {stats['tmi_harmonizations']} harmonization(s)")
    print(f"            from {input_file}")
    response = input("\nDo you want to proceed? (yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print("❌ Operation cancelled by user")
        sys.exit(0)

    # Remove TMI harmonizations
    print("\n🗑️  Removing TMI harmonizations...")
    updated_data = remove_tmi_harmonizations(data)

    # Save updated data
    print(f"💾 Saving updated data to: {input_file}")
    try:
        with open(input_file, 'w', encoding='utf-8') as f:
            json.dump(updated_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Successfully removed {stats['tmi_harmonizations']} TMI harmonization(s)")
    except Exception as e:
        print(f"❌ Error writing file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
