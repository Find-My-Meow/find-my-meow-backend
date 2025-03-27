import faiss
import numpy as np

# Load index
index = faiss.read_index("faiss_test.index")

# Number of vectors stored
print("Number of vectors:", index.ntotal)

# Vector dimension
print("Vector dimension:", index.d)

# -------------------
# Fake Search to Inspect IDs
# Make a random fake vector with same dimension
dummy_query = np.random.rand(1, index.d).astype("float32")

# Run search
distances, ids = index.search(dummy_query, k=5)
print("Dummy search result IDs:", ids)