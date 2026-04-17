import sys
import os
import logging
import requests
import networkx as nx
import matplotlib.pyplot as plt
from functools import lru_cache
from dotenv import load_dotenv
from collections import defaultdict

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

# ... (Imports et fonctions inchangées jusqu'à get_connections)

@lru_cache(maxsize=128)
def get_vlans():
    """Récupère la liste complète des VLANs depuis NetBox."""
    url = f"{NETBOX_URL}ipam/vlans/"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()["results"]
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des VLANs: {e}")
        return []

@lru_cache(maxsize=128)
def get_vlan_for_interface(interface_id):
    """Récupère le VLAN associé à une interface (VID et nom)."""
    url = f"{NETBOX_URL}dcim/interfaces/{interface_id}/"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        interface = response.json()
        logger.info(f"Interface {interface_id} (mode: {interface.get('mode')})")

        # Vérifie le mode (access/trunk)
        mode = interface.get("mode", {}).get("value") if interface.get("mode") else None

        if mode == "access" and interface.get("untagged_vlan"):
            vlan = interface["untagged_vlan"]
            logger.info(f"VLAN Access détecté : {vlan['name']} (VID={vlan['vid']})")
            return vlan["vid"], vlan["name"]

        elif mode == "trunk" and interface.get("tagged_vlans"):
            tagged_vlans = interface["tagged_vlans"]
            if tagged_vlans:
                # Prendre le premier VLAN taggé (ou tous, selon votre besoin)
                vlan = tagged_vlans[0]
                logger.info(f"VLAN Trunk détecté : {vlan['name']} (VID={vlan['vid']})")
                return vlan["vid"], vlan["name"]

        # Si l'interface n'a pas de mode défini mais a un VLAN (cas rare)
        elif interface.get("untagged_vlan"):
            vlan = interface["untagged_vlan"]
            logger.info(f"VLAN (sans mode) détecté : {vlan['name']} (VID={vlan['vid']})")
            return vlan["vid"], vlan["name"]

        logger.warning(f"Aucun VLAN trouvé pour l'interface {interface_id}")
        return None, None

    except Exception as e:
        logger.error(f"Erreur pour l'interface {interface_id}: {e}")
        return None, None
    


from pyvis.network import Network

