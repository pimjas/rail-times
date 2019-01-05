import requests
import atexit
import re
import xmltodict
import os
import time
from PIL import Image, ImageFont, ImageDraw
from rgbmatrix import Adafruit_RGBmatrix
from collections import OrderedDict

# From where? (station code)
stationfrom = "WAT"

# To where? (station code)
stationto = ""

# Screen matrix width
width = 128

# Screen matrix height
height = 32

matrix = Adafruit_RGBmatrix(32,4)
fps = 20

tcol1 = (220, 160, 0)
tcol2 = (200, 64, 64)

# Switches to 1 if there are train services to display

trfnd=0

# Information line if no train services to display
trinf=''

# Scheduled time of departure
trstd=[]

# Estimated time of departure
tretd=[]

# Destination
trdst=[]

# Operator
tropr=[]

# Platform
trplt=[]

# Subsequent calling points
trscp=[]

# Key consisting of train IDs to see if screen needs to be refreshed or not
trkey=''

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def fetch_railtime():
    
    global stationfrom
    global stationto
    global trfnd
    global trinf
    global trstd
    global tretd
    global trdst
    global tropr
    global trplt
    global trscp
    global trkey

    trfnd=0

    # Information line if no train services to display
    trinf=''

    # Scheduled time of departure
    trstd=[]

    # Estimated time of departure
    tretd=[]

    # Destination
    trdst=[]

    # Operator
    tropr=[]

    # Platform
    trplt=[]

    # Subsequent calling points
    trscp=[]
    
    # Key consisting of train IDs to see if screen needs to be refreshed or not
    trkey=''
    
    url="https://lite.realtime.nationalrail.co.uk/OpenLDBWS/ldb11.asmx"
    headers = {'content-type': 'application/soap+xml'}
    #headers = {'content-type': 'text/xml'}

    body = """<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:typ="http://thalesgroup.com/RTTI/2013-11-28/Token/types" xmlns:ldb="http://thalesgroup.com/RTTI/2017-10-01/ldb/">
       <soap:Header>
          <typ:AccessToken>
             <typ:TokenValue>231ebb31-3981-4838-be44-2de3bba15aa7</typ:TokenValue>
          </typ:AccessToken>
       </soap:Header>
       <soap:Body>
          <ldb:GetDepBoardWithDetailsRequest>
             <ldb:numRows>5</ldb:numRows>
             <ldb:crs>""" + stationfrom + """</ldb:crs>
             <ldb:filterCrs>""" + stationto + """</ldb:filterCrs>
             <ldb:filterType>to</ldb:filterType>
             <ldb:timeOffset>0</ldb:timeOffset>
             <ldb:timeWindow>120</ldb:timeWindow>
          </ldb:GetDepBoardWithDetailsRequest>
       </soap:Body>
    </soap:Envelope>"""
    
    response = requests.post(url,data=body,headers=headers)
    if response.status_code != 200:
        trinf = 'HTTP ' + str(response.status_code) + ': ' + response.reason
        trfnd = 0
    else:
        soapresp = response.text
        #print (soapresp)
        srp = xmltodict.parse(soapresp)
        if 'lt7:trainServices' in srp['soap:Envelope']['soap:Body']['GetDepBoardWithDetailsResponse']['GetStationBoardResult'].keys():
            i = 0
            while i < len(srp['soap:Envelope']['soap:Body']['GetDepBoardWithDetailsResponse']['GetStationBoardResult']['lt7:trainServices']['lt7:service']):
                sr = srp['soap:Envelope']['soap:Body']['GetDepBoardWithDetailsResponse']['GetStationBoardResult']['lt7:trainServices']['lt7:service'][i]
                #print(sr)

                # Add train ID to train key
                trkey = trkey + sr['lt4:serviceID']
                
                # Scheduled time of departure
                trstd.append(sr['lt4:std'])

                # Estimated time of departure
                tretd.append(sr['lt4:etd'])

                # If true, only one destination so simples. If false, two destinations so need to read both destinations and subsequent station lists
                if 'lt4:locationName' in sr['lt5:destination']['lt4:location']:
                    trdst.append(sr['lt5:destination']['lt4:location']['lt4:locationName'])
                    cplist=sr['lt7:subsequentCallingPoints']['lt7:callingPointList']['lt7:callingPoint']
                    if 'lt7:locationName' in cplist:
                        trscp.append(cplist['lt7:locationName'] + ' only')
                    else:
                        dlist = cplist[0]['lt7:locationName']
                        j = 1
                        while j < len(cplist):
                            dlist = str(dlist) + ', ' + str(cplist[j]['lt7:locationName'])
                            j = j + 1
                        trscp.append(dlist)
                else:
                    trdst.append(sr['lt5:destination']['lt4:location'][0]['lt4:locationName'] + ' & ' + sr['lt5:destination']['lt4:location'][1]['lt4:locationName'])
                    cplist = sr['lt7:subsequentCallingPoints']['lt7:callingPointList'][0]['lt7:callingPoint']
                    if 'lt7:locationName' in cplist:
                        dlist = cplist['lt7:locationName'] + ' only'
                    else:
                        dlist = cplist[0]['lt7:locationName']
                        j = 1
                        while j < len(cplist):
                            dlist = str(dlist) + ', ' + str(cplist[j]['lt7:locationName'])
                            j = j + 1

                    cplist = sr['lt7:subsequentCallingPoints']['lt7:callingPointList'][1]['lt7:callingPoint']
                    dlist = str(dlist) + '. This train divides in ' + cplist[0]['lt7:locationName'] + ' with a portion calling at ' + cplist[1]['lt7:locationName']
                    j = 2
                    while j < len(cplist):
                        dlist = str(dlist) + ', ' + str(cplist[j]['lt7:locationName'])
                        j = j + 1
                    trscp.append(dlist)

                # Train operator
                tropr.append(sr['lt4:operator'])

                # If true, platform number, if false, dash
                if 'lt4:platform' in sr:
                    trplt.append(sr['lt4:platform'])
                else:
                    trplt.append('-')

                # Format the data for screen and spit it out

                stdf = sr['lt4:std'][0:2] + sr['lt4:std'][3:5]
                if is_number(tretd[i][0:2]):
                    text1 = stdf + '/' + tretd[i][0:2] + tretd[i][3:5] + ' [' + trplt[i] + '] ' + trdst[i]
                elif tretd[i] == 'On time':
                    text1 = stdf + ' [' + trplt[i] + '] ' + trdst[i]
                else:
                    text1 = stdf + ' [' + trplt[i] + '] ' + trdst[i] + ' [' + tretd[i] + ']'
                text2 = tropr[i] + ' service calling at ' + trscp[i] + '.'   

                i = i + 1
            trfnd = 1

        elif 'lt4:nrccMessages' in srp['soap:Envelope']['soap:Body']['GetDepBoardWithDetailsResponse']['GetStationBoardResult'].keys():
            trfnd = 0
            trinf = ''
            i = 0
            while i < len(srp['soap:Envelope']['soap:Body']['GetDepBoardWithDetailsResponse']['GetStationBoardResult']['lt4:nrccMessages']['lt:message']):
                sr = srp['soap:Envelope']['soap:Body']['GetDepBoardWithDetailsResponse']['GetStationBoardResult']['lt4:nrccMessages']['lt:message'][i]
                trinf = trinf + re.sub('<[^<]+?>', '', sr)
                i = i + 1

        else:
            trfnd = 0
            trinf = 'No train information is currently available.'
            
