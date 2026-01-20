import requests

# URL of the login endpoint
url = "http://localhost:8000/api/v1/auth/login"

# Form data to send (mimicking frontend)
data = {
    'username': 'admin@shophub.com',  # Email as username
    'password': 'admin123'  # Admin password
}

# Send POST request with form data
response = requests.post(url, data=data)

# Print the response
print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")

if response.status_code == 200:
    print("Login successful!")
else:
    print("Login failed.")