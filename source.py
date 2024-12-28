import disnake
from disnake.ext import commands
import asyncio
import json
import os
from datetime import datetime

intents = disnake.Intents.default()
# Не пугайтесь! Это не ошибка, так надо.
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True
bot = commands.Bot(command_prefix="/", intents=disnake.Intents.all())
token = 'token'
vc_id = 123  # Задайте ему ID войса, где он будет сидеть изначально
time_file = 'time_info.json'


def load_time_data():
    if os.path.exists(time_file):
        with open(time_file, 'r') as file:
            return json.load(file)
    return {}


def save_time_data(data):
    with open(time_file, 'w') as file:
        json.dump(data, file, indent=4)

user_join_times = {}
time_data = load_time_data()


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    voice_channel = bot.get_channel(vc_id)
    if voice_channel is None:
        print(f'Voice channel with ID {vc_id} not found.')
    else:
        await voice_channel.connect()


@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel is not None and after.channel.id == vc_id:
        user_join_times[member.id] = datetime.utcnow()
    elif before.channel is not None and before.channel.id == vc_id:
        if member.id in user_join_times:
            join_time = user_join_times.pop(member.id)
            time_spent = datetime.utcnow() - join_time
            if str(member.id) not in time_data:
                time_data[str(member.id)] = {"hours": 0, "minutes": 0, "seconds": 0}
            time_data[str(member.id)]["hours"] += time_spent.seconds // 3600
            time_data[str(member.id)]["minutes"] += (time_spent.seconds % 3600) // 60
            time_data[str(member.id)]["seconds"] += time_spent.seconds % 60
            if time_data[str(member.id)]["seconds"] >= 60:
                time_data[str(member.id)]["minutes"] += time_data[str(member.id)]["seconds"] // 60
                time_data[str(member.id)]["seconds"] %= 60
            if time_data[str(member.id)]["minutes"] >= 60:
                time_data[str(member.id)]["hours"] += time_data[str(member.id)]["minutes"] // 60
                time_data[str(member.id)]["minutes"] %= 60
            save_time_data(time_data)


@bot.slash_command(description="Подключить бота к вам")
async def connect(interaction: disnake.ApplicationCommandInteraction):
    if not interaction.author.voice:
        await interaction.send("Вы не в гс! Зайдите в гс!")
        return
    if not interaction.author.guild_permissions.move_members:
        await interaction.send("У вас нет прав на это!")
        return
    voice_channel = interaction.author.voice.channel
    voice_client = disnake.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
    if voice_channel:
        await voice_channel.connect()
        await interaction.send(f"Подключился к каналу {voice_channel.name} :)")
    else:
        await interaction.send("Не удалось подключиться к голосовому каналу :(")


@bot.slash_command(description="Показать время пользователя, проведённого в гс с ботом")
async def time(interaction: disnake.ApplicationCommandInteraction):
    user_id = str(interaction.author.id)
    if user_id in time_data:
        time_spent = time_data[user_id]
        hours = str(time_spent['hours']).zfill(2)
        minutes = str(time_spent['minutes']).zfill(2)
        seconds = str(time_spent['seconds']).zfill(2)
        await interaction.send(f"Вы провели в гс: {hours}:{minutes}:{seconds}")
    else:
        await interaction.send("Вы ещё не были в гс со мной :(")


@bot.slash_command(description="Показать топ сервера")
async def top(interaction: disnake.ApplicationCommandInteraction):
    sorted_users = sorted(time_data.items(), key=lambda x: (x[1]['hours'], x[1]['minutes'], x[1]['seconds']),
                          reverse=True)
    message = f"Топ пользователей сервера {interaction.guild.name}:\n"
    for idx, (user_id, time_spent) in enumerate(sorted_users[:10], start=1):
        user = await bot.fetch_user(int(user_id))
        hours = str(time_spent['hours']).zfill(2)
        minutes = str(time_spent['minutes']).zfill(2)
        seconds = str(time_spent['seconds']).zfill(2)
        message += f"{idx} место: {user.name} - {hours}:{minutes}:{seconds}\n"
    await interaction.send(message)

bot.run(token)
