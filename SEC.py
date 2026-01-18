import json, csv, os, sys, re 
import datetime
from bs4 import BeautifulSoup
from fake_useragent import UserAgent, FakeUserAgent
import requests
import pandas as pd
from typing import Dict

# Add modules from base repo
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.session import RequestSession
from utils.excel_formatter import ExcelFormatter


def save_json(spath: str, data: Dict) -> None:
    """
        Save the data in some JSON file specified by spath

    :param spath: The path to the json file in which the data will be stored
    :param data: The json data to store into a file
    """
    print(f"\n[OMNI] - {datetime.datetime.now()} - Saving data in {spath}...\n")
    with open(spath, 'w+') as f:
        json.dump(data, f, indent=4)

class SEC():
    """
        This class will be used to scrape information from the SEC website for publically traded companies
    """

    def __init__(self):
        self.start = datetime.datetime.now()

     # Configuration
        self.reqsesh = RequestSession()
        self.ef = ExcelFormatter()
        self.url_template = "https://data.sec.gov/submissions/CIK##########.json"
        self.url_xbrl_acc_payable = "https://data.sec.gov/api/xbrl/companyconcept/CIK##########/us-gaap/AccountsPayableCurrent.json"
        self.url_xbrl = "https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json"
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.base_dir, "data")
        jpath = os.path.join(self.base_dir, "config/cik.json")
        self.cik_map = None
        with open(jpath, 'r') as f:
            self.cik_map = json.load(f)

        self.tickers = ['PLTR', 'BABA', 'VALE', 'WMT', 'SMCI']
        self.tickers = ['PLTR', 'AXTI', 'GOLD']
        print(f"Printing out the following tickers: {self.tickers}")
        for ticker in self.tickers:
            gaap_record = self.fetch_sec_filing(ticker)
            if gaap_record:
                gaap_record_cleaned = gaap_record.json() 
                #print(ticker, "\n", json.dumps(gaap_record_cleaned, indent=4))
                #save_json(os.path.join(os.path.dirname(__file__), f"data\\{ticker}.json"), gaap_record_cleaned)
                self.clean_facts(gaap_record_cleaned)
            print("\n\n")

        self.ef.save(f"EDGAR_FINANCIALS_{datetime.datetime.now().strftime('%Y%m%d')}_{datetime.datetime.now().strftime('%H%M%S')}.xlsx", os.path.join(os.path.dirname(__file__), "data"))
            

    def clean_facts(self, json) -> pd.DataFrame:
        """
        Given a suite of company facts data from SEC, clean it up and then store it in some CSV file
        
        :param json: JSON data which pertains to the facts being brought on for the particular ticker (company)
        """
        cik = json.get("cik", None)
        if not cik:
            print(f"\nThere is no CIK for the company you passed in.")
            return None

        entity = json.get("entityName", None)
        if not entity:
            print(f"\nThere is no entityName for the data you passed in")
            return None 
        
        facts = json.get("facts", None)
        if not facts:
            print(f"\nThere are no facts for the given entity: {entity}\n")
            return None 

        cfacts = []
        for key, value in facts.items():
            #print(f"\nAnalyzing the following facts: {key}...\n")
            for field, data in value.items():
                #print(f"Field name: {field}")
                for metafield, attr in data.items():
                    #if "label" == metafield:
                     #   print(f"Label: {attr}")
                    #if "description" == metafield:
                     #   print(f"Description: {attr}")
                    if "units" == metafield:
                        for key, list in attr.items():
                            #print(f"Grabbing all facts for the following unit: {key}...")
                            for obj in list:
                             # Columns: [CIK, EntityName, Timestamp, Value, AccountNumber, FiscalYear, FiscalPeriod, Form, FilingDate, Frame]
                                cfacts.append((cik, entity, field, obj.get("end", None), obj.get("val", None), obj.get("accn", None), obj.get("fy", None), obj.get("fp", None), obj.get("form", None), obj.get("filed", None), obj.get("frame", None)))
                #print(f"\n\n")

        fdata = pd.DataFrame(cfacts, columns=["CIK", "EntityName", "Field", "Timestamp", "Value", "AccountNumber", "FiscalYear", "FiscalPeriod", "Form", "FilingDate", "Frame"])
        print(fdata.head())

        self.ef.add_to_sheet(fdata, sheet_name=f"{entity}_FACTS")

    def fetch_sec_filing(self, ticker: str) -> bytes:
        """
        Fetch filings for a list of companies and save the aggregated data.
        
        :param cik_list: List of 10-digit CIK strings.
        """
        cik = self.cik_map[ticker]
        filings_data = self.extract_data(cik)
        print(filings_data, "\n\n")
        if filings_data:
            return filings_data
        else:
            print(f"No data found for ticker: {ticker}")


    def fetch_accounts_payable(self, cik: str) -> bytes:
        """
        Fetch filings for a list of companies and save the aggregated data.
        
        :param cik_list: List of 10-digit CIK strings.
        """
        aggregated_filings = {}
        filings_data = self.extract_data(cik)
        if filings_data:
            return filings_data 
        else:
            print(f"\n[SEC] - No accounts payable data found...")
            return b""

    def extract_data(self, cik: str) -> bytes:
        print(f"\n[REGI] - Extracting data for the following CIK (Central Index Key): {cik}\n")
        url = self.url_xbrl.replace('##########', cik)

        print(url)
        res = self.reqsesh.get(url)

        return res

    


if __name__=="__main__":
    sec = SEC()