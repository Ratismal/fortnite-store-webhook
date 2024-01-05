#!/usr/bin/env python

import json
import requests
import pathlib
import os
import math
from PIL import Image, ImageDraw, ImageColor, ImageFont

pathlib.Path("cache").mkdir(parents=True, exist_ok=True)

config = {}
oldData = []

with open('config.json') as f:
  config = json.load(f)

try:
  with open('cache.json') as f:
    oldData = json.load(f)
except:
  oldData = []

def getImagePath(img):
  ext = pathlib.Path(img['url']).suffix
  p = "cache/{}{}".format(img['id'], ext)
  return p

def checkImage(img):
  p = getImagePath(img)
  if not os.path.isfile(p):
    print("downloading " + p)
    img_data = requests.get(img['url']).content
    with open(p, 'wb') as f:
      f.write(img_data)

endpoint = 'https://fortnite-api.com/v2/shop/br'

response = requests.get(endpoint, headers = {
  'Authorization': config['apiKey']
})
data = response.json()

output = []

entryIds = []

layouts = {}

for entry in data['data']['featured']['entries']:
  entryIds.append(entry['offerId'])

  if entry['offerId'] in oldData:
    continue

  materials = entry['newDisplayAsset']
  item = {
    'regularPrice': entry['regularPrice'],
    'price': entry['finalPrice'],
    'title': '',
    'subtitle': '',
    'bundle': False,
    'image': False
  }
  if materials != None:
    material = materials['materialInstances'][0]
    item['image'] = {
      'id': material['id'],
      'url': material['images']['Background']
    }

    checkImage(item['image'])

  if entry['bundle'] != None:
    item['bundle'] = True
    item['title'] = entry['bundle']['name']
    item['subtitle'] = entry['bundle']['info']
  else:
    firstItem = entry['items'][0]
    item['title'] = firstItem['name']
    item['subtitle'] = firstItem['type']['displayValue']


  layoutId = entry['layout']['id']
  if not layoutId in layouts:
    layouts[layoutId] = {
      'name': entry['layout']['name'],
      'items': []
    }

  layout = layouts[layoutId]
  layout['items'].append(item)


if len(layouts) == 0:
  exit()

# Create Image
COLUMNS = 8
HEIGHT_PER_LAYOUT = 30
TILE_SIZE = 130
HEIGHT_PER_ROW = TILE_SIZE + 60
GAP = 20
height = 0
for key, value in layouts.items():
  height += HEIGHT_PER_LAYOUT
  itemCount = len(value['items'])
  layoutHeight = math.ceil(itemCount / COLUMNS) * (HEIGHT_PER_ROW)
  height += layoutHeight
  print("{} {} {} {}".format(key, math.ceil(itemCount / COLUMNS), layoutHeight, itemCount))

print(height)

fontTitle = ImageFont.truetype('Burbank Big Condensed Black.otf', size = 20)
fontTileTitle = ImageFont.truetype('Burbank Big Condensed Black.otf', size = 14)
fontTileSubtitle = ImageFont.truetype('Burbank Big Condensed Black.otf', size = 12)
whiteColor = ImageColor.getrgb("#FFFFFF")
greyColor = ImageColor.getrgb("#AAAAAA")
redColor = ImageColor.getrgb("#FF0000")
image = Image.new('RGB', (COLUMNS * (TILE_SIZE + GAP) + GAP, height + GAP), color = ImageColor.getrgb("#0c1715"))
draw = ImageDraw.Draw(image)
y = GAP
for key, value in layouts.items():
  x = GAP
  
  draw.text((x, y), value['name'], fill = whiteColor, font = fontTitle)

  y += HEIGHT_PER_LAYOUT

  i = 0
  for item in value['items']:
    if item['image'] != False:
      imgPath = getImagePath(item['image'])
      with Image.open(imgPath) as img:
        resized = img.resize((TILE_SIZE, TILE_SIZE))
        image.paste(resized, (x, y, x + TILE_SIZE, y + TILE_SIZE))

    draw.text((x, y + TILE_SIZE + 5), item['title'], fill = whiteColor, font = fontTileTitle)
    draw.text((x, y + TILE_SIZE + 25), item['subtitle'], fill = whiteColor, font = fontTileSubtitle)

    draw.text((x + TILE_SIZE, y + TILE_SIZE + 25), str(item['price']), fill = whiteColor, font = fontTileSubtitle, anchor = 'ra')

    if item['price'] != item['regularPrice']:
      draw.text((x + TILE_SIZE - 30, y + TILE_SIZE + 25), str(item['regularPrice']), fill = greyColor, font = fontTileSubtitle, anchor = 'ra')
      draw.line([(x + TILE_SIZE - 55, y + TILE_SIZE + 25 + 3), (x + TILE_SIZE - 30, y + TILE_SIZE + 25 + 6)], fill = redColor, width = 1, joint = None)

    x += TILE_SIZE + GAP
    i += 1
    if i >= COLUMNS:
      i = 0
      x = GAP
      y += HEIGHT_PER_ROW
  
  if i != 0:
    y += HEIGHT_PER_ROW

image.save('output.png', 'png')

files = {'file': open('output.png', 'rb')}

requests.post(config['webhook'], data = {
  'content': "Today's Fortnite Shop"
}, files = files)

# with open('output.txt', 'w') as f:
#   f.write(content)
with open('data.json', 'w') as f:
  f.write(json.dumps(data, indent=2))
with open('output.json', 'w') as f:
  f.write(json.dumps(layouts, indent=2))
with open('cache.json', 'w') as f:
  f.write(json.dumps(entryIds, indent=2))