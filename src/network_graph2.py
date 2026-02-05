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
    """Crée un graphe des périphériques avec leurs adresses IP et connexions, incluant les étiquettes des ports aux extrémités des connexions."""
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
            device_label += f"\n{', '.join(ip_addresses)}"

        G.add_node(device_id, label=device_label)

    # Récupérer toutes les connexions
    connections = get_connections()

    # Ajouter les connexions entre les périphériques
    edge_port_labels = {}  # Dictionnaire pour stocker les étiquettes des ports pour chaque arête

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

            # Ajouter l'arête
            G.add_edge(device_a_id, device_b_id)

            # Stocker les étiquettes des ports pour cette arête
            edge_port_labels[(device_a_id, device_b_id)] = (a_port_name, b_port_name)

        except Exception as e:
            print(f"Erreur lors du traitement de la connexion {connection.get('id', 'inconnu')}: {e}")

    # Dessiner le graphe avec Kamada-Kawai
    pos = nx.kamada_kawai_layout(G)
    node_labels = nx.get_node_attributes(G, 'label')

    plt.figure(figsize=(12, 8))

    # Dessiner les nœuds sous forme de rectangles
    nx.draw_networkx_nodes(G, pos, node_size=6000, node_shape="s", node_color='lightblue')

    # Dessiner les arêtes
    nx.draw_networkx_edges(G, pos)

    # Dessiner les étiquettes des nœuds
    for node, (x, y) in pos.items():
        plt.text(x, y, node_labels[node], ha='center', va='center', fontsize=8, fontweight='bold')

    # Ajouter les étiquettes des ports aux extrémités des connexions
    for edge, port_labels in edge_port_labels.items():
        x1, y1 = pos[edge[0]]
        x2, y2 = pos[edge[1]]

        # Positionner l'étiquette du port source près du nœud source
        x_start = x1 + 0.15 * (x2 - x1)
        y_start = y1 + 0.15 * (y2 - y1)
        plt.text(x_start, y_start, port_labels[0], bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'), fontsize=6, ha='center', va='center')

        # Positionner l'étiquette du port destination près du nœud destination
        x_end = x1 + 0.85 * (x2 - x1)
        y_end = y1 + 0.85 * (y2 - y1)
        plt.text(x_end, y_end, port_labels[1], bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'), fontsize=6, ha='center', va='center')

    plt.title("Réseau des périphériques avec rectangles ajustés (Kamada-Kawai)")
    plt.savefig("network_graph_with_rectangles.png")
    plt.show()


if __name__ == "__main__":
    create_network_graph()
