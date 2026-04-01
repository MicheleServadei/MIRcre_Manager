# 🎬 MirCrew Manager v2.1

MirCrew Manager è una dashboard moderna e automatizzata per monitorare, sfogliare e gestire le ultime release cinematografiche dal forum MirCrew. Dimentica lo scrolling infinito: tutto il catalogo viene organizzato con dati reali da **TMDB** (Poster, Rating, Anni) in un'unica interfaccia pulita.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-2.0+-black?style=for-the-badge&logo=flask)
![Playwright](https://img.shields.io/badge/Playwright-Latest-green?style=for-the-badge&logo=playwright)

---

## 🚀 Funzionalità Principali

* **Scraping Automatico**: Analizza le ultime release del forum usando Playwright.
* **Arricchimento TMDB**: Recupera automaticamente poster in alta risoluzione, voti medi e date di uscita.
* **Gestione Versioni**: Raggruppa automaticamente film con più qualità (es. 1080p e 4K) in un'unica scheda con selettore rapido.
* **Notifiche Telegram**: Invia un messaggio istantaneo al tuo bot ogni volta che viene pubblicata una nuova release.
* **Interfaccia Netflix-Style**: Ricerca istantanea, filtri per genere, ordinamento per rating o data e paginazione fluida.

---

## 🛠️ Requisiti & Installazione

Non devi impazzire con i comandi. Il progetto è progettato per auto-configurarsi.

1.  **Clona il repository**:
    ```bash
    git clone [https://github.com/TUO-UTENTE/mircrew-manager.git](https://github.com/TUO-UTENTE/mircrew-manager.git)
    cd mircrew-manager
    ```

2.  **Configurazione**:
    Apri `mircrew_manager.py` e inserisci le tue chiavi nelle variabili in alto:
    * `TMDB_API`: La tua chiave API di TheMovieDB.
    * `TELEGRAM_TOKEN`: Il token del tuo bot Telegram.
    * `TELEGRAM_CHAT_ID`: Il tuo ID chat.

3.  **Avvio Rapido (Windows)**:
    Fai doppio clic sul file **`START_MIRCREW.bat`**. 
    * Lo script installerà automaticamente le librerie (`flask`, `playwright`, `requests`).
    * Configurerà i driver del browser.
    * Avvierà Chrome in modalità Debug e il server Flask.

---

## 🖥️ Utilizzo Corretto

### Il Segreto del Debug
Per permettere allo scraper di leggere il forum, Chrome deve essere aperto sulla porta `9222`. 
* **Via Script**: Usa il file `.bat` (consigliato).
* **Via Windows+R**: Chiudi Chrome e digita:
    `chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\MirCrew_Debug"`

Una volta aperto Chrome, effettua il login sul forum e spunta **"Loggami automaticamente"**. Da quel momento, potrai lanciare lo **SCAN** direttamente dalla dashboard web.

---

## 📂 Struttura del Progetto

* `mircrew_manager.py`: Il cuore del sistema (Backend Flask + Scraper).
* `templates/index.html`: L'interfaccia utente (Frontend).
* `START_MIRCREW.bat`: Script di automazione per installazione e avvio.
* `static/`: Contiene il database JSON e le risorse statiche.

---

## ⚠️ Disclaimer
Questo progetto è sviluppato esclusivamente per **uso personale e didattico**. L'autore non si assume alcuna responsabilità per l'uso improprio dello strumento o per violazioni dei termini di servizio di siti terzi.

---

**Sviluppato con ❤️ per la community MirCrew.**
