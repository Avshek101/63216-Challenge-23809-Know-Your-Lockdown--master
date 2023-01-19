from django.shortcuts import render, redirect
from django.contrib import messages
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os.path
import gspread_dataframe as gd
from .services import allowed_services
from .news import get_news
import random
import numpy as np

# Create your views here.


my_path=os.path.abspath(os.path.dirname(__file__))
credential_path=os.path.join(my_path,"ibm-hack-281412-af7fffea1c18.json")
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credential_path
scope = ['https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name(
        credential_path, scope)
gc = gspread.authorize(credentials)



#visualize the data gathered using mental health quiz
def show_quiz(request):
    sheet = gc.open("Mental Health").worksheet("Form Responses 1")
    mh_df = pd.DataFrame(sheet.get_all_records())
    total = int(mh_df.Negative_Effect.count())
    data = mh_df[mh_df['Negative_Effect']=='Yes']
    lockdown_yes = int(data.Negative_Effect.count())
    lockdown_no = int(mh_df[mh_df['Negative_Effect']=='No'].Negative_Effect.count())
    lockdown_maybe = int(mh_df[mh_df['Negative_Effect']=='Maybe'].Negative_Effect.count())
    female = int(data[data['Gender']=='Female'].Negative_Effect.count())
    male = int(data[data['Gender']=='Male'].Negative_Effect.count())
    other = int(data[data['Gender']=='Other'].Negative_Effect.count())
    age = int(data[data['Age']=='18-30 years'].Negative_Effect.count())
    age_below = int(data[data['Age']=='Below 18 years'].Negative_Effect.count())
    age_above = int(data[data['Age']=='Above 30 years'].Negative_Effect.count())
    no_percent = (lockdown_no/total)*100
    yes_percent = (lockdown_yes/total)*100
    maybe_percent = (lockdown_maybe/total)*100
    male_percent = (male/lockdown_yes)*100
    female_percent = (female/lockdown_yes)*100
    other_percent = (other/lockdown_yes)*100
    age_percent = (age/lockdown_yes)*100
    age_below_percent = (age_below/lockdown_yes)*100
    age_above_percent = (age_above/lockdown_yes)*100
    sentiment_ws =gc.open('Sentiment live').worksheet('Master')
    live_sentiment = pd.DataFrame(sentiment_ws.get_all_records())
    pos_sent = live_sentiment['positive_count'].sum()
    neu_sent = live_sentiment['neutral_count'].sum()
    neg_sent = live_sentiment['negative_count'].sum()
    total_sent = pos_sent + neg_sent + neu_sent 
    context = {
        'yes': yes_percent,
        'no':no_percent,
        'maybe':maybe_percent,
        'age':age_percent,
        'age_above':age_above_percent,
        'age_below':age_below_percent,
        'male':male_percent,
        'female':female_percent,
        'other':other_percent,
        'tcount':total_sent,
        'theading':'Sentiments',
        'rcount':neg_sent,
        'rheading':'Negative',
        'ycount':neu_sent,
        'yheading':'Neutral',
        'gcount':pos_sent,
        'gheading':'Positive',
    }
    
    return render(request, 'quiz/quiz.html',context)

#get real time data for each timeslot
def timeslot(time_df,start,end,category):
    data_live = time_df[time_df['hour']>start]
    data_live = data_live[data_live['hour']<=end]
    if(category=='sentiment'):
        if(len(data_live)!=0):
            pos = data_live['positive_count'].sum()
            neg = data_live['negative_count'].sum()
            neu = data_live['neutral_count'].sum()
        else:
            pos = 0
            neg = 0
            neu = 0
        return pos,neg,neu
    else:
        if(len(data_live)!=0):
            #data_live=data_live[data_live['District']=='Total']
            pos = data_live['Cured'].max()
            neg = data_live['Deaths'].max()
            neu = data_live['Active'].max()
        else:
            pos = 0
            neg = 0
            neu = 0
        return pos,neg,neu

