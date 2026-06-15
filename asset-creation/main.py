#!/home/dtsadmin/netilion-dev/asset-creation/venv/bin/python3

import requests
import schedule
import time
import os
import sys
from dotenv import load_dotenv, dotenv_values

netilionUrl = "https://api.netilion.endress.com"

load_dotenv()

apiKey = os.getenv("API_KEY")
apiSecret = os.getenv("API_SECRET")
username = os.getenv("TECH_USERNAME")
password = os.getenv("PASSWORD")
subscriptionOwner = os.getenv("OWNER")

companyName = "Fake Company"
productCode = "False001"
productName = "False Product"
serialNumber = "FAKE01234567"

tokenAccess = ""
tokenRefresh = ""

assetID = ""
tenantID = ""
productID = ""
companyID = ""

def fetchCred():
    global tokenAccess
    global tokenRefresh

    # the request library will automatically URL percent encode the strings it is fed.
    authPayload = {'client_id': apiKey, 'client_secret': apiSecret, 'grant_type': 'password', 'username': username, 'password': password}
    authHeader = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(netilionUrl + "/oauth/token", headers=authHeader, params=authPayload)

    # response will evaluate to "true" if <399
    # so we can just raise an exception and print the response if not true.
    # some status codes in that range return something, but aren't useful.
    if response:
        authorization_dict = response.json()
        tokenAccess = authorization_dict['access_token']
        tokenRefresh = authorization_dict['refresh_token']
        print("Success!")
        print(tokenAccess)
        print(tokenRefresh)
    else:
        raise Exception(f"Non-success status code: {response.status_code}")

def refreshToken():
    global tokenAccess
    global tokenRefresh

    print("Refreshing credentials...")

    authPayload = {'client_id': apiKey, 'client_secret': apiSecret, 'grant_type': 'refresh_token', 'refresh_token': tokenRefresh}
    authHeader = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(netilionUrl + "/oauth/token", headers=authHeader, params=authPayload)

    if response:
        authorization_dict = response.json()
        tokenAccess = authorization_dict['access_token']
        tokenRefresh = authorization_dict['refresh_token']
        print("Success!")
        print(tokenAccess)
        print(tokenRefresh)
    else:
        raise Exception(f"Non-success status code: {response.status_code}")


    # looks like you can directly read the response into a dictionary
    # so there is not likely a need to use the json library.

             ###

# Check if serial number exist with associated product code/name
def checkAsset():
    global assetID

    responseAsset = requests.get(netilionUrl + "/v1/assets?include=product&serial_number=" + str(serialNumber), headers={'Authorization': "Bearer " + tokenAccess})

    if responseAsset:
        responseAsset_dict = responseAsset.json()
        
        if len(responseAsset_dict['assets'][0]) == 0:
            return True
        elif len(responseAsset_dict['assets'][0]) > 0 and responseAsset_dict['assets'][0]['product']['product_code'] == productCode:
            assetID = responseAsset_dict['assets'][0]['id']
            print("Asset ID: " + str(assetID))
            return False
        else:
            print("Serial number found, different product code")
    else:
        raise Exception(f"Non-success status code: {responseAsset.status_code}")

def deleteAsset():
    checkAsset()

    responseDeleteAsset = requests.delete(netilionUrl + "/v1/assets/" + str(assetID), headers={'Authorization': "Bearer " + tokenAccess, 'accept': '*/*'})

    if responseDeleteAsset:
        print("Success. Asset deleted.")
    else:
        raise Exception(f"Non-success status code: {responseDeleteAsset.status_code}")

# Create Tenant
# Assign account owner as admin
def createTenant():
    global tenantID

    # ------------------ Owner ID and Subscription ----------------------
    print("Retrieving owner ID and subscription name...")
    responseClientApplication = requests.get(netilionUrl + "/v1/client_applications", headers={'Authorization': "Bearer " + tokenAccess})

    if responseClientApplication:
        responseClientApplication_dict = responseClientApplication.json()
        ownerID = responseClientApplication_dict['client_applications'][0]['contact_person']['id']
        subscriptionName = responseClientApplication_dict['client_applications'][0]['name']
        print("Tenant Name: " + subscriptionName + "-" + str(ownerID))
    else:
        raise Exception(f"Non-success status code: {responseClientApplication.status_code}")

    # ------------------ Tenant ID --------------------------------------
    print("Creating tenant...")
    payload0 = {
        "name" : subscriptionName + '-' + str(ownerID),
        "description": "created via script"
    }

    responseTenant = requests.post(netilionUrl + "/v1/tenants", headers={'Authorization': "Bearer " + tokenAccess}, json=payload0)

    if responseTenant:
        responseTenant_dict = responseTenant.json()
        tenantID = responseTenant_dict['id']
        print("Tenant ID: " + str(tenantID))
    else:
        if responseTenant.status_code == 400:
            responseTenant_dict = responseTenant.json()

            if responseTenant_dict['errors'][0]['type'] == 'taken':
                print("Tenant exists")
                responseTenant2 = requests.get(netilionUrl + "/v1/tenants?name=" + subscriptionName + "-" + str(ownerID), headers={'Authorization': "Bearer " + tokenAccess})
                responseTenant2_dict = responseTenant2.json()
                tenantID = responseTenant2_dict['tenants'][0]['id']
                print("Tenant ID: " + str(tenantID))
            else:
                raise Exception(responseTenant.json())
        else:
            raise Exception(f"Non-success status code: {responseTenant.status_code}")
    
    # ------------------ Assign User ------------------------------------
    print("Assigning subscription owner to tenant...")

    payload1 = {
        "users": [
            {"email": subscriptionOwner}
            ]
    }

    responseAssign = requests.post(netilionUrl + "/v2/tenants/" + str(tenantID) + "/admins", headers={'Authorization': "Bearer " + tokenAccess}, json=payload1)

    if responseAssign:
        print(responseAssign.status_code)
        print("Assigned user: " + subscriptionOwner)
    else:
        if responseAssign.status_code == 400:
            responseAssign_dict = responseAssign.json()

            if responseAssign_dict['errors'][0]['type'] == 'associations_already_added':
                print("Assignment Exists")
            else:
                raise Exception(responseAssign.json())
        else:
            raise Exception(f"Non-success status code: {responseAssign.status_code}")

