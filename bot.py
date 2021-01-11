from discord.ext import commands, tasks
import json
from random import randint

with open('discord.json') as f:
    token = json.load(f)['TOKEN']

with open('config.json') as f:
    config = json.load(f)

bot = commands.Bot(command_prefix='!')
guild = None
channel = None

game = {
    "players": [],
    "scores": [],
    "cur_player": 0,
    "waiting_for_players": False,
    "in_progress": False,
}

async def next_player():
    global game
    global channel
    if game["cur_player"] == len(game["players"])-1:
        scores = []
        for i in range(len(game["players"])):
            scores.append((game["players"][i], game["scores"][i]))
        score_string = "\n".join("{}: {}".format(x[0], x[1]) for x in scores)
        await channel.send("The game is over! Final scores:\n{}".format(score_string))
        reset_game()
        return True
    else:
        game["cur_player"] = game["cur_player"] + 1
    return False

turn = {
    "dice": 6,
    "scored_dice": 0,
    "score": 0,
    "current_dice": [],
    "current_options": []
}

@bot.event
async def on_ready():
    global guild
    global channel
    for g in bot.guilds:
        if g.name == config['SERVER']:
            guild = g
            break
    print('Bot joined {}'.format(g))
    for c in guild.channels:
        if c.name == config['CHANNEL']:
            channel = c
            break
    await channel.send("I'm {}, say !farkle to play Farkle!".format(bot.user.name))

@bot.command()
async def farkle(ctx):
    global game
    if game["in_progress"]:
        return
    if ctx.author == bot.user:
        return
    await ctx.channel.send(ctx.author.mention + " let's play Farkle! Others say !join in the next 30 seconds to join the game.")
    game['players'].append(ctx.author)
    game['scores'].append(0)
    game['waiting_for_players'] = True
    game['in_progress'] = True
    start_game.start()

@bot.command()
async def join(ctx):
    global game
    if ctx.author == bot.user:
        return
    if game['waiting_for_players'] == True:
        game['players'].append(ctx.author)
        game['scores'].append(0)
        player_strings = [x.display_name for x in game['players']]
        await ctx.channel.send('{} joined the game! Current players: {}'.format(ctx.author.mention, ', '.join(player_strings)))

@tasks.loop(seconds=30, count=2)
async def start_game():
    global game
    if start_game.current_loop == 0:
        return
    game['waiting_for_players'] = False
    first_player = game['players'][0].mention
    await channel.send('Game starting! {} say !roll to start.'.format(first_player))

@bot.command()
async def roll(ctx):
    global turn
    global game
    if ctx.author == bot.user:
        return
    if ctx.author != game['players'][game['cur_player']]:
        return
    player = ctx.author.display_name
    dice = roll_dice(turn['dice'])
    turn["current_dice"] = dice
    scoring_options = get_scoring_options(dice)
    turn["current_options"] = scoring_options
    if len(scoring_options) == 0:
        reset_turn()
        game_over = next_player()
        if game_over:
            await ctx.channel.send('{} farkled! You get no points this round.'.format(player))
        else:
            await ctx.channel.send('{} farkled! You get no points this round.\nNow it\'s {}\'s turn, type !roll to begin.'.format(player, game["players"][game["cur_player"]].mention))
        return
    dice_string = ', '.join(str(n) for n in dice)
    options_string = "\n".join('{}. {}'.format(idx+1, option) for idx,option in enumerate(scoring_options))
    await ctx.channel.send('{} rolled {} dice: {}\nYour scoring options are:\n{}\nPlease enter !keep with your choices as integers separated by a space\ne.g. !keep 1 2 3'.format(player, str(turn['dice']), dice_string, options_string))

@bot.command()
async def keep(ctx, *args):
    global turn
    global game
    if ctx.author == bot.user:
        return
    if ctx.author != game['players'][game['cur_player']]:
        return
    if len(args) == 0:
        await ctx.channel.send("You didn't pick any dice. Please enter !keep with your choices as integers separated by a space.")
        return
    if len(args) > len(turn["current_options"]):
        await ctx.channel.send("You entered more options than are available. Try again.")
    for arg in args:
        if not arg.isnumeric():
            await ctx.channel.send("You entered an invalid choice, please enter !keep with your choices as integers separated by a space.")
        if int(arg)-1 > len(turn["current_options"]):
            await ctx.channel.send("You entered an option that isn't available. Try again.")
    for arg in args:
        choice = turn["current_options"][int(arg)-1]
        turn["score"] = turn["score"] + get_score(choice)
        turn["current_dice"] = update_dice(turn["current_dice"], choice)
    turn["scored_dice"] = 6 - len(turn["current_dice"])
    turn["dice"] = len(turn["current_dice"])
    await ctx.channel.send("{} your current score is {} and you have {} unscored dice. Enter !roll to roll them again or !next to end your turn.".format(ctx.author.display_name, turn["score"], turn["dice"]))