#get real time data
def get_real_time_data(df_live,category):
    rtpos = [None] * 8
    rtneu = [None] * 8
    rtneg = [None] * 8
    rt = [3,6,9,12,15,18,21,24]
    rtpos[0],rtneg[0],rtneu[0]=timeslot(df_live,0,3,category)
    rtpos[1],rtneg[1],rtneu[1]=timeslot(df_live,3,6,category)
    rtpos[2],rtneg[2],rtneu[2]=timeslot(df_live,6,9,category)
    rtpos[3],rtneg[3],rtneu[3]=timeslot(df_live,9,12,category)
    rtpos[4],rtneg[4],rtneu[4]=timeslot(df_live,12,15,category)
    rtpos[5],rtneg[5],rtneu[5]=timeslot(df_live,15,18,category)
    rtpos[6],rtneg[6],rtneu[6]=timeslot(df_live,18,21,category)
    rtpos[7],rtneg[7],rtneu[7]=timeslot(df_live,21,24,category)
    return rtpos,rtneu,rtneg,rt

#visualize charts
def get_chart(request):
    sentiment_ws =gc.open('Sentiment live').worksheet('Master')
    live_sentiment = pd.DataFrame(sentiment_ws.get_all_records())
    ws_p = gc.open("Real time patients").worksheet("Master")
    live_patient = pd.DataFrame(ws_p.get_all_records())
    rtpos,rtneu,rtneg,rt=get_real_time_data(live_sentiment,'sentiment')
    rtcured,rtactive,rtdeaths,rt= get_real_time_data(live_patient[live_patient['District']=='Total'],'corona')
    cdf,state_df =get_country_data()
    patient_total,patient_top10 = total_patient()
    pos_sent = live_sentiment['positive_count'].sum()
    neu_sent = live_sentiment['neutral_count'].sum()
    neg_sent = live_sentiment['negative_count'].sum()
    total_sent = pos_sent + neg_sent + neu_sent 
    context = {
        'cdf':cdf,
        'state_df':state_df,
        'patient_total':patient_total,
        'patient_top10':patient_top10,
        'tcount':total_sent,
        'theading':'Sentiments',
        'rcount':neg_sent,
        'rheading':'Negative',
        'ycount':neu_sent,
        'yheading':'Neutral',
        'gcount':pos_sent,
        'gheading':'Positive',
        'rtpos':rtpos,
        'rtneu':rtneu,
        'rtneg':rtneg,
        'rt':rt,
        'rtcured':rtcured,
        'rtactive':rtactive,
        'rtdeaths':rtdeaths

    }
    return render(request, 'quiz/chart.html',context)



#get data of a state
def get_location_data(state):
    ws = gc.open("Sentiment").worksheet("Master")
    df = pd.DataFrame(ws.get_all_records())

    ws2 = gc.open("Corona Patient").worksheet("Master")
    df_patient  = pd.DataFrame(ws2.get_all_records())
    sdf = pd.DataFrame(columns=['Date','pos','neu','neg'])
    state_patient = pd.DataFrame(columns=['Date','total','active','cured','deaths'])
    data= df[df['State']==state]
    dates = data['Date'].unique()
    for date in dates:
        data1= data[data['Date']==date]
        pos = data1['positive_count'].sum()
        neu = data1['neutral_count'].sum()
        neg = data1['negative_count'].sum()
        sdf.loc[len(sdf)] = [date,pos,neu,neg]
    
    data_patient = df_patient[df_patient['District']==state] 
    dates_patient = data_patient['Date'].unique()
    for date in dates_patient:
        data = data_patient[data_patient['Date']==date]
        
        total = data['Total'].max()
        active = data['Active'].max()
        cured = data['Cured'].max()
        deaths = data['Deaths'].max()
        state_patient.loc[len(state_patient)]=[date,total,active,cured,deaths]
    return sdf, state_patient

#get data of the country
def get_country_data():
    ws = gc.open("Sentiment").worksheet("Master")
    df = pd.DataFrame(ws.get_all_records())


    cdf = pd.DataFrame(columns=['Date','pos','neu','neg'])
    district_df= pd.DataFrame(columns=['state','district','pos','neu','neg'])
    for date in df['Date'].unique():
        data= df[df['Date']==date]
        pos = data['positive_count'].sum()
        neu = data['neutral_count'].sum()
        neg = data['negative_count'].sum()
        cdf.loc[len(cdf)] = [date,pos,neu,neg]
    states = df['State'].unique()
    dates = df['Date'].unique()
    state_df = pd.DataFrame(columns=['state','pos','neu','neg'])
    for state in states:
            data= df[df['State']==state]
            pos = data['positive_count'].sum()
            neu = data['neutral_count'].sum()
            neg = data['negative_count'].sum()
            state_df.loc[len(state_df)] = [state,pos,neu,neg]
  
    state_df=state_df.sort_values(by = ['pos','neu','neg'],ascending=False)
    
    return cdf,state_df.head(10)

