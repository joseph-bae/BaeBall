import concurrent.futures
import warnings
from datetime import date
from typing import Optional, Union
import requests
import pandas as pd
from tqdm import tqdm
import pybaseball.playerid_lookup as lookup
import numpy as np
import statsapi
import pybaseball.datasources.statcast as statcast_ds
from pybaseball.datasources.fangraphs import fg_batting_data
import datetime
import os
import requests
import json
import math



def get_top_n_batters(number_of_batters,season):
  """
  
  Just directly pulls from fangraphs the top batters.
  Might be personalizable in the future (in terms of how you want to find batters),
  but this is just a way to get a large pool of good batters from which the rest 
  of the code will select the best one. Also, all batters can be used for training the model.

  """

  batting_data=fg_batting_data(season)
  topn=batting_data.iloc[0:number_of_batters,:]
  topn=topn.loc[:,["IDfg","Name","Team","Age","AVG","OBP","SLG","Contact% (pi)",]]
  return topn

def get_batter_ids(player_names,Ages,Date):
  """
  
  A very drawn out way of figuring out the MLB player ID associated with 
  a given player name. Unfortunately, nicknames, suffixes (Jr., Sr., III) are 
  not always handled uniformly. This can in general result in us losing a few 
  candidate players. New players can also take some time to appear

  """
  player_URL='http://lookup-service-prod.mlb.com/json/named.search_player_all.bam?sport_code=%27mlb%27&active_sw=%27Y%27&name_part=%27{First}%20{Last}%25%27' #API for player lookup using just active players. May be unsupported soon. 

  IDs=[]
  MissingPlayers=[]
  for i,name in enumerate(player_names):
    playerfound=0
    FirstName=name.split(' ')[0]
    if name.split(' ')[-1]=='Jr.' or name.split(' ')[-1]=='II' or name.split(' ')[-1]=='III' or name.split(' ')[-1]=='Sr.': #Trying to find out a way to handle suffixes intelligently
      LastName=name.split(' ')[1]
    else:
      LastName=name.split(' ')[-1]
    QueryLastName=name.split(' ')[1]
    CurrentURL=player_URL.format(First=FirstName,Last=QueryLastName)
    TotalResult=requests.get(CurrentURL)
    CurrentAge=Ages.iloc[i]
    CurrentBirthYear=datetime.date.fromisoformat(Date).year-CurrentAge
    try:
      DesiredList=TotalResult.json()['search_player_all']['queryResults']['row']
      CurrentAge=Ages.iloc[i]
      CurrentBirthYear=datetime.date.fromisoformat(Date).year-CurrentAge
      if type(DesiredList)==list: #If there are multiple players with the searched names
        for result in DesiredList:
          
          checkNameLast=result['name_last']
          checkBday=result['birth_date']
          checkBday=datetime.date.fromisoformat(checkBday.split('T')[0])
          checkYear=checkBday.year
          if LastName==checkNameLast and abs(checkYear-CurrentBirthYear)<2:
            IDs.append(result['player_id'])
            playerfound=1
            break
          elif LastName+' Jr.'==checkNameLast and abs(checkYear-CurrentBirthYear)<2:
            IDs.append(result['player_id'])
            playerfound=1
            break   
          elif LastName+' Sr.'==checkNameLast and abs(checkYear-CurrentBirthYear)<2:
            IDs.append(result['player_id'])
            playerfound=1
            break       
      elif type(DesiredList)==dict: #If there is just a single player with the name
        checkNameLast=DesiredList['name_last']
        checkBday=DesiredList['birth_date']
        checkBday=datetime.date.fromisoformat(checkBday.split('T')[0])
        checkYear=checkBday.year
        if LastName==checkNameLast and abs(checkYear-CurrentBirthYear)<2:
          IDs.append(DesiredList['player_id'])
          playerfound=1
        elif LastName+' Jr.'==checkNameLast and abs(checkYear-CurrentBirthYear)<2:
          IDs.append(DesiredList['player_id'])
          playerfound=1
        elif LastName+' Sr.'==checkNameLast and abs(checkYear-CurrentBirthYear)<2:
          IDs.append(DesiredList['player_id'])
          playerfound=1
                      

    except:
      playerfound=0
    if playerfound==1:
      continue
  
    else:
      backup_URL='http://lookup-service-prod.mlb.com/json/named.search_player_all.bam?sport_code=%27mlb%27&name_part=%27{First}%20{Last}%25%27' #This will search the all time player lists for the player. Sometimes works if the player skipped a season and is just coming back.
      CurrentURL=backup_URL.format(First=FirstName,Last=QueryLastName)
      TotalResult=requests.get(CurrentURL)
      try:
        DesiredList=TotalResult.json()['search_player_all']['queryResults']['row']
        if type(DesiredList)==list:
          for result in DesiredList:
            
            checkNameLast=result['name_last']
            checkBday=result['birth_date']
            checkBday=datetime.date.fromisoformat(checkBday.split('T')[0])
            checkYear=checkBday.year
            if LastName==checkNameLast and abs(checkYear-CurrentBirthYear)<2:
              IDs.append(result['player_id'])
              playerfound=1
              break
            elif LastName+' Jr.'==checkNameLast and abs(checkYear-CurrentBirthYear)<2:
              IDs.append(result['player_id'])
              playerfound=1
              break                
        elif type(DesiredList)==dict:
          checkNameLast=DesiredList['name_last']
          checkBday=DesiredList['birth_date']
          checkBday=datetime.date.fromisoformat(checkBday.split('T')[0])
          checkYear=checkBday.year

          if LastName==checkNameLast and abs(checkYear-CurrentBirthYear)<2:
            IDs.append(DesiredList['player_id'])
            playerfound=1
          elif LastName+' Jr.'==checkNameLast and abs(checkYear-CurrentBirthYear)<2:
            IDs.append(DesiredList['player_id'])
            playerfound=1
      except:
        playerfound=0

      
              
    if playerfound==0: #Retrying a lookup using a different way of handling suffixes.
    #Special note, this was implemented solely for Vladimir Guerrero Jr.
        backup_URL='http://lookup-service-prod.mlb.com/json/named.search_player_all.bam?sport_code=%27mlb%27&name_part=%27{First}%20{Last}%25%27'
        LastName=''
        for namepart in name.split(' ')[1::]:
          LastName+=' '+namepart
  
        LastName=LastName[1::]  
        CurrentURL=backup_URL.format(First=FirstName,Last=QueryLastName)
        TotalResult=requests.get(CurrentURL)
        try:
          DesiredList=TotalResult.json()['search_player_all']['queryResults']['row']
          if type(DesiredList)==list:
            for result in DesiredList:
              
              checkNameLast=result['name_last']
              checkPitch=result['position']
              if LastName==checkNameLast and checkPitch=='P':
                IDs.append(result['player_id'])
                playerfound=1
                break
          elif type(DesiredList)==dict:
            checkNameLast=DesiredList['name_last']
            checkPitch=DesiredList['position']
            if LastName==checkNameLast and checkPitch=='P':
              IDs.append(DesiredList['player_id'])
              playerfound=1
        except:
          playerfound=0
    if playerfound==0:  
      IDs.append(np.nan)
      MissingPlayers.append(name)
  return IDs,MissingPlayers


