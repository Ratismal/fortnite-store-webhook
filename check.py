#!/usr/bin/env python

import json
import requests
import pathlib
import os
import math
from PIL import Image, ImageDraw, ImageColor, ImageFont
from datetime import datetime, timezone

pathlib.Path("cache").mkdir(parents=True, exist_ok=True)

config = {}
oldData = {}
oldEntryIds = []

with open('config.json') as f:
  config = json.load(f)

try:
  with open('cache.json') as f:
    oldEntryIds = json.load(f)
except:
  oldEntryIds = []
try:
  with open('data.json') as f:
    oldData = json.load(f)
except:
  oldData = None

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

endpoint = 'https://fortnite-api.com/v2/shop'

response = requests.get(endpoint, headers = {
  'Authorization': config['apiKey']
})
data = response.json()

# print(data)

output = []

entryIds = []

addedLayouts = {}
removedLayouts = {}

def process_entry(entry, layouts):
  item = {
    'regularPrice': entry['regularPrice'],
    'price': entry['finalPrice'],
    'title': '',
    'subtitle': '',
    'bundle': False,
    'image': False,
    'colors': {
      'color1': '004e66ff',
      'color2': '000a2eff',
      'color3': '00253dff',
      'textBackgroundColor': '000a2eff'
    }
  }

  if 'newDisplayAsset' in entry:
    materials = entry['newDisplayAsset']

    if len(materials['materialInstances']) > 0:
      material = materials['materialInstances'][0]
      url = ""
      if "Background" in material['images']:
        url = material['images']['Background']
      elif "OfferImage" in material['images']:
        url = material['images']['OfferImage']
      item['image'] = {
        'id': material['id'],
        'url': url
      }
      checkImage(item['image'])

    if len(materials['renderImages']) > 0:
      material = materials['renderImages'][0]
      item['image'] = {
        'id': material['fileName'],
        'url': material['image']
      }
      checkImage(item['image'])

  if 'bundle' in entry:
    item['bundle'] = True
    item['title'] = entry['bundle']['name']
    item['subtitle'] = entry['bundle']['info']
  elif 'items' in entry:
    if len(entry['items']) > 0:
      firstItem = entry['items'][0]
      item['title'] = firstItem['name']
      item['subtitle'] = firstItem['type']['displayValue']
  elif 'brItems' in entry:
    if len(entry['brItems']) > 0:
      firstItem = entry['brItems'][0]
      item['title'] = firstItem['name']
      item['subtitle'] = firstItem['type']['displayValue']
  elif 'tracks' in entry:
    if len(entry['tracks']) > 0:
      firstItem = entry['tracks'][0]
      item['title'] = firstItem['title']
      item['subtitle'] = 'Jam Track'
      item['image'] = {
        'id': firstItem['devName'],
        'url': firstItem['albumArt']
      }
      checkImage(item['image'])
  elif 'instruments' in entry:
    if len(entry['instruments']) > 0:
      firstItem = entry['instruments'][0]
      item['title'] = firstItem['name']
      item['subtitle'] = firstItem['type']['displayValue']

  if 'colors' in entry:
    item['colors'] = entry['colors']

  if 'layout' in entry:
    entryLayout = entry['layout']
    layoutId = entryLayout['id']
    if not layoutId in layouts:
      layouts[layoutId] = {
        'name': entryLayout['name'],
        'items': []
      }

    layout = layouts[layoutId]
    layout['items'].append(item)

for entry in data['data']['entries']:
  # print(entry)
  entryIds.append(entry['offerId'])

  if entry['offerId'] in oldEntryIds:
    continue

  process_entry(entry, addedLayouts)

if oldData is not None:
  for entry in oldData['data']['entries']:
    if entry['offerId'] in entryIds:
      continue

    process_entry(entry, removedLayouts)

# Create Image
COLUMNS = 8
HEIGHT_PER_LAYOUT = 30
TILE_SIZE = 130
HEIGHT_PER_ROW = TILE_SIZE + 60
GAP = 20

def calculate_height(layouts):
  height = 0

  for key, value in layouts.items():
    height += HEIGHT_PER_LAYOUT
    itemCount = len(value['items'])
    layoutHeight = math.ceil(itemCount / COLUMNS) * (HEIGHT_PER_ROW)
    height += layoutHeight
    print("{} {} {} {}".format(key, math.ceil(itemCount / COLUMNS), layoutHeight, itemCount))
  
  return height

fontTitle = ImageFont.truetype('Burbank Big Condensed Black.otf', size = 20)
fontTileTitle = ImageFont.truetype('Burbank Big Condensed Black.otf', size = 14)
fontTileSubtitle = ImageFont.truetype('Burbank Big Condensed Black.otf', size = 12)
whiteColor = ImageColor.getrgb("#FFFFFF")
greyColor = ImageColor.getrgb("#AAAAAA")
redColor = ImageColor.getrgb("#FF0000")

def create_image(title, layouts, bg_color, filename):
  if len(layouts) == 0:
    print("Skipping {}".format(filename))
    return()

  height = calculate_height(layouts)

  image = Image.new('RGB', (COLUMNS * (TILE_SIZE + GAP) + GAP, height + GAP), color = ImageColor.getrgb(bg_color))
  draw = ImageDraw.Draw(image)
  y = GAP
  for key, value in layouts.items():
    x = GAP
    
    draw.text((x, y), value['name'], fill = whiteColor, font = fontTitle)

    y += HEIGHT_PER_LAYOUT

    i = 0
    for item in value['items']:
      iconPosition = (x, y, x + TILE_SIZE, y + TILE_SIZE)

      draw.rectangle(
        (iconPosition[0], iconPosition[1], iconPosition[2] - 1, iconPosition[3] - 1),
        ImageColor.getrgb('#' + item['colors']['color1']))

      if item['image'] != False:
        imgPath = getImagePath(item['image'])
        with Image.open(imgPath) as img:
          resized = img.resize((TILE_SIZE, TILE_SIZE))
          converted = resized.convert('RGBA')
          alpha = converted.convert('LA')
          image.paste(converted, iconPosition, mask=alpha)

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

  print("Generating {}".format(filename))

  image.save(filename, 'png')

  files = {'file': open(filename, 'rb')}
  requests.post(config['webhook'], data = {
    'content': title
  }, files = files)

today = datetime.now(timezone.utc)
d = today.strftime("%B %d, %Y")
create_image("# Today's Fortnite Shop - {} UTC\n## New Items".format(d), addedLayouts, "#0c1715", "added.png")
create_image("## Removed Items", removedLayouts, "#210202", "removed.png")

# with open('output.txt', 'w') as f:
#   f.write(content)
with open('data.json', 'w') as f:
  f.write(json.dumps(data, indent=2))
# with open('output.json', 'w') as f:
#   f.write(json.dumps(layouts, indent=2))
with open('cache.json', 'w') as f:
  f.write(json.dumps(entryIds, indent=2))
