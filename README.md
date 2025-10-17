# LLM Code Deployment Agent

An intelligent web service that automatically builds, deploys, and updates single-page web applications using Large Language Models (LLMs), GitHub, and GitHub Pages.

## Overview

This project implements a complete CI/CD pipeline for AI-generated web applications. It receives application briefs via API, uses LLMs to generate HTML code, creates GitHub repositories, enables GitHub Pages for hosting, and handles revisions with professional documentation.

## Features

- **AI-Powered Code Generation**: Uses OpenAI-compatible LLMs to create single-page HTML applications from natural language briefs
- **Automated Deployment**: Creates public GitHub repositories and enables GitHub Pages hosting
- **Professional Documentation**: Auto-generates README.md and adds MIT license to all projects
- **Revision Support**: Handles application updates and redeployment for Round 2 evaluations
- **Robust Error Handling**: Comprehensive logging and retry mechanisms for reliability
- **Security**: Secret-based authentication and environment variable configuration

## Architecture

### Components
- **Flask Web Server**: Handles API requests and manages background processing
- **LLM Integration**: OpenAI-compatible API for code generation and documentation
- **GitHub API**: Repository creation, file management, and Pages deployment
- **Background Processing**: Threaded execution for non-blocking API responses

### API Endpoints
- `POST /api-endpoint`: Main endpoint for build/revision requests

### Request Format
```json
{
  "email": "student@example.com",
  "secret": "your-secret",
  "task": "unique-task-id",
  "round": 1,
  "nonce": "unique-nonce",
  "brief": "Application description",
  "checks": ["evaluation criteria"],
  "evaluation_url": "https://evaluation.api/endpoint",
  "attachments": [{"name": "file.txt", "url": "data:text/plain;base64,..."}]
}
```

## Setup

### Prerequisites
- Python 3.8+
- GitHub Personal Access Token with repo and pages permissions
- OpenAI API key or compatible LLM service

### Installation

1. Clone the repository:
```bash
git clone https://github.com/sachintiwary/tds-project1.git
cd tds-project1
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your configuration:
```env
MY_SECRET=your-api-secret
GITHUB_TOKEN=your-github-pat
GITHUB_USERNAME=your-github-username
AIPIPE_TOKEN=your-llm-api-key
OPENAI_BASE_URL=https://your-llm-endpoint/v1
```

### Local Development

Run the server:
```bash
python main.py
```

The API will be available at `http://localhost:5000/api-endpoint`

### Deployment

This service is designed to run on platforms like Render, Railway, or Heroku:

1. Deploy the code to your hosting platform
2. Set environment variables in the platform's dashboard
3. Note the public URL for API access

## Usage

### Round 1: Build
Send a POST request to create and deploy a new application:

```bash
curl -X POST https://your-api-url/api-endpoint \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "your-secret",
    "task": "my-app",
    "brief": "Create a simple calculator web app",
    "checks": ["Page displays calculator interface"],
    "evaluation_url": "https://evaluation.api/notify"
  }'
```

### Round 2: Revise
Send a POST request to update an existing application:

```bash
curl -X POST https://your-api-url/api-endpoint \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "your-secret",
    "task": "my-app",
    "round": 2,
    "brief": "Add scientific functions to the calculator",
    "checks": ["Calculator includes sin, cos, tan functions"],
    "evaluation_url": "https://evaluation.api/notify"
  }'
```

## Project Structure

```
tds-project1/
├── main.py              # Main Flask application
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (create locally)
├── README.md           # This file
└── __pycache__/        # Python cache (ignored)
```

## Dependencies

- Flask: Web framework
- python-dotenv: Environment variable management
- PyGitHub: GitHub API client
- OpenAI: LLM API client
- requests: HTTP client

## Security

- API requests require a secret key for authentication
- GitHub tokens should have minimal required permissions
- No sensitive data is logged or stored
- All generated repositories are public

## Logging

The application uses Python's logging module with structured output including timestamps and log levels. Logs are written to stdout for cloud platform compatibility.

## Error Handling

- LLM generation failures are caught and logged
- GitHub API errors trigger appropriate error messages
- Network timeouts are handled with retries
- Invalid requests return proper HTTP status codes

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

This is a TDS project implementation. For modifications, ensure all project requirements are maintained.

## Support

For issues related to deployment or API usage, check the logs for detailed error messages and ensure all environment variables are correctly configured.