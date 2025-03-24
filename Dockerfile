# -----------------------------------------------------
# 1) Base Image
# -----------------------------------------------------
    FROM python:3.10-slim

    # -----------------------------------------------------
    # 2) Working Directory
    # -----------------------------------------------------
    WORKDIR /app
    
    # -----------------------------------------------------
    # 3) Copy and install requirements
    # -----------------------------------------------------
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
    
    # -----------------------------------------------------
    # 4) Copy all source code
    #    (this will include modules/, app.py, etc.)
    # -----------------------------------------------------
    COPY . .
    
    # -----------------------------------------------------
    # 5) Set environment variable for PORT
    #    Cloud Run typically sets PORT dynamically
    # -----------------------------------------------------
    ENV PORT=8080
    
    # -----------------------------------------------------
    # 6) Run the Flask app with Gunicorn
    #    If your main Flask object is in app.py with `app = Flask(__name__)`
    # -----------------------------------------------------
    CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:create_app()"]

    