def get_pitcher_ids(player_names):
  """

  Similar to the above code for batters. 
  However, rather than use age we use pitcher position designation to identify players among duplicates.
  
  """
  player_URL='http://lookup-service-prod.mlb.com/json/named.search_player_all.bam?sport_code=%27mlb%27&active_sw=%27Y%27&name_part=%27{First}%20{Last}%25%27'
  IDs=[]
  MissingPlayers=[]
  for i,name in enumerate(player_names):
    playerfound=0
    FirstName=name.split(' ')[0]
    if name.split(' ')[-1]=='Jr.' or name.split(' ')[-1]=='II' or name.split(' ')[-1]=='III' or name.split(' ')[-1]=='Sr.':
      LastName=name.split(' ')[1]
    else:
      LastName=name.split(' ')[-1]
    QueryLastName=name.split(' ')[1]  
    CurrentURL=player_URL.format(First=FirstName,Last=QueryLastName)
    TotalResult=requests.get(CurrentURL)
    try:
      DesiredList=TotalResult.json()['search_player_all']['queryResults']['row']
      
      if type(DesiredList)==list:
        for result in DesiredList:
          
          checkNameLast=result['name_last']
          checkPitch=result['position']
          
          if LastName==checkNameLast and checkPitch=='P':
            IDs.append(result['player_id'])
            playerfound=1
            break
          elif LastName+' Jr.'==checkNameLast and checkPitch=='P':
            IDs.append(result['player_id'])
            playerfound=1
            break
          elif LastName+' Sr.'==checkNameLast and checkPitch=='P':
            IDs.append(result['player_id'])
            playerfound=1
            break
      elif type(DesiredList)==dict:
        checkNameLast=DesiredList['name_last']
        checkPitch=DesiredList['position']
        if LastName==checkNameLast and checkPitch=='P':
          IDs.append(DesiredList['player_id'])
          playerfound=1
        elif LastName+' Jr.'==checkNameLast and checkPitch=='P':
          IDs.append(result['player_id'])
          playerfound=1
        elif LastName+' Sr.'==checkNameLast and checkPitch=='P':
          IDs.append(result['player_id'])
          playerfound=1
      
    except:
      playerfound=0
    if playerfound==1:
        continue
    
    
    else:
        backup_URL='http://lookup-service-prod.mlb.com/json/named.search_player_all.bam?sport_code=%27mlb%27&name_part=%27{First}%20{Last}%25%27'
        CurrentURL=backup_URL.format(First=FirstName,Last=QueryLastName)
        TotalResult=requests.get(CurrentURL)
        try:
          DesiredList=TotalResult.json()['search_player_all']['queryResults']['row']
          if type(DesiredList)==list:
            for result in DesiredList:
              
              checkNameLast=result['name_last']
              checkPitch=result['position']
              if LastName==checkNameLast and checkPitch=='P':
                IDs.append(result['player_id'])
                playerfound=1
                break
          elif type(DesiredList)==dict:
            checkNameLast=DesiredList['name_last']
            checkPitch=DesiredList['position']
            if LastName==checkNameLast and checkPitch=='P':
              IDs.append(DesiredList['player_id'])
              playerfound=1
        except:
          playerfound=0

    if playerfound==0:
        backup_URL='http://lookup-service-prod.mlb.com/json/named.search_player_all.bam?sport_code=%27mlb%27&name_part=%27{First}%20{Last}%25%27'
        LastName=''
        for namepart in name.split(' ')[1::]:
          LastName+=' '+namepart
        LastName=LastName[1::]
          
          
        CurrentURL=backup_URL.format(First=FirstName,Last=QueryLastName)
        TotalResult=requests.get(CurrentURL)
        try:
          DesiredList=TotalResult.json()['search_player_all']['queryResults']['row']
          if type(DesiredList)==list:
            for result in DesiredList:
              
              checkNameLast=result['name_last']
              checkPitch=result['position']
              if LastName==checkNameLast and checkPitch=='P':
                IDs.append(result['player_id'])
                playerfound=1
                break
          elif type(DesiredList)==dict:
            checkNameLast=DesiredList['name_last']
            checkPitch=DesiredList['position']
            if LastName==checkNameLast and checkPitch=='P':
              IDs.append(DesiredList['player_id'])
              playerfound=1
        except:
          MissingPlayers.append(name)

    if playerfound==0:
      MissingPlayers.append(name)
      IDs.append(np.nan)
  return IDs,MissingPlayers

