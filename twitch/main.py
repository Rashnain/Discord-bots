import json
import urllib.parse
from time import sleep

import dotenv
import discord
from discord import Option
from discord.ext import tasks
from requests import Session

from discord_webhook import Webhook


bot = discord.Bot()


def twitch_init():
	"""
	Tokens have expiration date but I am too lazy to handle this, so I revoke the token and ask a new one.

	The new one is saved in the config and .env file.
	"""
	if config['TWITCH_APP_BEARER_TOKEN']:
		session.post(
			f'https://id.twitch.tv/oauth2/revoke?client_id={config["TWITCH_APP_ID"]}&'
			f'token={config["TWITCH_APP_BEARER_TOKEN"]}')

	r = session.post(
		f'https://id.twitch.tv/oauth2/token?'
		f'client_id={config["TWITCH_APP_ID"]}&'
		f'client_secret={config["TWITCH_APP_SECRET"]}&'
		f'grant_type=client_credentials')

	config["TWITCH_APP_BEARER_TOKEN"] = r.json()['access_token']

	dotenv.set_key('.env', 'TWITCH_APP_BEARER_TOKEN', config["TWITCH_APP_BEARER_TOKEN"], 'auto')


def save_to_files():
	"""
	Save channels and followers to files.
	"""
	with open('followers.json', 'w') as f:
		json.dump(followers, f, indent=2)
	with open('channels.json', 'w') as f:
		json.dump(channels, f, indent=2)


def read_from_files():
	"""
	Store channels and followers in variables.
	"""
	global followers, channels

	with open('followers.json', 'r') as f:
		followers = json.loads(f.read())
	with open('channels.json', 'r') as f:
		channels = json.loads(f.read())


def refresh_channels_data():
	for channel in channels:
		channels[channel]['stream_title'] = ''
		channels[channel]['is_streaming'] = None
		data = get_channel(channel, False)
		if len(data) == 1:
			data = data[0]
			channels[channel]['login'] = data['login']
			channels[channel]['display_name'] = data['display_name']
			channels[channel]['profile_image_url'] = data['profile_image_url']


def get_channel(query: str, is_login: bool) -> list:
	"""
	:param query: Channel's login or identifier.
	:param is_login: True if `query` represents the login of the channel.
	:return: Channel data, or an empty dict if `login` does not exist.
	"""
	if is_login:
		method = 'login'
	else:
		method = 'id'

	r = session.get(f'https://api.twitch.tv/helix/users?{method}={query}', headers=headers)

	if 'data' in r.json():
		return r.json()['data']
	else:
		return []


def get_followers(channel_id: str) -> list[str]:
	"""
	:param channel_id: Channel's identifier
	:return: A list of Discord user identifiers that have subscribed to the channel
	"""
	channel_followers = []
	for follower in followers:
		if channel_id in follower:
			channel_followers.append(follower)
	return channel_followers


@bot.event
async def on_ready():
	print('Bot ready, logged as', bot.user)
	if not check.is_running():
		check.start()


@bot.slash_command(description='Show the 10 most relevent Twitch channels')
async def search(ctx, query: Option(str, min_length=4, max_length=25)):
	query_formated = urllib.parse.quote_plus(query)

	r = session.get(f'https://api.twitch.tv/helix/search/channels?query={query_formated}&first=10', headers=headers)

	data = r.json()['data']

	response = f'```\nMost relevent channels for "{query}" :'

	for channel in data:
		response += f'\n - {channel["display_name"]} ({channel["broadcaster_login"]})'

	response += '\n```'

	if len(data) == 0:
		response = f'No result for "{query}".'

	await ctx.respond(response, ephemeral=True)


@bot.slash_command(description='Subscribe to a Twitch channel')
async def subscribe(ctx, channel_login: Option(str, min_length=4, max_length=25)):
	author_id = str(ctx.author.id)

	data = get_channel(channel_login, True)

	if len(data) == 1:
		channel = data[0]

		channel_id = str(channel['id'])

		if channel_id not in channels:
			channels[channel_id] = {}

		channels[channel_id]['login'] = channel['login']
		channels[channel_id]['display_name'] = channel['display_name']
		channels[channel_id]['profile_image_url'] = channel['profile_image_url']

		r = session.get(f'https://api.twitch.tv/helix/streams?user_id={channel_id}', headers=headers)
		data = r.json()['data']

		if data:
			channels[channel_id]['is_streaming'] = True
			channels[channel_id]['stream_title'] = data[0]['title']
			message = data[0]['title'] + f'\n<https://www.twitch.tv/{channel["login"]}>\n<@{author_id}>'
		else:
			channels[channel_id]['is_streaming'] = False
			channels[channel_id]['stream_title'] = ''
			message = '[OFFLINE]'

		webhook_message_payload = {
			'username': f'{channel["display_name"]} ({channel["login"]})',
			'avatar_url': channel['profile_image_url'],
			'content': message}

		if 'message_id' in channels[channel_id]:
			webhook.edit_message(webhook_message_payload, channels[channel_id]['message_id'])
		else:
			webhook.send_message(webhook_message_payload)
			channels[channel_id]['message_id'] = webhook.lastSentMessageInfo['id']

		if author_id not in followers:
			followers[author_id] = []

		if channel_id not in followers[author_id]:
			followers[author_id].append(channel_id)
			response = f'You have subscribed to {channel_login}.'
		else:
			response = f'You are already subscribed to {channel_login}.'

		save_to_files()
	else:
		response = 'This channel does not exis or is banned (if that is the case you must wait until it gets unbanned).'

	await ctx.respond(response, ephemeral=True)


