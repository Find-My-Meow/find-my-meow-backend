
import os
import sys
import numpy as np
import faiss
from PIL import Image
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.cat_detection import crop_cats, detect_cats, extract_cat_features
from utils.image_utils import is_too_small

DATA_DIR = "test_data"
EMBED_DIM = 512  # CLIP model output size
faiss_index_test = faiss.IndexIDMap(faiss.IndexFlatIP(EMBED_DIM))


def build_faiss_from_posts():
    ids = []
    vectors = []

    for folder in os.listdir(DATA_DIR):
        folder_path = os.path.join(DATA_DIR, folder)
        if not os.path.isdir(folder_path):
            continue

        post_path = os.path.join(folder_path, "post.jpg")
        if not os.path.exists(post_path):
            print(f"Skipping {folder}: no post.jpg")
            continue

        try:
            image = Image.open(post_path).convert("RGB")
            if is_too_small(image):
                print("Skipping low-quality crop")
                continue

            detections = detect_cats(image)
            if len(detections) == 0:
                print(f"❌ No cat detected in {post_path}")
                continue

            cat_crops = crop_cats(image, detections)
            cat_features = extract_cat_features(cat_crops)
            cat_features_np = np.array(cat_features, dtype=np.float32)
            cat_features_np = cat_features_np / \
                np.linalg.norm(cat_features_np, axis=1, keepdims=True)

            # Create FAISS IDs ex. 2500, 2501 for post_id 25
            post_id = int(folder)
            for i, vec in enumerate(cat_features_np):
                faiss_id = int(f"{post_id}{i:02}")
                ids.append(faiss_id)
                vectors.append(vec)

            print(f"✅ Added {folder} to FAISS index")

        except Exception as e:
            print(f"❌ Error processing {post_path}: {str(e)}")

    # Add all vectors with custom IDs
    if vectors:
        faiss_index_test.add_with_ids(
            np.array(vectors).astype("float32"), np.array(ids))
        faiss.write_index(faiss_index_test, "faiss_test.index")
        print("✅ FAISS index built and saved.")
    else:
        print("⚠️ No valid images found. Index not saved.")


if __name__ == "__main__":
    build_faiss_from_posts()
