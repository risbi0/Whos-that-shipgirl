from names import SHIP_NAMES
from dotenv import load_dotenv
from asyncio import TimeoutError
import discord, os, random

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

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

client = discord.Client(intents=discord.Intents.all())

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    global ship_names, record

    if message.author.bot or not message.content.startswith('!start'):
        return

    if message.content.startswith('!start'):
        ship_names = SHIP_NAMES.copy()
        record = {}
        await message.channel.send(view=View())

client.run(TOKEN)