def create_interactive_html_graph(G, edge_vlans, edge_port_labels, vlan_colors, output_file="network_graph.html"):
    """Exporte le graphe en HTML interactif avec Pyvis et une légende des VLANs."""
    net = Network(
        height="750px",
        width="100%",
        bgcolor="#222222",
        font_color="white",
        directed=False,
        notebook=False
    )

    # Ajouter les nœuds
    node_labels = nx.get_node_attributes(G, 'label')
    for node in G.nodes():
        net.add_node(
            node,
            label=node_labels[node],
            shape="box",
            color="#4DA6FF",
            title=f"Device ID: {node}"
        )

    # Ajouter les arêtes avec couleurs et étiquettes
    for edge, vlan_info in edge_vlans.items():
        vlan_name = vlan_info["name"]
        color = vlan_colors.get(vlan_name, "#808080")
        port_a, port_b = edge_port_labels[edge]

        net.add_edge(
            edge[0],
            edge[1],
            color=color,
            width=2,
            title=f"Ports: {port_a} ↔ {port_b}<br>VLAN: {vlan_name} ({vlan_info['vid']})" if vlan_info["vid"] else f"Ports: {port_a} ↔ {port_b}<br>VLAN: None",
            label=f"{port_a} ↔ {port_b}"
        )

    # Sauvegarder le fichier HTML initial
    net.save_graph(output_file)

    # Lire le fichier HTML et ajouter la légende
    with open(output_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Générer le HTML de la légende
    legend_html = """
    <div id="vlan-legend" style="
        position: absolute;
        bottom: 20px;
        right: 20px;
        background: rgba(0,0,0,0.7);
        padding: 10px;
        border-radius: 5px;
        z-index: 1000;
    ">
        <h3 style="color: white; margin-top: 0; margin-bottom: 10px;">Légende des VLANs</h3>
        <div id="legend-content" style="display: flex; flex-direction: column; gap: 5px;">
    """

    # Ajouter chaque VLAN à la légende
    seen_labels = set()
    for vlan_info in edge_vlans.values():
        vlan_name = vlan_info["name"]
        vlan_vid = vlan_info["vid"]
        label = f"{vlan_name} ({vlan_vid})" if vlan_vid is not None else vlan_name
        if label not in seen_labels:
            seen_labels.add(label)
            color = vlan_colors.get(vlan_name, "#808080")
            legend_html += f"""
            <div style="display: flex; align-items: center;">
                <div style="width: 20px; height: 2px; background: {color}; margin-right: 8px;"></div>
                <span style="color: white; font-size: 14px;">{label}</span>
            </div>
            """

    legend_html += """
        </div>
    </div>
    """

    # Ajouter le CSS et JavaScript pour la légende
    css_js = """
    <style>
        #vlan-legend {
            font-family: Arial, sans-serif;
        }
    </style>
    <script>
        // Ajuster la taille du réseau pour éviter le chevauchement
        document.addEventListener('DOMContentLoaded', function() {
            const networkDiv = document.querySelector('#mynetwork');
            if (networkDiv) {
                networkDiv.style.height = 'calc(100vh - 40px)';
            }
        });
    </script>
    """

    # Insérer la légende et le JS dans le HTML
    html_content = html_content.replace(
        '</body>',
        f'{legend_html}{css_js}</body>'
    )

    # Réécrire le fichier HTML
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    logger.info(f"Graphe interactif enregistré sous '{output_file}'")
    return output_file

import matplotlib.colors as mcolors  # Pour générer des couleurs dynamiques


def create_network_graph():
    G = nx.Graph()
    devices = get_devices()
    vlans_from_api = get_vlans()  # Liste complète des VLANs depuis NetBox

    # Initialiser un dictionnaire pour les couleurs des VLANs
    vlan_colors = {}
    edge_vlans = {}
    edge_port_labels = {}

    # Générer une palette de couleurs (une par VLAN)
    colors = list(mcolors.TABLEAU_COLORS.values())  # Palette de 10 couleurs distinctes
    if len(vlans_from_api) > len(colors):
        # Si plus de 10 VLANs, étendre avec une autre palette
        colors += list(mcolors.XKCD_COLORS.values())[:20]  # Ajoute 20 couleurs supplémentaires

    # Pré-remplir vlan_colors avec les VLANs de l'API
    for i, vlan in enumerate(vlans_from_api):
        vlan_colors[vlan["name"]] = colors[i % len(colors)]

    # Ajouter les nœuds (périphériques)
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

    # Récupérer les connexions
    connections = get_connections()

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

            # Récupérer les VLANs des interfaces
            a_vid, a_vlan_name = get_vlan_for_interface(a_interface["id"])
            b_vid, b_vlan_name = get_vlan_for_interface(b_interface["id"])

            # Déterminer le VLAN de la connexion et son VID
            if a_vid and b_vid and a_vid == b_vid:
                vlan_name = a_vlan_name
                vlan_vid = a_vid
            elif a_vid and not b_vid:
                vlan_name = a_vlan_name
                vlan_vid = a_vid
            elif b_vid and not a_vid:
                vlan_name = b_vlan_name
                vlan_vid = b_vid
            else:
                vlan_name = "No VLAN"
                vlan_vid = None

            # Si le VLAN n'est pas dans vlan_colors, lui attribuer une nouvelle couleur
            if vlan_name not in vlan_colors and vlan_name != "No VLAN":
                vlan_colors[vlan_name] = colors[len(vlan_colors) % len(colors)]

            # Stocker le nom et le VID dans edge_vlans
            G.add_edge(device_a_id, device_b_id)
            edge_port_labels[(device_a_id, device_b_id)] = (a_port_name, b_port_name)
            edge_vlans[(device_a_id, device_b_id)] = {"name": vlan_name, "vid": vlan_vid}

        except Exception as e:
            logger.error(f"Erreur pour la connexion {connection.get('id', 'inconnu')}: {e}")

    # Dessiner le graphe
    pos = nx.kamada_kawai_layout(G)
    node_labels = nx.get_node_attributes(G, 'label')

    plt.figure(figsize=(14, 10))
    nx.draw_networkx_nodes(G, pos, node_size=6000, node_shape="s", node_color='lightblue')

    # Dessiner les arêtes par VLAN (en utilisant le nom du VLAN)
    for edge, vlan_info in edge_vlans.items():
        vlan_name = vlan_info["name"]
        edges = [edge]  # Chaque arête est traitée individuellement
        nx.draw_networkx_edges(
            G, pos,
            edgelist=edges,
            edge_color=vlan_colors.get(vlan_name, "gray"),
            width=2,
            label=vlan_name  # Le label est géré par la légende
        )

    # Dessiner les étiquettes des nœuds et des ports
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

    # Générer la légende avec le VID
    handles = []
    for edge, vlan_info in edge_vlans.items():
        vlan_name = vlan_info["name"]
        vlan_vid = vlan_info["vid"]
        label = f"{vlan_name} ({vlan_vid})" if vlan_vid is not None else vlan_name
        if label not in [h.get_label() for h in handles]:  # Éviter les doublons
            handles.append(plt.Line2D([0], [0], color=vlan_colors.get(vlan_name, "gray"), lw=2, label=label))

    plt.legend(handles=handles, loc='upper right', fontsize=8)
    plt.title("Network Graph with Dynamic VLAN Colors")
    plt.savefig("network_graph_with_vlans.png", dpi=300, bbox_inches='tight')
    logger.info("Graphe enregistré sous 'network_graph_with_vlans.png'")
    plt.show()

    html_file = create_interactive_html_graph(G, edge_vlans, edge_port_labels, vlan_colors)
    print(f"Graphe interactif disponible : {html_file}")

if __name__ == "__main__":
    create_network_graph()