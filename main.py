from names import SHIP_NAMES
from dotenv import load_dotenv
from asyncio import TimeoutError
import discord, os, random, json, math

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

with open('leaderboard.json', 'r') as f:
    leaderboard_data = json.load(f)

class View(discord.ui.View):
	global ship_names, record

	@discord.ui.button(label='Join Game', style=discord.ButtonStyle.primary)
	async def join_game(self, interaction, button):
		# initialize player score
		record[interaction.user.id] = 0
		await interaction.response.edit_message(content=f"Participants:\n{''.join([f'<@{player_id}> ' for player_id in record.keys()])}")
		await interaction.followup.send(content='You have joined the game.', ephemeral=True)

	@discord.ui.button(label='Leave Game', style=discord.ButtonStyle.danger)
	async def leave_game(self, interaction, button):
		del record[interaction.user.id]
		await interaction.response.edit_message(content=f"Participants:\n{''.join([f'<@{player_id}> ' for player_id in record.keys()])}")
		await interaction.followup.send(content=f'You have left the game.', ephemeral=True)

	@discord.ui.button(label='Start Game', style=discord.ButtonStyle.success)
	async def start_game(self, interaction, button):
		if len(record) == 0:
			await interaction.response.send_message(content='No players have joined.')
			return

		players_msg = '\n'.join([f'<@{player}>' for player in record.keys()])
		await interaction.response.send_message(content=f'Starting game with players:\n{players_msg}')

		def check(msg):
			return msg.author.id in record and msg.channel == interaction.channel

		for i in range(1, 4):
			# get random shipgirl
			rand_ship_index = random.randint(0, len(ship_names))
			ship_name = ship_names[rand_ship_index]
			ship_names.remove(ship_name)

			await interaction.channel.send(f'Round {i} of 3')
			with open(f'img/hidden/{ship_name}.png', 'rb') as image:
				img = discord.File(image)
				await interaction.channel.send(file=img)

			# wait for a correct answer for 30 seconds
			loop = True
			while loop:
				try:
					message = await client.wait_for('message', check=check, timeout=20)
					# score the player who guessed correctly
					if message.content == ship_name or message.content == ship_name.lower():
						player_id = message.author.id
						record[player_id] += 1
						loop = False

						# show actual image w/ name
						await interaction.channel.send('Correct!')
						with open(f'img/unhidden/{ship_name}.png', 'rb') as image:
							img = discord.File(image)
							await interaction.channel.send(file=img)
				except TimeoutError:
					# show next image when no correct answer sent in 30 seconds
					await interaction.channel.send(f'Times up! Correct answer: {ship_name}')
					with open(f'img/unhidden/{ship_name}.png', 'rb') as image:
						img = discord.File(image)
						await interaction.channel.send(file=img)

					loop = False

		# display final scores
		await interaction.channel.send('**Final Scores**')
		for player_id, player_score in record.items():
			await interaction.channel.send(f'<@{player_id}> {player_score}')

		self.update_leaderboard(str(interaction.guild_id), record)

	def update_leaderboard(self, server_id, record):
		if server_id not in leaderboard_data:
			leaderboard_data[server_id] = {}

		for player_id, player_score in record.items():
			player_id = str(player_id)
			if player_id not in leaderboard_data[server_id]:
				leaderboard_data[server_id][player_id] = 0

			leaderboard_data[server_id][player_id] += player_score

		with open('leaderboard.json', 'w') as f:
			json.dump(leaderboard_data, f)

class Leaderboard(discord.ui.View):
	current_page = 1
	entries_per_page = 10

	@discord.ui.button(label='First Page', style=discord.ButtonStyle.primary)
	async def first_page(self, interaction, button):
		self.current_page = 1
		await interaction.response.defer()
		await self.update_message(self.data, True, False)

	@discord.ui.button(label='Prev Page', style=discord.ButtonStyle.primary)
	async def prev_page(self, interaction, button):
		self.current_page -= 1
		await interaction.response.defer()
		await self.update_message(self.data, True, True)

	@discord.ui.button(label='Next Page', style=discord.ButtonStyle.primary)
	async def next_page(self, interaction, button):
		self.current_page += 1
		await interaction.response.defer()
		await self.update_message(self.data, True, True)

	@discord.ui.button(label='Last Page', style=discord.ButtonStyle.primary)
	async def last_page(self, interaction, button):
		self.current_page = math.ceil(len(self.data) / self.entries_per_page)
		await interaction.response.defer()
		await self.update_message(self.data, False, True)

	async def send(self, message):
		self.message = await message.channel.send(view=self)
		await self.update_message(self.data, True, False)

	def create_embed(self, record):
		embed = discord.Embed(title='Leaderboard')
		record = dict(sorted(record.items(), key=lambda item: item[1], reverse=True))

		for index, (player_id, player_score) in enumerate(record.items()):
			player = client.get_user(int(player_id))
			embed.add_field(
				name=f'{index + 1}. {player.name}#{player.discriminator}',
				value=player_score,
				inline=False
			)

		return embed

	def update_buttons(self):
		if self.current_page == 1:
			self.first_page.disabled = True
			self.prev_page.disabled = True
		else:
			self.first_page.disabled = False
			self.prev_page.disabled = False

		if self.current_page == math.ceil(len(self.data) / self.entries_per_page):
			self.next_page.disabled = True
			self.last_page.disabled = True
		else:
			self.next_page.disabled = False
			self.last_page.disabled = False

	async def update_message(self, data, bool1, bool2):
		self.update_buttons()
		until_page = self.current_page * self.entries_per_page if bool1 else 0
		from_page = until_page - self.entries_per_page if bool2 else None
		data = dict(list(data.items())[from_page:until_page])
		await self.message.edit(embed=self.create_embed(data), view=self)

client = discord.Client(intents=discord.Intents.all())

@client.event
async def on_ready():
	print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
	global ship_names, record

	if message.author.bot:
		return

	if message.content.startswith('!start'):
		ship_names = SHIP_NAMES.copy()
		record = {}
		await message.channel.send(view=View())
	elif message.content.startswith('!leaderboard'):
		server_id = str(message.guild.id)
		leaderboard = Leaderboard()
		leaderboard.data = leaderboard_data[server_id]
		await leaderboard.send(message)

client.run(TOKEN)
