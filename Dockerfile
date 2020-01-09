FROM docker:stable

RUN apk add --no-cache python3 openssl-dev libffi-dev make git build-base python3-dev bash && \
    pip3 install docker-compose && \
    apk del build-base python3-dev libffi-dev openssl-dev

# Create /app/ and /app/hooks/
RUN mkdir -p /app/hooks/

WORKDIR /app

# Install requirements
COPY requirements.txt ./requirements.txt
RUN pip3 install -r requirements.txt && \
    rm -f requirements.txt

# Copy in webhook listener script
COPY webhook_listener.py ./webhook_listener.py
CMD ["python3", "webhook_listener.py"]
EXPOSE 8000
