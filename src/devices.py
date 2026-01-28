import sys
import os
import requests
import networkx as nx
from dotenv import load_dotenv

load_dotenv()

NETBOX_URL = os.getenv("NETBOX_URL")
NETBOX_TOKEN = os.getenv("NETBOX_TOKEN")


# En-têtes pour la requête
headers = {
    "Authorization": f"Token {NETBOX_TOKEN}",
    "Content-Type": "application/json",
}



def lister_peripherique_avec_ip(device_id):
    try:
        # Récupérer les informations du périphérique
        device_url = f"{NETBOX_URL}dcim/devices/{device_id}/"
        device_response = requests.get(device_url, headers=headers)
        device_response.raise_for_status()
        device = device_response.json()

        device_name = device["name"]
        print(f"Périphérique: {device_name}")

        # Vérifier si une IP primaire est définie
        if device.get("primary_ip4"):
            print(f"Adresse IP primaire: {device['primary_ip4']['address']}")

        # Récupérer les interfaces associées à ce périphérique
        interfaces_url = f"{NETBOX_URL}dcim/interfaces/?device_id={device_id}"
        interfaces_response = requests.get(interfaces_url, headers=headers)
        interfaces_response.raise_for_status()
        interfaces = interfaces_response.json()["results"]

        # Parcourir les interfaces et récupérer les adresses IP
        for interface in interfaces:
            interface_name = interface["name"]
            interface_id = interface["id"]

            # Récupérer les adresses IP associées à cette interface
            ip_url = f"{NETBOX_URL}ipam/ip-addresses/?interface_id={interface_id}"
            ip_response = requests.get(ip_url, headers=headers)
            ip_response.raise_for_status()
            ips = ip_response.json()["results"]

            if ips:
                print(f"\nInterface: {interface_name}")
                for ip in ips:
                    print(f"  - Adresse IP: {ip['address']}")
            # else:
            #     print(f"\nInterface: {interface_name} (aucune adresse IP associée)")

    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la requête à l'API NetBox: {e}")




def main():
    # Vérifier si un argument (ID du périphérique) est passé
    if len(sys.argv) == 2:
        device_id = sys.argv[1]
        lister_peripherique_avec_ip(device_id)
        sys.exit(0)

    # Exécuter la requête pour récupérer les devices
    response = requests.get(f"{NETBOX_URL}/dcim/devices", headers=headers)
    print(f"Status Code: {response.status_code}")  # Affiche le code de statut HTTP
    #print(f"Response Text: {response.text}")      # Affiche la réponse brute de l'API
    # Vérifier la réponse
    if response.status_code == 200:
        devices = response.json()["results"]
        print(f"Nombre de devices trouvés : {len(devices)}\n")

        # Afficher la liste des devices
        for device in devices:
            print(f"ID: {device['id']}")
            print(f"Nom: {device['name']}")
            print(f"Rôle: {device['role']['name']}")
            print(f"Type: {device['device_type']['model']}")
            print(f"Site: {device['site']['name']}")
            print(f"Statut: {device['status']['value']}")
            lister_peripherique_avec_ip(device['id'])
            print("-" * 50)
    else:
        print(f"Erreur lors de la requête : {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    main()