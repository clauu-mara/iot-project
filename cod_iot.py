import json
import time
import urllib.request
from paho.mqtt.client import Client, MQTTv311
import matplotlib.pyplot as plt
import calendar
from datetime import datetime
import csv
import smtplib
import numpy as np





API="Bl6eJ8sxxZ11IXdP2PF85dw3cpVJwxnG" # cheia API din Accuweather
countryCode="RO" # codul pentru Romania utilizat la accesarea locatiei in Accuweather
city=input("City Name: ") # scriem de la tastatura orasul in care vrem sa vedem prognoza pentru 5 zile
#city="Dej" # citim implicit un oras din Ro in care vrem sa vedem prognoza meteo
key="" #initializam 2 parametrii in care salvam datele
data = ""

# citim locatia din Romania de unde vom prelua datele meteo cu aplicatia Accuweather
def getLocation(CountryCode,city):
    search_address="http://dataservice.accuweather.com/locations/v1/cities/"+CountryCode+"/search?apikey="+API+"&q="+city+"&details=true"
    with urllib.request.urlopen(search_address) as search_address:
         data=json.loads(search_address.read().decode())
    location_key=data[0]['Key']
    return(location_key)


# accesam prognoza meteo pe 5 zile create in Accuwather  
def getForecast(location_key):
    daily_forcastUrl="http://dataservice.accuweather.com/forecasts/v1/daily/5day/"+location_key+"?apikey="+API+"&details=true"
    with urllib.request.urlopen(daily_forcastUrl) as daily_forcastUrl:
        data=json.loads(daily_forcastUrl.read().decode())

    # deschidere fisier CSV pt salvarea datelor
    csv_file = open('fisier_iot.csv', 'w') 
    fieldnames = ['Temperatura maxima', 'Temperatura minima', 'Temperatura resimtita', 'Probabilitate de precipitatii']
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
         
           
    precipitatie_pie = []
    zile=[]

    # preluam datele de pe accuwather
    for key1 in data['DailyForecasts']:
        print("Prognoza meteo pentru data: "+key1['Date'])
        a=key1['Temperature']['Maximum']['Value']
        a=(a-30)/2 # transformam din F in grade Celsius
        print("Temperatura maxima (in grade C) : "+str(a))
        b=key1['Temperature']['Minimum']['Value']
        b=(b-30)/2
        print("Temperatura minima (in grade C) : "+str(b)) 
        c=key1['RealFeelTemperature']['Minimum']['Value']
        c=(c-30)/2
        print("Temperatura resimtita (in grade C) : "+str(c))  
        print("Vant (mi/h) : "+str(key1['Day']['Wind']['Speed']['Value']))
        print("Soarele rasare la ora : "+str(key1['Sun']['Rise']))
        print("Probabilitate de ploaie (%) : "+str(key1['Day']['PrecipitationProbability']))
        print("Probabilitatea sa ninga (%) : "+str(key1['Day']['SnowProbability']))


        #definire client mqtt pentru conectarea cu Orange-ul
        def on_connect(client, userdata, flags, rc):
            print("CONNECTED WITH CODE: " + str(rc))
       
        mqtt_client=Client(client_id="urn:lo:nsid:mqtt:forecast",
                    clean_session=True,
                    protocol=MQTTv311)


        mqtt_client.on_connect=on_connect
        mqtt_client.tls_set()
        mqtt_client.username_pw_set(username="json+device", password="3434b5422df54e0093bc44e54a200c25")

        # trimitem datele in Orange Live Objects

        text = { 'value' : {
            'temperatura maxima': a,
            'temperatura minima': b,
            'temperatura resimtita' : c,
            'probabilitate de ploaie' : key1['Day']['PrecipitationProbability'],
            'probabilitate de ninsoare': key1['Day']['SnowProbability'],

        },   
        }

                        
        mqtt_client.connect(host="liveobjects.orange-business.com", port=8883)
        mqtt_client.loop_start()
        mqtt_client.publish(topic='dev/data', payload=json.dumps(text))
        mqtt_client.loop_stop()

        # incheiere conexiune cu Orange
        mqtt_client.disconnect()    

        # array pt pie chart - punem toate precipiatiile de ploaie din cele 5 zile intr un vector 
        precipitatie_pie.append(key1['Day']['PrecipitationProbability'])
        
        #preluarea datelor pentru primul widget
        y=[key1['Day']['SnowProbability']] # luam datele de pe axa orizontala, probailitatea de ninsoare
        day = datetime.strptime(key1["Date"], "%Y-%m-%dt%H:%M:%S%z") # preluam data in formatul specific 
        x=[calendar.day_name[day.weekday()]] # preluam ziua din saptamana asociata fiecarei probabilitate de ninsoare
        zile.append(calendar.day_name[day.weekday()])
        
        
        #scriere date in fisierul CSV
        writer.writerow({'Temperatura maxima': str(a), 'Temperatura minima': str(b), 'Temperatura resimtita': str(c), 'Probabilitate de precipitatii' : str(key1['Day']['PrecipitationProbability'])})         
    
         # creare widget 1 - Probabilitate ninsoase => HISTOGRAMA
        plt.figure(1)
        plt.bar(x, y.pop()+1)
        plt.ylabel('Probabilitatea sa ninga')
        plt.xlabel('Days')
        plt.title('Ninsoare in urmatoarele 5 zile')
        plt.ylim(0,100)

    #creare widget 2 - Probabilitate de ploaie => PIE CHART
    #fig =plt.figure(figsize = (10,7))
    #plt.pie(precipitatie_pie, labels=zile, autopct='%1.1f%%', startangle=90)
    #plt.axis('equal')
    #plt.title('Probabilitate de ploaie pentru urmatoarele 5 zile ')

    csv_file.close()    # inchidem fisierul 
     
    #creare widget 2 - Probabilitate de ploaie => PIE CHART

    fig2 =plt.figure(figsize = (10,7))
    ma = 0
    for z in precipitatie_pie:
        ma += z
    ma /= 5
    vec = np.array([ma,100-ma])
    plt.pie(vec, labels=['Ploaie','Soare'], autopct='%1.1f%%', startangle=90)
    plt.axis('equal')
    plt.title('Probabilitatea de ploaie/soare in urmatoarele 5 zile ')

    plt.show() # afisam widget urile

    # trimitere e mail

    EMAIL_ADDRESS = "aplicatieiot@gmail.com"
    PASSWORD = "aplicatieiot1998"
    msg = "ATENTIE! Va fi o zi ploioasa! Nu va uitati umbrela! Sansele ridicate de ploaie sunt in zilele:"
    
    for sansa in range(len(precipitatie_pie)):
            if((precipitatie_pie[sansa])>50): # putem modifica valoarea
                msg+= zile[sansa]+" "
            
                        
    def send_email(subject, message):
        
        try:
            server = smtplib.SMTP('smtp.gmail.com:587')
            server.ehlo()
            server.starttls()
            server.login(EMAIL_ADDRESS, PASSWORD)
            message = 'Subject: {}\n\n{}'.format(subject, msg)
            server.sendmail(EMAIL_ADDRESS, EMAIL_ADDRESS, message)
            server.quit()
            print("Success: Email sent!")
        except:
            print("Email failed to send.")


    subject = "Notificare!"
    msg+=" !"
    send_email(subject, msg)
     
#3434b5422df54e0093bc44e54a200c25 cheia API din Orange live objects

key=getLocation(countryCode,city)
getForecast(key)