#!/usr/bin/env python3
"""
Script to remove all harmonization data from reviews.

This script removes the 'harmonization' key and all its data from every review
in the evaluation JSON file. This is useful for cleaning up the dataset or
preparing it for re-harmonization.
"""

import json
import sys
from pathlib import Path

# Get the script directory and project root
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent

# Default path to reviews JSON
DEFAULT_REVIEWS_JSON = PROJECT_ROOT / "reviews" / "evaluation-data-all-venues.json"


def remove_harmonization(data, dry_run=False):
    """
    Remove harmonization data from all reviews.

    Args:
        data: List of papers with reviews
        dry_run: If True, only print what would be removed without modifying data

    Returns:
        tuple: (modified_data, stats_dict)
    """
    stats = {
        'total_papers': len(data),
        'total_reviews_processed': 0,
        'reviews_with_harmonization': 0,
        'harmonization_entries_removed': 0
    }

    modified_data = []

    for paper_idx, paper in enumerate(data):
        paper_title = paper.get('title', f'Paper {paper_idx}')
        reviews = paper.get('reviews', [])

        if not reviews:
            modified_data.append(paper)
            continue

        paper_copy = paper.copy()
        paper_copy['reviews'] = []

        for review_idx, review in enumerate(reviews):
            stats['total_reviews_processed'] += 1

            review_copy = review.copy()

            # Check if harmonization exists
            if 'harmonization' in review_copy:
                harmonization_data = review_copy['harmonization']
                if harmonization_data:
                    stats['reviews_with_harmonization'] += 1
                    num_entries = len(harmonization_data) if isinstance(harmonization_data, list) else 1
                    stats['harmonization_entries_removed'] += num_entries

                    if dry_run:
                        print(f"  [WOULD REMOVE] Paper '{paper_title[:65]}...' - Review {review_idx}: {num_entries} harmonization entries")
                    else:
                        print(f"  [REMOVING] Paper '{paper_title[:65]}...' - Review {review_idx}: {num_entries} harmonization entries")

                # Remove the harmonization key
                del review_copy['harmonization']

            paper_copy['reviews'].append(review_copy)

        modified_data.append(paper_copy)

    return modified_data, stats


def print_statistics(stats):
    """Print removal statistics."""
    print("\n" + "="*80)
    print("HARMONIZATION REMOVAL STATISTICS")
    print("="*80)
    print(f"Total papers processed:               {stats['total_papers']}")
    print(f"Total reviews processed:              {stats['total_reviews_processed']}")
    print(f"Reviews with harmonization:           {stats['reviews_with_harmonization']}")
    print(f"Harmonization entries removed:        {stats['harmonization_entries_removed']}")
    print("="*80 + "\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Remove all harmonization data from reviews'
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
        print("REMOVING ALL HARMONIZATION DATA")
    print(f"{'='*80}\n")

    modified_data, stats = remove_harmonization(data, dry_run=args.dry_run)

    # Print statistics
    print_statistics(stats)

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
