from names import SHIP_NAMES
from dotenv import load_dotenv
from asyncio import TimeoutError
from discord.ext import commands
from keep_alive import keep_alive
import discord, os, random, json, math

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

INFO = 'Guess the name of the shipgirl! 10 rounds and 15 second time limit.'

with open('leaderboard.json', 'r') as f:
    leaderboard_data = json.load(f)

class Menu(discord.ui.View):
	global ship_names, record

	@discord.ui.button(label='Join Game', style=discord.ButtonStyle.primary)
	async def join_game(self, interaction, button):
		# initialize player score
		record[interaction.user.id] = 0
		await interaction.response.edit_message(content=f"{INFO}\n**Participants**\n{''.join([f'<@{player_id}> ' for player_id in record.keys()])}")
		await interaction.followup.send(content='You have joined the game.', ephemeral=True)

	@discord.ui.button(label='Leave Game', style=discord.ButtonStyle.danger)
	async def leave_game(self, interaction, button):
		if interaction.user.id in record:
			del record[interaction.user.id]
			await interaction.response.edit_message(content=f"{INFO}\n**Participants**\n{''.join([f'<@{player_id}> ' for player_id in record.keys()])}")
			await interaction.followup.send(content='You have left the game.', ephemeral=True)
		else:
			await interaction.response.send_message(content='You haven\'t joined the game.', ephemeral=True)

	@discord.ui.button(label='Start Game', style=discord.ButtonStyle.success)
	async def start_game(self, interaction, button):
		def check(msg):
			return msg.author.id in record and msg.channel == interaction.channel

		async def show_unhidden(t, ship_name):
			embed = discord.Embed(title=t, description=ship_name)
			embed.set_image(url=f"https://raw.githubusercontent.com/risbi0/Whos-that-shipgirl/main/img/unhidden/{ship_name.replace(' ', '%20')}.png")
			await interaction.channel.send(embed=embed)

		if len(record) == 0:
			await interaction.response.send_message(content='No players have joined.')
			return

		# delete message so no one messes with the buttons mid-game
		await interaction.message.delete()

		players_msg = '\n'.join([f'<@{player}>' for player in record.keys()])
		await interaction.response.send_message(content=f'Starting game with players:\n{players_msg}')

		for i in range(1, 11):
			# get random shipgirl
			rand_ship_index = random.randint(0, len(ship_names))
			ship_name = ship_names[rand_ship_index]['filename']
			alt_names = ship_names[rand_ship_index]['names']
			ship_names.pop(rand_ship_index)

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
					if  answer == ship_name.lower() or answer in alt_names:
						player_id = message.author.id
						record[player_id] += 1
						# show actual image w/ name
						await show_unhidden('Correct!', ship_name)
						break
				except TimeoutError:
					# show next image when no correct answer sent in 15 seconds
					await show_unhidden('Times up!', ship_name)
					break

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
		self.current_page = self.last_page_num
		await interaction.response.defer()
		await self.update_message(self.data, False, True)

	async def send(self, ctx):
		self.message = await ctx.channel.send(view=self)
		await self.update_message(self.data, True, False)

	def add_ordinal_suffix(self, num):
		if 10 <= num % 100 <= 20:
			suffix = 'th'
		else:
			suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(num % 10, 'th')

		return f'{num}{suffix}'

	def create_embed(self, record):
		rank = list(self.data).index(self.user_id) + 1
		embed = discord.Embed(title=f'{self.server_name} Leaderboard')
		embed.set_footer(text=f'Page {self.current_page}/{self.total_pages} • Your leaderboard rank: {self.add_ordinal_suffix(rank)}')

		if hasattr(self, 'server_icon_url'):
			embed.set_thumbnail(url=self.server_icon_url)

		record = dict(sorted(record.items(), key=lambda item: item[1], reverse=True))

		for index, (player_id, player_score) in enumerate(record.items()):
			player = bot.get_user(int(player_id))
			embed.add_field(
				name='',
				value=f'**{index + 1}.** {player.name}#{player.discriminator}  **•**  {player_score}',
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

		if self.current_page == self.last_page_num:
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

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name='!start !lb'))

@bot.command()
async def start(ctx):
	global ship_names, record

	ship_names = SHIP_NAMES.copy()
	record = {}
	await ctx.send(INFO, view=Menu())

@bot.command(name='lb')
async def leaderboard(ctx):
	server_id = ctx.guild.id
	has_server_icon = hasattr(ctx.guild.icon, 'url')

	leaderboard = Leaderboard()
	leaderboard.data = leaderboard_data[str(server_id)]
	leaderboard.server_name = bot.get_guild(server_id)
	leaderboard.user_id = str(ctx.author.id)
	leaderboard.current_page = 1
	leaderboard.entries_per_page = 10
	leaderboard.total_pages = len(leaderboard.data)
	leaderboard.last_page_num = math.ceil(leaderboard.total_pages / leaderboard.entries_per_page)

	if has_server_icon:
		leaderboard.server_icon_url = ctx.guild.icon.url

	await leaderboard.send(ctx)

keep_alive()
bot.run(TOKEN)
