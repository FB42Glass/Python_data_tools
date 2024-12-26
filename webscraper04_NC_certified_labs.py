#!/usr/bin/env python
# coding: utf-8

# Overview:
# 
# This script extracts data about certified laboratories from the North Carolina DHHS State Laboratory of Public Health website. Selenium is used to navigate the site, interact with dynamic elements, and retrieve page content. BeautifulSoup parses the HTML. The script collects lab details from the such as name, address, contact information, and certifications, storing them in a Pandas DataFrame. The data is saved as a CSV file for further use.
# 
# This script was drafted to aggregate necessary information on laboratories certified by the State Laboratory of Public Health. The output dataset contains lab addresses that will be geocoded and used as a spatial data layer displaying locations of certified labs and their respective information.

# In[2]:


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd

# Initialize the WebDriver
driver = webdriver.Chrome()

# Initialize the results dataframe
all_certified_labs = pd.DataFrame()

try:
    # Step 1: Open the target URL
    driver.get("https://slphreporting.dph.ncdhhs.gov/Certification/CertifiedLaboratory.asp")
    
    # Wait for the first page to load fully
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    
    # Step 2: Locate and click the first element to open the table
    first_element = driver.find_element(By.XPATH, "//a[@href='#' and contains(@onclick, 'selectOnClick')]")
    first_element.click()
    
    # Step 3: Wait for the table with `labNameOnClick` links to appear
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'Javascript:labNameOnClick')]"))
    )
    
    # Step 4: Find all `labNameOnClick` links
    lab_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'Javascript:labNameOnClick')]")
    
    # Step 5: Iterate data scraping steps over each link
    for index, lab_link in enumerate(lab_links):
        try:
            # Refresh the list of links to avoid stale element reference issues
            lab_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'Javascript:labNameOnClick')]")
            lab_link = lab_links[index]
            
            # Click the link
            lab_link.click()
            
            # Wait for the new page or content to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "required"))  # Adjust as necessary for new page
            )
            
            # Scrape the HTML content using BeautifulSoup
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Extract values from specified HTML elements under a section
            data = []
            sections = soup.find_all("tr")  # Find all table rows to process sections
            
            current_section = None
            for section in sections:
                # Check if the row contains a section header
                section_header = section.find("td", class_="sectionHeader")
                if section_header:
                    current_section = section_header.get_text(strip=True)  # Extract section name
                    continue  # Move to the next row
                
                # If the row contains data values, extract them
                if current_section:
                    values = [td.get_text(strip=True) for td in section.find_all("td")]  # Extract all <td> values in the row
                    for value in values:
                        data.append({
                            "Section": current_section,
                            "Value": value
                        })
            
            # Create DataFrame
            df = pd.DataFrame(data)
            
            # Extracting lab information
            lab_name = df.loc[1, "Value"]
            lab_number = df.loc[4, "Value"]
            mailing_address = f"{df.loc[9, 'Value']} {df.loc[11, 'Value']}"
            phone = df.loc[16, "Value"]
            fax = df.loc[19, "Value"]
            
            # Extract certified contaminants lists
            synthetic_organic_compounds = df.loc[df["Section"] == "SYNTHETIC ORGANIC (SOC)", "Value"].tolist()
            volatile_organic_compounds = df.loc[df["Section"] == "VOLATILE ORGANIC (VOC)", "Value"].tolist()
            inorganic_compounds = df.loc[df["Section"] == "INORGANIC", "Value"].tolist()
            microbiology = df.loc[df["Section"] == "MICROBIOLOGY", "Value"].tolist()
            
            # Create a new dataframe for this lab
            certified_labs = pd.DataFrame({
                "Lab Name": [lab_name],
                "Lab Number": [lab_number],
                "Mailing Address": [mailing_address],
                "Phone": [phone],
                "Fax": [fax],
                "Synthetic Organic Compounds": [synthetic_organic_compounds],
                "Volatile Organic Compounds": [volatile_organic_compounds],
                "Inorganic": [inorganic_compounds],
                "Microbiology": [microbiology]
            })
            
            # Append the data to the main results dataframe
            all_certified_labs = pd.concat([all_certified_labs, certified_labs], ignore_index=True)
            
            # Navigate back to the table page
            driver.back()
            
            # Wait for the table to reload
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'Javascript:labNameOnClick')]"))
            )
        except Exception as e:
            print(f"An error occurred while processing link {index + 1}: {e}")
    
except Exception as e:
    print("An error occurred:", e)

finally:
    # Close the WebDriver
    driver.quit()

    # Save the results to a CSV file
    all_certified_labs.to_csv("NC_State_certified_labs.csv", index=False)
    print("Scraping completed. Data saved to certified_labs.csv.")


# In[3]:


print(all_certified_labs)


# In[4]:


all_certified_labs.head(50)

