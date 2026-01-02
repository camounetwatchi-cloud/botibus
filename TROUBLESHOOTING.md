# 🔧 Guide de Dépannage Rapide

## 🚀 Problèmes de Lancement

### ❌ Le fichier .bat ne lance pas l'application

**Solution 1:** Vérifiez que vous êtes dans le bon répertoire
```
Chemin attendu: c:\Users\natha\tradingllm\
```

**Solution 2:** Essayez la version PowerShell
```powershell
# Clic droit sur start_trading_app.ps1 → "Exécuter avec PowerShell"
```

**Solution 3:** Lancement manuel
```powershell
cd c:\Users\natha\tradingllm
.\venv\Scripts\Activate.ps1
python scripts\live_trade.py
# Dans un autre terminal:
streamlit run src\monitoring\dashboard.py
```

### ❌ Erreur "python n'est pas reconnu"

**Cause:** L'environnement virtuel n'est pas activé

**Solution:**
```powershell
cd c:\Users\natha\tradingllm
.\venv\Scripts\Activate.ps1
```

### ❌ Erreur "ModuleNotFoundError: No module named 'src'"

**Cause:** PYTHONPATH n'est pas défini

**Solution:**
```powershell
$env:PYTHONPATH="."
python scripts\live_trade.py
```

## 📊 Problèmes du Dashboard

### ❌ Le dashboard ne s'affiche pas

**Solution 1:** Vérifiez que Streamlit est démarré
- Cherchez une fenêtre de terminal avec "Streamlit"
- L'URL devrait être: http://localhost:8501

**Solution 2:** Ouvrez manuellement le navigateur
```
http://localhost:8501
```

**Solution 3:** Port déjà utilisé
```powershell
# Arrêtez le processus existant
Get-Process | Where-Object {$_.ProcessName -like "*python*"} | Stop-Process

# Relancez l'application
.\start_trading_app.bat
```

### ❌ Les boutons ne fonctionnent pas

**Cause:** Cache Streamlit corrompu

**Solution:**
1. Allez dans Settings
2. Cliquez sur "Clear Cache"
3. Rafraîchissez la page (F5)

### ❌ Les données ne s'affichent pas

**Cause:** Le bot de trading n'est pas démarré

**Solution:**
- Vérifiez qu'il y a une fenêtre "Trading Bot (Live)" ouverte
- Si non, relancez `start_trading_app.bat`

### ❌ L'export CSV ne fonctionne pas

**Solution:**
1. Vérifiez que vous avez des données à exporter
2. Autorisez les téléchargements dans votre navigateur
3. Vérifiez votre dossier de téléchargements

## 🎯 Problèmes de Performance

### ❌ L'application est lente

**Solution 1:** Désactivez l'auto-refresh
- Déscochez "Auto Refresh" dans la barre latérale
- Utilisez "Force Refresh" manuellement

**Solution 2:** Videz le cache
- Allez dans Settings → Clear Cache

**Solution 3:** Réduisez le refresh rate
- Augmentez le slider à 30-60 secondes

### ❌ Le navigateur consomme trop de mémoire

**Solution:**
- Fermez les autres onglets
- Redémarrez le navigateur
- Relancez l'application

## 🔐 Problèmes de Données

### ❌ Pas de données de trading

**Cause:** Le bot vient de démarrer

**Solution:**
- Attendez quelques minutes
- Le bot simule des trades toutes les 5-10 secondes
- Les données apparaîtront progressivement

### ❌ Les graphiques sont vides

**Cause:** Pas assez de données historiques

**Solution:**
- Laissez le bot tourner pendant 15-30 minutes
- Les graphiques se rempliront automatiquement
- Utilisez "Force Refresh" pour actualiser

## 🛑 Arrêt d'Urgence

### Comment arrêter l'application

**Méthode 1:** Bouton Emergency Stop
- Cliquez sur "🛑 EMERGENCY STOP" dans la barre latérale
- (En mode démo, c'est simulé)

**Méthode 2:** Fermer les fenêtres
- Fermez la fenêtre "Trading Bot (Live)"
- Fermez la fenêtre "Trading Dashboard"
- Fermez l'onglet du navigateur

**Méthode 3:** Kill processus
```powershell
# Arrêter tous les processus Python
Get-Process python | Stop-Process -Force

# Arrêter Streamlit spécifiquement
Get-Process | Where-Object {$_.MainWindowTitle -like "*Streamlit*"} | Stop-Process
```

## 📞 Support Avancé

### Vérifier les logs

**Bot de trading:**
- Regardez dans la fenêtre "Trading Bot (Live)"
- Les logs apparaissent en temps réel

**Dashboard:**
- Regardez dans la fenêtre "Trading Dashboard"
- Ou ouvrez la console du navigateur (F12)

### Réinitialisation complète

Si rien ne fonctionne:

```powershell
# 1. Arrêtez tout
Get-Process python | Stop-Process -Force

# 2. Nettoyez le cache
Remove-Item -Recurse -Force .streamlit\cache\* -ErrorAction SilentlyContinue

# 3. Redémarrez
.\start_trading_app.bat
```

### Vérifier l'environnement

```powershell
# Activez l'environnement virtuel
.\venv\Scripts\Activate.ps1

# Vérifiez Python
python --version

# Vérifiez les packages
pip list | Select-String streamlit
pip list | Select-String pandas

# Réinstallez si nécessaire
pip install -r requirements.txt
```

## ✅ Checklist de Diagnostic

Avant de demander de l'aide, vérifiez:

- [ ] L'environnement virtuel est dans `c:\Users\natha\tradingllm\venv`
- [ ] Le fichier `start_trading_app.bat` existe
- [ ] Python 3.x est installé
- [ ] Les dépendances sont installées (`pip list`)
- [ ] Aucun autre processus n'utilise le port 8501
- [ ] Votre navigateur est à jour
- [ ] Windows Defender n'bloque pas l'application

## 🆘 Contacts Urgents

**Pour les bugs critiques:**
1. Capturez une capture d'écran de l'erreur
2. Notez les messages dans le terminal
3. Vérifiez la version de Python et des packages
4. Consultez les logs

**Fichiers de support:**
- `GUIDE_UTILISATEUR.md` - Documentation complète
- `VERIFICATION_CHECKLIST.md` - Liste de vérification
- `walkthrough.md` - Guide détaillé des fonctionnalités

---

**Dernière mise à jour:** 2026-01-02  
**Version:** 1.0
