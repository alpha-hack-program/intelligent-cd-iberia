# Build stage
FROM registry.access.redhat.com/ubi9/python-312:latest as builder

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM registry.access.redhat.com/ubi9-minimal:latest

# Install Python runtime and tar (needed to extract oc CLI)
RUN microdnf install -y python312 tar gzip && \
    microdnf clean all

# Set working directory
WORKDIR /app

# Copy Python packages from builder stage (using correct paths for UBI)
COPY --from=builder /opt/app-root/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /opt/app-root/bin /usr/local/bin

# Install oc CLI (includes kubectl)
RUN curl -sL https://mirror.openshift.com/pub/openshift-v4/clients/ocp/stable-4.21/openshift-client-linux.tar.gz \
    | tar xzf - -C /usr/local/bin oc kubectl && \
    chmod +x /usr/local/bin/oc /usr/local/bin/kubectl

# Copy application code
COPY main.py .
COPY utils.py .

# Copy application modules
COPY tabs/ ./tabs/
COPY gradio_app/ ./gradio_app/
COPY pipeline/ ./pipeline/

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
CMD ["python3.12", "main.py"]
