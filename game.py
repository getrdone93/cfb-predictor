import utilities as util
from dateutil import parser as du
import os.path as path

#functions for reading in data from game.csv

FILE_NAME = 'game.csv'

def csv_to_map(**kwargs):
    """For a given list of maps in csv_reader, maps a game code id to 
       each map with the game code id removed from each map

    Args:
         csv_reader: list of maps
    
    Returns: map of game code ids to values
    """
    csv_reader = kwargs['csv_reader']
    result = {}

    for row in csv_reader:
        game_code_id = 'Game Code'
        result[row[game_code_id]] = {k: row[k] for k in set(row.keys())
                           .difference({game_code_id})}
    return result

def seasons_by_game_code(**kwargs):
    """Given a game_code_id and map of games, returns the games of
       teams that are in game_code_id

    Args:
         game_code_id: a game id
         games: map of game ids to their values
    
    Returns: map of team ids to their games
    """
    game_code_id, games = kwargs['game_code_id'], kwargs['games']
    visit_team, home_team = 'Visit Team Code', 'Home Team Code'

    games_by_team = {}
    games_by_team[games[game_code_id][visit_team]] = {}
    games_by_team[games[game_code_id][home_team]] = {}

    for gid, game_info in games.iteritems():
        if game_info[visit_team] in games_by_team:
            games_by_team[game_info[visit_team]][gid] = util.subset_of_map(full_map=game_info, 
                                                                           take_out_keys={'Game Code'})
        if game_info[home_team] in games_by_team:
            games_by_team[game_info[home_team]][gid] = util.subset_of_map(full_map=game_info, 
                                                                           take_out_keys={'Game Code'})
    return games_by_team

def subseason(**kwargs):
    """Returns a subset of the games in team_games according to
       a game_code_id and comparison operator

    Args:
         team_games: map of team id to its games, which is also a map
         game_code_id: game id to base comparison off of
         compare: comparison operator (e.g. op.lt, op.gt etc.)
    
    Returns: list of tuples

    Raises:
           ValueError: if game_code_id is not in team_games
    """
    team_games, game_code_id, compare, date = kwargs['team_games'], kwargs['game_code_id'],\
                                              kwargs['compare'], 'Date'
    
    if game_code_id in team_games:
        lis = map(lambda e: (e[0], du.parse(e[-1][date])), team_games.iteritems())
        lis.sort(key=lambda e: e[-1])
        return filter(lambda x: compare(x[-1], du.parse(team_games[game_code_id][date])), lis)
    else:
        raise ValueError("%s id was not in %s" % (str(game_code_id), str(team_games)))

def game_stats(**kwargs):
    """Reads in data from a game.csv file

    Args:
         directory: directory containing a game.csv file
    
    Returns: a map of game data
    """
    input_directory = kwargs['directory']

    game_file = path.join(input_directory, FILE_NAME)
    game_data = util.read_file(input_file=game_file, func=csv_to_map)
    
    return game_data
    
