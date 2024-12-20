from requests import Session
from base64 import b64encode


json_headers = {'Content-Type': 'application/json'}
boundary = '---------------------------discord_webhoook'
file_headers = {'Content-Type': 'multipart/form-data; boundary=' + boundary}


class Webhook:
	""" Webhook class

	Most informations are picked from the official Discord documentation, not all items are mentioned here, so, if you
	want more informations about a specific item, visit https://discord.com/developers/docs/resources/webhook.

	"""

	def __init__(self, identifier: str, token: str):
		""" Create the Webhook object

		identifier : identifier of the webhook.

		token : secret token of the token.

		"""

		self.__url = f'https://discord.com/api/webhooks/{identifier}/{token}'
		self.__session = Session()
		self.lastSentMessageInfo = None
		self.type = None
		self.id = None
		self.name = None
		self.avatar = None
		self.channel_id = None
		self.guild_id = None
		self.application_id = None
		self.get_webhook()

	def get_webhook(self):
		""" Store in variables the webhook's informations, shoul be called when the webhook is modified

		type (integer) : the type of the webhook
						1 = Incoming : Incoming Webhooks can post messages to channels with a generated token.
						2 = Channel Follower : Channel Follower Webhooks are internal webhooks used with
							Channel Following to post new messages into channels.

		id (string) : the id of the webhook.

		name (string) : the default name of the webhook.

		avatar (string) : the default avatar of the webhook.

		channel_id (string) : the channel id this webhook is for.

		guild_id (string) : the guild id this webhook is for.

		application_id (string) : the bot/OAuth2 application that created this webhook.

		token (string) : the secure token of the webhook (returned for Incoming Webhooks).

		"""

		assert self.__url is not None, 'Your webhook was deleted.'

		webhook_info = self.__session.get(self.__url).json()

		assert len(webhook_info.items()) == 9, 'The given ID/token is wrong.'

		self.type = webhook_info['type']
		self.id = webhook_info['id']
		self.name = webhook_info['name']
		self.avatar = webhook_info['avatar']
		self.channel_id = webhook_info['channel_id']
		self.guild_id = webhook_info['guild_id']
		self.application_id = webhook_info['application_id']

	def edit_webhook(self, name: str = None, avatar: str = None):
		""" Modify the webhook

		name (string) : the new name of the webhook.

		avatar (string) : the new avatar of the webhook,
							path or URL to an image file (PNG, JPG, WebP and GIF formats only).

		"""

		assert self.__url is not None, 'Your webhook was deleted.'

		payload = {}

		if name:
			assert 0 < len(name) <= 80, 'Webhook\'s name is limited to 80 characters.'
			payload['name'] = name

		if avatar:
			if avatar.startswith('http'):
				avatar_data = b64encode(self.__session.get(avatar).content)
			else:
				with open(avatar, 'rb') as f:
					avatar_data = b64encode(f.read())
			payload['avatar'] = 'data:image/' + avatar[-3:] + ';base64,' + avatar_data.decode()

		if payload:
			self.__session.patch(self.__url, json=payload, headers=json_headers)
			self.get_webhook()

	def delete_webhook(self):
		"""
		Send a delete request to permanently delete this webhook
		"""

		status_code = self.__session.delete(self.__url).status_code

		assert status_code == 204, 'The webhook was not deleted, an error has accured.'

		self.__url = None
		print('This webhook was permanently removed.')

	def send_message(self, payload: dict[str, ...], multiform: bool = False, payload_json: dict[str, ...] = None):
		""" Send a message

		payload, all the data of the message (or files when multiform is true) :
			content (string) : the message contents (up to 2000 characters).

			username (string) : override the default username of the webhook.

			avatar_url (string) : override the default avatar of the webhook.

			tts (boolean) : true if this is a TTS message.

			embeds (array of up to 10 embed objects) : embedded rich content.

			allowed_mentions (allowed mention object) : allowed mentions for the message.

			files[n] (file contents) : the contents of the file being sent.

			payload_json (string) : JSON encoded body of non-file params.

			attachments (array of partial attachment objects) : attachment objects with filename and description.

			flags (integer) : message flags combined as a bitfield (only SUPPRESS_EMBEDS can be set).

			thread_name (string) : name of thread to create (requires the webhook channel to be a forum channel).

			if multiform is true : list of file names.

		multiform (boolean) : whether its in multiform format or not (used for sending files).

		payload_json (dict) : include a "classic" JSON payload when multiform is true.

		"""

		assert self.__url is not None, 'Your webhook was deleted.'

		if multiform:
			filenames = payload
			index = 0
			payload = b''
			for filename in filenames:
				payload += \
					b'--' + boundary.encode() + b'\r\n' + \
					b'Content-Disposition: form-data;' + \
					b'name="files[' + str(index).encode() + b']";' + \
					b'filename="' + filename.encode() + b'"\r\n' + \
					b'Content-Type: application/octet-stream\r\n\r\n' + open(filename, 'rb').read() + b'\r\n'
				index += 1
			if payload_json:
				payload += \
					b'--' + boundary.encode() + b'\r\n' + \
					b'Content-Disposition: form-data;' + \
					b'name="payload_json"\r\n' + \
					b'Content-Type: application/json\r\n\r\n' + str(payload_json).replace('\'', '"').encode()
			payload += b'\r\n--' + boundary.encode() + b'--\r\n'
			response = self.__session.post(self.__url + '?wait=true', data=payload, headers=file_headers)
			self.lastSentMessageInfo = response.json()
		else:
			response = self.__session.post(self.__url + '?wait=true', json=payload, headers=json_headers)
			self.lastSentMessageInfo = response.json()

	def edit_message(self, payload: dict[str, ...], message_id: int | str = None):
		""" Edit a message

		payload :
			content (string) : the message content (up to 2000 characters).

			embeds (array) : array of up to 10 embed objects.

			allowed_mentions (boolean) : allowed mentions for the message.

		message_id (integer) : id of the message.

		"""

		assert self.__url is not None, 'Your webhook was deleted.'

		if not message_id:
			assert self.lastSentMessageInfo is not None, 'You have to give a message id.'
			message_id = self.lastSentMessageInfo['id']

		response = self.__session.patch(
			self.__url + f'/messages/{message_id}?wait=true',
			json=payload, headers=json_headers)
		self.lastSentMessageInfo = response.json()

	def get_message(self, message_id: int | str):
		""" Returns a previously-sent message.

		message_id (integer) : id of the target message.

		"""

		assert self.__url is not None, 'Your webhook was deleted.'

		response = self.__session.get(self.__url + f'/messages/{message_id}')

		return response.json()

	def delete_message(self, message_id: int | str = None, silent: bool = True):
		""" Delete a message

		message_id (integer) : id of the target message.

		silent (boolean) : whether or not to print a message after the deletion.

		"""

		assert self.__url is not None, 'Your webhook was deleted.'

		if not message_id and self.lastSentMessageInfo:
			message_id = self.lastSentMessageInfo['id']

		assert message_id is not None, 'You must give a message id.'

		response = self.__session.delete(self.__url + f'/messages/{message_id}?wait=true', headers=json_headers)

		assert response.status_code == 204, 'Something went wrong.'

		self.lastSentMessageInfo = None

		if not silent:
			print(f'The message with id {message_id} was removed.')
