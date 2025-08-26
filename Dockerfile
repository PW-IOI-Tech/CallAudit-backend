# Use a slim image for FastAPI
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy files
COPY . .

# Install dependencies
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Expose port
EXPOSE 8000

# Run the app
CMD ["python", "src/main.py"]
