"""
Harmonization script for AI-generated review responses.
Processes evaluation JSON and adds AI-generated harmonized responses to each review.
Uses asynchronous OpenAI API calls for efficient processing.
"""

import asyncio
import json
import os
import re
import random
from typing import List, Dict, Any
from openai import AsyncOpenAI
from dotenv import load_dotenv
from util.prompt_manager import prompt_manager


# Load environment variables from .env file
load_dotenv()


# Initialize async OpenAI client
client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Configuration from environment variables
INPUT_FILE = os.environ.get("HARMONIZATION_INPUT_FILE", "reviews/evaluation-data-all-venues.json")
OUTPUT_FILE = os.environ.get("HARMONIZATION_OUTPUT_FILE")  # None means overwrite input
MODEL_NAME = os.environ.get("HARMONIZATION_MODEL", "gpt-4o-mini")
MAX_CONCURRENT_REQUESTS = int(os.environ.get("HARMONIZATION_MAX_CONCURRENT", "10"))

# Retry configuration
MAX_RETRIES = int(os.environ.get("HARMONIZATION_MAX_RETRIES", "6"))
BASE_RETRY_DELAY = float(os.environ.get("HARMONIZATION_BASE_RETRY_DELAY", "2.0"))  # seconds


async def generate_harmonized_response(review_text: str, model: str = MODEL_NAME) -> str:
    """
    Generate a harmonized review response using OpenAI API with retry logic.

    Args:
        review_text: The original review text
        model: The OpenAI model to use

    Returns:
        The AI-generated harmonized response
    """
    # Render prompt
    prompt = prompt_manager.render(
        "harmonization.j2",
        review=review_text
    )

    for attempt in range(MAX_RETRIES):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert at standardizing and harmonizing academic peer reviews while preserving their original content and meaning."},
                    {"role": "user", "content": prompt}
                ],
                # temperature=0.3,  # Lower temperature for more consistent outputs
                # max_tokens=1500,  # Enough for ~300 word responses
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            error_str = str(e)
            
            # Check if this is a rate limit error (429)
            is_rate_limit = "429" in error_str or "rate_limit_exceeded" in error_str.lower()
            
            # Try to parse the suggested wait time from the error message
            wait_time = None
            if is_rate_limit:
                # Look for patterns like "Please try again in 3.162s"
                match = re.search(r'try again in ([\d.]+)s', error_str)
                if match:
                    wait_time = float(match.group(1))
            
            # If this is the last attempt or not a retryable error, fail
            if attempt == MAX_RETRIES - 1:
                print(f"Error generating harmonized response (final attempt): {e}")
                return ""
            
            # Calculate retry delay
            if wait_time:
                # Use the API-suggested wait time plus a small jitter
                delay = wait_time + random.uniform(0.1, 0.5)
                print(f"  ⏳ Rate limit hit. Retrying in {delay:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})...")
            elif is_rate_limit:
                # Use exponential backoff for rate limits without suggested time
                delay = BASE_RETRY_DELAY * (2 ** attempt) + random.uniform(0, 1)
                print(f"  ⏳ Rate limit hit. Retrying in {delay:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})...")
            else:
                # For other errors, use shorter exponential backoff
                delay = BASE_RETRY_DELAY * (2 ** attempt) + random.uniform(0, 0.5)
                print(f"  ⚠️  Error: {str(e)[:100]}... Retrying in {delay:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})...")
            
            # Wait before retrying
            await asyncio.sleep(delay)
    
    # Should not reach here, but just in case
    return ""


async def process_review(review: Dict[str, Any], paper_title: str, review_idx: int, model: str = MODEL_NAME) -> Dict[str, Any]:
    """
    Process a single review and add harmonization data.

    Args:
        review: The review dictionary
        paper_title: Title of the paper (for logging)
        review_idx: Index of the review (for logging)
        model: The OpenAI model to use

    Returns:
        Updated review dictionary with harmonization data
    """
    review_text = review.get("text", "")

    if not review_text:
        print(f"  ⚠ Skipping review {review_idx + 1} (empty text)")
        if "harmonization" not in review:
            review["harmonization"] = []
        return review

    # Initialize harmonization list if it doesn't exist
    if "harmonization" not in review:
        review["harmonization"] = []

    # Check if this model already has a harmonization
    existing_models = [h.get("model") for h in review["harmonization"]]
    if model in existing_models:
        print(f"  ⚠ Review {review_idx + 1} already has harmonization for model '{model}', skipping...")
        return review

    print(f"  Processing review {review_idx + 1}...")

    # Generate harmonized response
    harmonized_text = await generate_harmonized_response(review_text, model)

    if harmonized_text:
        # Append harmonization data to existing list
        review["harmonization"].append({
            "text": harmonized_text,
            "model": model,
            "similarity_scores": []
        })
        print(f"    ✓ Generated harmonized response (total: {len(review['harmonization'])} harmonizations)")
    else:
        print(f"    ✗ Failed to generate harmonized response")

    return review


