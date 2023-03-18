import json
import requests
import base64
import time
import re

# Bearer A21AALuQdDpomJi0M9yFRC093zsvZ_U54fwYBB21fRCdyNNc4wOoItjQdM_okCtW4Mb_XokZCYVja-knyd5vER4a8tT78I8SA

#client_id = 'AcZ03Wisk5lZ4WLYFThhznEc8bR4c5sLf5ZduDDwTuzBF93sud35OGxe6y6xCMPu3-V8LiyY4UBTpXA6'
#secret = 'EMVNx70mZo-gS-54tG1-oe-0ppAIL9bnHtUx5Xj12DHyqiV4SmevFxUTG9IOLlHAd12TM6mJymMEqq4k'



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
		uri = self.scopes['invoices']+'/'+id_invoice+'/send'
		return json.loads(requests.request("POST", uri, headers=headers, json=json_data).text)

	def create_draft_invoice(self, json_data):
		headers = {
	  		'Authorization': self.bearer,
	  		'Content-Type': 'application/json'
		}

		#invoice_number = self.gen_invoice_number()
		#print(invoice_number)

		#json_data['detail']['invoice_number'] = invoice_number
		return json.loads(requests.request("POST", self.scopes['invoices'], headers=headers, json=json_data).text)
		

	def gen_invoice_number(self):
		headers = {
	  		'Authorization': self.bearer,
	  		'Content-Type': 'application/json'
		}
		return json.loads(requests.request("POST", self.scopes['gen-invoice-number'],
			 headers=headers).text)['invoice_number']

	def get_bearer_token(self, client_id: str, secret: str):

		if self.need_new_bearer(client_id, secret):
			payload='grant_type=client_credentials'
			headers = {
			  'Authorization': '',
			  'Content-Type': 'application/x-www-form-urlencoded'
			}
			authorization = self.str2base64(client_id+':'+secret)
			headers['Authorization'] = f'Basic {authorization}'
			response = json.loads(requests.request("POST", self.scopes['get-token'], headers=headers, data=payload).text)
			self.bearer = response['token_type']+' '+response['access_token']

			# save the last config bearer
			self.config['acces_token']['last_client_id'] = client_id
			self.config['acces_token']['last_secret'] = secret
			self.config['acces_token']['bearer']['last_bearer_token'] = response['access_token']
			self.config['acces_token']['bearer']['due_token'] = time.time() + response['expires_in'] - 300

			self.save_config()
		else:
			self.bearer = config['acces_token']['bearer']['last_bearer_token']
	# tools
	def need_new_bearer(self, client_id, secret):
		same_client_id = self.config['acces_token']['last_client_id'] != client_id
		same_secret = self.config['acces_token']['last_secret'] != secret
		invalid_token = re.match("[a-zA-Z0-9_-]+$", self.config['acces_token']['bearer']['last_bearer_token'])
		expired_token = time.time() >= (self.config['acces_token']['bearer']['due_token'] - 3600 )
		return same_client_id or same_secret or invalid_token or expired_token

	def get_id_from_url(self, url):
		url = url.split('/')
		return url[len(url)-1]

	def str2base64(self, texto: str):
		sample_string_bytes = texto.encode("ascii")
		base64_bytes = base64.b64encode(sample_string_bytes)
		return base64_bytes.decode("ascii")

	def format_json_data(self, recipient, items, note='', terms='', invoicer=None, cc=[], website='', tax_id='', phone='', name_recipient=[], address_recipient=None, currency='USD'):
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
		if invoicer != '':
  			template['invoicer']["email_address"] = invoicer
		if website != '':
  			template['invoicer']['website'] = website
		if phone != '':
  			template['invoicer']['phones'] = [{
        				"country_code": "001",
				        "national_number": phone,
				        "phone_type": "MOBILE"
				      }]
		if tax_id != '':
  			template['invoicer']['tax_id'] = tax_id
		if cc:
  			template["additional_recipients"] = cc

		return template

if __name__ == '__main__':
	#response = getAccessToken(client_id, secret)
	#print(response)

	item = [{'name':'software','description':'un programa de facturacion','qty':'2','value':'20.00'}]
	invoice = Invoices()

	data = invoice.format_json_data('yugreaguirre@gmail.com',items=item, 
		note='una nota', terms='terminos', invoicer='akkalame@mail.com', 
		cc=['akk@mail.com','correo@mail.com'])

	
	draft = invoice.create_draft_invoice(data)
	id_invoice = invoice.get_id_from_url(draft['href'])
	print(draft)
	print(id_invoice)
	print(invoice.send_invoice(id_invoice))
	"""
	#print(invoice.gen_invoice_number())
	"""

