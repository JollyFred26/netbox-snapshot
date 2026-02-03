import sys
import os
import requests
import networkx as nx
import matplotlib.pyplot as plt

from dotenv import load_dotenv

load_dotenv()

NETBOX_URL = os.getenv("NETBOX_URL")
NETBOX_TOKEN = os.getenv("NETBOX_TOKEN")

# En-têtes pour l'authentification
headers = {
    "Authorization": f"Token {NETBOX_TOKEN}",
    "Accept": "application/json",
}

def get_devices():
    """Récupère la liste des périphériques depuis NetBox."""
    url = f"{NETBOX_URL}dcim/devices/"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["results"]

def get_interfaces(device_id):
    """Récupère les interfaces d'un périphérique donné."""
    url = f"{NETBOX_URL}dcim/interfaces/?device_id={device_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["results"]

def get_ip_addresses(interface_id):
    """Récupère les adresses IP associées à une interface donnée."""
    url = f"{NETBOX_URL}ipam/ip-addresses/?interface_id={interface_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["results"]

def get_connections():
    """Récupère toutes les connexions (câbles) depuis NetBox."""
    url = f"{NETBOX_URL}dcim/cables/"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["results"]

def create_network_graph():
    """Crée un graphe des périphériques avec leurs adresses IP et connexions, incluant les ports."""
    G = nx.Graph()

    # Récupérer tous les périphériques
    devices = get_devices()

    # Ajouter chaque périphérique comme un nœud
    for device in devices:
        device_id = device["id"]
        device_name = device["name"]
        device_label = f"{device_name}"

        # Récupérer les adresses IP du périphérique
        interfaces = get_interfaces(device_id)
        ip_addresses = []
        for interface in interfaces:
            ips = get_ip_addresses(interface["id"])
            for ip in ips:
                ip_addresses.append(ip["address"])

        # Ajouter les adresses IP au label du nœud
        if ip_addresses:
            device_label += f"\nIPs: {', '.join(ip_addresses)}"

        G.add_node(device_id, label=device_label)

    # Récupérer toutes les connexions
    connections = get_connections()

    # Ajouter les connexions entre les périphériques
    for connection in connections:
        try:
            # Récupérer les terminaisons A et B
            a_terminations = connection.get("a_terminations", [])
            b_terminations = connection.get("b_terminations", [])

            if not a_terminations or not b_terminations:
                print(f"Terminaisons manquantes pour la connexion {connection.get('id', 'inconnu')}")
                continue

            # Extraire les périphériques et les ports des terminaisons
            a_interface = a_terminations[0].get("object", {})
            b_interface = b_terminations[0].get("object", {})

            a_device = a_interface.get("device", {})
            b_device = b_interface.get("device", {})

            a_port_name = a_interface.get("name", "Unknown Port")
            b_port_name = b_interface.get("name", "Unknown Port")

            if not a_device or not b_device:
                print(f"Périphériques manquants pour la connexion {connection.get('id', 'inconnu')}")
                continue

            device_a_id = a_device.get("id")
            device_b_id = b_device.get("id")

            if not device_a_id or not device_b_id or device_a_id == device_b_id:
                continue

            # Trier les ports par ID de périphérique pour un ordre cohérent
            if device_a_id < device_b_id:
                edge_label = f"{a_port_name} ↔ {b_port_name}"
            else:
                edge_label = f"{b_port_name} ↔ {a_port_name}"
            #Ajouter l'arête avec une étiquette contenant les noms des ports
            G.add_edge(device_a_id, device_b_id, label=edge_label)

        except Exception as e:
            print(f"Erreur lors du traitement de la connexion {connection.get('id', 'inconnu')}: {e}")

    # Dessiner le graphe avec Kamada-Kawai
    pos = nx.kamada_kawai_layout(G)
    labels = nx.get_node_attributes(G, 'label')
    edge_labels = nx.get_edge_attributes(G, 'label')

    plt.figure(figsize=(12, 8))
    nx.draw(G, pos, labels=labels, with_labels=True, node_size=3000, node_color='lightblue', font_size=8, font_weight='bold')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='red', font_size=7)
    plt.title("Réseau des périphériques avec ports (Kamada-Kawai)")
    plt.savefig("network_graph_with_ports.png")
    plt.show()

if __name__ == "__main__":
    create_network_graph()