# Create Company
# Create Product
def createProduct():
    global productID
    global companyID

    # ------------------ Company ID -------------------------------------
    print("Creating Company")

    payload0 = {
        "name": companyName,
        "description": "Created by script",
        "tenant": {"id": tenantID}
        }

    responseCompanyID = requests.post(netilionUrl + "/v1/companies", headers={'Authorization': "Bearer " + tokenAccess}, json=payload0)

    if responseCompanyID:
        responseCompanyID_dict = responseCompanyID.json()
        companyID = responseCompanyID_dict["id"]
        print("Company ID: " + str(companyID))
    else:
        if responseCompanyID.status_code == 400:
            responseCompanyID_dict = responseCompanyID.json()

            if responseCompanyID_dict['errors'][0]['type'] == 'taken':
                print("Company exists")
                responseCompanyID2 = requests.get(netilionUrl + "/v1/companies?name=" + str(companyName), headers={'Authorization': "Bearer " + tokenAccess})
                responseCompanyID2_dict = responseCompanyID2.json()
                companyID = responseCompanyID2_dict['companies'][0]['id']
                print("Company ID: " + str(companyID))
            else:
                raise Exception(responseCompanyID.json())
        else:
            raise Exception(f"Non-success status code: {responseCompanyID.status_code}")
    
    # ------------------ Product ID -------------------------------------
    print("Creating Product")

    payload1 = {
        "product_code": productCode,
        "name": productName,
        "description": "Created by script",
        "manufacturer": {"id": companyID},
        "tenant": {"id": tenantID}
        }

    responseProductID = requests.post(netilionUrl + "/v1/products", headers={'Authorization': "Bearer " + tokenAccess}, json=payload1)

    if responseProductID:
        responseProductID_dict = responseProductID.json()
        productID = responseProductID_dict['id']
        print("Product ID: " + str(productID))
    else:
        if responseProductID.status_code == 400:
            responseProductID_dict = responseProductID.json()

            if responseProductID_dict['errors'][0]['type'] == 'taken':
                print("Product exists")
                responseProductID2 = requests.get(netilionUrl + "/v1/products?product_code=" + str(productCode), headers={'Authorization': "Bearer " + tokenAccess})
                responseProductID2_dict = responseProductID2.json()
                productID = responseProductID2_dict['products'][0]['id']
                print("Product ID: " + str(productID))
            else:
                raise Exception(responseProductID.json())
        else:
            raise Exception(f"Non-success status code: {responseProductID.status_code}")

# Determine if asset exists, create if not
# Create Asset
def createAsset():
    global assetID

        # ------------------ Asset ID ---------------------------------------
    print("Creating Asset")

    payload = {
        "serial_number": serialNumber,
        "description": "Created by script",
        "product": {"id": productID},
        "tenant": {"id": tenantID}
    }

    responseAssetID = requests.post(netilionUrl + "/v1/assets", headers={'Authorization': "Bearer " + tokenAccess}, json=payload)

    if responseAssetID:
        responseAssetID_dict = responseAssetID.json()
        assetID = responseAssetID_dict['id']
        print("Asset ID: " + str(assetID))
    else:
        raise Exception(f"Non-success status code: {responseAssetID.status_code}")

# Post Value to Netilion
def postAssetValue():
    return

# Get values from known asset
def getAssetValue():
    global assetID
    print("Getting primary value from asset: " + str(assetID))
    response = requests.get(netilionUrl + "/v1/assets/" + str(assetID) + "/values", headers={'Authorization': "Bearer " + tokenAccess})

    if response:
        response_dict = response.json()
        value = response_dict['values'][0]['value']
        print("Asset Value: " + str(value))
    else:
        raise Exception(f"Non-success status code: {response.status_code}")

schedule.every(10).minutes.do(refreshToken)
schedule.every(10).seconds.do(getAssetValue)

if __name__ == "__main__":
    fetchCred()

    # deleteAsset()

    if checkAsset():
        print("Asset not found, creating asset")
        createTenant()
        createProduct()
        createAsset()
    else:
        sys.exit("Asset exists")

    # while True:
    #     schedule.run_pending()
    #     time.sleep(10)
