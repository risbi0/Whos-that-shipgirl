from names import SHIP_NAMES
from dotenv import load_dotenv
from asyncio import TimeoutError
from discord.ext import commands
from keep_alive import keep_alive
import discord, os, random, json, math, re

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

INFO = 'Guess the name of the shipgirl!\nThere are 10 rounds each with a 15 second time limit.\nEnter `!names` to check all the possible names for each ship.'
game_data = {}

with open('leaderboard.json', 'r') as f:
    leaderboard_data = json.load(f)

def add_ordinal_suffix(num):
	if 10 <= num % 100 <= 20:
		suffix = 'th'
	else:
		suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(num % 10, 'th')

	return f'{num}{suffix}'

class Menu(discord.ui.View):
	@discord.ui.button(label='Join Game', style=discord.ButtonStyle.primary)
	async def join_game(self, interaction, button):
		# initialize player score
		game_data[self.server_id]['player_scores'][interaction.user.id] = 0
		await interaction.response.edit_message(content=f"{INFO}\n\n**Participants**\n{''.join([f'<@{player_id}> ' for player_id in game_data[self.server_id]['player_scores'].keys()])}")
		await interaction.followup.send(content='You have joined the game.', ephemeral=True)

	@discord.ui.button(label='Leave Game', style=discord.ButtonStyle.danger)
	async def leave_game(self, interaction, button):
		if interaction.user.id in game_data[self.server_id]['player_scores']:
			del game_data[self.server_id]['player_scores'][interaction.user.id]
			if len(game_data[self.server_id]['player_scores']) != 0:
				message = f"{INFO}\n\n**Participants**\n{''.join([f'<@{player_id}> ' for player_id in game_data[self.server_id]['player_scores'].keys()])}"
			else:
				message = INFO
			await interaction.response.edit_message(content=message)
			await interaction.followup.send(content='You have left the game.', ephemeral=True)
		else:
			await interaction.response.send_message(content='You haven\'t joined the game.', ephemeral=True)

	@discord.ui.button(label='Start Game', style=discord.ButtonStyle.success)
	async def start_game(self, interaction, button):
		def check(msg):
			return msg.author.id in game_data[self.server_id]['player_scores'] and msg.guild is not None and msg.guild.id == interaction.guild_id

		async def show_unhidden(t, ship_name):
			embed = discord.Embed(title=t, description=ship_name)
			embed.set_image(url=f"https://raw.githubusercontent.com/risbi0/Whos-that-shipgirl/main/img/unhidden/{ship_name.replace(' ', '%20')}.png")
			await interaction.channel.send(embed=embed)

		if len(game_data[self.server_id]['player_scores']) == 0:
			await interaction.response.send_message(content='No players have joined.')
			return

		game_data[self.server_id]['game_ongoing'] = True
		# delete message so no one messes with the buttons mid-game
		await interaction.message.delete()

		players_msg = '\n'.join([f'<@{player_id}>' for player_id in game_data[self.server_id]['player_scores'].keys()])
		await interaction.response.send_message(content=f'Starting game with players:\n{players_msg}')

		for i in range(1, 11):
			# get random shipgirl
			while True:
				rand_ship_index = random.randint(0, len(SHIP_NAMES))
				if rand_ship_index not in game_data[self.server_id]['picked_indices']:
					game_data[self.server_id]['picked_indices'].append(rand_ship_index)
					break
			ship_name = SHIP_NAMES[rand_ship_index]['filename']
			alt_names = SHIP_NAMES[rand_ship_index]['names']

			embed = discord.Embed(title=f'Round {i} of 10')
			embed.set_image(url=f"https://raw.githubusercontent.com/risbi0/Whos-that-shipgirl/main/img/hidden/{ship_name.replace(' ', '%20')}.png")
			await interaction.channel.send(embed=embed)

			# process sent messages until correct answer or timed out
			while True:
				try:
					# wait for correct answer for 15 seconds
					message = await bot.wait_for('message', check=check, timeout=15)
					answer = message.content.lower()
					# score the player who guessed correctly
					if answer == ship_name.lower() or answer in alt_names:
						player_id = message.author.id
						game_data[self.server_id]['player_scores'][player_id] += 1
						# show actual image w/ name
						await show_unhidden('Correct!', ship_name)
						break
				except TimeoutError:
					# show next image when no correct answer sent in 15 seconds
					await show_unhidden('Times up!', ship_name)
					break

		# display final scores
		await interaction.channel.send('**Final Scores**')
		for player_id, player_score in game_data[self.server_id]['player_scores'].items():
			await interaction.channel.send(f'<@{player_id}> {player_score}')

		self.update_leaderboard(str(interaction.guild_id))
		game_data[self.server_id]['game_ongoing'] = False

	def create_ordinal_list(self, server_data):
		ordinals = []
		current_ordinal = 1
		current_score = None

		for data in server_data.values():
			if data['score'] != current_score:
				current_ordinal += 1
				current_score = data['score']

			ordinals.append(current_ordinal - 1)

		return ordinals

	def update_leaderboard(self, server_id):
		if server_id not in leaderboard_data:
			leaderboard_data[server_id] = {}

		# add scores to leaderboard
		for player_id, player_score in game_data[self.server_id]['player_scores'].items():
			player_id = str(player_id)
			if player_id not in leaderboard_data[server_id]:
				leaderboard_data[server_id][player_id] = {}
				leaderboard_data[server_id][player_id]['score'] = 0

			leaderboard_data[server_id][player_id]['score'] += player_score

		# sort server records
		leaderboard_data[server_id] = dict(
			sorted(
				leaderboard_data[server_id].items(),
				key=lambda item: item[1]['score'],
				reverse=True
			)
		)

		# update rankings
		ranks = self.create_ordinal_list(leaderboard_data[server_id])
		for index, data in enumerate(leaderboard_data[server_id].values()):
			data['place'] = add_ordinal_suffix(ranks[index])

		with open('leaderboard.json', 'w') as f:
			json.dump(leaderboard_data, f)

class Leaderboard(discord.ui.View):
	@discord.ui.button(label='Prev Page', style=discord.ButtonStyle.primary)
	async def prev_page(self, interaction, button):
		self.current_page -= 1
		await interaction.response.defer()
		await self.update_message()

	@discord.ui.button(label='Next Page', style=discord.ButtonStyle.primary)
	async def next_page(self, interaction, button):
		self.current_page += 1
		await interaction.response.defer()
		await self.update_message()

	async def send(self, ctx):
		self.message = await ctx.channel.send(view=self)
		await self.update_message()

	def create_embed(self):
		embed = discord.Embed(title=f'Leaderboard • {self.server_name}')

		if hasattr(self, 'server_icon_url'):
			embed.set_thumbnail(url=self.server_icon_url)

		if not self.data:
			embed.add_field(name='', value='No data available.')
			return embed

		# fields
		for player_id, details in self.page_display.items():
			rank = re.sub('[^0-9]', '', details['place'])
			player = bot.get_user(int(player_id))
			embed.add_field(
				name='',
				value=f"**{rank}.** {player.name}#{player.discriminator}  **•**  {details['score']}",
				inline=False
			)

		# footer
		if self.user_id in self.data:
			rank = self.data[self.user_id]['place']
		else:
			rank = 'N/A'
		embed.set_footer(text=f'Page {self.current_page}/{self.last_page_num} • Your leaderboard rank: {rank}')

		return embed

	def update_buttons(self):
		self.prev_page.disabled = self.current_page == 1
		self.next_page.disabled = self.current_page == self.last_page_num

	async def update_message(self):
		self.update_buttons()
		until_page = self.current_page * self.entries_per_page
		from_page = until_page - self.entries_per_page
		self.page_display = dict(list(self.data.items())[from_page:until_page])
		await self.message.edit(embed=self.create_embed(), view=self)

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name='!start !lb'))

@bot.command()
async def start(ctx):
	server_id = ctx.guild.id

	try:
		if game_data[server_id]['game_ongoing'] == True:
			await ctx.send('Game is currently ongoing. Please wait for it to end before starting again.')
			return
	except KeyError:
		pass

	game_data[server_id] = {}
	game_data[server_id]['player_scores'] = {}
	game_data[server_id]['picked_indices'] = []

	menu = Menu()
	menu.server_id = server_id
	await ctx.send(INFO, view=menu)

@bot.command(name='lb')
async def leaderboard(ctx):
	server_id = ctx.guild.id
	has_server_icon = hasattr(ctx.guild.icon, 'url')

	leaderboard = Leaderboard()
	leaderboard.server_name = bot.get_guild(server_id)
	leaderboard.user_id = str(ctx.author.id)
	leaderboard.current_page = 1
	leaderboard.entries_per_page = 10
	try:
		leaderboard.data = leaderboard_data[str(server_id)]
		leaderboard.last_page_num = math.ceil(len(leaderboard.data) / leaderboard.entries_per_page)
	except KeyError:
		leaderboard.data = {}
		leaderboard.last_page_num = 1

	if has_server_icon:
		leaderboard.server_icon_url = ctx.guild.icon.url

	await leaderboard.send(ctx)

@bot.command()
async def names(ctx):
	user = await bot.fetch_user(ctx.author.id)
	messages = []
	message = 'Here are all the names of all ships. Some have other names which are also correct answers.\n```'

	for index, detail in enumerate(SHIP_NAMES):
		nicknames = ''
		if detail['names']:
			nicknames = f": {', '.join(detail['names'])}"

		line = f"{detail['filename'].lower()}{nicknames}\n"

		# cut message when limit is reached
		if len(message + line) + 3 > 2000: # added 3 for the following grave accents
			message += '```'
			messages.append(message)
			message = '```'

		message += line

		# add last message
		if index == len(SHIP_NAMES) - 1:
			message += '```'
			messages.append(message)

	for msg in messages:
		await user.send(msg)

keep_alive()
bot.run(TOKEN)
