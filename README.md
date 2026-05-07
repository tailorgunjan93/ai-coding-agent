# AI Coding Agent

AI Coding Agent is a Python project for experimenting with an agent workflow
that combines planning, model calls, code generation, testing, security checks,
database updates, Git operations, and CI/CD integration.

Start with this page to get a local checkout running, then use the docs in
`docs/` for architecture and contributor details.

## Requirements

- Python 3.11 or newer
- Git
- A virtual environment tool such as `venv`
- Optional: Ollama for local model integration tests
- Optional: provider API keys for cloud LLM adapters

The main Python dependencies are listed in `requirements.txt`. Formatting and
type-checking settings live in `pyproject.toml`.

## Quick Start

Clone the repository:

```bash
git clone https://github.com/tailorgunjan93/ai-coding-agent.git
cd ai-coding-agent
```

Create and activate a virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run the unit tests:

```bash
pytest tests/unit
```

Run the common local quality checks:

```bash
black --check src tests
flake8 src tests
mypy src
```

## Optional Provider Setup

The project includes adapters for several LLM providers. Set only the variables
for the provider you want to test:

```bash
export OPENAI_API_KEY="..."
export ANTHROPIC_API_KEY="..."
export GROQ_API_KEY="..."
export GOOGLE_API_KEY="..."
```

AWS Bedrock uses your normal AWS credential chain. Ollama tests expect a local
Ollama server:

```bash
ollama serve
```

Most unit tests should run without live provider credentials because external
calls are mocked.

## Troubleshooting

- If `python3.11` is not found, install Python 3.11+ or use the `python`
  launcher that points to a compatible version.
- If imports fail after installing dependencies, make sure the virtual
  environment is activated and rerun `pip install -r requirements.txt`.
- If an integration test is skipped, check whether the required local service or
  API key is configured.
- If `mypy` reports missing imports, reinstall dependencies inside the active
  virtual environment.

## Documentation

- [Documentation index](docs/doc_index.md)
- [Contributor guide](docs/contributor_guide.md)
- [Architecture overview](docs/architecture.md)
- [Repository structure](docs/repository_structure.md)
- [Testing strategy](docs/testing_strategy.md)

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. New
contributors should keep changes focused and include tests when behavior
changes.