#get covid realted data for complete country
def total_patient():
    ws2 = gc.open("Corona Patient").worksheet("Master")
    df_patient  = pd.DataFrame(ws2.get_all_records())
    patient_total = pd.DataFrame(columns=['Date','total','active','cured','deaths'])
    patient_top10 = pd.DataFrame(columns=['state','total','active','cured','deaths'])
    for date in df_patient['Date'].unique():
        data= df_patient[df_patient['Date']==date]
        data = data[data['District']=='Total']
        total = data['Total'].max()
        active = data['Active'].max()
        cured = data['Cured'].max()
        deaths = data['Deaths'].max()
        patient_total.loc[len(patient_total)]=[date,total,active,cured,deaths]
    df_patient = df_patient.sort_values(by=['Date'])
    dates =  df_patient['Date'].unique()
    currentdate = dates.tolist().pop()
    data1 = df_patient[df_patient['Date']==currentdate]
    
    states = data1['State'].unique()
    
    for state in states:
        if(state != 'Total'):
            data = data1[data1['District']==state]
            total = data['Total'].max()
            active = data['Active'].max()
            cured = data['Cured'].max()
            deaths = data['Deaths'].max()
            patient_top10.loc[len(patient_top10)]=[state,total,active,cured,deaths]
    patient_top10=patient_top10.sort_values(by = ['total'],ascending=False)
    return patient_total,patient_top10.head(10)

#get data for given district
def get_district_data(district,state):
    ws = gc.open("Sentiment").worksheet("Master")
    df = pd.DataFrame(ws.get_all_records())

    ws2 = gc.open("Corona Patient").worksheet("Master")
    df_patient  = pd.DataFrame(ws2.get_all_records())
    district_sentiment = pd.DataFrame(columns=['Date','pos','neu','neg'])
    district_patient = pd.DataFrame(columns=['Date','total','active','cured','deaths'])
    data= df[df['State']==state]
    dates = data['Date'].unique()
    for date in dates:
       
        data1= data[data['Date']==date]
        data_district = data1[data1['District']==district]
        
        pos = data_district['positive_count'].sum()
        neu = data_district['neutral_count'].sum()
        neg = data_district['negative_count'].sum()
        district_sentiment.loc[len(district_sentiment)] = [date,pos,neu,neg]
    if(district=='Bangalore Urban' or district == 'Bangalore Rural'):
            place =district.split(' ')
            place[0]= 'Bengaluru'
            district = place[0] +" "+ place[1]
    
    
    data_patient = df_patient[df_patient['State']==state] 
    dates_patient = data_patient['Date'].unique()
    for date in dates_patient:
        data = data_patient[data_patient['Date']==date]
        data_district = data[data['District']==district]
        
        total = data_district['Total'].max()
        active = data_district['Active'].max()
        cured = data_district['Cured'].max()
        deaths = data_district['Deaths'].max()
        district_patient.loc[len(district_patient)]=[date,total,active,cured,deaths]
       
    return district_sentiment, district_patient

#store data reterived from mental health quiz into google sheets
def submit(request):
    data=[]
    sheet_key = '1YKDFlcMWo0Hkm_FZe7Lmnsn3ttE0eqC6Mo02NymkJrc'
    sheet = gc.open("Mental Health").worksheet("Form Responses 1")
    mh_df = pd.DataFrame(sheet.get_all_records())
    data.append(request.GET.get('state').strip())
    data.append(request.GET.get('district').strip())
    data.append(request.GET.get('age'))
    data.append(request.GET.get('gender'))
    data.append(request.GET.get('negative_effect'))
    data.append(request.GET.get('help'))
    mh_df.loc[len(mh_df)]=data
    print(data)
    gd.set_with_dataframe(sheet, mh_df)
    
    return render(request, 'quiz/quiz.html',)

