





-- Aufbau Frontend
sidebar
  - Dashboard
  - shop for services
  - notifications
  - review requests
  - subscriptions
  - my services

dashboard
  - versenkbare sidebar
  - titel
  - suche
  - warenkorb
  - nutzeranmeldung

All Subscriptions Punkt
  - Auflistung aller Subscriptions
  - Suchfeld
  - Kategorie Filter
  - Subscription Status Filter
  - Sortierung
  - Button List Actions
  - Button Refresh

Notification Punkt
My Services Punkt
My Requests Punkt
Review Requests Punkt


---- Administration
Manage User Subscriptions
Catalog Management
Offering Management


---- Shop for Services
All Services
    - Request Service
       - Typ (Windows VM, Linux VM)
       - Netzwerk
          - Hostnamen- und Netzwerkkonfiguration
            - Systemtyp
                - db
                - dc
                - fp
                .. beliebig erweiterbar
            - Mandant
                - a1
                - b1
                - c1
            - Sicherheitsbereich
                - SecBereich1
                - SecBereich2
                - SecBereich3
            - Organisationsbereich
                - OuBereich1
                - OuBereich2
            - Standort
                - Standort1
                - Standort2
            - DNS Server
            - Loadbalancing-Subnetz
            - Sicherheitsklasse (AD Tier)
            - Layer
            - Netzwerk(VLAN)
        - Platzierung
            - Zuordnung im AD
                - APP
                - Debug
                - Test
                beliebig erweiterbar
            - Zuordnung im VMware Cluster
                - Single Side Cluster
                - Dual Site Cluster
        -Betriebssystem
            - Template
                - Windows 2016
                - Windows 2019
                - Windows 2022
        - VM Sizing
            - T-Shirt Size
                - 5 unterschiedliche Größen, füllt die folgenden Felder per Definition
                - CPU Cores
                - RAM
                - Größe OS Disk
        - Datenspeicher
            - zusätzliche Festplatte #1
            - zusätzliche Festplatte #2
            - zusätzliche Festplatte #3
            - zusätzliche Festplatte #4
        - Server Informationen
            - Allgemeine Informationen
                - Funktionsbeschreibung
                - Systembesteller  (mail)
                - Systemverantwortlicher (mail)
                - Kontaktgruppe (mail)
                - Ticket-ID
        - Softwaremanagement
            - Softwareverteilungssystem
                - Wartungszeitfenster
                - Patchwelle
        - Backup
            - Backupstatus
                - ja/nein
            - Standortreplikation
                - ja/nein


New Releases
Features Services
Popular Services



--
erstelle eine Installationshilfe/Script um eine Offline Demo Installation zu ermöglichen 

--
sammel die Prereqs zusammen und füge einen Prereqs Eintrag in den DEv Launcher ein
