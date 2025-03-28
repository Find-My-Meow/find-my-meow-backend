import os
import json

DATA_DIR = "test_data"
OUTPUT_FILE = "test_ai/test_labels.json"


def generate_test_labels():
    test_labels = []

    for folder in os.listdir(DATA_DIR):
        folder_path = os.path.join(DATA_DIR, folder)
        if not os.path.isdir(folder_path):
            continue

        try:
            post_id = int(folder)

            for filename in os.listdir(folder_path):
                if filename.startswith("query") and filename.endswith(".jpg"):
                    label_entry = {
                        "query_image_path": os.path.join(folder_path, filename),
                        "true_post_id": post_id
                    }
                    test_labels.append(label_entry)

        except ValueError:
            print(f"Skipping folder {folder}: not a valid numeric ID.")

    # Save to JSON
    os.makedirs("test_ai", exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(test_labels, f, indent=2)

    print(f"Generated {len(test_labels)} test label(s) in {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_test_labels()