#gather data of selected state/district
def getdata(request):
    state = request.POST.get('state')
    district = request.POST.get('district')
    sentiment_ws =gc.open('Sentiment live').worksheet('Master')
    live_sentiment = pd.DataFrame(sentiment_ws.get_all_records())
    ws_p = gc.open("Real time patients").worksheet("Master")
    live_patient = pd.DataFrame(ws_p.get_all_records())

    
    if(district!=None and district!='SELECT DISTRICT'):
        
        district=district.strip()
       
        state_live_sentiment=live_sentiment[live_sentiment['State']==state]
        district_live_sentiment=state_live_sentiment[state_live_sentiment['District']==district]
       
        live_patient_state = live_patient[live_patient['State']==state]
        district_sentiment, district_patient = get_district_data(district,state)
        if(district=='Bangalore Urban' or district == 'Bangalore Rural'):
            place =district.split(' ')
            place[0]= 'Bengaluru'
            district = place[0] +" "+ place[1]
        live_patient_district = live_patient_state[live_patient_state['District']==district]
        rtcured,rtactive,rtdeaths,rt=get_real_time_data(live_patient_district,'corona')
        rtpos,rtneu,rtneg,rt=get_real_time_data(district_live_sentiment,'sentiment')
        pos_sent = district_live_sentiment['positive_count'].sum()
        neu_sent = district_live_sentiment['neutral_count'].sum()
        neg_sent = district_live_sentiment['negative_count'].sum()
        total_sent = pos_sent + neg_sent + neu_sent
    else:
       
        state_live_sentiment=live_sentiment[live_sentiment['State']==state]
      
        live_patient_state = live_patient[live_patient['District']==state]
        rtcured,rtactive,rtdeaths,rt=get_real_time_data(live_patient_state,'corona')
        rtpos,rtneu,rtneg,rt=get_real_time_data(state_live_sentiment,'sentiment')
        pos_sent = state_live_sentiment['positive_count'].sum()
        neu_sent = state_live_sentiment['neutral_count'].sum()
        neg_sent = state_live_sentiment['negative_count'].sum()
        total_sent = pos_sent + neg_sent + neu_sent
        district_sentiment, district_patient = get_district_data(district,state)
    sdf,state_patient = get_location_data(state)
    cdf,state_df =get_country_data()
    patient_total,patient_top10 = total_patient()
    context = {
        'sdf':sdf,
        'cdf':cdf,
        'state':state,
        'state_df':state_df,
        'patient_total':patient_total,
        'patient_top10':patient_top10,
        'state_patient':state_patient,
        'district_sentiment':district_sentiment,
        'district_patient':district_patient,
        'district' : district,
        'tcount':total_sent,
        'theading':'Sentiments',
        'rcount':neg_sent,
        'rheading':'Negative',
        'ycount':neu_sent,
        'yheading':'Neutral',
        'gcount':pos_sent,
        'gheading':'Positive',
        'rtpos':rtpos,
        'rtneu':rtneu,
        'rtneg':rtneg,
        'rt':rt,
        'rtcured':rtcured,
        'rtactive':rtactive,
        'rtdeaths':rtdeaths
    }
    return render(request, 'quiz/chart.html',context)

