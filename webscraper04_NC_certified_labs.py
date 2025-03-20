#!/usr/bin/env python
# coding: utf-8

# Overview:
# 
# This script extracts data about certified laboratories from the North Carolina DHHS State Laboratory of Public Health website. Selenium is used to navigate the site, interact with dynamic elements, and retrieve page content. BeautifulSoup parses the HTML. The script collects lab details from the such as name, address, contact information, and certifications, storing them in a Pandas DataFrame. The data is saved as a CSV file for further use.
# 
# This script was drafted to aggregate necessary information on laboratories certified by the State Laboratory of Public Health. The output dataset contains lab addresses that will be geocoded and used as a spatial data layer displaying locations of certified labs and their respective information.
# 
# Updated 02.18.25 - adjusted script to separately scrape all Commercial Lab directory info and then Municipal laboratory directory info into separate CSVs.

# In[ ]:





# In[3]:


#pip install chromedriver-autoinstaller


# In[5]:


import chromedriver_autoinstaller
chromedriver_autoinstaller.install()  # Check if the current version of chromedriver exists
                                      # and if it doesn't exist, download it automatically,
                                      # then add chromedriver to path


# In[8]:

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
    
    # Step 2: Locate and click the "Search" element in the page
    search_element = driver.find_element(By.XPATH, "/html/body/form/table[8]/tbody/tr[2]/td/a")
    search_element.click()
    
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
            address = df.loc[6, "Value"]
            citystatezip = df.loc[11, "Value"]
            mailing_address = f"{df.loc[9, 'Value']} {df.loc[14, 'Value']}"
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
                "Location": [address],
                "City/State/Zip": [citystatezip],
                "Mailing Address": [mailing_address],
                "Phone": [phone],
                "Fax": [fax],
                "Synthetic Organic Compounds": [synthetic_organic_compounds],
                "Volatile Organic Compounds": [volatile_organic_compounds],
                "Inorganic": [inorganic_compounds],
                "Microbiology": [microbiology]
            })
            
            # Split the City/State/Zip column into separate columns
            city_state_zip_split = certified_labs["City/State/Zip"].str.extract(r'^(.*?),\s*([A-Z]{2})\s*(\d{5})$')

            # Assign the split values to new columns in the dataframe
            certified_labs["City"] = city_state_zip_split[0]
            certified_labs["State"] = city_state_zip_split[1]
            certified_labs["Zip"] = city_state_zip_split[2]

            # Drop the original City/State/Zip column if no longer needed
            certified_labs.drop(columns=["City/State/Zip"], inplace=True)
            
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

    # Function to reorder columns
    def reorder_columns(dataframe, columns_to_move, target_indices):
        current_columns = list(dataframe.columns)
        for i, column in enumerate(columns_to_move):
            # Remove the column from its current position
            current_columns.remove(column)
            # Insert the column into the desired position
            current_columns.insert(target_indices[i], column)

        # Reorder the DataFrame
        reordered_dataframe = dataframe[current_columns]
        return reordered_dataframe

    # Columns to move and their target indices
    columns_to_move = ["City", "State", "Zip"]
    target_indices = [3, 4, 5]

    # Reorder the DataFrame
    all_certified_labs = reorder_columns(all_certified_labs, columns_to_move, target_indices)

    # Save the results to a CSV file
    all_certified_labs.to_csv(r"C:\Users\bertr\OneDrive\Documents\NC_DHHS_PH_Work\Notes\Work Notes\Testing resources Dashboard\NC_State_certified_labs Dashboard\Data Prep\NC_State_certified_labs_comm.csv", index=False)
    print("Scraping completed. Data saved to NC_State_certified_labs_comm.csv.")


# In[9]:


# Initialize the WebDriver
driver = webdriver.Chrome()

# Initialize the results dataframe
all_certified_labs = pd.DataFrame()

try:
    # Step 1: Open the target URL
    driver.get("https://slphreporting.dph.ncdhhs.gov/Certification/CertifiedLaboratory.asp")
    
    # Wait for the first page to load fully
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    
    # New Step: Locate and click the "Search for Municipal Laboratory" label element
    municipal_lab_label = driver.find_element(By.XPATH, "/html/body/form/table[1]/tbody/tr[6]/td/label[2]")
    municipal_lab_label.click()
    
    # Step 2: Locate and click the "Search" element in the page
    search_element = driver.find_element(By.XPATH, "/html/body/form/table[8]/tbody/tr[2]/td/a")
    search_element.click()
    
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
            address = df.loc[6, "Value"]
            citystatezip = df.loc[11, "Value"]
            mailing_address = f"{df.loc[9, 'Value']} {df.loc[14, 'Value']}"
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
                "Location": [address],
                "City/State/Zip": [citystatezip],
                "Mailing Address": [mailing_address],
                "Phone": [phone],
                "Fax": [fax],
                "Synthetic Organic Compounds": [synthetic_organic_compounds],
                "Volatile Organic Compounds": [volatile_organic_compounds],
                "Inorganic": [inorganic_compounds],
                "Microbiology": [microbiology]
            })
            
            # Split the City/State/Zip column into separate columns
            city_state_zip_split = certified_labs["City/State/Zip"].str.extract(r'^(.*?),\s*([A-Z]{2})\s*(\d{5})$')

            # Assign the split values to new columns in the dataframe
            certified_labs["City"] = city_state_zip_split[0]
            certified_labs["State"] = city_state_zip_split[1]
            certified_labs["Zip"] = city_state_zip_split[2]

            # Drop the original City/State/Zip column if no longer needed
            certified_labs.drop(columns=["City/State/Zip"], inplace=True)
            
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

    # Function to reorder columns
    def reorder_columns(dataframe, columns_to_move, target_indices):
        current_columns = list(dataframe.columns)
        for i, column in enumerate(columns_to_move):
            # Remove the column from its current position
            current_columns.remove(column)
            # Insert the column into the desired position
            current_columns.insert(target_indices[i], column)

        # Reorder the DataFrame
        reordered_dataframe = dataframe[current_columns]
        return reordered_dataframe

    # Columns to move and their target indices
    columns_to_move = ["City", "State", "Zip"]
    target_indices = [3, 4, 5]

    # Reorder the DataFrame
    all_certified_labs = reorder_columns(all_certified_labs, columns_to_move, target_indices)

    # Save the results to a CSV file
    all_certified_labs.to_csv(r"C:\Users\bertr\OneDrive\Documents\NC_DHHS_PH_Work\Notes\Work Notes\Testing resources Dashboard\NC_State_certified_labs Dashboard\Data Prep\NC_State_certified_labs_municipal.csv", index=False)
    print("Scraping completed. Data saved to NC_State_certified_labs_municipal.csv.")


# In[ ]:


print(all_certified_labs)


# In[ ]:


all_certified_labs.head(50)
