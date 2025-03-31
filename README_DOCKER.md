# Docker Deployment for SMITE 2 Combat Log Agent

This guide explains how to deploy the SMITE 2 Combat Log Agent using Docker and Docker Compose.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed on your system
- [Docker Compose](https://docs.docker.com/compose/install/) installed on your system
- A valid OpenAI API key

## Quick Start

1. Clone the repository (if you haven't already):
   ```bash
   git clone https://github.com/YourUsername/S2CombatLogAgent.git
   cd S2CombatLogAgent
   ```

2. Set up your OpenAI API key:
   
   Create a `.env` file in the project root directory:
   ```bash
   echo "OPENAI_API_KEY=your-api-key-here" > .env
   ```

3. Start the application using Docker Compose:
   ```bash
   docker-compose up -d
   ```

4. Access the Streamlit web interface at:
   ```
   http://localhost:8501
   ```

5. To stop the application:
   ```bash
   docker-compose down
   ```

## Building and Running Manually

If you prefer to build and run the Docker container manually without Docker Compose:

1. Build the Docker image:
   ```bash
   docker build -t smite2-agent .
   ```

2. Run the Docker container:
   ```bash
   docker run -p 8501:8501 \
     -v $(pwd)/data:/app/data \
     -v $(pwd)/.env:/app/.env \
     -e OPENAI_API_KEY="your-api-key-here" \
     smite2-agent
   ```

## Project Structure in Docker

- The application runs inside the Docker container
- The Streamlit web interface is exposed on port 8501
- Database files are stored in a volume mounted from your local `./data` directory
- Log files are stored in a volume mounted from your local `./logs` directory
- The `.env` file is mounted from your local environment for API key storage

## Configuration Options

You can configure the Docker deployment by:

1. Modifying the `Dockerfile` for container-specific changes
2. Adjusting the `docker-compose.yml` for deployment configuration
3. Adding environment variables to the `.env` file

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `STREAMLIT_SERVER_PORT`: Port for the Streamlit server (default: 8501)
- `STREAMLIT_SERVER_HEADLESS`: Run Streamlit in headless mode (default: true)

## Database Files

The application expects database files in the `/app/data` directory inside the container. This is mounted from your local `./data` directory. Make sure to:

1. Place your SMITE 2 combat log database files in the `./data` directory
2. When using the application, select database files from the `/app/data` directory

## Troubleshooting

### Container Fails to Start

Check the logs for errors:
```bash
docker-compose logs
```

### Package Installation Errors

If you see errors related to package installation, such as:

```
ERROR: No matching distribution found for openai-agents>=1.0.0
```

This indicates that one of the package versions in `requirements.txt` is not available. Try these solutions:

1. **Update requirements.txt**: 
   - Check the current available versions of problematic packages:
     ```bash
     pip index versions openai-agents
     ```
   - Update requirements.txt with available versions
   - Rebuild the Docker image

2. **Use a custom requirements file for Docker**:
   - Create a `requirements-docker.txt` file with compatible versions
   - Modify the Dockerfile to use this file instead

3. **Build with --no-cache**:
   - Force a fresh build without using cached layers:
     ```bash
     docker-compose build --no-cache
     ```

### Can't Access the Web Interface

Ensure port 8501 is not being used by another application:
```bash
lsof -i :8501
```

### OpenAI API Issues

Verify your API key is correctly set in the `.env` file and that it's being properly passed to the container.

### Runtime Dependency Errors

If the application starts but crashes with dependency errors:

1. Enter the running container:
   ```bash
   docker exec -it smite2-agent bash
   ```

2. Check installed packages:
   ```bash
   pip list
   ```

3. Install missing dependencies manually:
   ```bash
   pip install <package-name>
   ```

## Production Deployment

For production deployment, consider:

1. Using a reverse proxy (like Nginx) in front of the Streamlit app
2. Setting up proper authentication
3. Using Docker Swarm or Kubernetes for container orchestration
4. Implementing proper logging and monitoring 