#!/usr/bin/env python3
"""
Script to remove all reviews from a specific reviewer.

This script removes all reviews where the reviewer matches a specified value.
By default, it removes reviews where reviewer == "ai/hkust-reviewer"
"""

import json
import sys
from pathlib import Path

# Get the script directory and project root
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent

# Default path to reviews JSON
DEFAULT_REVIEWS_JSON = PROJECT_ROOT / "reviews" / "evaluation-data-all-venues.json"
DEFAULT_REVIEWER = "ai/hkust-reviewer"


def remove_reviews_by_reviewer(data, reviewer_to_remove, dry_run=False):
    """
    Remove all reviews from a specific reviewer.

    Args:
        data: List of papers with reviews
        reviewer_to_remove: The reviewer value to match and remove
        dry_run: If True, only print what would be removed without modifying data

    Returns:
        tuple: (modified_data, stats_dict)
    """
    stats = {
        'total_papers': len(data),
        'papers_with_matching_reviews': 0,
        'total_reviews_processed': 0,
        'matching_reviews_found': 0,
        'matching_reviews_removed': 0
    }

    modified_data = []

    for paper_idx, paper in enumerate(data):
        paper_title = paper.get('title', f'Paper {paper_idx}')
        reviews = paper.get('reviews', [])

        if not reviews:
            modified_data.append(paper)
            continue

        new_reviews = []
        paper_had_matches = False

        for review_idx, review in enumerate(reviews):
            stats['total_reviews_processed'] += 1

            reviewer = review.get('reviewer', '')

            # Check if this review matches the reviewer to remove
            if reviewer == reviewer_to_remove:
                stats['matching_reviews_found'] += 1
                paper_had_matches = True

                if dry_run:
                    print(f"  [WOULD REMOVE] Paper '{paper_title[:65]}...' - Review {review_idx}: {reviewer}")
                else:
                    print(f"  [REMOVING] Paper '{paper_title[:65]}...' - Review {review_idx}: {reviewer}")
                    stats['matching_reviews_removed'] += 1
                # Don't add to new_reviews (effectively removing it)
                continue

            # Keep this review
            new_reviews.append(review)

        if paper_had_matches:
            stats['papers_with_matching_reviews'] += 1

        # Update paper with filtered reviews
        paper_copy = paper.copy()
        paper_copy['reviews'] = new_reviews
        modified_data.append(paper_copy)

    return modified_data, stats


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Remove all reviews from a specific reviewer'
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
        '--reviewer',
        type=str,
        default=DEFAULT_REVIEWER,
        help=f'Reviewer to remove (default: {DEFAULT_REVIEWER})'
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
    reviewer_to_remove = args.reviewer

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
        print(f"REMOVING ALL REVIEWS FROM: {reviewer_to_remove}")
    print(f"{'='*80}\n")

    modified_data, stats = remove_reviews_by_reviewer(data, reviewer_to_remove, dry_run=args.dry_run)

    # Print statistics
    print(f"\n{'='*80}")
    print("STATISTICS")
    print(f"{'='*80}")
    print(f"Reviewer to remove:                   {reviewer_to_remove}")
    print(f"Total papers processed:               {stats['total_papers']}")
    print(f"Papers with matching reviews:         {stats['papers_with_matching_reviews']}")
    print(f"Total reviews processed:              {stats['total_reviews_processed']}")
    print(f"Matching reviews found:               {stats['matching_reviews_found']}")

    if args.dry_run:
        print(f"Reviews that would be removed:        {stats['matching_reviews_found']}")
    else:
        print(f"Reviews removed:                      {stats['matching_reviews_removed']}")
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
