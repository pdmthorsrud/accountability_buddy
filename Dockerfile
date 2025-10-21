FROM python:3.9-slim

# Install cron
RUN apt-get update && apt-get install -y \
    cron \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Accept GitHub token as build argument
ARG GITHUB_TOKEN
ARG GITHUB_REPO=pdmthorsrud/accountability_buddy

# Clone the repository using token if provided
RUN if [ -n "$GITHUB_TOKEN" ]; then \
        git clone https://${GITHUB_TOKEN}@github.com/${GITHUB_REPO}.git . ; \
    else \
        git clone https://github.com/${GITHUB_REPO}.git . ; \
    fi

# Make setup script executable
RUN chmod +x setup.sh

# Run setup script as entrypoint
ENTRYPOINT ["/app/setup.sh"]
