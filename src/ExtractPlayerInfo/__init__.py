import logging

import azure.functions as func
import bs4
import requests
import pandas as pd
from datetime import datetime
import os
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
import tempfile

def get_headers():
    url = 'https://www.capfriendly.com/browse/active/2024/aav?stats-season=2023&age-calculation-date=today&display=birthday,expiry-year,aav,skater-individual-advanced-stats,skater-on-ice-advanced-stats,goalie-advanced-stats&hide=clauses,age,handed'
    cap_table_headers = []       
    
    #opens CapFriendly and pulls the text from the Table Header tag
    headers = requests.get(url)
    headers_text=bs4.BeautifulSoup(headers.text, "lxml")
    headers_contents = headers_text('th')
    for x in range(len(headers_contents)):
        cap_table_headers.append(headers_contents[x].getText())

    return cap_table_headers

def write_cap_data(cap_list, year):
    
    connect_str = os.getenv('EXPORT_AZURE_STORAGE_CONNECTION_STRING')
    # Create the BlobServiceClient object which will be used to create a container client
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)

    # Create a unique name for the container
    container_name = 'capfriendlydata'

    # Create the container if it doesn't exists
    try:
       container_client = blob_service_client.create_container(container_name)
    except ResourceExistsError:
       print("Container already exists.")

    cap_data = cap_list
    cap_year = year
    #convert lists to Dataframes and export to CSV
    cap_data_df = pd.DataFrame(cap_data)  
    
    #sets column names from capfriendly table headers 
    cap_data_df.columns = get_headers()            
    
    local_path = tempfile.gettempdir()

    if not os.path.exists(local_path):
        os.mkdir(local_path)

    dateTimeObj = datetime.now()
    local_file_name = 'CapFriendly_'+ str(cap_year)+ '_' + dateTimeObj.strftime("%d%m%Y_%H%M%S") + '.csv'
    upload_file_path = os.path.join(local_path, local_file_name)
    cap_data_df.to_csv(upload_file_path, index=False, header=True, encoding='ISO-8859-1')

    # Create a blob client using the local file name as the name for the blob
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=local_file_name)

    print("\nUploading to Azure Storage as blob:\n\t" + local_file_name)

    # Upload the created file
    with open(upload_file_path, "rb") as data:
        blob_client.upload_blob(data)

    return print('Cap Data saved as CapFriendly_'+ str(cap_year)+ '_' + str(datetime.now()) + '.csv')

def scrape_data(year, last_page):
    #Initializing lists that I will manipulate later and seperate into lists of lists
    cap_table_contents_text = [] 
    cap_table_contents_slice=[]
    
    #creates variable from function input to be manipulated
    cap_year = year
    
    #creates page variable to be incremented so scraper can move through pages of cap data
    page = 1
    
    #creates url string that can be adjusted by year of cap hits requested by function
    #the reason there are two is so the end of url can easily be appended with page number
    #without complex slicing needed
    url = 'https://www.capfriendly.com/browse/active/'+ str(cap_year) +'/aav?stats-season='+ str(int(cap_year)-1) +'&age-calculation-date=today&display=birthday,expiry-year,aav,skater-individual-advanced-stats,skater-on-ice-advanced-stats,goalie-advanced-stats&hide=clauses,age,handed&pg='
    
    new_url = url + str(page)
    
    #loop which moves through pages and scrapes the data on each page for year   
    while not new_url.endswith(str(last_page + 1)):  
        #Creates a response object to test to see if end of cap data has happened
        status_test = requests.get(new_url)
        status_test.raise_for_status()
        
        #initial pull of html data from CapFriendly site
        capfriendly = requests.get(new_url)
        
        #These next 3 lines of code breaks down the site with BS4
        capfriendly_text =bs4.BeautifulSoup(capfriendly.text, "lxml") 
        
        #breaks down the html into just the contents of the <td> tags
        cap_table_contents=capfriendly_text('td')  
        
        #checks to see if next iteration of URL contains any data in tables and 
        #if table is empty breaks the loop
        if not cap_table_contents:
            break

        #appends the lists initialized above with all data in <td> tags
        for x in range(len(cap_table_contents)):
            cap_table_contents_text.append(cap_table_contents[x].getText().replace(u'\u016b','u'))
        
        # these next two lines are test lines to make sure code is working properly
        print(new_url)
        print("WebSite DownLoaded!")
                
        #these two lines slice the contents of cap_table_contents_text into lists
        cap_table_contents_slice = [cap_table_contents_text[i:i + 46] for i in range(0, len(cap_table_contents_text), 46)]
       
        # this is key to incrementing while loop so loop will eventually end
        page += 1
        new_url = url + str(page)
            
    return cap_table_contents_slice

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        req_body = req.get_json()
    except ValueError:
        pass
    else:
        cap_years = req_body.get('year')
        last_page = req_body.get('lastPage')

    if not cap_years:
        return func.HttpResponse(
             "You must provide a year in the body.",
             status_code=404
        )
    
    #calls scrape function to scrape data based on years supplied by user
    cap_years_data = scrape_data(cap_years, last_page)

    write_cap_data(cap_years_data, cap_years)

    return func.HttpResponse(f"Got cap data for year {cap_years}")
    
