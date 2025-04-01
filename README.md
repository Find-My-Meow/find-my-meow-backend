# 🐾 Find My Meow - FastAPI Backend

This is the backend API for **Find My Meow**, a centralized platform to help users find lost, found, or adoptable cats using AI-powered image search and location-based filtering.

## Setup Instructions
### 1. Clone the repository
``` 
git clone https://github.com/Find-My-Meow/find-my-meow-backend.git
cd find-my-meow-backend
```

### 2. Create and activate a virtual environment
Create env
```
python -m venv env
```
Activate env

- macOS/Linux
    ```
    source env/bin/activate 
    ```
- Windows
    ```
    env\Scripts\activate
    ```

### 3. Install dependencies
```
pip install -r requirements.txt
```

### 4. Set up environment variables
Create a .env file in the root directory by copying the provided example:
```
cp .env.example .env
```
Then, open .env and fill in your actual credentials and configuration values.

### 5. Run the app
```
uvicorn main:app --reload
```

Visit: http://localhost:8000/docs for Swagger UI.



## Running Tests
### Test API Endpoints
Run all tests with verbose output:

```
pytest -v
```
Run a specific test file:

```
pytest tests/<file_name>.py
```

### Test AI Accuracy
1. **Prepare Test Data**  
    Download a test image dataset and place it in a folder named `test_data/` at the project root.


2. **Generate Test Labels**

    Use the label generation script to create ground truth labels:
    ```
    python test_ai/generate_test_labels.py
    ```

3. **Build FAISS Index**

    Create the FAISS index for the test dataset:
    ```
    python test_ai/build_faiss_index.py
    ```


4. **Run Similarity Test**

    Evaluate the AI image search accuracy:
    ```
    python test_ai/ai_test_search_similarity.py
    ```