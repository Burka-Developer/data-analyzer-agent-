# Use the official Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables to keep Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

# Set up a new user named "user" with UID 1000 (recommended for Hugging Face Spaces)
RUN useradd -m -u 1000 user

# Set the working directory inside the container
WORKDIR /home/user/app

# Copy the requirements file first to take advantage of Docker cache
COPY --chown=user:user requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the rest of the application files
COPY --chown=user:user . .

# Ensure standard runtime folders exist and are owned by the user
RUN mkdir -p data uploads && chown -R user:user /home/user/app

# Switch to the non-root user
USER user

# Expose port 7860
EXPOSE 7860

# Run the FastAPI server
CMD ["python", "main.py"]
