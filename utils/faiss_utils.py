import os
import faiss
from core.config import settings
from core.aws import s3_client


FAISS_INDEX_FILE = "faiss_cat_index.index"
D = 768  # Feature vector dimension
S3_BUCKET = settings.AWS_S3_BUCKET_NAME
S3_INDEX_KEY = "faiss_indexes/" + FAISS_INDEX_FILE


def download_faiss_index_from_s3():
    """
    Downloads the FAISS index from S3 if it exists.
    """
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=S3_INDEX_KEY)
        index_data = response['Body'].read()

        with open(FAISS_INDEX_FILE, "wb") as f:
            f.write(index_data)

        print("FAISS index downloaded from S3.")
    except s3_client.exceptions.NoSuchKey:
        print("FAISS index not found in S3. Initializing new index.")


def upload_faiss_index_to_s3():
    """
    Uploads the FAISS index to S3.
    """
    try:
        with open(FAISS_INDEX_FILE, "rb") as f:
            s3_client.put_object(Bucket=S3_BUCKET, Key=S3_INDEX_KEY, Body=f)
        print("FAISS index uploaded to S3.")
    except Exception as e:
        print(f"Failed to upload FAISS index to S3: {str(e)}")


def load_faiss_index():
    """
    Loads the FAISS index from S3 if available, otherwise initializes a new one.
    """
    download_faiss_index_from_s3()

    if os.path.exists(FAISS_INDEX_FILE):
        # Load FAISS Index from file
        faiss_index = faiss.read_index(FAISS_INDEX_FILE)
        if not isinstance(faiss_index, faiss.IndexIDMap):
            faiss_index = faiss.IndexIDMap(faiss_index)
    else:
        # Create new FAISS index
        faiss_index = faiss.IndexIDMap(faiss.IndexFlatL2(D))

    return faiss_index


def reset_faiss_index():
    """
    Resets the FAISS index.
    """
    global faiss_index

    # Create a new empty FAISS index
    faiss_index = faiss.IndexIDMap(faiss.IndexFlatL2(D))
    # Save the empty index locally
    faiss.write_index(faiss_index, FAISS_INDEX_FILE)
    # Upload the empty index to S3
    upload_faiss_index_to_s3()
    # Force reload from S3
    faiss_index = load_faiss_index()

    print("FAISS index has been fully reset and reloaded from S3.")
