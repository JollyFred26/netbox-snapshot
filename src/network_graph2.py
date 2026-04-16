import sys
import os
import logging
import requests
import networkx as nx
import matplotlib.pyplot as plt
from functools import lru_cache
from dotenv import load_dotenv

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

NETBOX_URL = os.getenv("NETBOX_URL")
NETBOX_TOKEN = os.getenv("NETBOX_TOKEN")

headers = {
    "Authorization": f"Token {NETBOX_TOKEN}",
    "Accept": "application/json",
}

@lru_cache(maxsize=128)
def get_devices():
    """Récupère la liste des périphériques depuis NetBox (avec cache)."""
    url = f"{NETBOX_URL}dcim/devices/"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()["results"]
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des périphériques: {e}")
        return []

@lru_cache(maxsize=128)
def get_interfaces(device_id):
    """Récupère les interfaces d'un périphérique (avec cache)."""
    url = f"{NETBOX_URL}dcim/interfaces/?device_id={device_id}"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()["results"]
    except Exception as e:
        logger.error(f"Erreur pour les interfaces du périphérique {device_id}: {e}")
        return []

@lru_cache(maxsize=128)
def get_ip_addresses(interface_id):
    """Récupère les adresses IP d'une interface (avec cache)."""
    url = f"{NETBOX_URL}ipam/ip-addresses/?interface_id={interface_id}"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()["results"]
    except Exception as e:
        logger.error(f"Erreur pour les IPs de l'interface {interface_id}: {e}")
        return []

@lru_cache(maxsize=128)
def get_connections():
    """Récupère les connexions (câbles) depuis NetBox (avec cache)."""
    url = f"{NETBOX_URL}dcim/cables/"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()["results"]
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des connexions: {e}")
        return []

def create_network_graph():
    """Crée un graphe des périphériques avec leurs connexions et étiquettes."""
    G = nx.Graph()
    devices = get_devices()

    for device in devices:
        device_id = device["id"]
        device_name = device["name"]
        device_label = f"{device_name}"

        interfaces = get_interfaces(device_id)
        ip_addresses = []
        for interface in interfaces:
            ips = get_ip_addresses(interface["id"])
            for ip in ips:
                ip_addresses.append(ip["address"])

        if ip_addresses:
            device_label += f"\n{', '.join(ip_addresses)}"

        G.add_node(device_id, label=device_label)

    connections = get_connections()
    edge_port_labels = {}

    for connection in connections:
        try:
            a_terminations = connection.get("a_terminations", [])
            b_terminations = connection.get("b_terminations", [])

            if not a_terminations or not b_terminations:
                logger.warning(f"Terminaisons manquantes pour la connexion {connection.get('id', 'inconnu')}")
                continue

            a_interface = a_terminations[0].get("object", {})
            b_interface = b_terminations[0].get("object", {})

            a_device = a_interface.get("device", {})
            b_device = b_interface.get("device", {})

            a_port_name = a_interface.get("name", "Unknown Port")
            b_port_name = b_interface.get("name", "Unknown Port")

            if not a_device or not b_device:
                logger.warning(f"Périphériques manquants pour la connexion {connection.get('id', 'inconnu')}")
                continue

            device_a_id = a_device.get("id")
            device_b_id = b_device.get("id")

            if not device_a_id or not device_b_id or device_a_id == device_b_id:
                continue

            G.add_edge(device_a_id, device_b_id)
            edge_port_labels[(device_a_id, device_b_id)] = (a_port_name, b_port_name)

        except Exception as e:
            logger.error(f"Erreur pour la connexion {connection.get('id', 'inconnu')}: {e}")

    # Dessiner le graphe
    pos = nx.kamada_kawai_layout(G)
    node_labels = nx.get_node_attributes(G, 'label')

    plt.figure(figsize=(12, 8))
    nx.draw_networkx_nodes(G, pos, node_size=6000, node_shape="s", node_color='lightblue')
    nx.draw_networkx_edges(G, pos)

    for node, (x, y) in pos.items():
        plt.text(x, y, node_labels[node], ha='center', va='center', fontsize=8, fontweight='bold')

    for edge, port_labels in edge_port_labels.items():
        x1, y1 = pos[edge[0]]
        x2, y2 = pos[edge[1]]
        x_start = x1 + 0.15 * (x2 - x1)
        y_start = y1 + 0.15 * (y2 - y1)
        plt.text(x_start, y_start, port_labels[0], bbox=dict(facecolor='white', alpha=0.7), fontsize=6, ha='center')
        x_end = x1 + 0.85 * (x2 - x1)
        y_end = y1 + 0.85 * (y2 - y1)
        plt.text(x_end, y_end, port_labels[1], bbox=dict(facecolor='white', alpha=0.7), fontsize=6, ha='center')

    plt.title("Graphe réseau (NetBox)")
    plt.savefig("network_graph.png", dpi=300, bbox_inches='tight')
    logger.info("Graphe enregistré sous 'network_graph.png'")
    plt.show()

if __name__ == "__main__":
    create_network_graph()