#get services,news and tweets
def info(request):
    ws_p = gc.open("Real time patients").worksheet("Master")
    live_patient = pd.DataFrame(ws_p.get_all_records())
    times = live_patient['hour'].unique()
    latest = times.tolist().pop()
    data = live_patient[live_patient['hour']==latest]
    datacount = data[data['District']=='Total']
    total_patient_count = datacount['Total'].max()
    active_patient_count = datacount['Active'].max()
    cured_patient_count = datacount['Cured'].max()
    death_patient_count = datacount['Deaths'].max()
    real_tweet_ws =gc.open('Real time tweets').worksheet('Master')
    data = pd.DataFrame(real_tweet_ws.get_all_records())

    positive_data = data[data['sentiment']=='positive']
    negative_data = data[data['sentiment']=='negative']
    pos_ids = positive_data['tweetid'].unique()
    neg_ids = negative_data['tweetid'].unique()    
    pos_ids = pos_ids.tolist()
    neg_ids = neg_ids.tolist()    
    pos_random_ids = random.sample(pos_ids,6)
    neg_random_ids = random.sample(neg_ids,6)
    #get latetst news
    data = get_news()
    datanews = random.sample(data,6)
    number_pos = []
    number_neg = []
    #to avoid rounding off of tweetid
    for id in pos_random_ids:
        number_pos.append(format(id,"0.0f"))
    for id in neg_random_ids:
        number_pos.append(format(id,"0.0f"))
    context = {
        'allowed_services': allowed_services,
        'data':datanews,
        'id':number_pos,
        'tcount': total_patient_count,
        'theading':'Cases',
        'rcount': death_patient_count,
        'rheading':'Deaths',
        'ycount':active_patient_count,
        'yheading':'Active',
        'gcount':cured_patient_count,
        'gheading':'Cured',
        }
    return render(request, 'quiz/info.html', context)


#tableau maps for visualzation
def map(request):
    sentiment_ws =gc.open('Sentiment live').worksheet('Master')
    live_sentiment = pd.DataFrame(sentiment_ws.get_all_records())
    pos_sent = live_sentiment['positive_count'].sum()
    neu_sent = live_sentiment['neutral_count'].sum()
    neg_sent = live_sentiment['negative_count'].sum()
    total_sent = pos_sent + neg_sent + neu_sent 
    context = {
        'tcount':total_sent,
        'theading':'Sentiments',
        'rcount':neg_sent,
        'rheading':'Negative',
        'ycount':neu_sent,
        'yheading':'Neutral',
        'gcount':pos_sent,
        'gheading':'Positive',
    }
    return render(request, 'quiz/map.html',context)

#get patient count for each state/district
def getcount(request):
    state = request.POST.get('state')
    district = request.POST.get('district')
    if(district=='Bangalore Urban' or district == 'Bangalore Rural'):
            place =district.split(' ')
            place[0]= 'Bengaluru'
            district = place[0] +" "+ place[1]
    ws_p = gc.open("Real time patients").worksheet("Master")
    live_patient = pd.DataFrame(ws_p.get_all_records())
    times = live_patient['hour'].unique()
    latest = times.tolist().pop()
    data = live_patient[live_patient['hour']==latest]
    datacount = data[data['District']==state]
    total_patient_count = datacount['Total'].max()
    active_patient_count = datacount['Active'].max()
    cured_patient_count = datacount['Cured'].max()
    death_patient_count = datacount['Deaths'].max()
    if(district!=None and district!='SELECT DISTRICT'):
        data1 = data[data['State']==state]
        datacount = data1[data1['District']==district]
        total_patient_count = datacount['Total'].max()
        active_patient_count = datacount['Active'].max()
        cured_patient_count = datacount['Cured'].max()
        death_patient_count = datacount['Deaths'].max()
    real_tweet_ws =gc.open('Real time tweets').worksheet('Master')
    data = pd.DataFrame(real_tweet_ws.get_all_records())
    positive_data = data[data['sentiment']=='positive']
    negative_data = data[data['sentiment']=='negative']
    pos_ids = positive_data['tweetid'].unique()
    neg_ids = negative_data['tweetid'].unique()    
    pos_ids = pos_ids.tolist()
    neg_ids = neg_ids.tolist()    
    pos_random_ids = random.sample(pos_ids,6)
    neg_random_ids = random.sample(neg_ids,6)
    #get latetst news
    data = get_news()
    datanews = random.sample(data,6)
    number_pos = []
    number_neg = []
    #to avoid rounding off of tweetid
    for id in pos_random_ids:
        number_pos.append(format(id,"0.0f"))
    for id in neg_random_ids:
        number_pos.append(format(id,"0.0f"))
    context = {
        'allowed_services': allowed_services,
        'data':datanews,
        'id': number_pos,
        'tcount': total_patient_count,
        'theading':'Cases',
        'rcount': death_patient_count,
        'rheading':'Deaths',
        'ycount':active_patient_count,
        'yheading':'Active',
        'gcount':cured_patient_count,
        'gheading':'Cured',
        'state':state,
        'district':district
        }
    return render(request, 'quiz/info.html', context)
