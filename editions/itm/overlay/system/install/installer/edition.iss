; Metis for ITM — the edition's identity, read by metis-setup.iss when present.
;
; Its own AppId: Windows treats it as its own program, so it installs, updates
; and uninstalls on its own terms, and an update can never come from the full
; build (see system/config/edition.json → update_repo).
#define MyAppName          "Metis for ITM"
#define MyAppId            "6F1E2B9C-3D47-4A85-9C61-2B7D0E5A9F13"
#define MyAppURL           "https://github.com/SVerITG/Metis_ITM"
; The update check looks for an asset starting with "MetisSetup"; keep that prefix.
#define OutputPrefix       "MetisSetup-ITM"
#define DefaultFolder      "Metis"
#define EditionInstitution "Institute of Tropical Medicine Antwerp"
#define NoDemo
#define EditionWelcome     "Welcome to Metis for ITM — a research companion for everyone at the institute.%n%nMetis gives every Claude conversation a memory of your subject, your papers, your projects and your working history, and it brings the institute's own templates and procedures with it: the IRB cover letter, the ITM presentation and poster.%n%nIt starts empty and learns from you: the next pages ask what you work on, which methods you use and what you want followed in the news. Everything Metis shows is built from those answers.%n%nYour files and data stay on your computer. Only what you type or share in a conversation goes to Claude.%n%n────────────────────────────────────────────%n%nThis installer will:%n  1. Install the Metis assistant and connect it to Claude Desktop%n  2. Install the research dashboard, with its ITM section%n  3. Ask you a few questions to set Metis up for your work%n%nInstallation takes 5–15 minutes depending on your connection. No API key is needed: Claude Desktop uses your Claude subscription."
