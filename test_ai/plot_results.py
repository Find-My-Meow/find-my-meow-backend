from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
import matplotlib.pyplot as plt


TOP_K = 10
RESULT_PATH = "test_ai/visual_results"


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


def plot_accuracy_over_k(accuracy_dict):
    ks = list(accuracy_dict.keys())
    accuracies = [v * 100 for v in accuracy_dict.values()]  # Convert to %

    plt.figure(figsize=(10, 6))
    plt.plot(ks, accuracies, marker='o', linestyle='-', color='#FF5722')
    plt.title("Top-K Accuracy vs K")
    plt.xlabel("K")
    plt.ylabel("Accuracy (%)")
    plt.xticks(ks)
    plt.ylim(0, 100)
    plt.grid(True)
    os.makedirs(RESULT_PATH, exist_ok=True)
    filename = "topk_accuracy_line.png"
    plt.savefig(f"{RESULT_PATH}/{filename}")
    print(f"📈 Saved Top-K accuracy line chart to {RESULT_PATH}/{filename}")


def compute_mrr(rank_hits):
    reciprocal_ranks = [1 / (r + 1) for r in rank_hits if r is not None]
    return sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0


def plot_similarity_distribution(sim_scores):
    plt.figure(figsize=(10, 5))
    plt.hist(sim_scores, bins=20, color="#009688", edgecolor="black")
    plt.title("Distribution of Top-1 Similarity Scores")
    plt.xlabel("Cosine Distance")
    plt.ylabel("Frequency")
    plt.savefig(f"{RESULT_PATH}/similarity_score_histogram.png")
    print("📊 Saved similarity score histogram.")


def plot_rank_histogram(rank_hits, k=TOP_K):
    counts = [0] * k
    for r in rank_hits:
        if r < k:
            counts[r] += 1

    labels = [f"Rank {i+1}" for i in range(k)]
    plt.figure(figsize=(10, 6))
    plt.bar(labels, counts, color="#607D8B")
    plt.ylabel("Number of Queries")
    plt.title("Distribution of Correct Match Rank in Top-K")
    plt.savefig(f"{RESULT_PATH}/rank_distribution.png")
    print(f"📊 Saved rank distribution to {RESULT_PATH}/rank_distribution.png")
