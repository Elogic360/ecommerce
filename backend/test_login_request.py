import requests

# URL of the login endpoint
url = "http://localhost:8000/api/v1/auth/login"

# Admin credentials
data = {
    "username": "admin@shophub.com",
    "password": "admin123"
}

# Make the POST request
response = requests.post(url, data=data)

# Print the response
print(f"Status Code: {response.status_code}")
print(f"Response Headers: {response.headers}")
print(f"Response Body: {response.text}")

if response.status_code == 200:
    print("Login successful!")
else:
    print("Login failed.")