def get_team_id_list(team_list):
  """

  These are the MLB IDs associated with different teams. 
  I think I found them on Yahoo Answers but they are accurate.

  """
  teamdict= {"LAA":108, "ARI":109, "BAL":110,
            "BOS":111, "CHC":112, "CIN":113, "CLE":114,
            "COL":115, "DET":116, "HOU":117, "KC":118,
            "LAD":119, "WSH":120, "NYM":121, "OAK":133,
            "PIT":134, "SD":135, "SEA":136, "SF":137,
            "STL":138, "TB":139, "TEX":140, "TOR":141,
            "MIN":142, "PHI":143, "ATL":144, "CWS":145,
            "MIA":146, "NYY":147, "MIL":158,"CHW":145, 
            "SDP":135, "WSN":120, "TBR":139, "SFG":137,
            "KCR":118
            }
  team_ids=[]
  

  for team in team_list:
    team_ids.append(teamdict[team])
  return team_ids

def batter_vs_pitcher(Batter,Pitcher,GameBeforeDate):
  """
  I use statcast to identify historical matchups between a batter and pitcher. 
  It is relatively sparse as new pitchers join the league and in rare matchups. 

  """
  
  Search_URL=r'/statcast_search/csv?all=true?&?hfPT=&hfAB=&hfGT=R%7C&hfPR=&hfZ=&stadium=&hfBBL=&hfNewZones=&hfPull=&hfC=&hfSea=2022%7C2021%7C2020%7C2019%7C2018%7C2017%7C2016%7C2015%7C2014%7C2013%7C2012%7C2011%7C2010%7C2009%7C2008%7C&hfSit=&player_type=batter&hfOuts=&opponent=&pitcher_throws=&batter_stands=&hfSA=&game_date_gt=2003-03-03&game_date_lt={Late}&hfInfield=&team=&position=&hfOutfield=&hfRO=&home_road=&batters_lookup%5B%5D={BatterID}&hfFlag=&hfBBT=&pitchers_lookup%5B%5D={PitcherID}&metric_1=&hfInn=&min_pitches=0&min_results=0&group_by=name&sort_col=ba&player_event_sort=api_p_release_speed&sort_order=desc&min_pas=0&chk_stats_abs=on&chk_stats_hits=on&chk_stats_ba=on#results'
  ROOT_URL = r'https://baseballsavant.mlb.com'
  Search_URL=Search_URL.format(BatterID=Batter,PitcherID=Pitcher,Late=GameBeforeDate)
  statcast_content = requests.get(ROOT_URL + Search_URL, timeout=None).content
  try: 
    return statcast_ds.get_statcast_data_from_csv(
      statcast_content.decode('utf-8'),
  )
  except: 
    return -1


