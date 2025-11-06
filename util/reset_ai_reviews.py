#!/usr/bin/env python3
"""
Script to remove the first half of AI reviews from each paper.

This script removes reviews where:
1. The reviewer name starts with "ai/"
2. The review is in the first half of all AI reviews for that paper

For each paper with 2N AI reviews, the first N are removed and the last N are kept.
If there's an odd number of AI reviews, the extra one is kept (e.g., 5 AI reviews -> remove 2, keep 3).
"""

import json
import sys
from pathlib import Path

# Get the script directory and project root
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent

# Default path to reviews JSON
DEFAULT_REVIEWS_JSON = PROJECT_ROOT / "reviews" / "evaluation-data-all-venues.json"


def remove_first_half_ai_reviews(data, dry_run=False):
    """
    Remove the first half of AI reviews from each paper.

    Args:
        data: List of papers with reviews
        dry_run: If True, only print what would be removed without modifying data

    Returns:
        tuple: (modified_data, stats_dict)
    """
    stats = {
        'total_papers': len(data),
        'papers_with_ai_reviews': 0,
        'total_reviews_processed': 0,
        'total_ai_reviews_found': 0,
        'total_ai_reviews_removed': 0,
        'total_ai_reviews_kept': 0
    }

    modified_data = []

    for paper_idx, paper in enumerate(data):
        paper_title = paper.get('title', f'Paper {paper_idx}')
        reviews = paper.get('reviews', [])

        if not reviews:
            modified_data.append(paper)
            continue

        # Find all AI reviews with their indices
        ai_review_indices = []
        for review_idx, review in enumerate(reviews):
            stats['total_reviews_processed'] += 1
            reviewer = review.get('reviewer', '')
            if reviewer.startswith('ai/'):
                ai_review_indices.append(review_idx)

        ai_count = len(ai_review_indices)

        if ai_count > 0:
            stats['papers_with_ai_reviews'] += 1
            stats['total_ai_reviews_found'] += ai_count

            # Calculate how many to remove (first half)
            num_to_remove = ai_count // 2
            num_to_keep = ai_count - num_to_remove

            # Indices of AI reviews to remove (first half)
            indices_to_remove = set(ai_review_indices[:num_to_remove])

            stats['total_ai_reviews_removed'] += num_to_remove
            stats['total_ai_reviews_kept'] += num_to_keep

            if dry_run:
                print(f"\nPaper '{paper_title[:70]}...'")
                print(f"  Total AI reviews: {ai_count}")
                print(f"  Will remove: {num_to_remove} (first half)")
                print(f"  Will keep: {num_to_keep} (last half)")
            else:
                print(f"\nPaper '{paper_title[:70]}...'")
                print(f"  Total AI reviews: {ai_count}")
                print(f"  Removing: {num_to_remove} (first half)")
                print(f"  Keeping: {num_to_keep} (last half)")

            # Build new reviews list
            new_reviews = []
            for review_idx, review in enumerate(reviews):
                if review_idx in indices_to_remove:
                    reviewer = review.get('reviewer', '')
                    if dry_run:
                        print(f"    [REMOVE] Review {review_idx}: {reviewer}")
                    else:
                        print(f"    Removing Review {review_idx}: {reviewer}")
                    # Don't add to new_reviews (effectively removing it)
                    continue

                # Keep this review
                new_reviews.append(review)

                # Log if it's an AI review that we're keeping
                if review_idx in ai_review_indices and review_idx not in indices_to_remove:
                    reviewer = review.get('reviewer', '')
                    if dry_run:
                        print(f"    [KEEP]   Review {review_idx}: {reviewer}")
                    else:
                        print(f"    Keeping  Review {review_idx}: {reviewer}")
        else:
            new_reviews = reviews

        # Update paper with filtered reviews
        paper_copy = paper.copy()
        paper_copy['reviews'] = new_reviews
        modified_data.append(paper_copy)

    return modified_data, stats


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Remove the first half of AI reviews from each paper'
    )
    parser.add_argument(
        '--input',
        type=Path,
        default=DEFAULT_REVIEWS_JSON,
        help=f'Path to input JSON file (default: {DEFAULT_REVIEWS_JSON})'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Path to output JSON file (default: overwrites input file)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be removed without making changes'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        default=True,
        help='Create backup before modifying (default: True)'
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Do not create backup before modifying'
    )

    args = parser.parse_args()

    input_file = args.input
    output_file = args.output or input_file

    # Validate input file
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    # Load data
    print(f"Loading data from: {input_file}")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data, list):
        print("Error: Expected JSON array of papers", file=sys.stderr)
        sys.exit(1)

    # Process data
    print(f"\n{'='*80}")
    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")
    else:
        print("REMOVING FIRST HALF OF AI REVIEWS FROM EACH PAPER")
    print(f"{'='*80}")

    modified_data, stats = remove_first_half_ai_reviews(data, dry_run=args.dry_run)

    # Print statistics
    print(f"\n{'='*80}")
    print("STATISTICS")
    print(f"{'='*80}")
    print(f"Total papers processed:               {stats['total_papers']}")
    print(f"Papers with AI reviews:               {stats['papers_with_ai_reviews']}")
    print(f"Total reviews processed:              {stats['total_reviews_processed']}")
    print(f"Total AI reviews found:               {stats['total_ai_reviews_found']}")

    if args.dry_run:
        print(f"AI reviews that would be removed:     {stats['total_ai_reviews_removed']}")
        print(f"AI reviews that would be kept:        {stats['total_ai_reviews_kept']}")
    else:
        print(f"AI reviews removed:                   {stats['total_ai_reviews_removed']}")
        print(f"AI reviews kept:                      {stats['total_ai_reviews_kept']}")
    print(f"{'='*80}\n")

    # Save if not dry run
    if not args.dry_run:
        # Create backup if requested
        if args.backup and not args.no_backup:
            backup_file = output_file.with_suffix('.json.backup')
            print(f"Creating backup: {backup_file}")
            try:
                with open(input_file, 'r', encoding='utf-8') as f:
                    backup_content = f.read()
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(backup_content)
                print(f"Backup created successfully\n")
            except Exception as e:
                print(f"Warning: Could not create backup: {e}", file=sys.stderr)

        # Save modified data
        print(f"Saving modified data to: {output_file}")
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(modified_data, f, indent=2, ensure_ascii=False)
            print(f" File saved successfully\n")
        except Exception as e:
            print(f"Error saving file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("DRY RUN complete. Use without --dry-run to apply changes.\n")


if __name__ == '__main__':
    main()
