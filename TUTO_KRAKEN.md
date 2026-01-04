# 🐙 Comment Créer tes Clés API Kraken (Alternative Fiable)

Kraken est l'un des échanges les plus sûrs et les plus ouverts aux développeurs en France. Contrairement à Bybit, ils permettent de créer des clés API personnalisées sans restrictions.

## 1. Créer/Se connecter à Kraken
Lien : [Kraken.com](https://www.kraken.com/)

## 2. Créer l'API Key
1.  Connecte-toi et clique sur ton **Nom/Profil** (en haut à droite).
2.  Direction **Settings** (Paramètres) > **API**.
3.  Clique sur **"Create API Key"** (Créer une clé API).
4.  **Nom** : Donne un nom (ex: `TradingBot`).
5.  **Permissions** :
    *   ✅ **Query Funds** (Consulter les fonds)
    *   ✅ **Query Open Orders & Trades** (Consulter les ordres ouverts)
    *   ✅ **Query Closed Orders & Trades** (Consulter les ordres fermés)
    *   ✅ **Modify Orders** (Modifier les ordres - c'est ça qui permet d'acheter/vendre)
    *   ❌ *Ne coche PAS "Withdraw Funds" (Retrait de fonds) pour ta sécurité.*
6.  **IP Restriction** : Laisse vide pour l'instant (ou mets ton IP si tu as une IP fixe).
7.  Clique sur **Generate Key**.

## 3. Récupérer les Clés
Tu vas obtenir :
*   **API Key**
*   **Private Key** (C'est le secret)

⚠️ **Copie-les bien !** Une fois la page fermée, tu ne pourras plus voir la Private Key.

---

## 4. Configuration MiCA (Important 2025)
En France, à cause des nouvelles lois (MiCA), privilégie les paires en **EUR** ou **USDC**. 
Le bot sera configuré par défaut pour utiliser ces paires stables.

---

## 5. Mettre à jour GitHub (Si besoin)
1.  Va dans ton dépôt **GitHub > Settings > Secrets > Actions**.
2.  Ajoute ou modifie `KRAKEN_API_KEY`.
3.  Ajoute ou modifie `KRAKEN_SECRET_KEY`.
4.  Modifie `ACTIVE_EXCHANGE` pour mettre `kraken`.
