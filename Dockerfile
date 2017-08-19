FROM python:3

# Create /app/ and /app/hooks/
RUN mkdir -p /app/hooks/

WORKDIR /app

# Copy in webhook listener and the entrypoint
COPY webhook_listener.py ./webhook_listener.py

# Install requirements
COPY requirements.txt ./requirements.txt
RUN pip install -r requirements.txt && \
    rm -f requirements.txt

CMD ["python", "webhook_listener.py"]
EXPOSE 8000