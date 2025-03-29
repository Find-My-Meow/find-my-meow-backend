from utils.cat_detection import detect_cats, crop_cats, extract_cat_features
from utils.image_utils import is_too_small
from test_ai.plot_results import compute_mrr, plot_accuracy_over_k, plot_rank_histogram, plot_similarity_distribution, save_visual_result
from PIL import Image
import numpy as np
import faiss
import sys
import os
import json
import matplotlib.pyplot as plt
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

FAISS_INDEX_PATH = "faiss_test.index"
TEST_LABELS_PATH = "test_ai/test_labels.json"
TOP_K = 10  # Number of top matches to consider for evaluation
MAX_K = 10  # Max value of K to plot Top-K accuracy curve


def run_similarity_test():
    """Test search by image accuracy using Top-K accuracy score."""
    # Load FAISS index
    index = faiss.read_index(FAISS_INDEX_PATH)

    # Load test cases (each contains a query image path and expected post ID(s))
    with open(TEST_LABELS_PATH, "r") as f:
        test_cases = json.load(f)

    # Init counters and containers
    total = len(test_cases)
    top1_correct = 0
    topk_correct = 0
    recallk_correct = 0
    # For Top-K accuracy curve
    accuracy_by_k = {k: 0 for k in range(1, MAX_K + 1)}
    rank_hits = []      # Track rank of correct match
    top1_scores = []    # Track similarity scores (cosine distances) of top-1

    # Loop through test cases
    for case in test_cases:
        image_path = case["query_image_path"]
        true_ids = case["true_post_id"]
        if not isinstance(true_ids, list):
            true_ids = [str(true_ids)]  # convert single value to list
        else:
            true_ids = list(map(str, true_ids))

        try:
            image = Image.open(image_path).convert("RGB")

            # Skip if image too small
            if is_too_small(image):
                print(f"⚠️ Skipping small image: {image_path}")
                continue

            # Cat detection
            detections = detect_cats(image)
            if len(detections) == 0:
                print(f"❌ No cat detected in {image_path}")
                continue

            # Extract features from cropped cat regions
            cat_crops = crop_cats(image, detections)
            cat_features = extract_cat_features(cat_crops)
            features_np = np.array(cat_features, dtype=np.float32)
            features_np = features_np / \
                np.linalg.norm(features_np, axis=1, keepdims=True)

            # Perform FAISS search
            distances, faiss_ids = index.search(features_np, k=TOP_K)

            # Track predictions and evaluation metrics
            all_image_ids = []
            top1_hit = False
            recall_hit = False
            found_k = set()

            # Evaluate each crop
            for crop_result, dist_result in zip(faiss_ids, distances):
                topk_ids_full = [str(fid // 100)
                                 for fid in crop_result if fid != -1]
                all_image_ids.extend(topk_ids_full[:TOP_K])

                # Top-1 accuracy check
                if topk_ids_full and topk_ids_full[0] in true_ids:
                    top1_hit = True

                 # Top-K recall
                if any(tid in true_ids for tid in topk_ids_full):
                    recall_hit = True

                # Track rank of true match
                match_rank = None
                for idx, pred_id in enumerate(topk_ids_full):
                    if pred_id in true_ids:
                        match_rank = idx
                        break
                if match_rank is not None:
                    rank_hits.append(match_rank)

                # Save top-1 distance for histogram
                if dist_result[0] != -1:
                    top1_scores.append(dist_result[0])

                # Top-K accuracy for various K
                for k in range(1, MAX_K + 1):
                    topk_ids = topk_ids_full[:k]
                    if any(tid in true_ids for tid in topk_ids):
                        found_k.add(k)

            # Update global counters
            if top1_hit:
                top1_correct += 1
            if any(tid in all_image_ids for tid in true_ids):
                topk_correct += 1
            if recall_hit:
                recallk_correct += 1
            for k in found_k:
                accuracy_by_k[k] += 1

            # Save visual result
            save_visual_result(
                query_path=image_path,
                topk_ids=all_image_ids[:TOP_K],
                save_dir="test_ai/visual_results",
                faiss_ids=faiss_ids[0],
                distances=distances[0]
            )

        except Exception as e:
            print(f"⚠️ Error processing {image_path}: {str(e)}")

    # Normalize Top-K accuracy
    for k in accuracy_by_k:
        accuracy_by_k[k] /= total

    # Compute MRR
    mrr = compute_mrr(rank_hits)

    # Final results
    print("\nTest Results:")
    print(f"Total Queries: {total}")
    print(f"  Top-1 Accuracy: {top1_correct / total * 100:.2f}%")
    print(f"  Top-{TOP_K} Accuracy: {topk_correct / total * 100:.2f}%")
    print(f"  Recall@{TOP_K}: {recallk_correct / total * 100:.2f}%")
    print(f"  Mean Reciprocal Rank (MRR): {mrr:.4f}")

    # Plot visual summaries
    os.makedirs("test_ai/visual_results", exist_ok=True)
    plot_accuracy_over_k(accuracy_by_k)
    plot_rank_histogram(rank_hits, k=TOP_K)
    plot_similarity_distribution(top1_scores)


if __name__ == "__main__":
    run_similarity_test()
