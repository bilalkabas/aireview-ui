#!/usr/bin/env python3
"""
Script to append reviews from multiple evaluation JSON files.

This script takes multiple evaluation data JSON files and appends reviews
to papers based on matching titles. Only reviews are appended - all other
paper metadata (title, abstract, decision, evaluators, etc.) is taken from
the first file where the paper appears.
"""

import json
import sys
import hashlib
from pathlib import Path
from collections import defaultdict


def load_json(file_path):
    """Load JSON data from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {file_path}: {e}", file=sys.stderr)
        sys.exit(1)


def normalize_title(title):
    """Normalize paper title for matching (lowercase, strip whitespace)."""
    return title.strip().lower()


def get_review_hash(review):
    """
    Generate a unique hash for a review based on its content.

    This helps identify truly duplicate reviews (same content) vs different reviews
    from the same reviewer type (e.g., multiple different human reviews).
    """
    # Create a string from key review fields
    review_str = json.dumps({
        'text': review.get('text', '')[:500],  # First 500 chars of text
        'reviewer': review.get('reviewer', ''),
        'metrics': review.get('metrics', {}),
    }, sort_keys=True)

    return hashlib.md5(review_str.encode()).hexdigest()


def merge_reviews(input_files, deduplicate=True):
    """
    Append reviews from multiple JSON files.

    Papers are matched by title. The first file's paper order and metadata is used,
    and only reviews are appended from subsequent files.

    Args:
        input_files: List of paths to JSON files
        deduplicate: If True, remove duplicate reviews based on content hash

    Returns:
        list: Paper data with appended reviews (in original order from first file)
    """
    # List to store papers in order (from first file)
    merged_papers = []
    # Dictionary to map normalized title to paper index for quick lookup
    title_to_index = {}

    # Statistics
    stats = {
        'total_files': len(input_files),
        'total_papers_seen': 0,
        'unique_papers': 0,
        'total_reviews_added': 0,
        'duplicate_reviews_skipped': 0,
        'files_processed': []
    }

    print(f"\nAppending reviews from {len(input_files)} files...\n")

    # Process each input file
    for file_idx, file_path in enumerate(input_files, 1):
        print(f"[{file_idx}/{len(input_files)}] Processing: {file_path}")

        data = load_json(file_path)

        if not isinstance(data, list):
            print(f"  Warning: Expected JSON array in {file_path}, skipping", file=sys.stderr)
            continue

        stats['files_processed'].append(str(file_path))
        file_papers_count = 0
        file_reviews_count = 0

        for paper in data:
            stats['total_papers_seen'] += 1
            file_papers_count += 1

            title = paper.get('title', '')
            if not title:
                print(f"  Warning: Paper without title found, skipping")
                continue

            normalized_title = normalize_title(title)

            # If this is a new paper (from first file), add it to the list
            if normalized_title not in title_to_index:
                paper_copy = paper.copy()
                paper_copy['reviews'] = []
                paper_copy['_review_hashes'] = set()  # Track review hashes for deduplication

                # Add to list and track its index
                title_to_index[normalized_title] = len(merged_papers)
                merged_papers.append(paper_copy)
                stats['unique_papers'] += 1

            # Get the existing paper from the list
            paper_index = title_to_index[normalized_title]
            existing_paper = merged_papers[paper_index]

            # Only append reviews - do NOT merge any other fields
            # Add reviews from this file
            for review in paper.get('reviews', []):
                if deduplicate:
                    # Generate hash of review content to detect true duplicates
                    review_hash = get_review_hash(review)

                    # Skip if we've already seen this exact review content
                    if review_hash in existing_paper['_review_hashes']:
                        stats['duplicate_reviews_skipped'] += 1
                        continue
                    existing_paper['_review_hashes'].add(review_hash)

                existing_paper['reviews'].append(review)
                stats['total_reviews_added'] += 1
                file_reviews_count += 1

        print(f"  Found {file_papers_count} papers, added {file_reviews_count} reviews")

    # Clean up temporary fields
    for paper in merged_papers:
        del paper['_review_hashes']

    # Papers are already in the order from the first file
    return merged_papers, stats


def print_statistics(stats):
    """Print merge statistics."""
    print("\n" + "="*80)
    print("MERGE STATISTICS")
    print("="*80)
    print(f"Files processed:                      {stats['total_files']}")
    print(f"Total papers seen (across all files): {stats['total_papers_seen']}")
    print(f"Unique papers in output:              {stats['unique_papers']}")
    print(f"Total reviews added:                  {stats['total_reviews_added']}")
    print(f"Duplicate reviews skipped:            {stats['duplicate_reviews_skipped']}")
    print("\nFiles merged:")
    for file_path in stats['files_processed']:
        print(f"  - {file_path}")
    print("="*80 + "\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Append reviews from multiple evaluation JSON files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Append reviews from two files
  python merge_reviews.py file1.json file2.json -o output.json

  # Append reviews from all JSON files in a directory
  python merge_reviews.py reviews/*.json -o output.json

  # Append without removing duplicates
  python merge_reviews.py file1.json file2.json --no-deduplicate -o output.json

Note: Only reviews are appended. All other paper metadata (title, abstract,
decision, evaluators, etc.) is taken from the first file where each paper appears.
        """
    )

    parser.add_argument(
        'input_files',
        nargs='+',
        type=Path,
        help='Input JSON files to merge (can specify multiple files or use wildcards)'
    )
    parser.add_argument(
        '-o', '--output',
        type=Path,
        required=True,
        help='Output JSON file path'
    )
    parser.add_argument(
        '--no-deduplicate',
        action='store_true',
        help='Do not remove duplicate reviews (same reviewer for same paper)'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create backup if output file already exists'
    )
    parser.add_argument(
        '--pretty',
        action='store_true',
        default=True,
        help='Pretty print JSON output (default: True)'
    )

    args = parser.parse_args()

    # Validate input files
    valid_files = []
    for file_path in args.input_files:
        if not file_path.exists():
            print(f"Warning: File not found: {file_path}", file=sys.stderr)
            continue
        if not file_path.is_file():
            print(f"Warning: Not a file: {file_path}", file=sys.stderr)
            continue
        valid_files.append(file_path)

    if not valid_files:
        print("Error: No valid input files found", file=sys.stderr)
        sys.exit(1)

    if len(valid_files) < 2:
        print("Warning: Only one input file provided. Consider using cp instead of merge.")

    # Create backup if requested and output exists
    if args.backup and args.output.exists():
        backup_path = args.output.with_suffix('.json.backup')
        print(f"Creating backup: {backup_path}")
        try:
            import shutil
            shutil.copy2(args.output, backup_path)
            print(f"Backup created successfully\n")
        except Exception as e:
            print(f"Warning: Could not create backup: {e}", file=sys.stderr)

    # Merge reviews
    merged_data, stats = merge_reviews(valid_files, deduplicate=not args.no_deduplicate)

    # Print statistics
    print_statistics(stats)

    # Save merged data
    print(f"Saving merged data to: {args.output}")
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            if args.pretty:
                json.dump(merged_data, f, indent=2, ensure_ascii=False)
            else:
                json.dump(merged_data, f, ensure_ascii=False)
        print(f" Successfully saved {len(merged_data)} papers with merged reviews\n")
    except Exception as e:
        print(f"Error saving file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
