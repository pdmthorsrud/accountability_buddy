FROM python:3.9-slim

# Install cron
RUN apt-get update && apt-get install -y \
    cron \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Clone the repository
ARG GITHUB_REPO=https://github.com/pdmthorsrud/accountability_buddy.git
RUN git clone ${GITHUB_REPO} . || echo "Using local files"

# Copy local files if they exist (for building from local directory)
COPY requirements.txt ./
COPY *.py ./
COPY setup.sh ./

# Make setup script executable
RUN chmod +x setup.sh

# Run setup script as entrypoint
ENTRYPOINT ["/app/setup.sh"]