async def process_paper(paper: Dict[str, Any], paper_idx: int, total_papers: int, model: str = MODEL_NAME) -> Dict[str, Any]:
    """
    Process all reviews in a paper.

    Args:
        paper: The paper dictionary
        paper_idx: Index of the paper
        total_papers: Total number of papers
        model: The OpenAI model to use

    Returns:
        Updated paper dictionary with harmonization data
    """
    title = paper.get("title", "Unknown")
    reviews = paper.get("reviews", [])

    print(f"\n[{paper_idx + 1}/{total_papers}] Processing: {title[:80]}...")
    print(f"  Reviews: {len(reviews)}")

    if not reviews:
        print("  ⚠ No reviews to process")
        return paper

    # Process all reviews in this paper concurrently
    tasks = [
        process_review(review, title, idx, model)
        for idx, review in enumerate(reviews)
    ]

    updated_reviews = await asyncio.gather(*tasks)
    paper["reviews"] = updated_reviews

    return paper


async def process_all_papers(papers: List[Dict[str, Any]], model: str = MODEL_NAME) -> List[Dict[str, Any]]:
    """
    Process all papers with rate limiting.

    Args:
        papers: List of paper dictionaries
        model: The OpenAI model to use

    Returns:
        Updated list of papers with harmonization data
    """
    total_papers = len(papers)
    print(f"\n🚀 Starting harmonization for {total_papers} papers using model: {model}")

    # Process papers in batches to avoid overwhelming the API
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def limited_process_paper(paper: Dict[str, Any], idx: int) -> Dict[str, Any]:
        async with semaphore:
            return await process_paper(paper, idx, total_papers, model)

    tasks = [
        limited_process_paper(paper, idx)
        for idx, paper in enumerate(papers)
    ]

    updated_papers = await asyncio.gather(*tasks)

    return updated_papers


async def harmonize_evaluation_data(input_file: str, output_file: str = None, model: str = MODEL_NAME):
    """
    Main function to harmonize evaluation data.

    Args:
        input_file: Path to the input JSON file
        output_file: Path to the output JSON file (defaults to overwriting input)
        model: The OpenAI model to use
    """
    # Set output file to input file if not specified
    if not output_file:
        output_file = input_file

    print(f"\n📖 Reading evaluation data from: {input_file}")

    # Load the evaluation data
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            papers = json.load(f)
    except Exception as e:
        print(f"❌ Error reading input file: {e}")
        return

    print(f"   Loaded {len(papers)} papers")

    # Process all papers
    try:
        updated_papers = await process_all_papers(papers, model)
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        return

    # Print summary before saving
    total_reviews = sum(len(paper.get("reviews", [])) for paper in updated_papers)
    harmonized_reviews = sum(
        1 for paper in updated_papers
        for review in paper.get("reviews", [])
        if review.get("harmonization") and len(review.get("harmonization", [])) > 0
    )

    print(f"\n" + "=" * 60)
    print(f"📊 PROCESSING SUMMARY")
    print(f"=" * 60)
    print(f"   Total papers: {len(updated_papers)}")
    print(f"   Total reviews: {total_reviews}")
    print(f"   Harmonized reviews: {harmonized_reviews}")
    print(f"   Success rate: {harmonized_reviews/total_reviews*100:.1f}%" if total_reviews > 0 else "   Success rate: N/A")
    print(f"=" * 60)

    # User confirmation if overwriting input file
    if input_file == output_file:
        print(f"\n⚠️  WARNING: This will OVERWRITE the input file: {input_file}")
        response = input("Do you want to proceed? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("❌ Operation cancelled by user")
            return

    # Save the updated data
    print(f"\n💾 Saving harmonized data to: {output_file}")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(updated_papers, f, indent=2, ensure_ascii=False)
        print(f"✅ Successfully saved harmonized data!")
    except Exception as e:
        print(f"❌ Error writing output file: {e}")
        return


def main():
    """
    Main entry point for the harmonization script.
    Configuration is loaded from environment variables (.env file).
    """
    # Check if OpenAI API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("   Please set it in your .env file: OPENAI_API_KEY=your-api-key")
        return

    # Display configuration
    print("\n⚙️  Configuration:")
    print(f"   Input file: {INPUT_FILE}")
    output_display = OUTPUT_FILE if OUTPUT_FILE else f"{INPUT_FILE} (overwrite)"
    print(f"   Output file: {output_display}")
    print(f"   Model: {MODEL_NAME}")
    print(f"   Max concurrent requests: {MAX_CONCURRENT_REQUESTS}")
    print(f"   Max retries: {MAX_RETRIES}")
    print(f"   Base retry delay: {BASE_RETRY_DELAY}s")

    # Run the harmonization
    asyncio.run(harmonize_evaluation_data(INPUT_FILE, OUTPUT_FILE, MODEL_NAME))


if __name__ == "__main__":
    main()