def pitcher_and_ballpark(teamID,date):
  """

  Using the MLB schedule to get the schedule for a given date. 
  Also gets us the pitcher and ballpark for their stats. 

  """
  ballpark_dict={ #Using the MLBs ranking of batter friendly parks. Unfortunately, spellings are not uniform.
    'Coors Field':1, "Coor's Field":1, 'Rogers Centre': 2, 'Rogers Center': 2,
    "Roger's Centre": 2, "Roger's Center": 2, 'Fenway Park':3,
    'Angel Stadium': 4, 'Angel Stadium of Anaheim':4, 'Kauffman Stadium': 5, 'Yankee Stadium':6,
    'Progressive Field':7, 'Great American Ball Park': 8, 'Turner Field':8, 'Oracle Park':9,
    'AT&T Park':9, 'PNC Park': 10, 'Sahlen Field': 11, 'Truist Park':12, 'Chase Field': 13,
    'Globe Life Field': 14, 'Busch Stadium': 15, 'Citizens Bank Park':16,
    "Citizen's Bank Park":16, "Dodger Stadium": 17, "Miller Park":18, 
    "American Family Field":18, "Oakland–Alameda County Coliseum":19, 
    "RingCentral Coliseum":19,"O.co Coliseum":19, "Oakland Coliseum":19, "Marlins Park":20,
    "Marlin's Park":20, "Tropicana Field": 21, "Citi Field":22,
    "Guaranteed Rate Field":23, "U.S. Cellular Field":23, "Wrigley Field":24, "Comerica Park":25,
    "Target Field":26, "T-Mobile Park":27, "Globe Life Park in Arlington":28,
    "Nationals Park":29, "National's Park":29, "Oriole Park at Camden Yards":30,
    "Camden Yards":30, "Petco Park":31, "Minute Maid Park":32, "SunTrust Park":12,
    "Estadio de Beisbol Monterrey":33, "Safeco Field": 27, "loanDepot park": 20, 'TD Ballpark':23
  }
  try:
    statsdate=date.split('-')[1]+'/'+date.split('-')[2]+'/'+date.split('-')[0]
    GameSchedule=statsapi.schedule(date=statsdate, start_date=None, end_date=None, team=teamID, opponent="", sportId=1, game_id=None)
    if np.shape(GameSchedule)==(0,):
      return np.nan,np.nan,np.nan,np.nan
    else:
      home=0
      if GameSchedule[0]['away_id']==teamID:
        pitcher=GameSchedule[0]['home_probable_pitcher']
        home=0
      else:
        pitcher=GameSchedule[0]['away_probable_pitcher']
        home=1
    if pitcher=='': #I use dropna() a lot in the final feature matrix generation code. Edit np.nans as appropriate if you want to get sparse matrices or remove the dropna()s.
      pitcher=np.nan
    return pitcher, home, GameSchedule[0]['venue_name'], ballpark_dict[GameSchedule[0]['venue_name']]
  except:
    
    try:
      return pitcher,home,GameSchedule[0]['venue_name'],np.nan
    except:
      return np.nan,np.nan,np.nan,np.nan