fetch_railtime()
    
font = ImageFont.load('pilfonts/helvR08.pil')
#font = ImageFont.load_default()
#font = ImageFont.load('pilfonts/luRS08.pil')

# Determine how long animation goes on for
if trfnd == 1:
    maxwidth = 128 + font.getsize(tropr[0] + ' service calling at ' + trscp[0] + '.')[0]
else:
    maxwidth = 128 + font.getsize(trinf)[0]

q = 0
r = 0
k = 0
l = 0
m = 0
n = 1
p = 0

newtrain = 0

#if maxwidth < 500:
#    limit = 500
#else:
#    limit = maxwidth
limit = 1500
image=[]

def clearOnExit():
    matrix.Clear()

atexit.register(clearOnExit)

image       = Image.new('RGB', (width, height))
draw        = ImageDraw.Draw(image)
currentTime = 0.0
prevTime    = 0.0

yoffset = -2
y1 = 0 + yoffset
y2 = 10 + yoffset
y3 = 20 + yoffset
y3a = 0

while True:
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    
    if newtrain > 0:
        draw.text((0,y1),"HOLD", fill=l1col, font=font)
        newtrain = newtrain - 1
        q = q + 1
        continue
    
    # Fetch information again after 30 seconds
    if p > (30000/((1/fps))*1000):
        trkey2 = trkey
        print ('1: '+ trkey2)
        fetch_railtime()
        print ('2: '+ trkey)
        p = 0
        if trkey2 != trkey:
            newtrain = 40
            if trfnd == 1:
                maxwidth = 128 + font.getsize(tropr[0] + ' service calling at ' + trscp[0] + '.')[0]
            else:
                maxwidth = 128 + font.getsize(trinf)[0]
            q = 0
            r = 0
            k = 0
            l = 0
            m = 0
            n = 1
            #if maxwidth < 500:
            #    limit = 500
            #else:
            #    limit = maxwidth

    # Counter for alternate time display in case of delay
    if r >= 40:
        if k == 1:
            k = 0
        else:
            k = 1
        r = 0


    # Counter for third train display
    if len(trstd) > 2:
        if m > 160:
            if n == 1:
                n = 2
                y3a = 10
            else:
                n = 1
                y3a = 10
            m = 0
        else:
            m = m + 1

    # Counter for train destination display in case needed
    maxwidth2 = 0
    if len(trdst) > 1:
        if font.getsize(trdst[n])[0] > font.getsize(trdst[0])[0]:
            maxwidth2 = font.getsize(trdst[n])[0]
        else:
             maxwidth2 = font.getsize(trdst[0])[0]
    if l > 96+maxwidth2:
        l = 0

    #Train found
    if trfnd == 1:

        #Draw first line

        if is_number(tretd[0][0:2]) == False and tretd[0] != 'On time' and k == 1:
            line1 = tretd[0]       
            l1col = tcol2
        else:
            line1 = trdst[0]
            l1col = tcol1

        if font.getsize(line1)[0] > 92:
            draw.text((128-l,y1),line1, fill=l1col, font=font)
        else:
            draw.text((36,y1),line1, fill=l1col, font=font)

        draw.rectangle([(0,0),(34,10)],fill=(0,0,0))

        if is_number(tretd[0][0:2]) & k == 1:
            draw.text((0,y1),tretd[0], fill=tcol2, font=font)
        elif is_number(tretd[0][0:2]) & k == 0:
            draw.text((0,y1),trstd[0], fill=tcol1, font=font)
        elif tretd[0] == 'On time':
            draw.text((0,y1),trstd[0], fill=tcol1, font=font)


        #Draw third line for trains 2/3 in case there is one
        if (len(trstd) > 1):

            if is_number(tretd[n][0:2]) == False and tretd[n] != 'On time' and k == 1:
                line2 = tretd[n]       
                l2col = tcol2
            else:
                line2 = trdst[n]
                l2col = tcol1

            if font.getsize(line2)[0] > 92:
                draw.text((128-l,y3+y3a),line2, fill=l2col, font=font)
            else:
                draw.text((36,y3+y3a),line2, fill=l2col, font=font)

            draw.rectangle([(0,y3),(34,32)],fill=(0,0,0))

            if is_number(tretd[n][0:2]) & k == 1:
                draw.text((0,y3+y3a),tretd[n], fill=tcol2, font=font)
                draw.text((100,y1),str(n) + ' ' + str(p), fill=(255,255,255), font=font)
            elif is_number(tretd[n][0:2]) & k == 0:
                draw.text((0,y3+y3a),trstd[n], fill=tcol1, font=font)
                draw.text((100,y1),str(n) + ' ' + str(p), fill=(255,255,255), font=font)
            elif tretd[n] == 'On time':
                draw.text((0,y3+y3a),trstd[n], fill=tcol1, font=font)
                draw.text((100,y1),str(n) + ' ' + str(p), fill=(255,255,255), font=font)

        # Draw information line for first train and scroll
        draw.text((129-q,y2),tropr[0] + ' service calling at ' + trscp[0] + '.', fill=tcol1, font=font)

        # If there are no trains there is an information message. Display it
    elif trfnd == 0:
        pos = 126-q
        #draw.point((1,1), fill=(0,0,0))
        draw.text( (pos, y2) , trinf, fill=(255,255,255), font=font)

    if y3a > 0:
        y3a = y3a - 1
    q = q + 1
    r = r + 1
    l = l + 1
    p = p + 1
    
    currentTime = time.time()
	timeDelta   = (1.0 / fps) - (currentTime - prevTime)
	if(timeDelta > 0.0):
		time.sleep(timeDelta)
	prevTime = currentTime
    
    matrix.SetImage(image.im.id, 0, 0)

#image[0].save('screen.gif',save_all=True,append_images=image[1:],duration=40,loop=0)
