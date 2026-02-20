import urllib.request

try:
    with urllib.request.urlopen("http://127.0.0.1:8000/") as response:
        content = response.read().decode('utf-8')
        print(f"Status Code: {response.status}")
        print("First 500 characters of response:")
        print(content[:500])
        
    with urllib.request.urlopen("http://127.0.0.1:8000/login") as response:
        content = response.read().decode('utf-8')
        print(f"\nLogin Route Status Code: {response.status}")
        print("First 500 characters of login response:")
        print(content[:500])
except Exception as e:
    print(f"Error connecting to server: {e}")
