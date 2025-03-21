import torch
from core.database import db


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