def recent_pitcher_stats(pitcher_ids,season):

  """

  Simple enough, getting a pitcher's recent stats from the MLB API.

  """

  Pitcher_URL='http://lookup-service-prod.mlb.com/json/named.sport_pitching_tm.bam?league_list_id=%27mlb%27&game_type=%27R%27&season=%27{Season}%27&player_id=%27{ID}%27'
  
  era=[]
  h9=[]
  k9=[]
  kbb=[]
  whip=[]
  avg=[]
  MissingData=[]
  for pitcher in pitcher_ids:
    try:
      PitcherResult=requests.get(Pitcher_URL.format(Season=season,ID=pitcher))
      DesiredDict=PitcherResult.json()['sport_pitching_tm']['queryResults']['row']
      
    except:
      try:
        PitcherResult=requests.get(Pitcher_URL.format(Season=season-1,ID=pitcher))
        DesiredDict=PitcherResult.json()['sport_pitching_tm']['queryResults']['row']
      except:
        MissingData.append(pitcher)
        era.append(np.nan)
        h9.append(np.nan)
        k9.append(np.nan)
        whip.append(np.nan)
        avg.append(np.nan)
    if type(DesiredDict)==list:
      DesiredDict=DesiredDict[-1]
    era.append(DesiredDict['era'])
    h9.append(DesiredDict['h9'])
    k9.append(DesiredDict['k9'])

    whip.append(DesiredDict['whip'])
    avg.append(DesiredDict['avg'])
  PitchStats={'era':era,'h9':h9,'k9':k9,'whip':whip,'avg':avg}
  FinalStats=pd.DataFrame.from_dict(PitchStats)
  return FinalStats,MissingData
    


      
