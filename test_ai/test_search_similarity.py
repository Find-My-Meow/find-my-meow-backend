from utils.image_utils import is_too_small
from utils.cat_detection import detect_cats, crop_cats, extract_cat_features
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import faiss
import sys
import os
import json
import matplotlib.pyplot as plt
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

FAISS_INDEX_PATH = "faiss_test.index"
TEST_LABELS_PATH = "test_ai/test_labels.json"
TOP_K = 5


def save_visual_result(query_path, topk_ids, save_dir, faiss_ids, distances):
    # Create subfolder based on folder name of query image
    query_folder = os.path.basename(os.path.dirname(query_path))
    folder_dir = os.path.join(save_dir, query_folder)
    os.makedirs(folder_dir, exist_ok=True)

    query_img = Image.open(query_path).resize((224, 224))

    top_images = []
    sim_scores = []

    for fid, dist in zip(faiss_ids, distances):
        post_id = str(fid // 100)
        image_path = f"test_data/{post_id}/post.jpg"
        if os.path.exists(image_path):
            img = Image.open(image_path).resize((224, 224))
            top_images.append(img)
            sim_scores.append(dist)
        else:
            top_images.append(
                Image.new("RGB", (224, 224), color=(200, 200, 200)))
            sim_scores.append(None)

    total_width = 224 * (1 + len(top_images))
    result_img = Image.new("RGB", (total_width, 240), color=(255, 255, 255))
    result_img.paste(query_img, (0, 0))

    font = ImageFont.load_default()

    for i, (img, sim) in enumerate(zip(top_images, sim_scores)):
        x = 224 * (i + 1)
        result_img.paste(img, (x, 0))
        draw = ImageDraw.Draw(result_img)
        if sim is not None:
            draw.text((x + 5, 224), f"{sim:.2f}", fill="black", font=font)

    query_name = os.path.basename(query_path).replace(".jpg", "")
    out_path = os.path.join(folder_dir, f"{query_name}_result.jpg")
    result_img.save(out_path)


def plot_test_summary(top1, topk, recallk, total, k=TOP_K):
    scores = [
        top1 / total * 100,
        topk / total * 100,
        recallk / total * 100,
    ]
    labels = [f"Top-1 Accuracy", f"Top-{k} Accuracy", f"Recall@{k}"]

    plt.figure(figsize=(8, 6))
    bars = plt.bar(labels, scores, color=["#4CAF50", "#2196F3", "#FFC107"])
    plt.ylim(0, 100)
    plt.ylabel("Percentage (%)")
    plt.title("Image Similarity Search Test Summary")

    for bar, score in zip(bars, scores):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() +
                 2, f"{score:.2f}%", ha="center", fontsize=12)

    os.makedirs("test_ai/visual_results", exist_ok=True)
    summary_plot_path = "test_ai/visual_results/test_summary_chart.png"
    plt.savefig(summary_plot_path)
    print(f"📊 Saved summary chart to {summary_plot_path}")


def run_similarity_test():
    """Test search by image accuracy using Top-K accuracy score."""
    # Load FAISS index
    index = faiss.read_index(FAISS_INDEX_PATH)

    # Load test labels
    with open(TEST_LABELS_PATH, "r") as f:
        test_cases = json.load(f)

    total = len(test_cases)
    top1_correct = 0
    topk_correct = 0
    recallk_correct = 0

    for case in test_cases:
        image_path = case["query_image_path"]
        true_ids = case["true_post_id"]
        if not isinstance(true_ids, list):
            true_ids = [str(true_ids)]  # convert single value to list
        else:
            true_ids = list(map(str, true_ids))

        try:
            image = Image.open(image_path).convert("RGB")
            if is_too_small(image):
                print(f"⚠️ Skipping small image: {image_path}")
                continue

            detections = detect_cats(image)
            if len(detections) == 0:
                print(f"❌ No cat detected in {image_path}")
                continue

            cat_crops = crop_cats(image, detections)
            cat_features = extract_cat_features(cat_crops)
            features_np = np.array(cat_features, dtype=np.float32)
            features_np = features_np / \
                np.linalg.norm(features_np, axis=1, keepdims=True)

            distances, faiss_ids = index.search(features_np, k=TOP_K)

            # Collect all predicted image_ids from all crops
            all_image_ids = []
            top1_hit = False
            recall_hit = False

            for crop_result in faiss_ids:
                topk_ids = [str(fid // 100)
                            for fid in crop_result if fid != -1]
                all_image_ids.extend(topk_ids)

                # Log top-k prediction for this crop
                print(f"\n Image: {image_path}")
                print(f"   Top-{TOP_K} predictions: {topk_ids}")

                if topk_ids and topk_ids[0] in true_ids:
                    top1_hit = True
                if any(tid in true_ids for tid in topk_ids):
                    recall_hit = True

            if top1_hit:
                top1_correct += 1
            if any(tid in all_image_ids for tid in true_ids):
                topk_correct += 1
            if recall_hit:
                recallk_correct += 1

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

    print("\n Test Results:")
    print(f"Total Queries: {total}")
    print(f"  Top-1 Accuracy: {top1_correct / total * 100:.2f}%")
    print(f"  Top-{TOP_K} Accuracy: {topk_correct / total * 100:.2f}%")
    print(f"  Recall@{TOP_K}: {recallk_correct / total * 100:.2f}%")

    plot_test_summary(top1_correct, topk_correct, recallk_correct, total)


if __name__ == "__main__":
    run_similarity_test()
