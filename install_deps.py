import subprocess
import sys
import os

def install_dependencies():
    print("🚀 Début de l'installation des dépendances...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("\n✅ Installation terminée avec succès !")
    except Exception as e:
        print(f"\n❌ Erreur lors de l'installation : {e}")
        print("\n💡 Suggestion : Vérifie ta connexion internet ou essaie d'exécuter la commande manuellement :")
        print("pip install -r requirements.txt")

if __name__ == "__main__":
    # Check if requirements.txt exists
    if not os.path.exists("requirements.txt"):
        print("❌ Fichier requirements.txt non trouvé.")
    else:
        install_dependencies()
