# Import the library to make the request to the TomTom API
import requests
import csv, time
import pandas as pd
# Import the Beautiful Soup Library
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.dates as dates
from scipy.ndimage.filters import gaussian_filter1d

my_key='register in https://developer.tomtom.com to get KEY'

# Busca latitud y longitud a partir de una direccion con TomTom API
def FindGeocode(address):
    # Busqueda latitud longitud
    r = requests.get("https://api.tomtom.com/search/2/geocode/" + address + ".xml?countrySet=ES&key=" + my_key)
    print("FindGeocode:",r)
    # Grab the content from our request
    c = r.content
    soup = BeautifulSoup(c)
    lat = soup.find("position").find("lat").string
    lon = soup.find("position").find("lon").string
    return lat, lon

# Rellena la latitud y longitud en el fichero si esta vacio
def RellenaLatLonFile(file_name):
    df = pd.read_csv(file_name)
    cambiado = False
    for index, row in df.iterrows():
        if pd.isnull(row['origen_lat']) or pd.isnull(row['origen_lon']) or pd.isnull(row['destino_lat']) or pd.isnull(row['destino_lon']):
            origen_lat , origen_lon  = FindGeocode(row['direccion_origen'])
            destino_lat, destino_lon = FindGeocode(row['direccion_destino'])
            df['origen_lat'][index] = origen_lat
            df['origen_lon'][index] = origen_lon
            df['destino_lat'][index] = destino_lat
            df['destino_lon'][index] = destino_lon
            cambiado = True
    if cambiado:
        df.to_csv(file_name,index = False)

# Calcula distancia y duracion de ruta entre puntos Origen, Destino (lat,lon)
def CalculaRoute(origen_lat, origen_lon, destino_lat, destino_lon):
    origen = origen_lat + "," + origen_lon
    destino = destino_lat + "," + destino_lon
    # calculateRoute
    r = requests.get("https://api.tomtom.com/routing/1/calculateRoute/" + origen + ":" + destino + "/xml?avoid=unpavedRoads&travelMode=car&key=" + my_key)
    print("CalculaRoute:",r)
    time.sleep(1)
    if r.status_code==200:
        # Grab the content from our request
        c = r.content
        soup = BeautifulSoup(c)
        kms = int(soup.find("lengthinmeters").string)/1000
        mins = int(soup.find("traveltimeinseconds").string)/60
        trafficdelay_mins = int(soup.find("trafficdelayinseconds").string)/60
        timestamp = soup.find("departuretime").string
        return kms, mins, trafficdelay_mins, timestamp
    else:
        return 0, 0, 0, 0

# Guarda los graficos de la ruta por los periodos definidos en period
def GuardaGrafico(dataframe, id_ruta, origen_destino):
    ahora = datetime.now(timezone.utc)
    # diccionario con los periodos y dias asociados
    period = dict(lastday=1, lastweek=9, lastmonth=30)

    for periodo,dias in period.items():
        #print(periodo, dias)
        # filtro Nombre de la ruta y tiempo -dias
        grafico = dataframe[['kms','mins','delay','timestamp','weekday','hour','minute10']][dataframe['nombre']==id_ruta][dataframe['timestamp']>=(ahora - dt.timedelta(days=dias))]
        # media por hora minute10 de dias laborables
        media_mins = dataframe[['kms','mins','delay','timestamp','weekday','hour','minute10']][dataframe['nombre']==id_ruta][dataframe['weekday'].isin([0,1,2,3,4])].groupby(['hour','minute10'])['mins'].mean().reset_index().rename(columns={'mins': 'mins_media'})
        grafico_media = grafico.merge(media_mins, on=('hour','minute10'), how= 'left')

        x = grafico_media['timestamp']
        y = grafico_media['mins']
        ymedia = grafico_media['mins_media']

        #ysmoothed = gaussian_filter1d(y, sigma=2) # It is commented because smoothing you lost max and min values

        fig, ax = plt.subplots(figsize=(10,5))
        ax.plot(x,y,'bo-',markevery=6)
        ax.plot(x,ymedia,'g--')

        quy= y.quantile(0.9)
        for i in range(0,len(y)):
            if y.iloc[i] > quy :
                ax.text(x.iloc[i],y.iloc[i],dt.datetime.strftime(x.iloc[i], '%H') )

        ax.set(xlabel='time (s)', ylabel='minutos',
               title='Duracion (mins) ' + origen_destino + '_' + periodo)
        ax.xaxis.set_minor_locator(dates.HourLocator(interval=6))   # every 4 hours
        ax.xaxis.set_minor_formatter(dates.DateFormatter('%H:%M'))  # hours and minutes
        ax.xaxis.set_major_locator(dates.DayLocator(interval=1))    # every day
        ax.xaxis.set_major_formatter(dates.DateFormatter('\n%Y-%m-%d')) #('\n%d-%m-%Y'))
        ax.grid()
        save_file = "../mysite/static/Tiempos_ruta_" + id_ruta + "_" + periodo + ".png"
        #save_file = "Tiempos_ruta_" + id_ruta + "_" + periodo + ".png"
        fig.savefig(save_file)
        plt.close()

# abre fichero direcciones
while True:
    #file_direcciones = 'direcciones_ida.csv'
    #file_direcciones = 'direcciones_vuelta.csv'
    file_rutas = 'calculo_rutas.csv'
    file_direcciones = 'direcciones_todo.csv'
    RellenaLatLonFile(file_direcciones)
    File = open(file_direcciones)
    reader = csv.reader(File)
    headers = next(reader)[0:]
    # abre fichero para guardar las rutas calculadas
    rutas = open(file_rutas, 'a')
    fn = ['nombre','kms','mins','delay','timestamp','direccion_origen','origen_lat','origen_lon','direccion_destino','destino_lat','destino_lon']
    writer = csv.DictWriter(rutas, fieldnames=fn)
    for row in reader:
        #print("********",row[0],row[1],row[2])
        origen_lat=row[3]
        origen_lon=row[4]
        destino_lat=row[5]
        destino_lon=row[6]
        # calcula ruta
        kms, mins, delay, timestamp = CalculaRoute(origen_lat,origen_lon, destino_lat,destino_lon)
        #print(kms, mins, delay, timestamp)

        # GUARDA DATOS
        writer.writerow({fn[0]:row[0],
                         fn[1]:kms,
                         fn[2]:mins,
                         fn[3]:delay,
                         fn[4]:timestamp,
                         fn[5]:row[1],
                         fn[6]:row[3],
                         fn[7]:row[4],
                         fn[8]:row[2],
                         fn[9]:row[5],
                         fn[10]:row[6]})
    File.close()
    rutas.close()

    # GUARDAR LOS GRAFICOS
    dfd = pd.read_csv(file_direcciones)
    df = pd.read_csv(file_rutas)
    # borra filas con timestamp = 0 de file_rutas
    df = df[df['timestamp']!='0'].dropna()
    df = df.reset_index(drop=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=False)
    df['year'] = df['timestamp'].dt.year
    df['month'] = df['timestamp'].dt.month
    df['weekday'] = df['timestamp'].dt.weekday #Monday=0, Sunday=6
    df['day'] = df['timestamp'].dt.day
    df['hour'] = df['timestamp'].dt.hour
    df['minute10'] = df['timestamp'].dt.minute//10

    for i, row in dfd.iterrows():
        print("GuardaGrafico",dfd['nombre'][i])
        GuardaGrafico(df, dfd['nombre'][i], dfd['direccion_origen'][i] + '-' + dfd['direccion_destino'][i])
    time.sleep(600)