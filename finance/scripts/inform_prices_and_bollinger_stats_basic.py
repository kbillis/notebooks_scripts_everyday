import schedule
import numpy as np
import pandas as pd
import pandas_datareader as pdr
import matplotlib.pyplot as plt
import datetime
import time
import os
import sys
import argparse
import yfinance as yf

import email
import smtplib


import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


parser = argparse.ArgumentParser(description='This is my example: python3 ./inform_prices_and_bollinger_stats.py ')
args = parser.parse_args()


start = time.time()

# mystocks = sys.argv[1].split(',')
myCurrencies = ['GBPEUR=X','GBPCHF=X']
# mystocks = ['NIO','BMY','SOFI','PACB','ME','NCLH','CCL','CRSP','ILMN','SPCE','ROKU','MRNA','ZM','MSFT', 'VZ', 'NVAX','GTLB']
mystocks = ['NIO']

mystocks_not_to_check = ['']
mystocks_to_check = [x for x in mystocks if x not in mystocks_not_to_check]
print(mystocks_to_check)




def sent_email_to_inform_hotmail_DEPRICATED(symbol, action, text):
    test = True
    if test: 
        return
    msg = email.message_from_string(text)
    receiver = "recieve@gmail.com"
    msg['From'] = "from@hotmail.com"
    msg['To'] = receiver
    msg['Subject'] = f"STOCKS from me: {symbol} {action}"
    print("### This is important, I will sent an email ### ")
    s = smtplib.SMTP("smtp.office365.com",587, timeout=60)
    s.ehlo() # Hostname to send for this command defaults to the fully qualified domain name of the local host.
    s.starttls() #Puts connection to SMTP server in TLS mode
    s.login('your@hotmail.com', os.environ['dump_hotmail_pass'] )

    s.sendmail("your@hotmail.com", receiver, msg.as_string())

    s.quit()


def sent_email_to_inform(symbol, action, text):
    # Check if the required environment variables are set
    if not os.environ.get('SENDER_EMAIL') or not os.environ.get('RECEIVER_EMAIL') or not os.environ.get('SENDGRID_API_KEY'):
        # Replaced print with log.info for consistency with original code
        log.info(
            "Error: SENDER_EMAIL or SENDGRID_API_KEY environment variables not set.")
        log.info("Please set these variables and tgit ary again.")
        return 0    
    
    
    message = Mail(
        from_email=os.environ.get('SENDER_EMAIL'),
        to_emails=os.environ.get('RECEIVER_EMAIL'),
        subject=f"STOCKS from me: {symbol} {action}",
        html_content=text)
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        # sg.set_sendgrid_data_residency("eu")
        # uncomment the above line if you are sending mail using a regional EU subuser
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e.message)
    
    

def get_sma(prices, rate):
    return prices.rolling(rate).mean()

def get_bollinger_bands(prices, rate=10):
    sma = get_sma(prices, rate)
    std = prices.rolling(rate).std()
    bollinger_up = sma + std * 2 # Calculate top band
    bollinger_down = sma - std * 2 # Calculate bottom band
    return bollinger_up, bollinger_down

def find_stock_to_buy_or_sell(symbol,roling_window):
    end = datetime.date.today()
    #  BUG: there is a problem here. https://stackoverflow.com/questions/74832296/typeerror-string-indices-must-be-integers-when-getting-data-of-a-stock-from-y
    # df = pdr.DataReader(symbol, 'yahoo', '2021-01-01', datetime.date.today())
    df = yf.download(symbol, start='2023-01-01', end=datetime.date.today())

    df.index = np.arange(df.shape[0])
    closing_prices = df['Close']
    print("")
    print("get bands")
    bollinger_up, bollinger_down = get_bollinger_bands(closing_prices, roling_window)

    makeGraph="bo"
    if (makeGraph=="yes"):
        plt.title(symbol + ' Bollinger Bands')
        plt.xlabel('Days')
        plt.ylabel('Closing Prices')
        plt.plot(closing_prices, label='Closing Prices')
        plt.plot(bollinger_up, label='Bollinger Up', c='g')
        plt.plot(bollinger_down, label='Bollinger Down', c='r')
        plt.legend()
        plt.show()

    # shouldn't change this
    N = 1
    low = df["Low"]
    high = df["High"]

    toPrint = "WhatToDo"
    status = "NA"
    percentage_fall = 0
    percentage_up   = 0



    for x, y, h, z, m in zip(
        [closing_prices[-N:].values.item()], 
        [bollinger_down[-N:].values.item()], 
        [bollinger_up[-N:].values.item()], 
        [low[-N:].values.item()], 
        [high[-N:].values.item()]
    ):        

        info = (
            f"closing_price: {round(x,2)} "
            f"bollinger_down: {round(y,2)} "
            f"bollinger_up: {round(h,2)} "
            f"low: {round(z,2)} "
            f"high: {round(m,2)}"
        )

        print(info)
        if (x<y):
            # os.system("printf '\a'") # or '\7'
            toPrint="!!BUY!!! "+info
            status="BUY"
            sent_email_to_inform(symbol, status, toPrint)
            # print("BUY!")
        elif (x>h):
            # os.system("printf '\7'") # or '\7'
            toPrint="!!SELL!! "+info
            status="SELL"
            sent_email_to_inform(symbol, status, toPrint)
            # print("SELL!")
        else:
            toPrint="HOLD "+info
            status="HOLD"
            # print("HOLD")
    print("Symbol:" + symbol + " to " +toPrint)
    return 'good'


#create the alarm clock.
def print_now_time():
    now = datetime.datetime.now()
    print("Current date and time : ")
    print(now.strftime("%Y-%m-%d %H:%M:%S"))


def job(number_loops=1):
    # sleep for some time....
    print("################")

    for lp in range(number_loops):
        print(number_loops)
        print_now_time()

        for stock in mystocks_to_check:
            time.sleep(10)
            print("Checking: long: "+stock)
            find_stock_to_buy_or_sell(stock, 50)
            print("Checking: short: "+stock)
            find_stock_to_buy_or_sell(stock, 5)
        # time.sleep(12800)
        for currency in myCurrencies:
            print("Checking: long: "+currency)
            find_stock_to_buy_or_sell(currency, 70)
            print("Checking: short: "+currency)
            find_stock_to_buy_or_sell(currency, 15)
        # time.sleep(12800)
        # for i in range(1000,0,-1):
        #     sys.stdout.write(str(i)+' ')
        #     sys.stdout.flush()
        #     time.sleep(10)



print("before")
debug_email = 0  # 1 or 0

if debug_email == 1 :
    print('test email')
    sent_email_to_inform('TEST', 'TESTREADY', 'ALL GOOD!! COMMENT')
    exit()

job()
# schedule.every().day.at("11:48").do(job)
# schedule.every(1).hours.until("11:08").do(job)
# print("after")
# while 1:
#     schedule.run_pending()
#     time.sleep(1)

# schedule.clear()

print("end")
