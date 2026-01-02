# 🚀 Guide d'Activation 24/7 (Gratuit)

Pour que ton bot tourne jour et nuit sans ton ordinateur, suis ces 3 étapes simples.

## Étape 1 : Créer ta "Mémoire" (Base de données)
Le bot a besoin d'un endroit pour noter ses trades. On va utiliser **Supabase** (gratuit).

1. Va sur [Supabase.com](https://supabase.com/) et clique sur **"Start your project"**.
2. Connecte-toi avec ton compte **GitHub**.
3. Clique sur **"New Project"**.
4. Donne un nom (ex: `TradingBot`) et crée un mot de passe fort (⚠️ **NOTE-LE BIEN !**).
5. Choisis une région proche de toi (ex: `Frankfurt` ou `London`).
6. Une fois le projet créé (ça prend 2 minutes), va dans les **Settings** (icône d'engrenage en bas à gauche) -> **Database**.
7. Cherche la section **Connection String** et clique sur **URI**.
8. Copie le lien qui ressemble à ça :
   `postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres`
9. **Remplace `[YOUR-PASSWORD]`** par le mot de passe que tu as choisi à l'étape 4. C'est ton `DATABASE_URL`.

## Étape 2 : Connecter à GitHub
Maintenant, on donne les clés au bot sur GitHub.

1. Va sur la page de ton projet sur **GitHub**.
2. Clique sur l'onglet **Settings** (tout à droite).
3. Dans la colonne de gauche, clique sur **Secrets and variables** -> **Actions**.
4. Clique sur le bouton vert **New repository secret**.
5. Ajoute les secrets suivants (un par un) :

| Nom du Secret | Valeur à coller |
|---|---|
| `BINANCE_API_KEY` | Ta clé API Binance (publique) |
| `BINANCE_SECRET_KEY` | Ta clé API Binance (secrète) |
| `DATABASE_URL` | Le lien Supabase copié à l'étape 1 (avec ton mot de passe) |
| `TELEGRAM_BOT_TOKEN` | (Optionnel) Ton token Telegram |
| `TELEGRAM_CHAT_ID` | (Optionnel) Ton ID Telegram |

## Étape 3 : Lancer la machine !
Tout est prêt.

1. Sur ton ordinateur, envoie la mise à jour sur GitHub (je peux le faire pour toi).
2. Va dans l'onglet **Actions** sur GitHub.
3. Tu verras "Trading Bot 24/7" apparaître.
4. Il se lancera tout seul **toutes les 15 minutes**.
5. Tu peux cliquer dessus pour voir les logs (lignes noires) et vérifier qu'il trade bien !

---
**Note :** Le bot dormira quand il n'y a rien à faire, mais il se réveillera toutes les 15 minutes pour vérifier les prix et gérer tes positions.
