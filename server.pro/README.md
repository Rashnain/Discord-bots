# server.pro

This bot allows admins of a Server.pro free server (NB: it has only been tested with a Minecraft server) to renew their server within Discord, the bot will send the captcha and you can resolve the captcha using `/captcha`.

### Dependencies

You can install the needed packages by doing `pip install -r requirements.txt`.

It depends on Firefox and its driver, which can be found [here](https://www.mozilla.org/firefox/all/) and [there](https://github.com/mozilla/geckodriver/releases) respectively.

You will need to extract the archive and put the driver in the same folder as `main.py`.

### Secrets

You will have to write 5 secrets in the `.env` file :

* The Discord user ID of the person who will have the right to shutdown the bot and send commands (`OWNER_ID`)
* The Discord channel ID of the channel where the captchas will be sent (`CAPTCHA_CHANNEL`)
* The bot token, which can be found on your bot [dashboard](https://discord.com/developers/applications) (`BOT_TOKEN`)
* The email used to login to your Server.pro account (`SERVER_PRO_EMAIL`)
* The password used to login to your Server.pro account (`SERVER_PRO_PWD`)

### Commands

`/resume` resume the server

`/captcha <answer>` try to resolve a captcha (when resuming or renewing)

`/stop` stop the server

`/start` start the server

`/restart` restart the server

`/console [command]` show the 10 last console output, a `command` can be sent to the console

`/shutdown` shutdown the bot