def get_recent_batting_stats(playerID,EarlyDate,GameDate,Season,number_of_games=5):
  """

  Using baseball Savant to get the most recent stats for a batter
  
  """
  
  URL="https://baseballsavant.mlb.com/statcast_search/csv?all=true?&?hfPT=&hfAB=&hfGT=R%7C&hfPR=&hfZ=&stadium=&hfBBL=&hfNewZones=&hfPull=&hfC=&hfSea={SeasonYear}%7C&hfSit=&player_type=batter&hfOuts=&opponent=&pitcher_throws=&batter_stands=&hfSA=&game_date_gt={Early}&game_date_lt={Late}&hfInfield=&team=&position=&hfOutfield=&hfRO=&home_road=&batters_lookup%5B%5D={BatterID}&hfFlag=&hfBBT=&metric_1=&hfInn=&min_pitches=0&min_results=0&group_by=name-date&sort_col=ba&player_event_sort=api_p_release_speed&sort_order=desc&min_pas=0&chk_stats_abs=on&chk_stats_hits=on&chk_stats_ba=on#results"
  URL=URL.format(SeasonYear=Season,Early=EarlyDate,Late=GameDate,BatterID=playerID)
  BatterContent=requests.get(URL,timeout=None).content
  BatterDataFrame=statcast_ds.get_statcast_data_from_csv(
    BatterContent.decode('utf-8'),
  )
  sortedDataFrame=BatterDataFrame.sort_values(by=['game_date'],ascending=False)
  Batting_Averages=[]
  for ba in sortedDataFrame.ba:
    Batting_Averages.append(ba)
  return Batting_Averages[0:number_of_games]

