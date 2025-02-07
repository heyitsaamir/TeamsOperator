# Operator use in teams

This is a demo of operator use in Teams. It uses the browser_use library to run the agent.

## Prerequisites

1. Clone the repo
2. Set up your environment variables:
   You need to include either Azure OpenAI or OpenAI credentials in the `.env` file:

   ```
   BOT_ID=
   BOT_PASSWORD=
   AZURE_OPENAI_API_KEY=
   AZURE_OPENAI_DEPLOYMENT=
   AZURE_OPENAI_API_BASE=
   AZURE_OPENAI_API_VERSION=
   OPENAI_API_KEY=
   OPENAI_MODEL_NAME=
   ```

   Note: You can't have both Azure and OpenAI keys, so pick the one you have.

3. Set up a tunnel for the agent on port 3978:

   > [!NOTE]
   > See [setting up dev tunnels](#setting-up-dev-tunnels) on how to do that. (Note: Normally Teams Toolkit does this for you, but I don't like how it builds a new tunnel every time.).

4. Run the tunnel with `devtunnel host <tunnel-name>`
5. Go to `.env.local` and set the `BOT_ENDPOINT` to the URL of your tunnel, and `BOT_DOMAIN` to the domain of your tunnel (without the https://).
6. Provision the bot by either:
   - Running `teamsapp provision --env=local`, or
   - Using the Teams Toolkit extension
7. Deploy the bot by either:
   - Running `teamsapp deploy --env=local`, or
   - Using the Teams Toolkit extension

## Run locally

1. Make sure you have uv installed. (https://docs.astral.sh/uv/)
2. Run `uv sync` to install the dependencies
3. Activate the virtual environment with `source .venv/bin/activate` (or `.\.venv\Scripts\activate` on Windows)
4. Run the agent with `python src/app.py`

## Run on Docker

1. Build the Docker image:

```bash
docker build -t teams-operator .
```

2. Run the container:

```bash
docker run -p 3978:3978 \
  --env-file .env \
  teams-operator
```

> [!NOTE]
> When running in Docker, the browser will automatically run in headless mode. If you need to debug browser interactions, run the application locally instead.

## Run on Teams

1. Build the package zip with `teamsapp package --env local`
2. Sideload the package into teams.
3. To see the bot side by side with the web, you need to disable the`simplifiedBotChatPaneIsOptInList` flag.
4. Open up the app and type: `operator: <your query>`

## Setting up dev tunnels

1. Make sure [devtunnel](https://github.com/microsoft/devtunnel) is installed.
2. Run `devtunnel create <tunnel-name>` to create a new tunnel.
3. Run `devtunnel port create <tunnel-name> -p <port-number>` to create a new port for the tunnel.
4. Run `devtunnel access create <tunnel-name> -p <port-number> --anonymous` to set up anonymous access to the tunnel.
