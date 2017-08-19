FROM python:3

# Install docker
RUN cd /usr/bin; \
    curl -L 'https://download.docker.com/linux/static/stable/x86_64/docker-17.06.1-ce.tgz' | tar --strip-components=1 -zxv; \
    pip install docker-compose

# Create /app/ and /app/hooks/
RUN mkdir -p /app/hooks/

WORKDIR /app

# Install requirements
COPY requirements.txt ./requirements.txt
RUN pip install -r requirements.txt && \
    rm -f requirements.txt

# Copy in webhook listener script
COPY webhook_listener.py ./webhook_listener.py
CMD ["python", "webhook_listener.py"]
EXPOSE 8000