def get_feature_matrix(number_of_batters=100,number_of_games=5,
                       date=datetime.datetime.today().strftime('%Y-%m-%d'),
                       duration_prior=90,GetMatchupValues=1,train=1,
                       method_few_recent_games='padzero'): #can be 'drop'
  """
  
  The big function. Uses all of the above to generate a DataFrame of batters
  and relevant features (at least what I think is relevant).
  
  """
  progressdfs={}
  log={}

  season=int(date.split('-')[0])
  top_batters=get_top_n_batters(number_of_batters,season)
  top_batters = top_batters[top_batters.Team != '- - -']

  top_batters.index=list(range(top_batters.shape[0]))
  top_batters['BatterIDs'],MissingBatters=get_batter_ids(top_batters.Name,top_batters.Age,date)
  
  progressdfs['BatterIDs']=top_batters
  log['BattersMissingIDs']=MissingBatters

  top_batters=top_batters.dropna()
  top_batters=top_batters.reset_index(drop=True)
  TeamIDs=get_team_id_list(top_batters.Team)
  top_batters['TeamIDs']=TeamIDs
  
  progressdfs['TeamIDs']=top_batters
  
  
  pitcherInfo=top_batters.TeamIDs.to_frame().apply(lambda row: pitcher_and_ballpark(row['TeamIDs'],date),axis=1, result_type='expand')
  pitcherLabels=['Pitchers','Home','Ballpark','BallparkNumber']
  pitcherInfo.columns=pitcherLabels
  
  progressdfs['PitcherInfo']=pitcherInfo
  log['pitcherInfoNaNs']=pitcherInfo[pitcherInfo.isna().any(axis=1)]
    
  df=pd.concat([top_batters,pitcherInfo],axis='columns')
  df=df.dropna()
  df=df.reset_index(drop=True)
  df['PitcherIDs'],MissingPitchers=get_pitcher_ids(df.Pitchers.values)
  df=df.dropna()
  df=df.reset_index(drop=True)

  progressdfs['PitcherIDs']=df
  log['PitchersMissingIDs']=MissingPitchers


  PitchingStats,MissingPitchingData=recent_pitcher_stats(df.PitcherIDs.values,season)
  MissingPitchingDataDict={}
  for ID in MissingPitchingData:
    name=df.loc[df['PitcherIDs']==ID,'Pitchers'].values
    MissingPitchingDataDict[ID]=name
  
  log['PitchersMissingStats']=MissingPitchingDataDict
  progressdfs['PitcherStats']=PitchingStats
  df=pd.concat([df,PitchingStats],axis='columns')
  
  CurrentDate=datetime.date(int(date.split('-')[0]),int(date.split('-')[1]),int(date.split('-')[2]))
  CurrentDate=CurrentDate-datetime.timedelta(days=1)
  delta=datetime.timedelta(days=duration_prior)
  EarlyDateTime=CurrentDate-delta
  EarlyDate=str(EarlyDateTime.year)+'-'+str(EarlyDateTime.month)+'-'+str(EarlyDateTime.day)
  
  delta2=datetime.timedelta(days=1)
  DayBeforeDate=CurrentDate-delta2
  DayBeforeDate=str(DayBeforeDate.year)+'-'+str(DayBeforeDate.month)+'-'+str(DayBeforeDate.day)
  CurrentDate=str(CurrentDate.year)+'-'+str(CurrentDate.month)+'-'+str(CurrentDate.day)
  if GetMatchupValues:
    MatchupAverages=[]
    RecentBattingAverages=[]

    for batter,pitcher in zip(df.BatterIDs.values,df.PitcherIDs.values):
      try:
        MatchupAverages.append(batter_vs_pitcher(batter,pitcher,DayBeforeDate).ba.iloc[0])
      except:
        MatchupAverages.append(np.nan)
        
    df['MatchupAverage']=MatchupAverages
    df=df.dropna()
    df=df.reset_index(drop=True)
    progressdfs['MatchupAverage']=df



  tempdict={}
  for batter in df.BatterIDs.values:
    try:
      recentgameAverages=get_recent_batting_stats(batter,EarlyDate,CurrentDate,season, number_of_games)
    except:
      recentgameAverages=[]
    while len(recentgameAverages)<number_of_games:
      if method_few_recent_games=='drop':
        recentgameAverages.append(np.nan)
      else:
        recentgameAverages.append(0.0)
    tempdict[batter]=recentgameAverages
  RecentBAdf=pd.DataFrame(tempdict).T
  GameNames=['Game '+str(i+1) for i in range(len(RecentBAdf.columns))]
  RecentBAdf.columns=GameNames
  RecentBAdf=RecentBAdf.reset_index(drop=True)
  progressdfs['RecentBattingAverages']=RecentBAdf
  df2=pd.concat([df,RecentBAdf],axis='columns')
  
  if train:
    Test_Day_Labels=[]
    TestURL='https://baseballsavant.mlb.com/statcast_search/csv?all=true?hfPT=&hfAB=&hfGT=R%7C&hfPR=&hfZ=&stadium=&hfBBL=&hfNewZones=&hfPull=&hfC=&hfSea={season}%7C&hfSit=&player_type=batter&hfOuts=&opponent=&pitcher_throws=&batter_stands=&hfSA=&game_date_gt={ED}&game_date_lt={LD}&hfInfield=&team=&position=&hfOutfield=&hfRO=&home_road=&batters_lookup%5B%5D={BatterID}&hfFlag=&hfBBT=&metric_1=&hfInn=&min_pitches=0&min_results=0&group_by=name&sort_col=ba&player_event_sort=api_p_release_speed&sort_order=desc&min_pas=0&chk_stats_abs=on&chk_stats_hits=on&chk_stats_ba=on#results'
    for batter in df2.BatterIDs:
      CurrentTestURL=TestURL.format(season=season,ED=date,LD=date,BatterID=batter)
      TestContent=requests.get(CurrentTestURL,timeout=None).content
      try:
        Testdf=statcast_ds.get_statcast_data_from_csv(TestContent.decode('utf-8'))
        Test_Day_Labels.append(Testdf.hits.iloc[0]>0)
      except:
        Test_Day_Labels.append(np.nan)
    df2['TestLabels']=Test_Day_Labels
    
  df2=df2.dropna()
  return df2,log,progressdfs    
