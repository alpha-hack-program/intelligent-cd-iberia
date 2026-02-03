# Build stage
FROM registry.access.redhat.com/ubi9/python-314:latest as builder

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM registry.access.redhat.com/ubi9-minimal:latest

# Install Python runtime only
RUN microdnf install -y python314 && \
    microdnf clean all

# Set working directory
WORKDIR /app

# Copy Python packages from builder stage (using correct paths for UBI)
COPY --from=builder /opt/app-root/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /opt/app-root/bin /usr/local/bin

# Install kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && \
    mv kubectl /usr/local/bin/

# Copy application code
COPY main.py .
COPY utils.py .

# Copy application modules
COPY tabs/ ./tabs/
COPY gradio_app/ ./gradio_app/

# Copy assets folder for chatbot avatars
COPY assets/ ./assets/

# Expose the port Gradio runs on
EXPOSE 7860

# Set environment variables
ENV GRADIO_SERVER_NAME=0.0.0.0
ENV GRADIO_SERVER_PORT=7860
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Run the application
CMD ["python3.14", "main.py"]