@bot.command()
async def next(ctx):
    global game
    if ctx.author == bot.user:
        return
    if ctx.author != game['players'][game['cur_player']]:
        return
    game["scores"][game["cur_player"]] += turn["score"]
    reset_turn()
    game_over = next_player()
    if not game_over:
        await ctx.channel.send('Now it\'s {}\'s turn, type !roll to begin.'.format(game["players"][game["cur_player"]].mention))


def reset_turn():
    global turn
    turn = {
        "dice": 6,
        "scored_dice": 0,
        "score": 0,
        "current_dice": [],
        "current_options": []
    }

def reset_game():
    global game
    reset_turn()
    game = {
        "players": [],
        "scores": [],
        "cur_player": 0,
        "waiting_for_players": False,
        "in_progress": False,
    }
    
def roll_dice(n):
    dice = []
    for i in range(n):
        dice.append(randint(1,6))
    return dice

def get_scoring_options(dice):
    all_scoring_options = [
        'Single 1',
        'Two 1s',
        'Single 5',
        'Two 5s',
        'Three 1s',
        'Three 2s',
        'Three 3s',
        'Three 4s',
        'Three 5s',
        'Three 6s'
    ]
    scoring_options = []
    if 1 in dice:
        ones = dice.count(1)
        if ones >= 3:
            scoring_options.append('Three 1s')
            if ones == 4:
                scoring_options.append('Single 1')
            elif ones == 5:
                scoring_options.append('Two 1s')
            elif ones == 6:
                scoring_options.append('Three 1s')
        else:
            if ones == 1:
                scoring_options.append('Single 1')
            else:
                scoring_options.append('Two 1s')
    if 2 in dice:
        twos = dice.count(2)
        if twos == 3:
            scoring_options.append('Three 2s')
        if twos == 6:
            scoring_options.append('Three 2s')
            scoring_options.append('Three 2s')
    if 3 in dice:
        threes = dice.count(3)
        if threes == 3:
            scoring_options.append('Three 3s')
        if threes == 6:
            scoring_options.append('Three 3s')
            scoring_options.append('Three 3s')
    if 4 in dice:
        fours = dice.count(4)
        if fours == 3:
            scoring_options.append('Three 4s')
        if fours == 6:
            scoring_options.append('Three 4s')
            scoring_options.append('Three 4s')
    if 5 in dice:
        fives = dice.count(5)
        if fives >= 3:
            scoring_options.append('Three 5s')
            if fives == 4:
                scoring_options.append('Single 5')
            elif fives == 5:
                scoring_options.append('Two 5s')
            elif fives == 6:
                scoring_options.append('Three 5s')
        else:
            if fives == 1:
                scoring_options.append('Single 5')
            else:
                scoring_options.append('Two 5s')
    if 6 in dice:
        sixes = dice.count(6)
        if sixes == 3:
            scoring_options.append('Three 6s')
        if sixes == 6:
            scoring_options.append('Three 6s')
            scoring_options.append('Three 6s')
    return scoring_options

def update_dice(dice, option):
    if option == 'Single 1':
        dice.remove(1)
    elif option == 'Two 1s':
        dice.remove(1)
        dice.remove(1)
    elif option == 'Single 5':
        dice.remove(5)
    elif option == 'Two 5s':
        dice.remove(5)
        dice.remove(5)
    elif option == 'Three 1s':
        for i in range(3):
            dice.remove(1)
    elif option == 'Three 2s':
        for i in range(3):
            dice.remove(2)
    elif option == 'Three 3s':
        for i in range(3):
            dice.remove(3)
    elif option == 'Three 4s':
        for i in range(3):
            dice.remove(4)
    elif option == 'Three 5s':
        for i in range(3):
            dice.remove(5)
    elif option == 'Three 6s':
        for i in range(3):
            dice.remove(6)
    return dice

def get_score(option):
    option_values = {
        'Single 1': 100,
        'Two 1s': 200,
        'Single 5': 50,
        'Two 5s': 100,
        'Three 1s': 100,
        'Three 2s': 200,
        'Three 3s': 300,
        'Three 4s': 400,
        'Three 5s': 500,
        'Three 6s': 600
    }
    return option_values[option]
    

bot.run(token, bot=True, reconnect=True)