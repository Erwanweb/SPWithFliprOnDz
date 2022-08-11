#!/usr/bin/python
# -*- coding: latin-1 -*-

import requests

url = "https://apis.goflipr.com/OAuth2/token"

payload='grant_type=password&username=erwanleu@yahoo.com&password=Texavery1'
headers = {
  'Content-Type': 'application/x-www-form-urlencoded',
  'Cookie': 'ARRAffinity=e7eb41d88dc1d0d267ff2d136e49ca19a13d2c61504aad914f4e92e340e46d11; ARRAffinitySameSite=e7eb41d88dc1d0d267ff2d136e49ca19a13d2c61504aad914f4e92e340e46d11'
}

response = requests.request("POST", url, headers=headers, data=payload)
data = response.text
data2 = "Bearer " + data.split('"')[3]



url = "https://apis.goflipr.com/modules/1A138E/survey/last"

payload={}
headers = {
  'Authorization': data2,
  'Cookie': 'ARRAffinity=e7eb41d88dc1d0d267ff2d136e49ca19a13d2c61504aad914f4e92e340e46d11; ARRAffinitySameSite=e7eb41d88dc1d0d267ff2d136e49ca19a13d2c61504aad914f4e92e340e46d11'
}

response = requests.request("GET", url, headers=headers, data=payload)

print(response.text.encode('unicode-escape').decode('utf-8'))
