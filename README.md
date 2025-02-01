# Operator use in teams

This is a demo of operator use in Teams. It uses the browser_use library to run the agent.

# Running the code

This code has two parts to it:

1. The teams bot agent. This runs in python.
2. The web app. This is a Remix app.

## Keys

You need to include either your Azure open ai details or your OpenAI details in the `.env` file.

## Running the agent

1. Clone the repo
2. Make sure you have uv installed. (https://docs.astral.sh/uv/)
3. Run `uv sync` to install the dependencies.
4. Activate the virtual environment with `source .venv/bin/activate` (or `.\.venv\Scripts\activate` on Windows)
5. Set up a tunnel for the agent on port 3978.
   > [!NOTE]
   > See [setting up dev tunnels](#setting-up-dev-tunnels) on how to do that. (Note: Normally Teams Toolkit does this for you, but I don't like how it builds a new tunnel every time.).
6. Run the tunnel with `devtunnel host <tunnel-name>`
7. Go to `.env.local` and set the `BOT_ENDPOINT` to the URL of your tunnel, and `BOT_DOMAIN` to the domain of your tunnel (without the https://).
8. At this point, you can need to provision the bot. You can either do this manually by running `teamsapp provision --env=local` or you can do it using the Teams Toolkit extension.
9. Now run the agent with `python src/app.py`

## Running the web app

1. cd into `operator_web`
2. Run `npm install` to install the dependencies.
3. Run `npm run dev` to start the app. It'll run it on port 5173.
4. Create a tunnel for the web app on port 5173. See [setting up dev tunnels](#setting-up-dev-tunnels) on how to do that.
5. Run the tunnel with `devtunnel host <tunnel-name>`
6. Go to `.env.local` and set the `BOT_WEB_URL` to the URL of your tunnel.

## Run on teams

1. Build the package zip with `teamsapp package --env local`
2. Sideload the package into teams.

## Setting up dev tunnels

1. Make sure [devtunnel](https://github.com/microsoft/devtunnel) is installed.
2. Run `devtunnel create <tunnel-name>` to create a new tunnel.
3. Run `devtunnel port create <tunnel-name> -p <port-number>` to create a new port for the tunnel.
4. Run `devtunnel access create <tunnel-name> -p <port-number>` to set up anonymous access to the tunnel.
