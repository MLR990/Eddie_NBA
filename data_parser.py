from bs4 import BeautifulSoup as bs
import requests
from constants import SEASONS, SEASON_MONTHS,SEASON_DATES;
from util import util
import pyodbc
from datetime import datetime
from datetime import date
import numpy as np;
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium import webdriver
import time 
from datetime import timedelta
from webdriver_manager.chrome import ChromeDriverManager

class dataParser():
    def load_all_season_games():
        connection = pyodbc.connect('DRIVER={SQL Server Native Client 11.0};server=(localdb)\\mssqllocaldb;database=Eddie;')
        cursor = connection.cursor()

        for season in SEASONS:
            seasonId = season[0]
            year = season[1]
            for month in SEASON_MONTHS:
                print(f"season: {year} month:{month}")
                try:
                    url = f"https://www.basketball-reference.com/leagues/NBA_{year}_games-{month}.html"
                    resp = requests.get(url)
                    soup=bs(resp.text,features="html.parser")

                    gameRows = soup.find("table", {"id": "schedule"}).find_all('tbody')[0].find_all('tr')
                    for game in gameRows:
                        cols = game.find_all('td')
                        awayTeam = util.getTeamCode(cols[1].get_text())
                        awayScore = cols[2].get_text()
                        homeTeam = util.getTeamCode(cols[3].get_text())
                        homeScore = cols[4].get_text()
                        boxScore = ''
                        if len(cols[5].findAll('a',text='Box Score')) > 0:
                            boxScore = cols[5].findAll('a',text='Box Score')[0]['href'].split('/')[2].split('.')[0]
  
                        dbDate = datetime.strptime("{} {}m".format(game.find_all('th')[0].get_text(), cols[0].get_text()),  "%a, %b %d, %Y %I:%M%p")

                        attendance = cols[7].get_text()

                        print(f"INSERT INTO Games ([GameKey], [SeasonId], [HomeTeam],[HomeWins],[HomeLosses], [HomeScore], [AwayTeam],[AwayWins],[AwayLosses], [AwayScore], [GameDate]) VALUES ({boxScore},{homeTeam},0,0,{homeScore},{awayTeam},0,0,{awayScore},{dbDate})")
                        cursor.execute("INSERT INTO Games ([GameKey], [SeasonId], [HomeTeam],[HomeWins],[HomeLosses],  [HomeScore], [AwayTeam], [AwayWins],[AwayLosses],[AwayScore], [GameDate],[TotalPlayerMinutes]) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", boxScore, seasonId, homeTeam,0,0,homeScore,awayTeam,0,0,awayScore, dbDate,0)
                        cursor.commit()
                except:
                    print(f"nothing found for {year} Season in {month}")
        cursor.close()
    
    def load_records():        
        connection = pyodbc.connect('DRIVER={SQL Server Native Client 11.0};server=(localdb)\\mssqllocaldb;database=Eddie;')
        cursor = connection.cursor()
        cursor.execute("SELECT GameId, GameKey, HomeTeam, AwayTeam FROM Games WHERE SeasonId = 19")
        for game in cursor.fetchall():
            url = f'https://www.basketball-reference.com/boxscores/{game[1]}.html'
            awayTeam = game[3]
            homeTeam = game[2]
            gameId = int(game[0])
            resp = requests.get(url)
            soup=bs(resp.text,features="html.parser")
            scoreContainer = soup.find("div", {"class": "scorebox"})
            awayScoreDiv = scoreContainer.find_all("div", {"class": "scores"})[0]
            awayRecordDiv = awayScoreDiv.find_next_sibling("div")
            awayWins = int(awayRecordDiv.get_text().split('-')[0])
            awayLosses = int(awayRecordDiv.get_text().split('-')[1])
            awayScore = int(awayScoreDiv.find_all('div')[0].get_text())
            homeScoreDiv = scoreContainer.find_all("div", {"class": "scores"})[1]
            homeRecordDiv = homeScoreDiv.find_next_sibling("div")
            homeWins = int(homeRecordDiv.get_text().split('-')[0])
            homeLosses = int(homeRecordDiv.get_text().split('-')[1])
            homeScore = int(homeScoreDiv.find_all('div')[0].get_text())

            if homeScore > awayScore:
                homeWins-=1
                awayLosses-=1
            else:
                awayWins-=1
                homeLosses-=1
            print(f'Game: {gameId} -- {awayTeam}({awayWins}-{awayLosses}): {awayScore} @ {homeTeam}({homeWins}-{homeLosses}): {homeScore}')
            cursor.execute("UPDATE Games SET HomeWins = ?,HomeLosses = ?,AwayWins = ?,AwayLosses = ? WHERE GameId = ?", homeWins, homeLosses, awayWins, awayLosses, gameId)
            cursor.commit()

    def load_players():
        connection = pyodbc.connect('DRIVER={SQL Server Native Client 11.0};server=(localdb)\\mssqllocaldb;database=Eddie;')
        cursor = connection.cursor()

        cursor.execute("SELECT Game, HomeTeam, AwayTeam FROM Games")
        players = []
        for row in cursor.fetchall():

            game = row[0]
            homeTeam = row[1]
            awayTeam = row[2]
            print(f"Game: {game} - {awayTeam} @ {homeTeam} ")
            try:
                url = f"https://www.basketball-reference.com/boxscores/{game}.html"
                resp = requests.get(url)
                soup=bs(resp.text,features="html.parser")
                

                homeBasicStatRows = soup.find("table", {"id": f"box-{homeTeam}-game-basic"}).find_all('tbody')[0].find_all('tr')
                for stat in homeBasicStatRows:
                    if len(stat.findAll('a', href=True)) == 0:
                        continue
                    name = stat.findAll('a', href=True)[0].get_text()
                    referenceUrl = stat.findAll('a', href=True)[0]['href']
                    referenceKey = referenceUrl.split('/')[3].split('.')[0]
                    
                    if [referenceKey, name, referenceUrl] not in players:
                        players.append([referenceKey, name, referenceUrl])
                    cols = stat.find_all('td')

                    if len(cols) > 0:
                        if cols[0].get_text() == 'Did Not Play':    
                            print('{} ({}) did not play'.format(name, referenceKey))
                        else:
                            print('{} ({}) played in the game'.format(name, referenceKey))

                awayBasicStatRows = soup.find("table", {"id": f"box-{awayTeam}-game-basic"}).find_all('tbody')[0].find_all('tr')
                for stat in awayBasicStatRows:
                    if len(stat.findAll('a', href=True)) == 0:
                        continue
                    name = stat.findAll('a', href=True)[0].get_text()  
                    referenceUrl = stat.findAll('a', href=True)[0]['href']
                    referenceKey = referenceUrl.split('/')[3].split('.')[0]

                    if [referenceKey, name, referenceUrl] not in players:
                        players.append([referenceKey, name, referenceUrl])
                    cols = stat.find_all('td')

                    if len(cols) > 0:
                        if cols[0].get_text() == 'Did Not Play':
                            print('{} ({}) did not play'.format(name, referenceKey))
                        else:
                            print('{} ({}) played in the game'.format(name, referenceKey))
            except:
                print(f"Something went amiss")
        for player in players:

            print(player[0],player[1],player[2])
            cursor.execute("INSERT INTO Players ([ReferenceKey], [Name], [ReferenceURL]) VALUES (?,?,?)", player[0], player[1],player[2])
            cursor.commit()
        cursor.close()

    def get_new_playerId():
        connection = pyodbc.connect('DRIVER={SQL Server Native Client 11.0};server=(localdb)\\mssqllocaldb;database=Eddie;')
        cursor = connection.cursor()
        cursor.execute("SELECT TOP (1) [NBAId] FROM [Eddie].[dbo].[Players] ORDER BY NBAId ASC")
        for row in cursor.fetchall():
            playerId = int(row[0])
            return playerId - 1

    def get_player_NBAId(name):
        url = 'https://www.nba.com/players'
        driver = webdriver.Chrome(ChromeDriverManager().install())
        driver.get(url)
        driver.implicitly_wait(5)
        
        playerId = -1
        driver.implicitly_wait(10)
        playerSearch = driver.find_elements(By.CLASS_NAME, 'PlayerList_listHeader__2u0cn')[0].find_elements(By.TAG_NAME, 'input')[0]
        playerSearch.send_keys(name)
        time.sleep(3)
        playerList = driver.find_elements(By.CLASS_NAME, 'players-list')
        if len(playerList) == 0:
            print(name + " Not Found")
            playerSearch.clear()
            time.sleep(1)
            driver.close()
            return dataParser.get_new_playerId()

        rows = playerList[0].find_elements(By.TAG_NAME, 'tbody')[0].find_elements(By.TAG_NAME,'tr')
        if len(rows) == 1:
            href = rows[0].find_element(By.TAG_NAME, 'a').get_attribute('href')

            if 'stats' in href:
                playerId = href.split('/')[5]
            else:
                playerId = href.split('/')[4]
        else:
            print(f'more than 1 player found for {name}')
        driver.close()
        return playerId

    def get_player_id(key, name,url):
        connection = pyodbc.connect('DRIVER={SQL Server Native Client 11.0};server=(localdb)\\mssqllocaldb;database=Eddie;')
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(1) FROM Players WHERE ReferenceKey = ?", key)
        if cursor.fetchone()[0]:
            cursor.execute("SELECT NBAId FROM Players WHERE ReferenceKey = ?", key)
            for row in cursor.fetchall():
                return row[0]
        else:
            print(f'player ({name}) not found')
            playerId = dataParser.get_player_NBAId(name)
            cursor.execute("SET IDENTITY_INSERT Players ON")
            cursor.commit()
            cursor.execute("INSERT INTO Players ( NBAId, ReferenceKey, ReferenceURL, Name) VALUES (?,?,?,?)", playerId, key,url,name)
            cursor.commit()
            return playerId

    def parse_minutes(minutes):
        minute = minutes.split(':')[0]
        second = minutes.split(':')[1]
        
        return int(minute)+(int(second)/60) 

    def load_career_and_season_stats():
        connection = pyodbc.connect('DRIVER={SQL Server Native Client 11.0};server=(localdb)\\mssqllocaldb;database=Eddie;')
        cursor = connection.cursor()

        cursor.execute("SELECT NBAId, ReferenceURL FROM Players ")
        i = 0
        for player in cursor.fetchall():
            print(f'{player[0]} - {player[1]} ({i}/1999)')
            i += 1

            playerId = player[0]
            url = player[1]
            playerUrl = f'https://www.basketball-reference.com{url}'
            resp = requests.get(playerUrl)
            soup=bs(resp.text,features="html.parser")

            totalsTable = soup.find("table", {"id": "totals"})
            if totalsTable is None:
                gamesPlayed = 0
                gamesStarted = 0
                minutes = 0
                fgm =  0
                fga = 0
                threeMade =  0
                threeAtt =  0
                ftm =  0
                fta =  0
                oReb = 0
                dReb = 0
                ast =  0
                stl =  0
                blk =  0
                tov =  0
                pf = 0
                points =  0
                cursor.execute("INSERT INTO CareerBasicStats ([PlayerId],[ThroughDate],[GamesPlayed],[GamesStarted],[Minutes],[Points],[FGM],[FGA],[ThreePointMade],[ThreePointAttempted],[FreeThrowMade],[FreeThrowAttempted],[OffensiveRebound],[DefensiveRebound],[Assist],[TurnOver],[Steal],[Block],[PersonalFoul],[GameId]) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", playerId,'2021-10-26',gamesPlayed,gamesStarted,minutes,points,fgm,fga,threeMade,threeAtt,ftm,fta,oReb,dReb,ast,tov,stl,blk,pf,0)
                cursor.commit()
            else:
                seasonStats = totalsTable.find_all('tbody')[0].find_all('tr')
                for stat in seasonStats:
                    seasonCol = stat.find_all('th')[0].get_text()
                    currentSeason = SEASON_DATES.get(seasonCol)
                    if currentSeason is None:
                        continue
                    playerStats = stat.find_all('td')
                    gamesPlayed = playerStats[4].get_text()
                    gamesStarted = playerStats[5].get_text()
                    minutes = playerStats[6].get_text()
                    fgm = playerStats[7].get_text()
                    fga = playerStats[8].get_text()
                    threeMade = playerStats[10].get_text()
                    threeAtt = playerStats[11].get_text()
                    ftm = playerStats[17].get_text()
                    fta = playerStats[18].get_text()
                    oReb = playerStats[20].get_text()
                    dReb = playerStats[21].get_text()
                    ast = playerStats[23].get_text()
                    stl = playerStats[24].get_text()
                    blk = playerStats[25].get_text()
                    tov = playerStats[26].get_text()
                    pf = playerStats[27].get_text()
                    points = playerStats[28].get_text()
                    cursor.execute("SELECT COUNT(1) FROM SeasonBasicStats WHERE PlayerId = ? AND SeasonId = ?",playerId,currentSeason[0])
                    if cursor.fetchone()[0]:
                        if 'TOT' in playerStats[1].text:
                            cursor.execute("UPDATE SeasonBasicStats SET [ThroughDate] = ?,[GamesPlayed] = ?,[GamesStarted] = ?,[Minutes] = ?,[Points] = ?,[FGM] = ?,[FGA] = ?,[ThreePointMade] = ?,[ThreePointAttempted] = ?,[FreeThrowMade] = ?,[FreeThrowAttempted] = ?,[OffensiveRebound] = ?,[DefensiveRebound] = ?,[Assist] = ?,[TurnOver] = ?,[Steal] = ?,[Block] = ?,[PersonalFoul] = ? WHERE PlayerId = ? AND SeasonId = ?",currentSeason[1], gamesPlayed,gamesStarted, minutes, points,fgm,fga,threeMade,threeAtt,ftm,fta,oReb,dReb,ast,tov,stl,blk,pf,playerId, currentSeason[0])
                            cursor.commit()
                    else:
                        cursor.execute("INSERT INTO SeasonBasicStats ([PlayerId],[ThroughDate],[SeasonId],[GamesPlayed],[GamesStarted],[Minutes],[Points],[FGM],[FGA],[ThreePointMade],[ThreePointAttempted],[FreeThrowMade],[FreeThrowAttempted],[OffensiveRebound],[DefensiveRebound],[Assist],[TurnOver],[Steal],[Block],[PersonalFoul],[GameId]) Values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",playerId, currentSeason[1], currentSeason[0], gamesPlayed,gamesStarted, minutes, points,fgm,fga,threeMade,threeAtt,ftm,fta,oReb,dReb,ast,tov,stl,blk,pf,0)
                        cursor.commit()


                playerStats = totalsTable.find_all('tfoot')[0].find_all('tr')[0].find_all('td')
                gamesPlayed = playerStats[4].get_text()
                gamesStarted = playerStats[5].get_text()
                minutes = playerStats[6].get_text()
                fgm = playerStats[7].get_text()
                fga = playerStats[8].get_text()
                threeMade = playerStats[10].get_text()
                threeAtt = playerStats[11].get_text()
                ftm = playerStats[17].get_text()
                fta = playerStats[18].get_text()
                oReb = playerStats[20].get_text()
                dReb = playerStats[21].get_text()
                ast = playerStats[23].get_text()
                stl = playerStats[24].get_text()
                blk = playerStats[25].get_text()
                tov = playerStats[26].get_text()
                pf = playerStats[27].get_text()
                points = playerStats[28].get_text()
                cursor.execute("INSERT INTO CareerBasicStats ([PlayerId],[ThroughDate],[GamesPlayed],[GamesStarted],[Minutes],[Points],[FGM],[FGA],[ThreePointMade],[ThreePointAttempted],[FreeThrowMade],[FreeThrowAttempted],[OffensiveRebound],[DefensiveRebound],[Assist],[TurnOver],[Steal],[Block],[PersonalFoul],[GameId]) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", playerId,'2021-10-26',gamesPlayed,gamesStarted,minutes,points,fgm,fga,threeMade,threeAtt,ftm,fta,oReb,dReb,ast,tov,stl,blk,pf,0)
                cursor.commit()
            

        

    def load_boxscore(gameId, key, homeTeam, awayTeam):
        connection = pyodbc.connect('DRIVER={SQL Server Native Client 11.0};server=(localdb)\\mssqllocaldb;database=Eddie;')
        cursor = connection.cursor()
        url = f'https://www.basketball-reference.com/boxscores/{key}.html'
        resp = requests.get(url)
        soup = bs(resp.text,features="html.parser")

        i = 0
        homeBasicStatRows = soup.find("table", {"id": f"box-{homeTeam}-game-basic"}).find_all('tbody')[0].find_all('tr')
        for stat in homeBasicStatRows:
            starter = True
            if i > 4:
                starter = False
            i = i + 1
            if len(stat.findAll('a', href=True)) == 0:
                continue

            name = stat.findAll('a', href=True)[0].get_text() 
            referenceUrl = stat.findAll('a', href=True)[0]['href']
            referenceKey = referenceUrl.split('/')[3].split('.')[0]
            playerId = dataParser.get_player_id(referenceKey, name, referenceUrl)
            cols = stat.find_all('td')

            if len(cols) > 0:
                if len(cols) > 1:
                    minutes = dataParser.parse_minutes(cols[0].get_text())
                    fg = cols[1].get_text()
                    fga = cols[2].get_text()
                    fgPer = cols[3].get_text()
                    if fgPer == '':
                        fgPer = 0
                    threesMade = cols[4].get_text()
                    threesAtt = cols[5].get_text()
                    threePer = cols[6].get_text()
                    if threePer == '':
                        threePer = 0
                    ftm = cols[7].get_text()
                    fta = cols[8].get_text()
                    ftPer = cols[9].get_text()
                    if ftPer == '':
                        ftPer = 0
                    oReb = cols[10].get_text()
                    dReb = cols[11].get_text()
                    ast = cols[13].get_text()
                    stl = cols[14].get_text()
                    blk = cols[15].get_text()
                    tov = cols[16].get_text()
                    pf = cols[17].get_text()
                    pts = cols[18].get_text()
                    plusMinus = cols[19].get_text()
                    cursor.execute("INSERT INTO [dbo].[BoxScore] ([GameId],[PlayerId],[TeamId],[Starter],[Minutes],[Points],[FGM],[FGA],[FGPer],[ThreePointMade],[ThreePointAttempted],[ThreePointPercent],[FreeThrowMade],[FreeThrowAttempted],[FreeThrowPercentage],[OffensiveRebound],[DefensiveRebound],[Assist],[TurnOver],[Steal],[Block],[PersonalFoul],[PlusMinus],[Inactive]) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",gameId, playerId, homeTeam, starter, minutes, pts, fg, fga, fgPer, threesMade, threesAtt, threePer,ftm, fta, ftPer, oReb, dReb, ast, tov, stl, blk, pf, plusMinus, False)
                    cursor.commit()
                if len(cols) == 1:
                    situation = cols[0].get_text()
                    if 'Did Not Play' in situation:
                        cursor.execute("INSERT INTO [dbo].[BoxScore] ([GameId],[PlayerId],[TeamId],[Starter],[Minutes],[Points],[FGM],[FGA],[FGPer],[ThreePointMade],[ThreePointAttempted],[ThreePointPercent],[FreeThrowMade],[FreeThrowAttempted],[FreeThrowPercentage],[OffensiveRebound],[DefensiveRebound],[Assist],[TurnOver],[Steal],[Block],[PersonalFoul],[PlusMinus],[Inactive]) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",gameId, playerId, homeTeam, False, 0, 0, 0, 0, 0, 0, 0, 0,0,0, 0, 0, 0, 0, 0, 0, 0, 0, 0, False)
                        cursor.commit()
                    else:
                        cursor.execute("INSERT INTO [dbo].[BoxScore] ([GameId],[PlayerId],[TeamId],[Starter],[Minutes],[Points],[FGM],[FGA],[FGPer],[ThreePointMade],[ThreePointAttempted],[ThreePointPercent],[FreeThrowMade],[FreeThrowAttempted],[FreeThrowPercentage],[OffensiveRebound],[DefensiveRebound],[Assist],[TurnOver],[Steal],[Block],[PersonalFoul],[PlusMinus],[Inactive]) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",gameId, playerId, homeTeam, False, 0, 0, 0, 0, 0, 0, 0, 0,0,0, 0, 0, 0, 0, 0, 0, 0, 0, 0, True)
                        cursor.commit()

        awayBasicStatRows = soup.find("table", {"id": f"box-{awayTeam}-game-basic"}).find_all('tbody')[0].find_all('tr')
        i = 0
        for stat in awayBasicStatRows:
            starter = True
            if i > 4:
                starter = False
            i = i + 1

            if len(stat.findAll('a', href=True)) == 0:
                continue

            
            name = stat.findAll('a', href=True)[0].get_text() 
            referenceUrl = stat.findAll('a', href=True)[0]['href']
            referenceKey = referenceUrl.split('/')[3].split('.')[0]
            playerId = dataParser.get_player_id(referenceKey,name,referenceUrl)
            cols = stat.find_all('td')
            if len(cols) > 0:
                if len(cols) > 1:
                    minutes = dataParser.parse_minutes(cols[0].get_text())
                    fg = cols[1].get_text()
                    fga = cols[2].get_text()
                    fgPer = cols[3].get_text()
                    if fgPer == '':
                        fgPer = 0
                    threesMade = cols[4].get_text()
                    threesAtt = cols[5].get_text()
                    threePer = cols[6].get_text()
                    if threePer == '':
                        threePer = 0
                    ftm = cols[7].get_text()
                    fta = cols[8].get_text()
                    ftPer = cols[9].get_text()
                    if ftPer == '':
                        ftPer = 0
                    oReb = cols[10].get_text()
                    dReb = cols[11].get_text()
                    ast = cols[13].get_text()
                    stl = cols[14].get_text()
                    blk = cols[15].get_text()
                    tov = cols[16].get_text()
                    pf = cols[17].get_text()
                    pts = cols[18].get_text()
                    plusMinus = cols[19].get_text()
                    cursor.execute("INSERT INTO [dbo].[BoxScore] ([GameId],[PlayerId],[TeamId],[Starter],[Minutes],[Points],[FGM],[FGA],[FGPer],[ThreePointMade],[ThreePointAttempted],[ThreePointPercent],[FreeThrowMade],[FreeThrowAttempted],[FreeThrowPercentage],[OffensiveRebound],[DefensiveRebound],[Assist],[TurnOver],[Steal],[Block],[PersonalFoul],[PlusMinus],[Inactive]) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",gameId, playerId, awayTeam, starter, minutes, pts, fg, fga, fgPer, threesMade, threesAtt, threePer,ftm, fta, ftPer, oReb, dReb, ast, tov, stl, blk, pf, plusMinus, False)
                    cursor.commit()
                if len(cols) == 1:
                    situation = cols[0].get_text()
                    if 'Did Not Play' in situation:
                        cursor.execute("INSERT INTO [dbo].[BoxScore] ([GameId],[PlayerId],[TeamId],[Starter],[Minutes],[Points],[FGM],[FGA],[FGPer],[ThreePointMade],[ThreePointAttempted],[ThreePointPercent],[FreeThrowMade],[FreeThrowAttempted],[FreeThrowPercentage],[OffensiveRebound],[DefensiveRebound],[Assist],[TurnOver],[Steal],[Block],[PersonalFoul],[PlusMinus],[Inactive]) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",gameId, playerId, awayTeam, False, 0, 0, 0, 0, 0, 0, 0, 0,0,0, 0, 0, 0, 0, 0, 0, 0, 0, 0, False)
                        cursor.commit()
                    else:
                        cursor.execute("INSERT INTO [dbo].[BoxScore] ([GameId],[PlayerId],[TeamId],[Starter],[Minutes],[Points],[FGM],[FGA],[FGPer],[ThreePointMade],[ThreePointAttempted],[ThreePointPercent],[FreeThrowMade],[FreeThrowAttempted],[FreeThrowPercentage],[OffensiveRebound],[DefensiveRebound],[Assist],[TurnOver],[Steal],[Block],[PersonalFoul],[PlusMinus],[Inactive]) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",gameId, playerId, awayTeam, False, 0, 0, 0, 0, 0, 0, 0, 0,0,0, 0, 0, 0, 0, 0, 0, 0, 0, 0, True)
                        cursor.commit()
        
        divs = soup.find_all("div")
        inactiveDiv = False
        for div in divs:
            if 'Inactive' in div.get_text():
                contain = div.parent
                inactiveDiv = True
        useHomeTeam = False
        if inactiveDiv:
            for item in contain.find_all():
                if 'None' in item.text:
                    continue
                if 'Officials' in item.text:
                    break
                
                if item.text == homeTeam:
                    useHomeTeam = True
                if (homeTeam not in item.text and awayTeam not in item.text and 'Inactive' not in item.text):
                    href = item['href']
                    name = item.get_text() 
                    if href is None:
                        continue
                    if len(name) > 0:
                        team = ''
                        
                        
                        player = item['href'].split('/')[3].split('.')[0]
                        playerId = dataParser.get_player_id(player,name,href)
                        if useHomeTeam:
                            team = homeTeam
                        else:
                            team = awayTeam

                        cursor.execute("INSERT INTO [dbo].[BoxScore] ([GameId],[PlayerId],[TeamId],[Starter],[Minutes],[Points],[FGM],[FGA],[FGPer],[ThreePointMade],[ThreePointAttempted],[ThreePointPercent],[FreeThrowMade],[FreeThrowAttempted],[FreeThrowPercentage],[OffensiveRebound],[DefensiveRebound],[Assist],[TurnOver],[Steal],[Block],[PersonalFoul],[PlusMinus],[Inactive]) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",gameId, playerId, team, False, 0, 0, 0, 0, 0, 0, 0, 0,0,0, 0, 0, 0, 0, 0, 0, 0, 0, 0, True)
                        cursor.commit()

    def load_boxscores():
        connection = pyodbc.connect('DRIVER={SQL Server Native Client 11.0};server=(localdb)\\mssqllocaldb;database=Eddie;')
        cursor = connection.cursor()
        for season in SEASONS:
            seasonId = season[0]
            cursor.execute("SELECT GameId, GameKey, SeasonId, HomeTeam, AwayTeam FROM Games WHERE GameKey != '' AND SeasonId = ?", seasonId)
            for game in cursor.fetchall():

                gameId = game[0]
                key = game[1]
                homeTeam = game[3]
                awayTeam = game[4]
                print(f'{key} in season: {seasonId}')
                dataParser.load_boxscore(gameId, key, homeTeam, awayTeam)

    def build_boxscore_snapshot():
        connection = pyodbc.connect('DRIVER={SQL Server Native Client 11.0};server=(localdb)\\mssqllocaldb;database=Eddie;')
        cursor = connection.cursor()
        cursor.execute("SELECT GameId, SeasonId, GameDate FROM Games WHERE GameKey != '' ORDER BY GameDate DESC")
        for game in cursor.fetchall():
            gameId = game[0]
            seasonId = game[1]
            gameDate = game[2]
            cursor.execute("SELECT [PlayerId],[TeamId],[Starter],[Minutes],[Points],[FGM],[FGA],[FGPer],[ThreePointMade],[ThreePointAttempted],[ThreePointPercent],[FreeThrowMade],[FreeThrowAttempted],[FreeThrowPercentage],[OffensiveRebound],[DefensiveRebound],[Assist],[TurnOver],[Steal],[Block],[PersonalFoul],[PlusMinus],[Inactive] FROM [Eddie].[dbo].[BoxScore] WHERE GameId = ?", gameId)
            for boxScore in cursor.fetchall():
                playerId = boxScore[0]
                cursor.execute("SELECT * FROM SeasonBasicStats WHERE SeasonId = ? AND PlayerId = ? ORDER BY Id DESC", seasonId, playerId)
                for seasonStat in cursor.fetchmany(1):
                    gamesStarted = seasonStat[9]
                    if boxScore[2] == 1:
                        gamesStarted = gamesStarted -1

                    minutes = seasonStat[10] - boxScore[3]
                    gamesPlayed = seasonStat[8]
                    if boxScore[3] > 0:
                        gamesPlayed = gamesPlayed - 1

                    points = seasonStat[11] - boxScore[4]
                    fgm = seasonStat[12] - boxScore[5]
                    fga = seasonStat[13] - boxScore[6]
                    threeMade = seasonStat[15] - boxScore[8]
                    threeAtt = seasonStat[16] - boxScore[9]
                    ftm = seasonStat[18] - boxScore[11]
                    fta = seasonStat[19] - boxScore[12]
                    oReb = seasonStat[21] - boxScore[14]
                    dReb = seasonStat[22] - boxScore[15]
                    ast = seasonStat[23] - boxScore[16]
                    to = seasonStat[24] - boxScore[17]
                    steal = seasonStat[25] - boxScore[18]
                    blk = seasonStat[26] - boxScore[19]
                    pf =  seasonStat[27] - boxScore[20]
                    cursor.execute("INSERT INTO SeasonBasicStats ([SeasonId],[PlayerId],[ThroughDate],[GamesPlayed],[GamesStarted],[Minutes],[Points],[FGM],[FGA],[ThreePointMade],[ThreePointAttempted],[FreeThrowMade],[FreeThrowAttempted],[OffensiveRebound],[DefensiveRebound],[Assist],[TurnOver],[Steal],[Block],[PersonalFoul],[GameId]) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", seasonId,playerId,gameDate,gamesPlayed,gamesStarted,minutes,points,fgm,fga,threeMade,threeAtt,ftm,fta,oReb,dReb,ast,to,steal,blk,pf,gameId)
                    cursor.commit()
                    if playerId == 2544:
                        print(f'Season: {seasonId} Game: {gameId} Player {playerId} Min: {minutes} Points: {points} FG: {fga}/{fgm}')

    def build_boxscore_snapshot_career():
        connection = pyodbc.connect('DRIVER={SQL Server Native Client 11.0};server=(localdb)\\mssqllocaldb;database=Eddie;')
        cursor = connection.cursor()
        cursor.execute("SELECT GameId, SeasonId, GameDate FROM Games ORDER BY GameDate DESC")
        for game in cursor.fetchall():
            gameId = game[0]
            seasonId = game[1]
            gameDate = game[2]
            cursor.execute("SELECT [PlayerId],[TeamId],[Starter],[Minutes],[Points],[FGM],[FGA],[FGPer],[ThreePointMade],[ThreePointAttempted],[ThreePointPercent],[FreeThrowMade],[FreeThrowAttempted],[FreeThrowPercentage],[OffensiveRebound],[DefensiveRebound],[Assist],[TurnOver],[Steal],[Block],[PersonalFoul],[PlusMinus],[Inactive] FROM [Eddie].[dbo].[BoxScore] WHERE GameId = ?", gameId)
            for boxScore in cursor.fetchall():
                playerId = boxScore[0]
                cursor.execute("SELECT * FROM CareerBasicStats WHERE PlayerId = ? ORDER BY Id DESC", playerId)
                for seasonStat in cursor.fetchmany(1):
                    gamesStarted = seasonStat[5]
                    if boxScore[2] == 1:
                        gamesStarted = gamesStarted -1

                    minutes = seasonStat[6] - boxScore[3]
                    gamesPlayed = seasonStat[4]
                    if boxScore[3] > 0:
                        gamesPlayed = gamesPlayed - 1

                    points = seasonStat[7] - boxScore[4]
                    fgm = seasonStat[8] - boxScore[5]
                    fga = seasonStat[9] - boxScore[6]
                    threeMade = seasonStat[11] - boxScore[8]
                    threeAtt = seasonStat[12] - boxScore[9]
                    ftm = seasonStat[14] - boxScore[11]
                    fta = seasonStat[15] - boxScore[12]
                    oReb = seasonStat[17] - boxScore[14]
                    dReb = seasonStat[18] - boxScore[15]
                    ast = seasonStat[19] - boxScore[16]
                    to = seasonStat[20] - boxScore[17]
                    steal = seasonStat[21] - boxScore[18]
                    blk = seasonStat[22] - boxScore[19]
                    pf =  seasonStat[23] - boxScore[20]
                    cursor.execute("INSERT INTO CareerBasicStats ([PlayerId],[ThroughDate],[GamesPlayed],[GamesStarted],[Minutes],[Points],[FGM],[FGA],[ThreePointMade],[ThreePointAttempted],[FreeThrowMade],[FreeThrowAttempted],[OffensiveRebound],[DefensiveRebound],[Assist],[TurnOver],[Steal],[Block],[PersonalFoul],[GameId]) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", playerId,gameDate,gamesPlayed,gamesStarted,minutes,points,fgm,fga,threeMade,threeAtt,ftm,fta,oReb,dReb,ast,to,steal,blk,pf,gameId)
                    cursor.commit()
                    if playerId == 2544:
                        print(f'Season: {seasonId} Game: {gameId} Player {playerId} Min: {minutes} Points: {points} FG: {fga}/{fgm}')

    def load_basic_snapshot_prediction():
        connection = pyodbc.connect('DRIVER={SQL Server Native Client 11.0};server=(localdb)\\mssqllocaldb;database=Eddie;')
        cursor = connection.cursor()
        cursor.execute("SELECT GameId, SeasonId, HomeTeam, HomeScore, AwayTeam, AwayScore, TotalPlayerMinutes, HomeWins, HomeLosses, AwayWins, AwayLosses FROM Games WHERE GameId < 22584 AND GameId > 22576") #avoid games from first two seasons of data, games that haven't happened yet, or games from the 2020 bubble
        for game in cursor.fetchall():
            gameId = game[0]
            seasonId = game[1]
            homeTeam = game[2]
            homeScore = game[3]
            awayTeam = game[4]
            awayScore = game[5]
            gameMinutes = game[6]
            homeWins = game[7]
            homeLosses = game[8]
            homeGamesPlayed = homeWins + homeLosses
            awayWins = game[9]
            awayLosses = game[10]
            awayGamesPlayed = awayWins + awayLosses
            totalScore = homeScore + awayScore
            inactiveHomePlayers = 0
            inactiveAwayPlayers = 0
            
            seasonHomeGamesPlayed = 0
            seasonHomeGamesStarted = 0
            seasonHomeMinutesPlayed = 0
            seasonHomePoints = 0
            seasonHomeFGM = 0
            seasonHomeFGA = 0
            seasonHome3PM = 0
            seasonHome3PA = 0
            seasonHomeFTM = 0
            seasonHomeFTA = 0
            seasonHomeOReb = 0
            seasonHomeDReb = 0
            seasonHomeAst = 0
            seasonHomeTO = 0
            seasonHomeStl = 0
            seasonHomeBlock = 0
            seasonHomePF = 0
            inactiveSeasonHomeGamesPlayed = 0
            inactiveSeasonHomeGamesStarted = 0
            inactiveSeasonHomeMinutesPlayed = 0
            inactiveSeasonHomePoints = 0
            inactiveSeasonHomeFGM = 0
            inactiveSeasonHomeFGA = 0
            inactiveSeasonHome3PM = 0
            inactiveSeasonHome3PA = 0
            inactiveSeasonHomeFTM = 0
            inactiveSeasonHomeFTA = 0
            inactiveSeasonHomeOReb = 0
            inactiveSeasonHomeDReb = 0
            inactiveSeasonHomeAst = 0
            inactiveSeasonHomeTO = 0
            inactiveSeasonHomeStl = 0
            inactiveSeasonHomeBlock = 0
            inactiveSeasonHomePF = 0

            careerHomeGamesPlayed = 0
            careerHomeGamesStarted = 0
            careerHomeMinutesPlayed = 0
            careerHomePoints = 0
            careerHomeFGM = 0
            careerHomeFGA = 0
            careerHome3PM = 0
            careerHome3PA = 0
            careerHomeFTM = 0
            careerHomeFTA = 0
            careerHomeOReb = 0
            careerHomeDReb = 0
            careerHomeAst = 0
            careerHomeTO = 0
            careerHomeStl = 0
            careerHomeBlock = 0
            careerHomePF = 0
            inactiveCareerHomeGamesPlayed = 0
            inactiveCareerHomeGamesStarted = 0
            inactiveCareerHomeMinutesPlayed = 0
            inactiveCareerHomePoints = 0
            inactiveCareerHomeFGM = 0
            inactiveCareerHomeFGA = 0
            inactiveCareerHome3PM = 0
            inactiveCareerHome3PA = 0
            inactiveCareerHomeFTM = 0
            inactiveCareerHomeFTA = 0
            inactiveCareerHomeOReb = 0
            inactiveCareerHomeDReb = 0
            inactiveCareerHomeAst = 0
            inactiveCareerHomeTO = 0
            inactiveCareerHomeStl = 0
            inactiveCareerHomeBlock = 0
            inactiveCareerHomePF = 0

            seasonAwayGamesPlayed = 0
            seasonAwayGamesStarted = 0
            seasonAwayMinutesPlayed = 0
            seasonAwayPoints = 0
            seasonAwayFGM = 0
            seasonAwayFGA = 0
            seasonAway3PM = 0
            seasonAway3PA = 0
            seasonAwayFTM = 0
            seasonAwayFTA = 0
            seasonAwayOReb = 0
            seasonAwayDReb = 0
            seasonAwayAst = 0
            seasonAwayTO = 0
            seasonAwayStl = 0
            seasonAwayBlock = 0
            seasonAwayPF = 0
            inactiveSeasonAwayGamesPlayed = 0
            inactiveSeasonAwayGamesStarted = 0
            inactiveSeasonAwayMinutesPlayed = 0
            inactiveSeasonAwayPoints = 0
            inactiveSeasonAwayFGM = 0
            inactiveSeasonAwayFGA = 0
            inactiveSeasonAway3PM = 0
            inactiveSeasonAway3PA = 0
            inactiveSeasonAwayFTM = 0
            inactiveSeasonAwayFTA = 0
            inactiveSeasonAwayOReb = 0
            inactiveSeasonAwayDReb = 0
            inactiveSeasonAwayAst = 0
            inactiveSeasonAwayTO = 0
            inactiveSeasonAwayStl = 0
            inactiveSeasonAwayBlock = 0
            inactiveSeasonAwayPF = 0
            careerAwayGamesPlayed = 0
            careerAwayGamesStarted = 0
            careerAwayMinutesPlayed = 0
            careerAwayPoints = 0
            careerAwayFGM = 0
            careerAwayFGA = 0
            careerAway3PM = 0
            careerAway3PA = 0
            careerAwayFTM = 0
            careerAwayFTA = 0
            careerAwayOReb = 0
            careerAwayDReb = 0
            careerAwayAst = 0
            careerAwayTO = 0
            careerAwayStl = 0
            careerAwayBlock = 0
            careerAwayPF = 0
            inactiveCareerAwayGamesPlayed = 0
            inactiveCareerAwayGamesStarted = 0
            inactiveCareerAwayMinutesPlayed = 0
            inactiveCareerAwayPoints = 0
            inactiveCareerAwayFGM = 0
            inactiveCareerAwayFGA = 0
            inactiveCareerAway3PM = 0
            inactiveCareerAway3PA = 0
            inactiveCareerAwayFTM = 0
            inactiveCareerAwayFTA = 0
            inactiveCareerAwayOReb = 0
            inactiveCareerAwayDReb = 0
            inactiveCareerAwayAst = 0
            inactiveCareerAwayTO = 0
            inactiveCareerAwayStl = 0
            inactiveCareerAwayBlock = 0
            inactiveCareerAwayPF = 0
            # cursor.execute("SELECT PlayerId, Minutes, Starter, Inactive FROM BoxScore WHERE GameId = ? AND TeamId = ?", gameId, homeTeam)
            cursor.execute("SELECT PlayerId, Inactive FROM Rosters WHERE GameId = ? AND Team = ?", gameId, homeTeam)
            for boxScoreHome in cursor.fetchall():
                playerId = boxScoreHome[0]
                # minutes = boxScoreHome[1]
                # starter = boxScoreHome[2]
                inactive = boxScoreHome[1]
                if inactive == True:                    
                    inactiveHomePlayers += 1
                minuteRatio = 1#minutes/gameMinutes
                cursor.execute("SELECT * FROM SeasonBasicStats WHERE GameId = ? AND PlayerId = ?", gameId, playerId)
                for seasonStat in cursor.fetchmany(1):
                    if inactive == True:
                        inactiveSeasonHomeGamesPlayed += seasonStat[8] * homeGamesPlayed
                        inactiveSeasonHomeGamesStarted  += seasonStat[9] 
                        inactiveSeasonHomeMinutesPlayed  += seasonStat[10] 
                        inactiveSeasonHomePoints += seasonStat[11] 
                        inactiveSeasonHomeFGM += seasonStat[12] 
                        inactiveSeasonHomeFGA += seasonStat[13] 
                        inactiveSeasonHome3PM += seasonStat[15] 
                        inactiveSeasonHome3PA += seasonStat[16] 
                        inactiveSeasonHomeFTM += seasonStat[18] 
                        inactiveSeasonHomeFTA += seasonStat[19] 
                        inactiveSeasonHomeOReb += seasonStat[21]
                        inactiveSeasonHomeDReb += seasonStat[22] 
                        inactiveSeasonHomeAst += seasonStat[23] 
                        inactiveSeasonHomeTO += seasonStat[24] 
                        inactiveSeasonHomeStl += seasonStat[25] 
                        inactiveSeasonHomeBlock += seasonStat[26] 
                        inactiveSeasonHomePF += seasonStat[27] 
                    else:
                        seasonHomeGamesPlayed += seasonStat[8] * minuteRatio  * homeGamesPlayed
                        seasonHomeGamesStarted  += seasonStat[9] * minuteRatio
                        seasonHomeMinutesPlayed  += seasonStat[10] * minuteRatio
                        seasonHomePoints += seasonStat[11] * minuteRatio
                        seasonHomeFGM += seasonStat[12] * minuteRatio
                        seasonHomeFGA += seasonStat[13] * minuteRatio
                        seasonHome3PM += seasonStat[15] * minuteRatio
                        seasonHome3PA += seasonStat[16] * minuteRatio
                        seasonHomeFTM += seasonStat[18] * minuteRatio
                        seasonHomeFTA += seasonStat[19] * minuteRatio
                        seasonHomeOReb += seasonStat[21] * minuteRatio
                        seasonHomeDReb += seasonStat[22] * minuteRatio
                        seasonHomeAst += seasonStat[23] * minuteRatio
                        seasonHomeTO += seasonStat[24] * minuteRatio
                        seasonHomeStl += seasonStat[25] * minuteRatio
                        seasonHomeBlock += seasonStat[26] * minuteRatio
                        seasonHomePF += seasonStat[27] * minuteRatio

                cursor.execute("SELECT * FROM CareerBasicStats WHERE GameId = ? AND PlayerId = ?", gameId, playerId)
                for careerStat in cursor.fetchmany(1):
                    if inactive == True:
                        inactiveCareerHomeGamesPlayed += careerStat[4] 
                        inactiveCareerHomeGamesStarted  += careerStat[5]
                        inactiveCareerHomeMinutesPlayed  += careerStat[6] 
                        inactiveCareerHomePoints += careerStat[7] 
                        inactiveCareerHomeFGM += careerStat[8] 
                        inactiveCareerHomeFGA += careerStat[9] 
                        inactiveCareerHome3PM += careerStat[11] 
                        inactiveCareerHome3PA += careerStat[12] 
                        inactiveCareerHomeFTM += careerStat[14] 
                        inactiveCareerHomeFTA += careerStat[15] 
                        inactiveCareerHomeOReb += careerStat[17] 
                        inactiveCareerHomeDReb += careerStat[18]
                        inactiveCareerHomeAst += careerStat[19] 
                        inactiveCareerHomeTO += careerStat[20] 
                        inactiveCareerHomeStl += careerStat[21] 
                        inactiveCareerHomeBlock += careerStat[22] 
                        inactiveCareerHomePF += careerStat[23] 
                    else:
                        careerHomeGamesPlayed += careerStat[4]  * minuteRatio
                        careerHomeGamesStarted  += careerStat[5] * minuteRatio
                        careerHomeMinutesPlayed  += careerStat[6]  * minuteRatio
                        careerHomePoints += careerStat[7]  * minuteRatio
                        careerHomeFGM += careerStat[8]  * minuteRatio
                        careerHomeFGA += careerStat[9]  * minuteRatio
                        careerHome3PM += careerStat[11]  * minuteRatio
                        careerHome3PA += careerStat[12]  * minuteRatio
                        careerHomeFTM += careerStat[14]  * minuteRatio
                        careerHomeFTA += careerStat[15]  * minuteRatio
                        careerHomeOReb += careerStat[17]  * minuteRatio
                        careerHomeDReb += careerStat[18] * minuteRatio
                        careerHomeAst += careerStat[19]  * minuteRatio
                        careerHomeTO += careerStat[20]  * minuteRatio
                        careerHomeStl += careerStat[21]  * minuteRatio
                        careerHomeBlock += careerStat[22]  * minuteRatio
                        careerHomePF += careerStat[23]  * minuteRatio


            cursor.execute("SELECT PlayerId, Inactive FROM Rosters WHERE GameId = ? AND Team = ?", gameId, homeTeam)
            for boxScoreAway in cursor.fetchall():
                playerId = boxScoreAway[0]
                # minutes = boxScoreAway[1]
                # starter = boxScoreAway[2]
                inactive = boxScoreAway[1]
                if inactive == True:                    
                    inactiveAwayPlayers += 1
                minuteRatio = 1 #minutes/gameMinutes
                cursor.execute("SELECT * FROM SeasonBasicStats WHERE GameId = ? AND PlayerId = ?", gameId, playerId)
                for seasonStat in cursor.fetchmany(1):
                    if inactive == True:
                        inactiveSeasonAwayGamesPlayed += seasonStat[8] * awayGamesPlayed
                        inactiveSeasonAwayGamesStarted  += seasonStat[9] 
                        inactiveSeasonAwayMinutesPlayed  += seasonStat[10] 
                        inactiveSeasonAwayPoints += seasonStat[11] 
                        inactiveSeasonAwayFGM += seasonStat[12] 
                        inactiveSeasonAwayFGA += seasonStat[13] 
                        inactiveSeasonAway3PM += seasonStat[15] 
                        inactiveSeasonAway3PA += seasonStat[16] 
                        inactiveSeasonAwayFTM += seasonStat[18] 
                        inactiveSeasonAwayFTA += seasonStat[19] 
                        inactiveSeasonAwayOReb += seasonStat[21]
                        inactiveSeasonAwayDReb += seasonStat[22] 
                        inactiveSeasonAwayAst += seasonStat[23] 
                        inactiveSeasonAwayTO += seasonStat[24] 
                        inactiveSeasonAwayStl += seasonStat[25] 
                        inactiveSeasonAwayBlock += seasonStat[26] 
                        inactiveSeasonAwayPF += seasonStat[27] 
                    else:
                        seasonAwayGamesPlayed += seasonStat[8] * minuteRatio  * awayGamesPlayed
                        seasonAwayGamesStarted  += seasonStat[9] * minuteRatio
                        seasonAwayMinutesPlayed  += seasonStat[10] * minuteRatio
                        seasonAwayPoints += seasonStat[11] * minuteRatio
                        seasonAwayFGM += seasonStat[12] * minuteRatio
                        seasonAwayFGA += seasonStat[13] * minuteRatio
                        seasonAway3PM += seasonStat[15] * minuteRatio
                        seasonAway3PA += seasonStat[16] * minuteRatio
                        seasonAwayFTM += seasonStat[18] * minuteRatio
                        seasonAwayFTA += seasonStat[19] * minuteRatio
                        seasonAwayOReb += seasonStat[21] * minuteRatio
                        seasonAwayDReb += seasonStat[22] * minuteRatio
                        seasonAwayAst += seasonStat[23] * minuteRatio
                        seasonAwayTO += seasonStat[24] * minuteRatio
                        seasonAwayStl += seasonStat[25] * minuteRatio
                        seasonAwayBlock += seasonStat[26] * minuteRatio
                        seasonAwayPF += seasonStat[27] * minuteRatio

                cursor.execute("SELECT * FROM CareerBasicStats WHERE GameId = ? AND PlayerId = ?", gameId, playerId)
                for careerStat in cursor.fetchmany(1):
                    if inactive == True:
                        inactiveCareerAwayGamesPlayed += careerStat[4] 
                        inactiveCareerAwayGamesStarted  += careerStat[5]
                        inactiveCareerAwayMinutesPlayed  += careerStat[6] 
                        inactiveCareerAwayPoints += careerStat[7] 
                        inactiveCareerAwayFGM += careerStat[8] 
                        inactiveCareerAwayFGA += careerStat[9] 
                        inactiveCareerAway3PM += careerStat[11] 
                        inactiveCareerAway3PA += careerStat[12] 
                        inactiveCareerAwayFTM += careerStat[14] 
                        inactiveCareerAwayFTA += careerStat[15] 
                        inactiveCareerAwayOReb += careerStat[17] 
                        inactiveCareerAwayDReb += careerStat[18]
                        inactiveCareerAwayAst += careerStat[19] 
                        inactiveCareerAwayTO += careerStat[20] 
                        inactiveCareerAwayStl += careerStat[21] 
                        inactiveCareerAwayBlock += careerStat[22] 
                        inactiveCareerAwayPF += careerStat[23] 
                    else:
                        careerAwayGamesPlayed += careerStat[4]  * minuteRatio
                        careerAwayGamesStarted  += careerStat[5] * minuteRatio
                        careerAwayMinutesPlayed  += careerStat[6]  * minuteRatio
                        careerAwayPoints += careerStat[7]  * minuteRatio
                        careerAwayFGM += careerStat[8]  * minuteRatio
                        careerAwayFGA += careerStat[9]  * minuteRatio
                        careerAway3PM += careerStat[11]  * minuteRatio
                        careerAway3PA += careerStat[12]  * minuteRatio
                        careerAwayFTM += careerStat[14]  * minuteRatio
                        careerAwayFTA += careerStat[15]  * minuteRatio
                        careerAwayOReb += careerStat[17]  * minuteRatio
                        careerAwayDReb += careerStat[18] * minuteRatio
                        careerAwayAst += careerStat[19]  * minuteRatio
                        careerAwayTO += careerStat[20]  * minuteRatio
                        careerAwayStl += careerStat[21]  * minuteRatio
                        careerAwayBlock += careerStat[22]  * minuteRatio
                        careerAwayPF += careerStat[23]  * minuteRatio

            gameInfo = np.array([gameId, homeScore,awayScore,homeWins,homeLosses,inactiveHomePlayers,awayWins,awayLosses,inactiveAwayPlayers])

            homeSeasonSnapshot = np.array([seasonHomeGamesPlayed,seasonHomeGamesStarted,seasonHomeMinutesPlayed,seasonHomePoints,seasonHomeFGM,seasonHomeFGA,seasonHome3PM,seasonHome3PA,seasonHomeFTM,seasonHomeFTA,seasonHomeOReb,seasonHomeDReb,seasonHomeAst,seasonHomeTO,seasonHomeStl,seasonHomeBlock,seasonHomePF])
            inactiveHomeSeasonSnapshot = np.array([inactiveSeasonHomeGamesPlayed,inactiveSeasonHomeGamesStarted,inactiveSeasonHomeMinutesPlayed,inactiveSeasonHomePoints,inactiveSeasonHomeFGM,inactiveSeasonHomeFGA,inactiveSeasonHome3PM,inactiveSeasonHome3PA,inactiveSeasonHomeFTM,inactiveSeasonHomeFTA,inactiveSeasonHomeOReb,inactiveSeasonHomeDReb,inactiveSeasonHomeAst,inactiveSeasonHomeTO,inactiveSeasonHomeStl,inactiveSeasonHomeBlock,inactiveSeasonHomePF])
            homeCareerSnapshot = np.array([careerHomeGamesPlayed,careerHomeGamesStarted,careerHomeMinutesPlayed,careerHomePoints,careerHomeFGM,careerHomeFGA,careerHome3PM,careerHome3PA,careerHomeFTM,careerHomeFTA,careerHomeOReb,careerHomeDReb,careerHomeAst,careerHomeTO,careerHomeStl,careerHomeBlock,careerHomePF])
            homeInactiveCareerSnapshot = np.array([inactiveCareerHomeGamesPlayed,inactiveCareerHomeGamesStarted,inactiveCareerHomeMinutesPlayed,inactiveCareerHomePoints,inactiveCareerHomeFGM,inactiveCareerHomeFGA,inactiveCareerHome3PM,inactiveCareerHome3PA,inactiveCareerHomeFTM,inactiveCareerHomeFTA,inactiveCareerHomeOReb,inactiveCareerHomeDReb,inactiveCareerHomeAst,inactiveCareerHomeTO,inactiveCareerHomeStl,inactiveCareerHomeBlock,inactiveCareerHomePF])
            
            awaySeasonSnapshot = np.array([seasonAwayGamesPlayed,seasonAwayGamesStarted,seasonAwayMinutesPlayed,seasonAwayPoints,seasonAwayFGM,seasonAwayFGA,seasonAway3PM,seasonAway3PA,seasonAwayFTM,seasonAwayFTA,seasonAwayOReb,seasonAwayDReb,seasonAwayAst,seasonAwayTO,seasonAwayStl,seasonAwayBlock,seasonAwayPF])
            inactiveAwaySeasonSnapshot = np.array([inactiveSeasonAwayGamesPlayed,inactiveSeasonAwayGamesStarted,inactiveSeasonAwayMinutesPlayed,inactiveSeasonAwayPoints,inactiveSeasonAwayFGM,inactiveSeasonAwayFGA,inactiveSeasonAway3PM,inactiveSeasonAway3PA,inactiveSeasonAwayFTM,inactiveSeasonAwayFTA,inactiveSeasonAwayOReb,inactiveSeasonAwayDReb,inactiveSeasonAwayAst,inactiveSeasonAwayTO,inactiveSeasonAwayStl,inactiveSeasonAwayBlock,inactiveSeasonAwayPF])
            awayCareerSnapshot = np.array([careerAwayGamesPlayed,careerAwayGamesStarted,careerAwayMinutesPlayed,careerAwayPoints,careerAwayFGM,careerAwayFGA,careerAway3PM,careerAway3PA,careerAwayFTM,careerAwayFTA,careerAwayOReb,careerAwayDReb,careerAwayAst,careerAwayTO,careerAwayStl,careerAwayBlock,careerAwayPF])
            awayInactiveCareerSnapshot = np.array([inactiveCareerAwayGamesPlayed,inactiveCareerAwayGamesStarted,inactiveCareerAwayMinutesPlayed,inactiveCareerAwayPoints,inactiveCareerAwayFGM,inactiveCareerAwayFGA,inactiveCareerAway3PM,inactiveCareerAway3PA,inactiveCareerAwayFTM,inactiveCareerAwayFTA,inactiveCareerAwayOReb,inactiveCareerAwayDReb,inactiveCareerAwayAst,inactiveCareerAwayTO,inactiveCareerAwayStl,inactiveCareerAwayBlock,inactiveCareerAwayPF])
            
            if homeGamesPlayed > 0:
                homeSeasonSnapshot = homeSeasonSnapshot / homeGamesPlayed
                inactiveHomeSeasonSnapshot = inactiveHomeSeasonSnapshot / homeGamesPlayed

            if awayGamesPlayed > 0:
                awaySeasonSnapshot = awaySeasonSnapshot / awayGamesPlayed
                inactiveAwaySeasonSnapshot = inactiveAwaySeasonSnapshot / awayGamesPlayed


            dataLoad = np.concatenate([gameInfo,homeSeasonSnapshot,inactiveHomeSeasonSnapshot,homeCareerSnapshot,homeInactiveCareerSnapshot,awaySeasonSnapshot,inactiveAwaySeasonSnapshot,awayCareerSnapshot,awayInactiveCareerSnapshot])
            insertStatement = f'INSERT INTO BasicPredictions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
            
            print(gameId)
            cursor.execute(insertStatement,dataLoad.tolist())
            cursor.commit()

    def load_basic_snapshot(gameId):
        connection = pyodbc.connect('DRIVER={SQL Server Native Client 11.0};server=(localdb)\\mssqllocaldb;database=Eddie;')
        cursor = connection.cursor()
        # cursor.execute("SELECT GameId, SeasonId, HomeTeam, HomeScore, AwayTeam, AwayScore, TotalPlayerMinutes, HomeWins, HomeLosses, AwayWins, AwayLosses,AwayDistanceTraveled FROM Games WHERE SeasonId > 2 AND GameKey != '' AND (GameId < 21103 OR GameId > 21191)") #avoid games from first two seasons of data, games that haven't happened yet, or games from the 2020 bubble
        cursor.execute("SELECT GameId, SeasonId, HomeTeam, HomeScore, AwayTeam, AwayScore, TotalPlayerMinutes, HomeWins, HomeLosses, AwayWins, AwayLosses, AwayDistanceTraveled FROM Games WHERE GameId = ?", gameId)
        for game in cursor.fetchall():
            gameId = game[0]
            seasonId = game[1]
            homeTeam = game[2]
            homeScore = game[3]
            awayTeam = game[4]
            awayScore = game[5]
            gameMinutes = game[6]
            homeWins = game[7]
            homeLosses = game[8]
            homeGamesPlayed = homeWins + homeLosses
            awayWins = game[9]
            awayLosses = game[10]
            distance = game[11]
            awayGamesPlayed = awayWins + awayLosses
            totalScore = homeScore + awayScore
            inactiveHomePlayers = 0
            inactiveAwayPlayers = 0
            
            seasonHomeGamesPlayed = 0
            seasonHomeGamesStarted = 0
            seasonHomeMinutesPlayed = 0
            seasonHomePoints = 0
            seasonHomeFGM = 0
            seasonHomeFGA = 0
            seasonHome3PM = 0
            seasonHome3PA = 0
            seasonHomeFTM = 0
            seasonHomeFTA = 0
            seasonHomeOReb = 0
            seasonHomeDReb = 0
            seasonHomeAst = 0
            seasonHomeTO = 0
            seasonHomeStl = 0
            seasonHomeBlock = 0
            seasonHomePF = 0
            inactiveSeasonHomeGamesPlayed = 0
            inactiveSeasonHomeGamesStarted = 0
            inactiveSeasonHomeMinutesPlayed = 0
            inactiveSeasonHomePoints = 0
            inactiveSeasonHomeFGM = 0
            inactiveSeasonHomeFGA = 0
            inactiveSeasonHome3PM = 0
            inactiveSeasonHome3PA = 0
            inactiveSeasonHomeFTM = 0
            inactiveSeasonHomeFTA = 0
            inactiveSeasonHomeOReb = 0
            inactiveSeasonHomeDReb = 0
            inactiveSeasonHomeAst = 0
            inactiveSeasonHomeTO = 0
            inactiveSeasonHomeStl = 0
            inactiveSeasonHomeBlock = 0
            inactiveSeasonHomePF = 0

            careerHomeGamesPlayed = 0
            careerHomeGamesStarted = 0
            careerHomeMinutesPlayed = 0
            careerHomePoints = 0
            careerHomeFGM = 0
            careerHomeFGA = 0
            careerHome3PM = 0
            careerHome3PA = 0
            careerHomeFTM = 0
            careerHomeFTA = 0
            careerHomeOReb = 0
            careerHomeDReb = 0
            careerHomeAst = 0
            careerHomeTO = 0
            careerHomeStl = 0
            careerHomeBlock = 0
            careerHomePF = 0
            inactiveCareerHomeGamesPlayed = 0
            inactiveCareerHomeGamesStarted = 0
            inactiveCareerHomeMinutesPlayed = 0
            inactiveCareerHomePoints = 0
            inactiveCareerHomeFGM = 0
            inactiveCareerHomeFGA = 0
            inactiveCareerHome3PM = 0
            inactiveCareerHome3PA = 0
            inactiveCareerHomeFTM = 0
            inactiveCareerHomeFTA = 0
            inactiveCareerHomeOReb = 0
            inactiveCareerHomeDReb = 0
            inactiveCareerHomeAst = 0
            inactiveCareerHomeTO = 0
            inactiveCareerHomeStl = 0
            inactiveCareerHomeBlock = 0
            inactiveCareerHomePF = 0

            seasonAwayGamesPlayed = 0
            seasonAwayGamesStarted = 0
            seasonAwayMinutesPlayed = 0
            seasonAwayPoints = 0
            seasonAwayFGM = 0
            seasonAwayFGA = 0
            seasonAway3PM = 0
            seasonAway3PA = 0
            seasonAwayFTM = 0
            seasonAwayFTA = 0
            seasonAwayOReb = 0
            seasonAwayDReb = 0
            seasonAwayAst = 0
            seasonAwayTO = 0
            seasonAwayStl = 0
            seasonAwayBlock = 0
            seasonAwayPF = 0
            inactiveSeasonAwayGamesPlayed = 0
            inactiveSeasonAwayGamesStarted = 0
            inactiveSeasonAwayMinutesPlayed = 0
            inactiveSeasonAwayPoints = 0
            inactiveSeasonAwayFGM = 0
            inactiveSeasonAwayFGA = 0
            inactiveSeasonAway3PM = 0
            inactiveSeasonAway3PA = 0
            inactiveSeasonAwayFTM = 0
            inactiveSeasonAwayFTA = 0
            inactiveSeasonAwayOReb = 0
            inactiveSeasonAwayDReb = 0
            inactiveSeasonAwayAst = 0
            inactiveSeasonAwayTO = 0
            inactiveSeasonAwayStl = 0
            inactiveSeasonAwayBlock = 0
            inactiveSeasonAwayPF = 0
            careerAwayGamesPlayed = 0
            careerAwayGamesStarted = 0
            careerAwayMinutesPlayed = 0
            careerAwayPoints = 0
            careerAwayFGM = 0
            careerAwayFGA = 0
            careerAway3PM = 0
            careerAway3PA = 0
            careerAwayFTM = 0
            careerAwayFTA = 0
            careerAwayOReb = 0
            careerAwayDReb = 0
            careerAwayAst = 0
            careerAwayTO = 0
            careerAwayStl = 0
            careerAwayBlock = 0
            careerAwayPF = 0
            inactiveCareerAwayGamesPlayed = 0
            inactiveCareerAwayGamesStarted = 0
            inactiveCareerAwayMinutesPlayed = 0
            inactiveCareerAwayPoints = 0
            inactiveCareerAwayFGM = 0
            inactiveCareerAwayFGA = 0
            inactiveCareerAway3PM = 0
            inactiveCareerAway3PA = 0
            inactiveCareerAwayFTM = 0
            inactiveCareerAwayFTA = 0
            inactiveCareerAwayOReb = 0
            inactiveCareerAwayDReb = 0
            inactiveCareerAwayAst = 0
            inactiveCareerAwayTO = 0
            inactiveCareerAwayStl = 0
            inactiveCareerAwayBlock = 0
            inactiveCareerAwayPF = 0
            cursor.execute("SELECT PlayerId, Minutes, Starter, Inactive FROM BoxScore WHERE GameId = ? AND TeamId = ?", gameId, homeTeam)
            for boxScoreHome in cursor.fetchall():
                playerId = boxScoreHome[0]
                # minutes = boxScoreHome[1]
                # starter = boxScoreHome[2]
                inactive = boxScoreHome[1]
                if inactive == True:                    
                    inactiveHomePlayers += 1
                minuteRatio = 1#minutes/gameMinutes
                cursor.execute("SELECT * FROM SeasonBasicStats WHERE GameId = ? AND PlayerId = ?", gameId, playerId)
                for seasonStat in cursor.fetchmany(1):
                    if inactive == True:
                        inactiveSeasonHomeGamesPlayed += seasonStat[8] * homeGamesPlayed
                        inactiveSeasonHomeGamesStarted  += seasonStat[9] 
                        inactiveSeasonHomeMinutesPlayed  += seasonStat[10] 
                        inactiveSeasonHomePoints += seasonStat[11] 
                        inactiveSeasonHomeFGM += seasonStat[12] 
                        inactiveSeasonHomeFGA += seasonStat[13] 
                        inactiveSeasonHome3PM += seasonStat[15] 
                        inactiveSeasonHome3PA += seasonStat[16] 
                        inactiveSeasonHomeFTM += seasonStat[18] 
                        inactiveSeasonHomeFTA += seasonStat[19] 
                        inactiveSeasonHomeOReb += seasonStat[21]
                        inactiveSeasonHomeDReb += seasonStat[22] 
                        inactiveSeasonHomeAst += seasonStat[23] 
                        inactiveSeasonHomeTO += seasonStat[24] 
                        inactiveSeasonHomeStl += seasonStat[25] 
                        inactiveSeasonHomeBlock += seasonStat[26] 
                        inactiveSeasonHomePF += seasonStat[27] 
                    else:
                        seasonHomeGamesPlayed += seasonStat[8] * minuteRatio  * homeGamesPlayed
                        seasonHomeGamesStarted  += seasonStat[9] * minuteRatio
                        seasonHomeMinutesPlayed  += seasonStat[10] * minuteRatio
                        seasonHomePoints += seasonStat[11] * minuteRatio
                        seasonHomeFGM += seasonStat[12] * minuteRatio
                        seasonHomeFGA += seasonStat[13] * minuteRatio
                        seasonHome3PM += seasonStat[15] * minuteRatio
                        seasonHome3PA += seasonStat[16] * minuteRatio
                        seasonHomeFTM += seasonStat[18] * minuteRatio
                        seasonHomeFTA += seasonStat[19] * minuteRatio
                        seasonHomeOReb += seasonStat[21] * minuteRatio
                        seasonHomeDReb += seasonStat[22] * minuteRatio
                        seasonHomeAst += seasonStat[23] * minuteRatio
                        seasonHomeTO += seasonStat[24] * minuteRatio
                        seasonHomeStl += seasonStat[25] * minuteRatio
                        seasonHomeBlock += seasonStat[26] * minuteRatio
                        seasonHomePF += seasonStat[27] * minuteRatio

                cursor.execute("SELECT * FROM CareerBasicStats WHERE GameId = ? AND PlayerId = ?", gameId, playerId)
                for careerStat in cursor.fetchmany(1):
                    if inactive == True:
                        inactiveCareerHomeGamesPlayed += careerStat[4] 
                        inactiveCareerHomeGamesStarted  += careerStat[5]
                        inactiveCareerHomeMinutesPlayed  += careerStat[6] 
                        inactiveCareerHomePoints += careerStat[7] 
                        inactiveCareerHomeFGM += careerStat[8] 
                        inactiveCareerHomeFGA += careerStat[9] 
                        inactiveCareerHome3PM += careerStat[11] 
                        inactiveCareerHome3PA += careerStat[12] 
                        inactiveCareerHomeFTM += careerStat[14] 
                        inactiveCareerHomeFTA += careerStat[15] 
                        inactiveCareerHomeOReb += careerStat[17] 
                        inactiveCareerHomeDReb += careerStat[18]
                        inactiveCareerHomeAst += careerStat[19] 
                        inactiveCareerHomeTO += careerStat[20] 
                        inactiveCareerHomeStl += careerStat[21] 
                        inactiveCareerHomeBlock += careerStat[22] 
                        inactiveCareerHomePF += careerStat[23] 
                    else:
                        careerHomeGamesPlayed += careerStat[4]  * minuteRatio
                        careerHomeGamesStarted  += careerStat[5] * minuteRatio
                        careerHomeMinutesPlayed  += careerStat[6]  * minuteRatio
                        careerHomePoints += careerStat[7]  * minuteRatio
                        careerHomeFGM += careerStat[8]  * minuteRatio
                        careerHomeFGA += careerStat[9]  * minuteRatio
                        careerHome3PM += careerStat[11]  * minuteRatio
                        careerHome3PA += careerStat[12]  * minuteRatio
                        careerHomeFTM += careerStat[14]  * minuteRatio
                        careerHomeFTA += careerStat[15]  * minuteRatio
                        careerHomeOReb += careerStat[17]  * minuteRatio
                        careerHomeDReb += careerStat[18] * minuteRatio
                        careerHomeAst += careerStat[19]  * minuteRatio
                        careerHomeTO += careerStat[20]  * minuteRatio
                        careerHomeStl += careerStat[21]  * minuteRatio
                        careerHomeBlock += careerStat[22]  * minuteRatio
                        careerHomePF += careerStat[23]  * minuteRatio


            cursor.execute("SELECT PlayerId, Minutes, Starter, Inactive FROM BoxScore WHERE GameId = ? AND TeamId = ?", gameId, awayTeam)
            for boxScoreAway in cursor.fetchall():
                playerId = boxScoreAway[0]
                # minutes = boxScoreAway[1]
                # starter = boxScoreAway[2]
                inactive = boxScoreAway[1]
                if inactive == True:                    
                    inactiveAwayPlayers += 1
                minuteRatio = 1 #minutes/gameMinutes
                cursor.execute("SELECT * FROM SeasonBasicStats WHERE GameId = ? AND PlayerId = ?", gameId, playerId)
                for seasonStat in cursor.fetchmany(1):
                    if inactive == True:
                        inactiveSeasonAwayGamesPlayed += seasonStat[8] * awayGamesPlayed
                        inactiveSeasonAwayGamesStarted  += seasonStat[9] 
                        inactiveSeasonAwayMinutesPlayed  += seasonStat[10] 
                        inactiveSeasonAwayPoints += seasonStat[11] 
                        inactiveSeasonAwayFGM += seasonStat[12] 
                        inactiveSeasonAwayFGA += seasonStat[13] 
                        inactiveSeasonAway3PM += seasonStat[15] 
                        inactiveSeasonAway3PA += seasonStat[16] 
                        inactiveSeasonAwayFTM += seasonStat[18] 
                        inactiveSeasonAwayFTA += seasonStat[19] 
                        inactiveSeasonAwayOReb += seasonStat[21]
                        inactiveSeasonAwayDReb += seasonStat[22] 
                        inactiveSeasonAwayAst += seasonStat[23] 
                        inactiveSeasonAwayTO += seasonStat[24] 
                        inactiveSeasonAwayStl += seasonStat[25] 
                        inactiveSeasonAwayBlock += seasonStat[26] 
                        inactiveSeasonAwayPF += seasonStat[27] 
                    else:
                        seasonAwayGamesPlayed += seasonStat[8] * minuteRatio  * awayGamesPlayed
                        seasonAwayGamesStarted  += seasonStat[9] * minuteRatio
                        seasonAwayMinutesPlayed  += seasonStat[10] * minuteRatio
                        seasonAwayPoints += seasonStat[11] * minuteRatio
                        seasonAwayFGM += seasonStat[12] * minuteRatio
                        seasonAwayFGA += seasonStat[13] * minuteRatio
                        seasonAway3PM += seasonStat[15] * minuteRatio
                        seasonAway3PA += seasonStat[16] * minuteRatio
                        seasonAwayFTM += seasonStat[18] * minuteRatio
                        seasonAwayFTA += seasonStat[19] * minuteRatio
                        seasonAwayOReb += seasonStat[21] * minuteRatio
                        seasonAwayDReb += seasonStat[22] * minuteRatio
                        seasonAwayAst += seasonStat[23] * minuteRatio
                        seasonAwayTO += seasonStat[24] * minuteRatio
                        seasonAwayStl += seasonStat[25] * minuteRatio
                        seasonAwayBlock += seasonStat[26] * minuteRatio
                        seasonAwayPF += seasonStat[27] * minuteRatio

                cursor.execute("SELECT * FROM CareerBasicStats WHERE GameId = ? AND PlayerId = ?", gameId, playerId)
                for careerStat in cursor.fetchmany(1):
                    if inactive == True:
                        inactiveCareerAwayGamesPlayed += careerStat[4] 
                        inactiveCareerAwayGamesStarted  += careerStat[5]
                        inactiveCareerAwayMinutesPlayed  += careerStat[6] 
                        inactiveCareerAwayPoints += careerStat[7] 
                        inactiveCareerAwayFGM += careerStat[8] 
                        inactiveCareerAwayFGA += careerStat[9] 
                        inactiveCareerAway3PM += careerStat[11] 
                        inactiveCareerAway3PA += careerStat[12] 
                        inactiveCareerAwayFTM += careerStat[14] 
                        inactiveCareerAwayFTA += careerStat[15] 
                        inactiveCareerAwayOReb += careerStat[17] 
                        inactiveCareerAwayDReb += careerStat[18]
                        inactiveCareerAwayAst += careerStat[19] 
                        inactiveCareerAwayTO += careerStat[20] 
                        inactiveCareerAwayStl += careerStat[21] 
                        inactiveCareerAwayBlock += careerStat[22] 
                        inactiveCareerAwayPF += careerStat[23] 
                    else:
                        careerAwayGamesPlayed += careerStat[4]  * minuteRatio
                        careerAwayGamesStarted  += careerStat[5] * minuteRatio
                        careerAwayMinutesPlayed  += careerStat[6]  * minuteRatio
                        careerAwayPoints += careerStat[7]  * minuteRatio
                        careerAwayFGM += careerStat[8]  * minuteRatio
                        careerAwayFGA += careerStat[9]  * minuteRatio
                        careerAway3PM += careerStat[11]  * minuteRatio
                        careerAway3PA += careerStat[12]  * minuteRatio
                        careerAwayFTM += careerStat[14]  * minuteRatio
                        careerAwayFTA += careerStat[15]  * minuteRatio
                        careerAwayOReb += careerStat[17]  * minuteRatio
                        careerAwayDReb += careerStat[18] * minuteRatio
                        careerAwayAst += careerStat[19]  * minuteRatio
                        careerAwayTO += careerStat[20]  * minuteRatio
                        careerAwayStl += careerStat[21]  * minuteRatio
                        careerAwayBlock += careerStat[22]  * minuteRatio
                        careerAwayPF += careerStat[23]  * minuteRatio

            gameInfo = np.array([gameId, homeScore,awayScore,homeWins,homeLosses,inactiveHomePlayers,awayWins,awayLosses,inactiveAwayPlayers])

            homeSeasonSnapshot = np.array([seasonHomeGamesPlayed,seasonHomeGamesStarted,seasonHomeMinutesPlayed,seasonHomePoints,seasonHomeFGM,seasonHomeFGA,seasonHome3PM,seasonHome3PA,seasonHomeFTM,seasonHomeFTA,seasonHomeOReb,seasonHomeDReb,seasonHomeAst,seasonHomeTO,seasonHomeStl,seasonHomeBlock,seasonHomePF])
            inactiveHomeSeasonSnapshot = np.array([inactiveSeasonHomeGamesPlayed,inactiveSeasonHomeGamesStarted,inactiveSeasonHomeMinutesPlayed,inactiveSeasonHomePoints,inactiveSeasonHomeFGM,inactiveSeasonHomeFGA,inactiveSeasonHome3PM,inactiveSeasonHome3PA,inactiveSeasonHomeFTM,inactiveSeasonHomeFTA,inactiveSeasonHomeOReb,inactiveSeasonHomeDReb,inactiveSeasonHomeAst,inactiveSeasonHomeTO,inactiveSeasonHomeStl,inactiveSeasonHomeBlock,inactiveSeasonHomePF])
            homeCareerSnapshot = np.array([careerHomeGamesPlayed,careerHomeGamesStarted,careerHomeMinutesPlayed,careerHomePoints,careerHomeFGM,careerHomeFGA,careerHome3PM,careerHome3PA,careerHomeFTM,careerHomeFTA,careerHomeOReb,careerHomeDReb,careerHomeAst,careerHomeTO,careerHomeStl,careerHomeBlock,careerHomePF])
            homeInactiveCareerSnapshot = np.array([inactiveCareerHomeGamesPlayed,inactiveCareerHomeGamesStarted,inactiveCareerHomeMinutesPlayed,inactiveCareerHomePoints,inactiveCareerHomeFGM,inactiveCareerHomeFGA,inactiveCareerHome3PM,inactiveCareerHome3PA,inactiveCareerHomeFTM,inactiveCareerHomeFTA,inactiveCareerHomeOReb,inactiveCareerHomeDReb,inactiveCareerHomeAst,inactiveCareerHomeTO,inactiveCareerHomeStl,inactiveCareerHomeBlock,inactiveCareerHomePF])
            
            awaySeasonSnapshot = np.array([seasonAwayGamesPlayed,seasonAwayGamesStarted,seasonAwayMinutesPlayed,seasonAwayPoints,seasonAwayFGM,seasonAwayFGA,seasonAway3PM,seasonAway3PA,seasonAwayFTM,seasonAwayFTA,seasonAwayOReb,seasonAwayDReb,seasonAwayAst,seasonAwayTO,seasonAwayStl,seasonAwayBlock,seasonAwayPF])
            inactiveAwaySeasonSnapshot = np.array([inactiveSeasonAwayGamesPlayed,inactiveSeasonAwayGamesStarted,inactiveSeasonAwayMinutesPlayed,inactiveSeasonAwayPoints,inactiveSeasonAwayFGM,inactiveSeasonAwayFGA,inactiveSeasonAway3PM,inactiveSeasonAway3PA,inactiveSeasonAwayFTM,inactiveSeasonAwayFTA,inactiveSeasonAwayOReb,inactiveSeasonAwayDReb,inactiveSeasonAwayAst,inactiveSeasonAwayTO,inactiveSeasonAwayStl,inactiveSeasonAwayBlock,inactiveSeasonAwayPF])
            awayCareerSnapshot = np.array([careerAwayGamesPlayed,careerAwayGamesStarted,careerAwayMinutesPlayed,careerAwayPoints,careerAwayFGM,careerAwayFGA,careerAway3PM,careerAway3PA,careerAwayFTM,careerAwayFTA,careerAwayOReb,careerAwayDReb,careerAwayAst,careerAwayTO,careerAwayStl,careerAwayBlock,careerAwayPF])
            awayInactiveCareerSnapshot = np.array([inactiveCareerAwayGamesPlayed,inactiveCareerAwayGamesStarted,inactiveCareerAwayMinutesPlayed,inactiveCareerAwayPoints,inactiveCareerAwayFGM,inactiveCareerAwayFGA,inactiveCareerAway3PM,inactiveCareerAway3PA,inactiveCareerAwayFTM,inactiveCareerAwayFTA,inactiveCareerAwayOReb,inactiveCareerAwayDReb,inactiveCareerAwayAst,inactiveCareerAwayTO,inactiveCareerAwayStl,inactiveCareerAwayBlock,inactiveCareerAwayPF,distance])
            
            if homeGamesPlayed > 0:
                homeSeasonSnapshot = homeSeasonSnapshot / homeGamesPlayed
                inactiveHomeSeasonSnapshot = inactiveHomeSeasonSnapshot / homeGamesPlayed

            if awayGamesPlayed > 0:
                awaySeasonSnapshot = awaySeasonSnapshot / awayGamesPlayed
                inactiveAwaySeasonSnapshot = inactiveAwaySeasonSnapshot / awayGamesPlayed


            dataLoad = np.concatenate([gameInfo,homeSeasonSnapshot,inactiveHomeSeasonSnapshot,homeCareerSnapshot,homeInactiveCareerSnapshot,awaySeasonSnapshot,inactiveAwaySeasonSnapshot,awayCareerSnapshot,awayInactiveCareerSnapshot])
            insertStatement = f'INSERT INTO BasicSnapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
            
            print(gameId)
            cursor.execute(insertStatement,dataLoad.tolist())
            cursor.commit()

    def get_overtime_value(overTime):
        minutesPlayed = 48
        if overTime == 'OT':
            minutesPlayed = 53
        if '2' in overTime:
            minutesPlayed = 58
        if '3' in overTime:
            minutesPlayed = 63
        if '4' in overTime:
            minutesPlayed = 68
        if '5' in overTime:
            minutesPlayed = 73
        if '6' in overTime:
            minutesPlayed = 78
        if '7' in overTime:
            minutesPlayed = 83

        return minutesPlayed

    def parse_overtimes():
        connection = pyodbc.connect('DRIVER={SQL Server Native Client 11.0};server=(localdb)\\mssqllocaldb;database=Eddie;')
        cursor = connection.cursor()

        for season in SEASONS:
            seasonId = season[0]
            year = season[1]
            for month in SEASON_MONTHS:
                print(f"season: {year} month:{month}")
                try:
                    url = f"https://www.basketball-reference.com/leagues/NBA_{year}_games-{month}.html"
                    resp = requests.get(url)
                    soup=bs(resp.text,features="html.parser")

                    gameRows = soup.find("table", {"id": "schedule"}).find_all('tbody')[0].find_all('tr')
                    for game in gameRows:
                        cols = game.find_all('td')
                        awayTeam = util.getTeamCode(cols[1].get_text())
                        awayScore = cols[2].get_text()
                        homeTeam = util.getTeamCode(cols[3].get_text())
                        homeScore = cols[4].get_text()
                        boxScore = cols[5].findAll('a',text='Box Score')[0]['href'].split('/')[2].split('.')[0]
  
                        dbDate = datetime.strptime("{} {}m".format(game.find_all('th')[0].get_text(), cols[0].get_text()),  "%a, %b %d, %Y %I:%M%p")

                        
                        overTime = cols[6].get_text()
                        minutesPlayed = dataParser.get_overtime_value(overTime)

                        print(f'{awayTeam} @ {homeTeam}  ({boxScore}) - {minutesPlayed} Minutes Played')
                        cursor.execute("UPDATE Games SET TotalPlayerMinutes = ? WHERE GameKey = ?", minutesPlayed, boxScore)
                        cursor.commit()
                except:
                    print(f"nothing found for {year} Season in {month}")
        cursor.close()


    def load_today_season_stats(todaysPlayers, currentDate):
        connection = pyodbc.connect('DRIVER={SQL Server Native Client 11.0};server=(localdb)\\mssqllocaldb;database=Eddie;')
        cursor = connection.cursor()
        playerDict = dict(todaysPlayers)
        url = 'https://www.basketball-reference.com/leagues/NBA_2022_totals.html'
        resp = requests.get(url)
        soup = bs(resp.text,features="html.parser")
        players = soup.find("table", {"id": "totals_stats"}).find_all('tbody')[0].find_all('tr')
        for player in players:
            cols = player.find_all('td')
            if len(cols) == 0:
                continue
            name = cols[0].get_text()
            cols = player.find_all('td')
            
            url = cols[0].findAll('a')[0]['href']
            key = url.split('/')[3].split('.')[0]
            playerId = dataParser.get_player_id(key, name, url)
            gamesPlayed = cols[4].get_text()
            gamesStarted = cols[5].get_text()
            minutes = cols[6].get_text()
            fgm = cols[7].get_text()
            fga = cols[8].get_text()
            threeMade = cols[10].get_text()
            threeAtt = cols[11].get_text()
            ftm = cols[17].get_text()
            fta = cols[18].get_text()
            oReb = cols[20].get_text()
            dReb = cols[21].get_text()
            ast = cols[23].get_text()
            stl = cols[24].get_text()
            blk = cols[25].get_text()
            tov = cols[26].get_text()
            pf = cols[27].get_text()
            points = cols[28].get_text()
            if playerId in playerDict:
                print(f'loading season stats for {name}')
                gameId = playerDict[playerId]
                cursor.execute("INSERT INTO SeasonBasicStats ([PlayerId],[ThroughDate],[SeasonId],[GamesPlayed],[GamesStarted],[Minutes],[Points],[FGM],[FGA],[ThreePointMade],[ThreePointAttempted],[FreeThrowMade],[FreeThrowAttempted],[OffensiveRebound],[DefensiveRebound],[Assist],[TurnOver],[Steal],[Block],[PersonalFoul],[GameId]) Values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",playerId, currentDate, 19, gamesPlayed,gamesStarted, minutes, points,fgm,fga,threeMade,threeAtt,ftm,fta,oReb,dReb,ast,tov,stl,blk,pf,gameId)
                cursor.commit()
                
    def load_distance():
        connection = pyodbc.connect('DRIVER={SQL Server Native Client 11.0};server=(localdb)\\mssqllocaldb;database=Eddie;')
        cursor = connection.cursor()

        for season in SEASONS:
            seasonId = season[0]
            cursor.execute(f'SELECT GameId, HomeTeam, AwayTeam, AwayDistanceTraveled FROM Games WHERE SeasonId = {seasonId} ORDER BY GameId')
            for game in cursor.fetchall():
                gameId = game[0]
                homeTeam = game[1]
                awayTeam = game[2]

                previousDistance = 0

                newDistance = 0
                team1 = homeTeam
                team2 = awayTeam
                cursor.execute(f"SELECT HomeTeam,AwayTeam,AwayDistanceTraveled FROM Games WHERE SeasonId = {seasonId} AND (HomeTeam = '{awayTeam}' OR AwayTeam = '{awayTeam}') AND GameId < {gameId} ORDER BY GameId DESC")
                previousGame = cursor.fetchone()
                if previousGame is not None:
                    if previousGame[1] == awayTeam:
                        team2 = previousGame[0]
                        previousDistance = previousGame[2]

                if team1 != team2:
                    data1 = dataParser.update_old_team_location(team1)
                    data2 = dataParser.update_old_team_location(team2)
                    cursor.execute(f"SELECT Distance FROM StadiumDistances WHERE (Team1 = '{data1}' AND Team2 = '{data2}') OR (Team1 = '{data2}' AND Team2 = '{data1}')")
                    traveled = cursor.fetchone()
                    if traveled is not None:
                        newDistance = traveled[0]
                    else:
                        print(f'Distance missing for {team1} and {team2}')
                
                totalDistance = previousDistance + newDistance
                cursor.execute(f'UPDATE Games SET AwayDistanceTraveled = {totalDistance} WHERE GameId = {gameId}')
                cursor.commit()
                print(f'{awayTeam} traveling from {team2} to {team1} ({totalDistance} miles)')

    def load_today_rosters(team, gameId,date):
        playersOnRoster = []
        print(f'Loading rosters for {team}')
        connection = pyodbc.connect('DRIVER={SQL Server Native Client 11.0};server=(localdb)\\mssqllocaldb;database=Eddie;')
        cursor = connection.cursor()
        url = f"https://www.basketball-reference.com/teams/{team}/2022.html"
        resp = requests.get(url)
        soup=bs(resp.text,features="html.parser")
        rosterRows = soup.find("table", {"id": "roster"}).find_all('tbody')[0].find_all('tr')
        for player in rosterRows:
            cols = player.find_all('td')
            name = cols[0].get_text()
            if '(TW)' in name:
                name = name.removesuffix(' (TW)')
            url = cols[0].findAll('a')[0]['href']
            key = url.split('/')[3].split('.')[0]
            playerId = dataParser.get_player_id(key, name, url)

            playersOnRoster.append([playerId, gameId])

            cursor.execute("INSERT INTO Rosters (GameId, PlayerId, Team, Minutes, Inactive) VALUES (?,?,?,?,?) ", gameId, playerId, team, 0, False)
            cursor.commit()

            playerUrl = f'https://www.basketball-reference.com{url}'
            resp = requests.get(playerUrl)
            soup=bs(resp.text,features="html.parser")
            totalsTable = soup.find("table", {"id": "totals"})
            if totalsTable is None:
                gamesPlayed = 0
                gamesStarted = 0
                minutes = 0
                fgm =  0
                fga = 0
                threeMade =  0
                threeAtt =  0
                ftm =  0
                fta =  0
                oReb = 0
                dReb = 0
                ast =  0
                stl =  0
                blk =  0
                tov =  0
                pf = 0
                points =  0
            else:
                playerStats = totalsTable.find_all('tfoot')[0].find_all('tr')[0].find_all('td')
                gamesPlayed = playerStats[4].get_text()
                gamesStarted = playerStats[5].get_text()
                minutes = playerStats[6].get_text()
                fgm = playerStats[7].get_text()
                fga = playerStats[8].get_text()
                threeMade = playerStats[10].get_text()
                threeAtt = playerStats[11].get_text()
                ftm = playerStats[17].get_text()
                fta = playerStats[18].get_text()
                oReb = playerStats[20].get_text()
                dReb = playerStats[21].get_text()
                ast = playerStats[23].get_text()
                stl = playerStats[24].get_text()
                blk = playerStats[25].get_text()
                tov = playerStats[26].get_text()
                pf = playerStats[27].get_text()
                points = playerStats[28].get_text()
            print(f'inserting updated career stats for: {url}')
            cursor.execute("INSERT INTO CareerBasicStats ([PlayerId],[ThroughDate],[GamesPlayed],[GamesStarted],[Minutes],[Points],[FGM],[FGA],[ThreePointMade],[ThreePointAttempted],[FreeThrowMade],[FreeThrowAttempted],[OffensiveRebound],[DefensiveRebound],[Assist],[TurnOver],[Steal],[Block],[PersonalFoul],[GameId]) Values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",playerId, date, gamesPlayed,gamesStarted, minutes, points,fgm,fga,threeMade,threeAtt,ftm,fta,oReb,dReb,ast,tov,stl,blk,pf,gameId)
            cursor.commit()
        return playersOnRoster

    def load_today_records(gameId, team, isHomeTeam):
        connection = pyodbc.connect('DRIVER={SQL Server Native Client 11.0};server=(localdb)\\mssqllocaldb;database=Eddie;')
        cursor = connection.cursor()

        print(f'updating record for {team}')

        cursor.execute(f"SELECT TOP (1) [HomeTeam],[HomeWins],[HomeLosses],[HomeScore],[AwayTeam],[AwayWins],[AwayLosses],[AwayScore] FROM [Eddie].[dbo].[Games] WHERE (HomeTeam = '{team}' OR AwayTeam = '{team}') AND GameKey != '' ORDER BY GameId DESC")
        for game in cursor.fetchall():
            if game[0] == team:
                wins = game[1]
                losses = game[2]
                score = game[3]
                opponentScore = game[7]

            if game[4] == team:
                wins = game[5]
                losses = game[6]
                score = game[7]
                opponentScore = game[3]

            if score > opponentScore:
                wins += 1
            else:
                losses += 1

            if isHomeTeam:
                cursor.execute(f'UPDATE Games SET HomeWins = {wins}, HomeLosses = {losses} WHERE GameId = {gameId}')
                cursor.commit()
            else:
                cursor.execute(f'UPDATE Games SET AwayWins = {wins}, AwayLosses = {losses} WHERE GameId = {gameId}')
                cursor.commit()

    def load_todays_games():
        todaysPlayers = []
        connection = pyodbc.connect('DRIVER={SQL Server Native Client 11.0};server=(localdb)\\mssqllocaldb;database=Eddie;')
        cursor = connection.cursor()

        today = date.today().strftime("%Y-%m-%d")

        cursor.execute(f"SELECT GameId, HomeTeam, AwayTeam FROM Games WHERE GameDate BETWEEN '{today}T00:00:00.00' AND '{today}T23:59:59.999'")
        for game in cursor.fetchall():
            gameId = game[0]
            
            dataParser.load_today_records(gameId, game[1], True)
            homePlayers = dataParser.load_today_rosters(game[1], gameId,today)
            
            dataParser.load_today_records(gameId, game[2], False)
            awayPlayers = dataParser.load_today_rosters(game[2], gameId,today)

            for p in homePlayers:
                todaysPlayers.append(p)
            for p in awayPlayers:
                todaysPlayers.append(p)

        dataParser.load_today_season_stats(todaysPlayers, today)

    def update_yesterdays_games():
        connection = pyodbc.connect('DRIVER={SQL Server Native Client 11.0};server=(localdb)\\mssqllocaldb;database=Eddie;')
        cursor = connection.cursor()


        today = date.today()
        yesterday = (today - timedelta(days = 1))
        yesterdayDate = yesterday.strftime("%Y-%m-%d")
        month = yesterday.strftime("%B").lower()

        url = f'https://www.basketball-reference.com/leagues/NBA_2022_games-{month}.html'
        resp = requests.get(url)
        soup=bs(resp.text,features="html.parser")

        gameRows = soup.find("table", {"id": "schedule"}).find_all('tbody')[0].find_all('tr')
        for game in gameRows:
            cols = game.find_all('td')
            dbDate = datetime.strptime("{} {}m".format(game.find_all('th')[0].get_text(), cols[0].get_text()),  "%a, %b %d, %Y %I:%M%p")

            if dbDate.strftime("%Y-%m-%d") == yesterdayDate:

                awayTeam = util.getTeamCode(cols[1].get_text())
                awayScore = cols[2].get_text()
                homeTeam = util.getTeamCode(cols[3].get_text())
                homeScore = cols[4].get_text()
                boxScore = ''
                if len(cols[5].findAll('a',text='Box Score')) > 0:
                    boxScore = cols[5].findAll('a',text='Box Score')[0]['href'].split('/')[2].split('.')[0]

                overTime = cols[6].get_text()
                minutesPlayed = dataParser.get_overtime_value(overTime)
                
                print(f'{awayTeam} ({awayScore}) @ {homeTeam} ({homeScore}) -- {boxScore}')
                cursor.execute(f"SELECT GameId FROM Games WHERE (GameDate BETWEEN '{yesterdayDate}T00:00:00.00' AND '{yesterdayDate}T23:59:59.999') AND HomeTeam = '{homeTeam}' AND AwayTeam = '{awayTeam}'")
                for game in cursor.fetchall():
                    gameId = game[0]
                    cursor.execute(f"UPDATE Games SET GameKey = '{boxScore}', HomeScore = {homeScore}, AwayScore = {awayScore}, TotalPlayerMinutes = {minutesPlayed} WHERE GameId = {gameId}")
                    cursor.commit()
                
                print(f'loading boxscores for {awayTeam} @ {homeTeam} ({gameId}) ')
                dataParser.load_boxscore(gameId, boxScore, homeTeam, awayTeam)
                print(f'loading basic snapshot for {awayTeam} @ {homeTeam} ({gameId}) ')
                dataParser.load_basic_snapshot(gameId)
                

    def  daily_update():
        dataParser.update_yesterdays_games()
        dataParser.load_todays_games()

    def update_old_team_location(team):
        if team == 'CHO':
            return 'CHA'
        if team == 'NOH':
            return 'NOP'
        if team == 'NOK':
            return 'OKC'
        if team == 'LAL':
            return 'LAC'
        if team not in ('CHO', 'NOH', 'NOK', 'LAL'):
            return team

    
                


            
            

            
