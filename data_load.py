from data_parser import dataParser
from LinearRegression.regression import test;


def main():
    # dataParser.load_players()

    # dataParser.load_all_season_games()
    # dataParser.parse_overtimes()
    # dataParser.load_records()
    # dataParser.load_career_and_season_stats()
    # dataParser.load_boxscores()
    
    # dataParser.build_boxscore_snapshot()
    # dataParser.build_boxscore_snapshot_career()
    
    # dataParser.load_basic_snapshot()

    dataParser.daily_update()
    # dataParser.load_basic_snapshot_prediction()
    # test()
    # dataParser.load_distance()

main()