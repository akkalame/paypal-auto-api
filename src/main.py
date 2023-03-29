import json
import requests
import base64
import time
import re
import os
from bs4 import BeautifulSoup

class Invoices:
	def __init__(self):
		self.bearer = ''
		self.scopes = {
			'gen-invoice-number':'https://api-m.paypal.com/v2/invoicing/generate-next-invoice-number',
			'invoices':'https://api-m.paypal.com/v2/invoicing/invoices',
			'get-token':'https://api-m.paypal.com/v1/oauth2/token'
		}

		self.load_config()

	def load_config(self):
		with open('config.json', mode='r') as f:
			self.config = json.loads(f.read())

	def save_config(self):
		with open('config.json', mode='w') as f:
			f.write(json.dumps(self.config))
			
	def send_invoice(self, id_invoice):
		headers = {
	  		'Authorization': self.bearer,
	  		'Content-Type': 'application/json',
	  		"PayPal-Request-Id":"b1d1f06c7246c"
		}
		json_data = {
			'send_to_invoicer': False,
			'send_to_recipient': True
		}
		endpoint = self.scopes['invoices']+'/'+id_invoice+'/send'
		return json.loads(requests.request("POST", endpoint, headers=headers, json=json_data).text)

	def create_draft_invoice(self, json_data):
		headers = {
	  		'Authorization': self.bearer,
	  		'Content-Type': 'application/json'
		}

		invoice_number = self.gen_invoice_number()

		json_data['detail']['invoice_number'] = invoice_number
		return json.loads(requests.request("POST", self.scopes['invoices'], headers=headers, json=json_data).text)
		
	def gen_invoice_number(self):
		headers = {
	  		'Authorization': self.bearer,
	  		'Content-Type': 'application/json'
		}
		return json.loads(requests.request("POST", self.scopes['gen-invoice-number'],
			 headers=headers).text)['invoice_number']

	def list_invoices(self, page=1, page_size=100):
		headers = {
	  		'Authorization': self.bearer,
	  		'Content-Type': 'application/json'
		}
		endpoint = self.scopes['invoices']+'?page='+str(page)+'&page_size='+str(page_size)

		return json.loads(requests.request("GET", endpoint, headers=headers).text)

	def send_reminder(self, id_invoice, subject, note):
		headers = {
	  		'Authorization': self.bearer,
	  		'Content-Type': 'application/json'
		}
		json_data = {
			'subject': subject,
			'note': note
		}
		endpoint = self.scopes['invoices']+'/'+id_invoice+'/remind'
		print(requests.request("POST", endpoint, headers=headers, json=json_data).text)

	def get_bearer_token(self, client_id: str, secret: str):
		#print(self.need_new_bearer(client_id, secret))
		if not self.need_new_bearer(client_id, secret):
			payload='grant_type=client_credentials'
			headers = {
			  'Authorization': '',
			  'Content-Type': 'application/x-www-form-urlencoded'
			}
			authorization = self.str2base64(client_id+':'+secret)
			headers['Authorization'] = f'Basic {authorization}'
			response = json.loads(requests.request("POST", self.scopes['get-token'], headers=headers, data=payload).text)
			print(response, '\n')
			try:
				self.bearer = response['token_type']+' '+response['access_token']

				# save the last config bearer
				self.config['acces_token']['last_client_id'] = client_id
				self.config['acces_token']['last_secret'] = secret
				self.config['acces_token']['bearer']['last_bearer_token'] = response['token_type']+' '+response['access_token']
				self.config['acces_token']['bearer']['due_token'] = time.time() + response['expires_in'] - 300

				self.save_config()
			except Exception as e:
				with open('error.log', 'a') as f:
					f.write(str(e)+'\n')
				return 'Error getting bearer token'+str(e)
		else:
			self.bearer = self.config['acces_token']['bearer']['last_bearer_token']
	# tools
	def need_new_bearer(self, client_id, secret):
		same_client_id = self.config['acces_token']['last_client_id'] == client_id
		same_secret = self.config['acces_token']['last_secret'] == secret
		valid_token = re.match("^Bearer [a-zA-Z0-9_-]+$", self.config['acces_token']['bearer']['last_bearer_token'])
		
		expired_token = time.time() <= (self.config['acces_token']['bearer']['due_token'] - 1800 )
		return same_client_id and same_secret and valid_token and expired_token

	def get_id_from_url(self, url):
		url = url.split('/')
		return url[len(url)-1]

	def str2base64(self, texto: str):
		sample_string_bytes = texto.encode("ascii")
		base64_bytes = base64.b64encode(sample_string_bytes)
		return base64_bytes.decode("ascii")

	def format_json_data(self, recipient, items, note='', terms='', invoicer='', cc=[],
			website='', tax_id='', phone='', name_recipient=[], business_name='',
			address_recipient=None, currency='USD'):
		
		with open('data_template.json', mode='r') as f:
			template = json.loads(f.read())

		if recipient != '':
			template['primary_recipients'] = [{"billing_info": {"email_address": recipient}}]
		if name_recipient:
			#print(template)
			template['primary_recipients'][0]['billing_info']['name'] = {'given_name':name_recipient[0],
																		'surname':name_recipient[1]}
			template['primary_recipients'][0]['shipping_info'] = {"name":{
																		'given_name':name_recipient[0],
																		'surname':name_recipient[1]}
																}
		if address_recipient:
			address = {
				"address_line_1": address_recipient[0],
				"admin_area_2": address_recipient[1],
				"admin_area_1": address_recipient[2],
				"postal_code": address_recipient[3],
				"country_code": address_recipient[4]
		    }
			template['primary_recipients'][0]['billing_info']['address'] = address
			template['primary_recipients'][0]['shipping_info']['address'] = address
		# items: 
		
		if items:
			for item in items:
				template['items'].append(
					{
						"name": item['name'],
						"description": item['description'],
						"quantity": item['qty'],
						"unit_amount": {
							"currency_code": "USD",
							"value": item['value']
						}
					}
				)
		template['invoicer'] = {}
		template['detail']['currency_code'] = currency
		if note:
			template['detail']['note'] = note
		if terms:
			template['detail']['terms_and_conditions'] = terms
		if invoicer != '' and invoicer != None:
  			template['invoicer']["email_address"] = invoicer
		if website != '':
  			template['invoicer']['website'] = website
		if phone != '':
  			template['invoicer']['phones'] = [{
        				"country_code": "001",
				        "national_number": phone,
				        "phone_type": "MOBILE"
				      }]
		if business_name != '' and business_name != None:
			template['invoicer']["business_name"] = {"business_name": business_name}
		#template['invoicer']["business_name_validation"] = {"business_name": "akk ere"}

		if tax_id != '' and tax_id != None:
  			template['invoicer']['tax_id'] = tax_id
		if cc:
  			template["additional_recipients"] = cc

		return template



def make_config():
	content = {"acces_token": {
				"last_client_id": "", 
				"last_secret": "", 
				"bearer": {
					"last_bearer_token": "",
					"due_token": 0
					}
				}
			}

	with open('config.json', 'w') as f:
		json.dump(content, f)

def time_now():
	url = f'https://unixtime.org/'
	response = requests.get(url)
	soup = BeautifulSoup(response.content, 'html.parser')

	return int(soup.find('div', class_='epoch h1').get_text())

# verifica que el usuario este autorizado
def check_licence(user='huzu'):
	url = f'https://raw.githubusercontent.com/akkalame/paypal-auto-api/develop/licencias/{user}.txt'
	response = requests.get(url)
	try:
		soup = BeautifulSoup(response.content, 'html.parser')
		expire_time = int(soup.get_text())

		return expire_time > time_now() 
	except Exception as e:
		with open('error.log', 'a') as f:
			f.write(str(e)+'\n')
		return False

def woke():
	if not os.path.exists('./config.json'):
		make_config()


