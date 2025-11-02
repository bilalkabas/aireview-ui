import os
import json
import dotenv


# Load environment variables from .env file
dotenv.load_dotenv()


json_path = os.getenv("WEBAPP_REVIEWS_JSON")

metrics_defaults = {
    "coverage": 0,
    "specificity": 0,
    "correctness": 0,
    "constructiveness": 0,
    "stance": 0,
    "source": "",
    "comment": ""
}

# Iterate in JSON list and assign metrics to metrics_defaults for each list item
with open(f"../{json_path}", "r") as f:
    data = json.load(f)
    for item in data:
        for review in item["reviews"]:
            review["metrics"] = metrics_defaults
        
        item["status"] = "not_started"

# Overwrite the new JSON
with open(f"../{json_path}", "w") as f:
    json.dump(data, f, indent=2)

