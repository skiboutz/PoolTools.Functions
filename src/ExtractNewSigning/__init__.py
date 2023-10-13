import logging
import os
import tempfile
import azure.functions as func
from datetime import date, datetime, timedelta
import bs4
import pandas as pd
import requests
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError

def scrape_data():
    #Initializing lists that I will manipulate later and seperate into lists of lists
    signing_table_contents_text = [] 
    signing_table_contents_slice=[]
    unsupported_caracters_mapping = str.maketrans({u'\u016b':'u',u'\u2714':'y'})
    
    #creates variable from funciton input to be manipulated
    date_rage_from = date.strftime(date.today() - timedelta(days=1), "%m%d%Y")
    date_rage_to = date.strftime(date.today(), "%m%d%Y")

    url = 'https://www.capfriendly.com/signings/all/all/all/1-15/0-15000000/' + date_rage_from + "-" + date_rage_to

    #Creates a response object to test to see if end of cap data has happened
    status_test = requests.get(url)
    status_test.raise_for_status()
    
    #initial pull of html data from CapFriendly site
    capfriendly = requests.get(url)
    
    #These next 3 lines of code breaks down the site with BS4
    signing_text =bs4.BeautifulSoup(capfriendly.text, "lxml")

    #breaks down the html into just the contents of the <td> tags
    signing_table_row_contents=signing_text.find('tr',{'class':['odd', 'even']})


    #if table is empty return
    if not signing_table_row_contents:
        return
    
    signing_table_contents = signing_table_row_contents('td')
    for x in range(len(signing_table_contents)):
            signing_table_contents_text.append(signing_table_contents[x].getText().translate(unsupported_caracters_mapping))
    
    signing_table_contents_slice = [signing_table_contents_text[i:i + 11] for i in range(0, len(signing_table_contents_text), 11)]

    return signing_table_contents_slice

def get_headers():
    date_rage_from = date.strftime(date.today() - timedelta(days=1), "%m%d%Y")
    date_rage_to = date.strftime(date.today(), "%m%d%Y")

    url = 'https://www.capfriendly.com/signings/all/all/all/1-15/0-15000000/' + date_rage_from + "-" + date_rage_to

    signing_table_headers = []       
    
    #opens CapFriendly and pulls the text from the Table Header tag
    headers = requests.get(url)
    headers_text=bs4.BeautifulSoup(headers.text, "lxml")
    headers_contents = headers_text.find('tr',{'class': 'column_head'})
    for child in headers_contents.findChildren():
        signing_table_headers.append(child.getText())

    return signing_table_headers

def write_data(new_signing) -> str:
    connect_str = os.getenv('EXPORT_AZURE_STORAGE_CONNECTION_STRING')
    # Create the BlobServiceClient object which will be used to create a container client
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)

    # Create a unique name for the container
    container_name = 'signings'

    # Create the container if it doesn't exists
    try:
       blob_service_client.create_container(container_name)
    except ResourceExistsError:
       print("Container already exists.")
    
    signing_df = pd.DataFrame(new_signing)

    #sets column names from capfriendly table headers 
    signing_df.columns = get_headers()            
    
    local_path = tempfile.gettempdir()

    if not os.path.exists(local_path):
        os.mkdir(local_path)

    dateTimeObj = datetime.now()
    local_file_name = 'CapFriendly_Signing_' + dateTimeObj.strftime("%d%m%Y_%H%M%S") + '.csv'
    upload_file_path = os.path.join(local_path, local_file_name)
    signing_df.to_csv(upload_file_path, index=False, header=True, encoding='ISO-8859-1')

    # Create a blob client using the local file name as the name for the blob
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=local_file_name)

    print("\nUploading to Azure Storage as blob:\n\t" + local_file_name)

    # Upload the created file
    with open(upload_file_path, "rb") as data:
        blob_client.upload_blob(data)

    print('New signing(s) saved as CapFriendly_Signing_' + dateTimeObj.strftime("%d%m%Y_%H%M%S") + '.csv')

    return blob_client.url

def main(myTimer: func.TimerRequest, msg: func.Out[str]) -> None:
    new_signings = scrape_data()

    if not new_signings:
        logging.info('No new signings. Nothing to do!')
        return
    
    blob_url = write_data(new_signings)

    #send message to a queue
    msg.set(blob_url)
