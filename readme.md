# NetBox Device IP Lister

A Python script to list network devices and their IP addresses from a NetBox instance.

---

## Description

This script allows you to retrieve information about a network device (such as a router or switch) from a NetBox instance and display its interfaces along with their associated IP addresses. It uses the NetBox REST API to fetch the data.

---

## Prerequisites

- Python 3.x
- Access to a NetBox instance
- A NetBox API token with the necessary permissions
- The Python `requests` library (install via `pip install requests`)

---

## Installation

1. Clone this repository to your local machine:
   ```bash
   git clone https://github.com/JollyFred26/netbox-snapshot.git

2. Navigate to the project directory:
   ```bash
   cd netbox-snapshot

3. Install the required dependencies:
   ```bash
   pip install requests

## Configuration

1. Open the device.py file.
2. Update the following variables with your NetBox instance details:
    ```python
    NETBOX_URL = "http://192.168.0.250:8000/api/"  # Your NetBox instance URL
    NETBOX_TOKEN = "YOUR_API_TOKEN"  # Your NetBox API token

## Usage

To run the script and list the information for a specific device, use the following command:
   ```bash
   python device.py
   ```
     
You can use the script without parameters, in this case all devices will be scaned. If you want you can indicate a the device ID as:  

   ```bash
   python device.py 1
   ```

## Contributing
Contributions are welcome! To contribute:

1. Fork this repository.
2. Create a branch for your feature (git checkout -b new-feature).
3. Commit your changes (git commit -am 'Add a new feature').
4. Push your branch (git push origin new-feature).
5. Open a Pull Request.

## License
This project is licensed under the MIT License. See the LICENSE file for details.


