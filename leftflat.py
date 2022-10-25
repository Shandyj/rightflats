import requests
from bs4 import BeautifulSoup
import sqlite3
import slack
import os
from pathlib import Path
from dotenv import load_dotenv

ExportPayload = []


##########################################
con = sqlite3.connect("rightflat.db")
cur = con.cursor()

cur.execute('''CREATE TABLE IF NOT EXISTS rightflats
                (id integer PRIMARY KEY, title text, price text, location text, url text)''')

########################################
# initializing slack client
env_path = Path('.') / 'dot.env'
load_dotenv(dotenv_path=env_path)
client = slack.WebClient(token=os.environ['SLACK_TOKEN'])


url = 'https://www.rightmove.co.uk/property-to-rent/find.html?locationIdentifier=REGION%5E93598&minBedrooms=2&maxPrice=1300&radius=3.0&propertyTypes=&includeLetAgreed=false&mustHave=&dontShow=&furnishTypes=&keywords='

result = requests.get(url)
soup = BeautifulSoup(result.text, 'html.parser')

#print(soup)
# with open('sample.txt', 'w') as f:
#    f.write('dict = ' + str(soup) + '\n')

ListingContainer = soup.select('div[data-test*="propertyCard-"]')

for Listing in ListingContainer:
    ListingURL = "https://www.rightmove.co.uk" + Listing.select_one('a[class="propertyCard-link"]').attrs['href']
    ListingID = ListingURL.split('/')[-2].strip("#")
    follower = requests.get(ListingURL)
    followersoup = BeautifulSoup(follower.text, 'html.parser')
    ListingAvailable = followersoup.select_one('dl[class="_2E1qBJkWUYMJYHfYJzUb_r"] > div > dd').text.split("/")

    DesiredMonths = ['12']
    
    if any(c in ListingAvailable[len(ListingAvailable)-2] for c in DesiredMonths):


        print(ListingAvailable)

        ListingPrice = Listing.select_one('span[class="propertyCard-priceValue"]').text
        print(ListingPrice)
        ListingLocation = Listing.select_one('address[class="propertyCard-address"] > span').text
        print(ListingLocation)
    
        ListingTitle = Listing.select_one('h2[class="propertyCard-title"]').text.strip()
        print(ListingTitle)

        ExportPayload.append((ListingID, ListingTitle, ListingPrice, ListingLocation, ListingURL))
    else:
        continue
    

for PayloadIterator in ExportPayload:
    print(PayloadIterator[0] + "is being processed")
    cur.execute("""SELECT id 
                FROM rightflats
                WHERE id=?""",
                (PayloadIterator[0],))
    result = cur.fetchone()
    if result:
        print(PayloadIterator[0] + " found")
    else:
        cur.execute('''INSERT OR IGNORE INTO rightflats VALUES
                   (?, ?, ?, ?, ?)''', PayloadIterator)
        print(
            PayloadIterator[0] + " non existent, adding to database and sending notification")
        con.commit()
         ###################################################################################
     # contacting user via slack api
        FinalPayload = [

            {
                "type": "header",
                "text": {
                        "type": "plain_text",
                        "text": "Rightmove Property Found\n{}".format(PayloadIterator[0])
                }
            },
            {
                "type": "section",
                "fields": [
                        {
                            "type": "mrkdwn",
                            "text": "*Name:*\n{}".format(PayloadIterator[1])
                        },
                    {
                            "type": "mrkdwn",
                            "text": "*Find it here:*\n<{}|Click ME>".format(PayloadIterator[4])
                    }
                ]
            },
            {
                "type": "section",
                "fields": [
                        {
                            "type": "mrkdwn",
                            "text": "*Price:*\n{}".format(PayloadIterator[2])
                        },
                    {
                            "type": "mrkdwn",
                            "text": "{}".format(PayloadIterator[3])
                    }
                ]
            }

        ]
        FinalPayload = str(FinalPayload)

        client.chat_postMessage(channel="#flathunt", blocks=FinalPayload)

    
