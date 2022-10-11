# Tytta 🦉
<img src="https://user-images.githubusercontent.com/68649697/195161899-9efafdaa-d630-4afc-aa25-80fa3b6b538d.png" width="200px" align="right">

Tytta is a telegram bot that **listens to voice recordings** you send and transcribes them into **spreadsheets or text** documents.<br>

## Quickstart
1. Send ```/newbot``` to the [BotFather](https://telegram.me/BotFather) on Telegram to create a bot.
2. Clone the repository:
```
git clone https://github.com/pedroblayaluz/tyttabot
cd tyttabot
```
3. Replace ```"INSERT BOT TOKEN"``` in the [Dockerfile](https://github.com/pedroblayaluz/tyttabot/blob/main/Dockerfile) with your bot's token.
#### Using Docker
4. Install [Docker](https://docs.docker.com/engine/install/) and make sure the docker engine is running.
5. Build and run the Dockerfile from inside the cloned directory:
```
docker build . -t tyttabot
docker run tyttabot
```
#### Without docker
4. Install the required packages:
```
sudo apt-get update
sudo apt-get install -y python3 python3-pip python-dev build-essential python3-venv ffmpeg
pip install -r requirements.txt
```
5. Start the bot:
```
python3 tyttabot.py
```