@bot.slash_command(description='Unsubscribe from a Twitch channel')
async def unsubscribe(ctx, channel_login: Option(str, min_length=4, max_length=25)):
	author_id = str(ctx.author.id)

	data = get_channel(channel_login, True)

	if len(data) == 1:
		if author_id not in followers:
			response = f'You are not subscribed to {channel_login}.'
		else:
			channel_id = data[0]['id']

			if channel_id in followers[author_id]:
				followers[author_id].remove(channel_id)

				if len(followers[author_id]) == 0:
					followers.pop(author_id)

				if len(get_followers(channel_id)) == 0:
					webhook.delete_message(channels[channel_id]['message_id'])
					channels.pop(channel_id)

				response = f'You have unsubscribed from {channel_login}.'

				save_to_files()
			else:
				response = f'You are not subscribed to {channel_login}.'

	else:
		response = f'The channel {channel_login} does not exist.'

	await ctx.respond(response, ephemeral=True)


@bot.slash_command(description='Unsubscribe from all Twitch channels')
async def unsubscribe_from_all(ctx):
	author_id = str(ctx.author.id)

	if author_id not in followers:
		response = 'You are not subscribed to anyone.'
	else:
		for channel_id in followers[author_id]:
			if len(get_followers(channel_id)) == 0:
				webhook.delete_message(channels[channel_id]['message_id'])
				channels.pop(channel_id)
				sleep(0.1)

		followers.pop(author_id)

		response = 'You have unsubscribed from all channels.'

		save_to_files()

	await ctx.respond(response, ephemeral=True)


@tasks.loop(minutes=5)
async def check():
	users_to_ping = set()

	for channel in channels:

		mentions = set()

		payload = {
			'username': f'{channels[channel]["display_name"]} ({channels[channel]["login"]})',
			'avatar_url': channels[channel]['profile_image_url']}

		r = session.get(f'https://api.twitch.tv/helix/streams?user_id={channel}', headers=headers)
		stream_info = r.json()['data']

		if len(stream_info) == 1:

			stream_info = stream_info[0]

			payload['content'] = f'{stream_info["title"]}\n<https://www.twitch.tv/{channels[channel]["login"]}>\n'

			for follower in followers:
				if channel in followers[follower]:
					payload['content'] += f'<@{follower}>'
					mentions.add(f'<@{follower}>')

			if not channels[channel]['is_streaming']:
				channels[channel]['is_streaming'] = True
				webhook.send_message({'content': channels[channel]['display_name']})
				sleep(0.1)
				webhook.delete_message()

				for follower in mentions:
					users_to_ping.add(follower)

			if channels[channel]['stream_title'] != stream_info['title']:
				webhook.edit_message(payload, channels[channel]['message_id'])
				channels[channel]['stream_title'] = stream_info['title']

		else:
			if channels[channel]['is_streaming'] is not False:
				channels[channel]['is_streaming'] = False
				payload['content'] = '[OFFLINE]'
				webhook.edit_message(payload, channels[channel]['message_id'])

	if users_to_ping:
		webhook.send_message({'content': ''.join(users_to_ping)})
		sleep(0.1)
		webhook.delete_message()

	save_to_files()


if __name__ == '__main__':
	config = dotenv.dotenv_values('.env')
	webhook = Webhook(config['DISCORD_WEBHOOK_ID'], config['DISCORD_WEBHOOK_TOKEN'])
	session = Session()
	twitch_init()
	headers = {'Authorization': f'Bearer {config["TWITCH_APP_BEARER_TOKEN"]}', 'Client-ID': config["TWITCH_APP_ID"]}
	followers, channels = {}, {}
	try:
		read_from_files()
		refresh_channels_data()
	except FileNotFoundError:
		save_to_files()
	bot.run(config['DISCORD_BOT_TOKEN'])
