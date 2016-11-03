from flask import Flask, render_template, request, make_response
import os, json
import requests
import logging
import re
#from dateutil import parser

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

notification_url = 'https://console.eu-gb.bluemix.net/status/api/notifications'
regions_url = 'https://console.eu-gb.bluemix.net/status/api/v1/regions'
categories_url = 'https://console.eu-gb.bluemix.net/status/api/v1/categories'
eventtypes_url = 'https://console.eu-gb.bluemix.net/status/api/v1/eventTypes'
statuses_url = 'https://console.eu-gb.bluemix.net/status/api/v1/statuses'
events_url = 'https://console.eu-gb.bluemix.net/events/'



port = int(os.getenv('VCAP_APP_PORT', 8080))
app = Flask(__name__, static_url_path="/static")

@app.context_processor
def description_processor():
  def format_description(text):
    ### Some posts have characters in title or description that upsets some RSS readers.
    ## This is a helper function to clean up the text
    
    t = text.replace('<br>', '\n').replace('&', 'and')
    # Get rid of remainding HTML tags
    ct = re.sub('<.*?>', '', t)
    
    return ct.replace('>','').replace('<','')
  return dict(format_description=format_description)
    

@app.route("/")
def get_options():
  # Render a template that shows all the options and allows generating a feed url based on checkboxes  
  regions = requests.get(regions_url).json()
  categories = requests.get(categories_url).json()
  types = requests.get(eventtypes_url).json()
  form = render_template('inputform.html', regions = regions, categories = categories, types = types)
  
  return form

@app.route("/feed/notifications.rss")
def generate_feed():
  categories = request.args.getlist('categories')
  types = request.args.getlist('eventtypes')
  regions = request.args.getlist('regions')
  subcategories = request.args.getlist('subcategories')
  
  # Get all notifications
  r = requests.get(notification_url)
  
  
  # Filter the notifications
  filtered_notifications = []
  LOGGER.info('Total posts: %i' % len(r.json()))
  for notification in r.json():
    if types:
      LOGGER.debug('Applying types filter')
      if not notification['obj']['type'] in types:
        LOGGER.debug('%s did not pass the filter' % notification['_id'])
        continue
      else:
        LOGGER.debug('%s Passed the filter' % notification['_id'])
    if categories:
      LOGGER.debug('Applying categories filter')
      if not notification['obj']['category'] in categories:
        LOGGER.debug('%s did not pass the filter' % notification['_id'])
        continue
      else:
        LOGGER.debug('%s Passed the filter' % notification['_id'])
    if regions:
      LOGGER.debug('Applying regions filter')
      desired_region = False
      for region in regions:
        if any(d['id'] == region for d in notification["obj"]["regionsAffected"]):
         desired_region = True
      if not desired_region:
        LOGGER.debug('%s did not pass the filter' % notification['_id'])
        continue
      else:
        LOGGER.debug('%s Passed the filter' % notification['_id'])
        
    if subcategories:
      LOGGER.debug('Applying subcategories filter')
      if not notification['obj']['subCategory'] in subcategories:
        LOGGER.debug('%s did not pass the filter' % notification['_id'])
        continue
      else:
        LOGGER.debug('%s Passed the filter' % notification['_id'])
    
    filtered_notifications.append(notification)
  
  LOGGER.debug('Filters applied:')
  LOGGER.debug(regions)
  LOGGER.debug(categories)
  LOGGER.debug(types)
  LOGGER.debug(subcategories)
  LOGGER.info('Filtered posts: %i' % len(filtered_notifications))
  notification_xml = render_template('notifications.rss', notifications=filtered_notifications)
  response = make_response(notification_xml)
  response.headers["Content-Type"] = 'application/rss+xml'
  
  return response

app.run(host='0.0.0.0', port=port)
