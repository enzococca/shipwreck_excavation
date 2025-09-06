# Guida per Connettere PyCharm DB Manager a Supabase

## Credenziali Supabase trovate nel codice

Dal file `database/supabase_database_manager.py` (righe 31-34), ho estratto le seguenti credenziali:

- **URL Supabase**: `https://bqlmbmkffhzayinboanu.supabase.co`
- **Anon Key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxbG1ibWtmZmh6YXlpbmJvYW51Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4NzYyNzUsImV4cCI6MjA3MjQ1MjI3NX0.namIzY2eLMuBwk_FRFWizFzhxyvySW-hl4tnYqAwUhg`

## Configurazione PyCharm DB Manager

### Passo 1: Aprire Database Tool Window
1. In PyCharm, vai su **View** → **Tool Windows** → **Database**
2. Oppure usa la scorciatoia `Alt+1` o clicca sull'icona Database nella barra laterale

### Passo 2: Aggiungere una Nuova Connessione
1. Clicca sul pulsante **"+"** nella finestra Database
2. Seleziona **Data Source** → **PostgreSQL**

### Passo 3: Configurare la Connessione PostgreSQL
Inserisci i seguenti parametri:

#### Parametri di Connessione:
- **Host**: `db.bqlmbmkffhzayinboanu.supabase.co`
- **Port**: `5432`
- **Database**: `postgres`
- **User**: `postgres`
- **Password**: `[RICHIESTA NECESSARIA]` ⚠️

⚠️ **IMPORTANTE**: La password del database PostgreSQL non è presente nel codice per motivi di sicurezza. Dovrai:
1. Accedere al tuo account Supabase (https://supabase.com)
2. Andare nelle **Settings** del tuo progetto
3. Sezione **Database** → **Connection info**
4. Copiare la password del database

#### Parametri Avanzati (Scheda Advanced):
- **SSL Mode**: `require`

### Passo 4: Test della Connessione
1. Clicca su **Test Connection** per verificare che tutto funzioni
2. Se il test fallisce, controlla:
   - La password del database
   - La connessione internet
   - Le impostazioni firewall

### Passo 5: Salvare la Connessione
1. Dai un nome alla connessione (es. "Supabase - Shipwreck Excavation")
2. Clicca **OK** per salvare

## Struttura del Database

Una volta connesso, dovresti vedere le seguenti tabelle principali:
- `sites` - Siti di scavo
- `finds` - Reperti trovati
- `dive_logs` - Log delle immersioni
- `media_relations` - Relazioni media
- `workers` - Lavoratori
- `settings` - Impostazioni

## Alternative di Connessione

### Opzione 1: Utilizzando l'API REST Supabase
Se la connessione diretta PostgreSQL non funziona, puoi utilizzare l'API REST:
- **URL Base**: `https://bqlmbmkffhzayinboanu.supabase.co/rest/v1/`
- **API Key**: (quella trovata nel codice)
- **Authorization Header**: `Bearer [anon_key]`

### Opzione 2: Utilizzando Client SQL Esterni
Puoi anche usare client come:
- **pgAdmin**
- **DBeaver**
- **TablePlus**
- **Postico** (macOS)

Con gli stessi parametri di connessione PostgreSQL.

## Risoluzione Problemi Comuni

### Errore di Connessione SSL
Se hai errori SSL, prova:
- SSL Mode: `disable` (solo per test)
- Oppure scarica il certificato SSL di Supabase

### Errore di Autenticazione
- Verifica che la password del database sia corretta
- Controlla che l'IP sia autorizzato (Supabase di default permette tutte le connessioni)

### Timeout di Connessione
- Verifica la connessione internet
- Controlla se ci sono proxy o firewall che bloccano la porta 5432

## Note di Sicurezza

⚠️ **ATTENZIONE**: 
- La chiave API nel codice è pubblica (anon key) e ha permessi limitati
- Per operazioni administrative, dovresti usare la service_role key (non presente nel codice per sicurezza)
- Non condividere mai le credenziali complete del database

## Contatti per Supporto

Se hai problemi con la connessione:
1. Verifica lo stato di Supabase: https://status.supabase.com
2. Controlla la documentazione ufficiale: https://supabase.com/docs/guides/database/connecting-to-postgres
3. Verifica le impostazioni del progetto Supabase

---

*Guida creata automaticamente basata sull'analisi del codice del plugin QGIS Shipwreck Excavation*