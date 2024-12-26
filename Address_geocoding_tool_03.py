#!/usr/bin/env python
# coding: utf-8

# Overview:
# This script accesses the Geoapify geocoding API and batch geocodes address data from the NC Local Health Departments Directory Dataset
# 
# [Geoapify](https://myprojects.geoapify.com/api/Cljb2vX61qVCcBOShv2A/statistics) will geocode  up to 3,000 addresses for free per day. 

# In[1]:


import requests
import pandas as pd
from requests.structures import CaseInsensitiveDict


# In[2]:


csv_file = "NC Local Health Department Directory Info.csv"
data = pd.read_csv(csv_file, dtype=str, delimiter=',', engine='python',encoding='latin1', header=0) #
df=data.copy()


# In[3]:


# Function to split address into components
def split_address(address):
    if pd.isna(address):
        return pd.Series([None, None, None, None])  # Return None for each column if address is NaN
    parts = address.split(',')
    if len(parts) >= 3:
        # Concatenate parts that belong to the street address
        street = ','.join(parts[:-2]).strip()
        city = parts[-2].strip()
        state_zip = parts[-1].strip().split()
        state = state_zip[0] if len(state_zip) > 0 else None
        zip_code = state_zip[1] if len(state_zip) > 1 else None
        return pd.Series([street, city, state, zip_code])
    else:
        return pd.Series([None, None, None, None])

# Apply the function to split the Address column
df[['streetAddress', 'City', 'State', 'Zip']] = df['Address'].apply(split_address)

# Drop the original City/State/Zip column if no longer needed
df.drop(columns=["Address"], inplace=True)

# Print the resulting DataFrame
df.head(50)


# In[7]:


# Replace with your API key
API_KEY = "YOUR_API_KEY"

def geocode_address(streetAddress, city, state, zip_code, api_key):
    """
    Constructs the API URL dynamically and makes a geocoding request.
    """
    address = f"{streetAddress}, {city}, {state}, {zip_code}"
    url = f"https://api.geoapify.com/v1/geocode/search?text={requests.utils.quote(address)}&apiKey={api_key}"
    headers = CaseInsensitiveDict()
    headers["Accept"] = "application/json"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()  # Return the JSON response if successful
    else:
        return {"error": response.status_code}

# Add new columns for geocoding results
df["Latitude"] = None
df["Longitude"] = None

# Batch process each address
for index, row in df.iterrows():
    result = geocode_address(row["streetAddress"], row["City"], row["State"], row["Zip"], API_KEY)
    
    # Parse result to extract latitude and longitude, if available
    if "features" in result and len(result["features"]) > 0:
        geometry = result["features"][0]["geometry"]
        df.at[index, "Latitude"] = geometry["coordinates"][1]  # Latitude
        df.at[index, "Longitude"] = geometry["coordinates"][0]  # Longitude
    else:
        df.at[index, "Latitude"] = None
        df.at[index, "Longitude"] = None

# Display or save the updated DataFrame
print(df)
# Optionally save to CSV
df.to_csv("NC_LHDs_geo.csv", index=False)


# In[ ]:




