import os
import faiss
import torch
from core.database import db


FAISS_INDEX_FILE = "faiss_cat_index.index"
D = 768  # Feature vector dimension

# TODO: Move faiss to s3
def load_faiss_index():
    """
    Loads the FAISS index from file if available, otherwise initializes a new one.
    """
    if os.path.exists(FAISS_INDEX_FILE):
        # Loade FAISS Index from file
        faiss_index = faiss.read_index(FAISS_INDEX_FILE)

        if not isinstance(faiss_index, faiss.IndexIDMap):
            faiss_index = faiss.IndexIDMap(faiss_index)
    else:
        # Creating a new FAISS index
        faiss_index = faiss.IndexIDMap(faiss.IndexFlatL2(D))

    return faiss_index, FAISS_INDEX_FILE


def get_device():
    # CUDA GPU
    if torch.torch.cuda.is_available():
        return torch.device('cuda:0')
    # Mac GPU
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device('mps')
    # CPU
    else:
        return torch.device('cpu')


async def get_next_image_id():
    counter = await db.database["counters"].find_one_and_update(
        {"_id": "image_id"},
        {"$inc": {"seq": 1}},  # Increment sequence by 1
        upsert=True,
        return_document=True
    )
    return str(counter["seq"])


async def get_next_post_id():
    counter = await db.database["counters"].find_one_and_update(
        {"_id": "post_id"},
        {"$inc": {"seq": 1}},  # Increment sequence by 1
        upsert=True,
        return_document=True
    )
    return str(counter["seq"])
