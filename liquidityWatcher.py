import requests
import time
import os
from datetime import datetime
from web3 import Web3
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration
VAULT_ADDRESS = os.getenv("VAULT_ADDRESS")
AVALANCHE_RPC = os.getenv("AVALANCHE_RPC", "https://api.avax.network/ext/bc/C/rpc")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "3600"))  # 1 heure en secondes par défaut

# ABI minimal pour récupérer la liquidité disponible
VAULT_ABI = [
    {
        "inputs": [],
        "name": "totalAssets",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "asset",
        "outputs": [{"type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# ABI pour récupérer les infos de l'asset (token)
ERC20_ABI = [
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

def init_web3():
    """Initialise la connexion Web3 à Avalanche"""
    w3 = Web3(Web3.HTTPProvider(AVALANCHE_RPC))
    if not w3.is_connected():
        raise Exception("Impossible de se connecter au réseau Avalanche")
    return w3

def get_available_liquidity(w3, vault_address):
    """Récupère la liquidité disponible dans le vault"""
    try:
        # Créer le contrat vault
        vault = w3.eth.contract(address=Web3.to_checksum_address(vault_address), abi=VAULT_ABI)

        # Récupérer l'adresse de l'asset
        asset_address = vault.functions.asset().call()

        # Créer le contrat de l'asset
        asset = w3.eth.contract(address=asset_address, abi=ERC20_ABI)

        # Récupérer les informations
        decimals = asset.functions.decimals().call()
        symbol = asset.functions.symbol().call()

        # La liquidité disponible = balance de l'asset dans le vault
        available_liquidity = asset.functions.balanceOf(vault_address).call()

        # Convertir en valeur lisible
        liquidity_formatted = available_liquidity / (10 ** decimals)

        return {
            'raw': available_liquidity,
            'formatted': liquidity_formatted,
            'symbol': symbol,
            'decimals': decimals
        }

    except Exception as e:
        print(f"Erreur lors de la récupération de la liquidité: {e}")
        return None

def format_number(num):
    """Formate un nombre avec des espaces pour les milliers"""
    return f"{num:,.2f}".replace(",", " ")

def monitor_liquidity():
    """Surveille la liquidité toutes les heures"""
    print("🚀 Démarrage de la surveillance du vault Euler sur Avalanche")
    print(f"📍 Adresse du vault: {VAULT_ADDRESS}")
    print(f"⏰ Vérification toutes les {CHECK_INTERVAL//3600} heure(s)")
    print("-" * 60)

    # Initialiser Web3
    w3 = init_web3()
    print("✅ Connexion établie avec Avalanche\n")

    previous_liquidity = None

    while True:
        try:
            # Récupérer la liquidité
            liquidity_data = get_available_liquidity(w3, VAULT_ADDRESS)

            if liquidity_data:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                liquidity = liquidity_data['formatted']
                symbol = liquidity_data['symbol']

                # Afficher les résultats
                print(f"[{timestamp}]")
                print(f"💰 Liquidité disponible: {format_number(liquidity)} {symbol}")

                # Calculer la variation si on a une valeur précédente
                if previous_liquidity is not None:
                    change = liquidity - previous_liquidity
                    change_pct = (change / previous_liquidity * 100) if previous_liquidity != 0 else 0

                    if change > 0:
                        print(f"📈 Variation: +{format_number(change)} {symbol} (+{change_pct:.2f}%)")
                    elif change < 0:
                        print(f"📉 Variation: {format_number(change)} {symbol} ({change_pct:.2f}%)")
                    else:
                        print(f"➡️  Variation: Aucune")

                previous_liquidity = liquidity
                print("-" * 60)

            # Attendre 1 heure
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\n\n⛔ Arrêt de la surveillance...")
            break
        except Exception as e:
            print(f"❌ Erreur: {e}")
            print("⏳ Nouvelle tentative dans 5 minutes...")
            time.sleep(300)  # Attendre 5 minutes en cas d'erreur

if __name__ == "__main__":
    # Vérifier que l'adresse du vault est configurée
    if not VAULT_ADDRESS:
        print("⚠️  ATTENTION: Vous devez configurer l'adresse du vault!")
        print("Créez un fichier .env et ajoutez: VAULT_ADDRESS=0xVotreAdresse")
    else:
        monitor_liquidity()