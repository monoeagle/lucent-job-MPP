# Abhaengigkeitsmatrix — Windows/Linux VM Template

## Alle Enum-Felder und ihre Optionen

| # | Feld | Optionen | Anzahl |
|---|------|---------|--------|
| 1 | vm_type | windows, linux | 2 |
| 2 | system_type | db, dc, fp, app, web | 5 |
| 3 | mandant | a1, b1, c1 | 3 |
| 4 | security_area | sec1, sec2, sec3 | 3 |
| 5 | org_area | ou1, ou2 | 2 |
| 6 | location | standort1, standort2 | 2 |
| 7 | ad_tier | tier0, tier1, tier2 | 3 |
| 8 | network_layer | frontend, backend, management | 3 |
| 9 | network_vlan | vlan100, vlan110, vlan200, vlan300, vlan400 | 5 |
| 10 | ad_assignment | app, debug, test, prod | 4 |
| 11 | vmware_cluster | single-site, dual-site | 2 |
| 12 | os_template | win2016, win2019, win2022 | 3 |
| 13 | os_template_linux | ubuntu2204, ubuntu2404, rhel9, alma10 | 4 |
| 14 | tshirt_size | xs, s, m, l, xl | 5 |
| 15 | maintenance_window | wed-02-06, sat-02-06, sun-02-06 | 3 |
| 16 | patch_wave | wave1, wave2, wave3 | 3 |
| 17 | backup_enabled | true, false | 2 |
| 18 | site_replication | true, false | 2 |

## Theoretische Kombinationen (ohne Einschraenkungen)

**Nur Enum-Felder:** 2 x 5 x 3 x 3 x 2 x 2 x 3 x 3 x 5 x 4 x 2 x 4 x 5 x 3 x 3 x 2 x 2 = **~23.328.000**

(os_template und os_template_linux sind exklusiv → effektiv max 4 statt 3+4)

**Korrigiert (vm_type bestimmt OS):** 2 x 5 x 3 x 3 x 2 x 2 x 3 x 3 x 5 x 4 x 2 x 4 x 5 x 3 x 3 x 2 x 2 / 2 = **~11.664.000**

## Abhaengigkeitsmatrix

### Legende
- **→ filtert** = Auswahl A schraenkt Optionen von B ein
- **→ sichtbar** = Auswahl A bestimmt ob B sichtbar ist
- **→ fuellt** = Auswahl A setzt Wert von B automatisch

### Abhaengigkeiten

```
vm_type ──→ sichtbar ──→ os_template (nur bei windows)
        ──→ sichtbar ──→ os_template_linux (nur bei linux)

system_type ──→ filtert ──→ ad_tier (Tier0 nur bei dc)
            ──→ filtert ──→ network_layer (management nur bei dc/db)
            ──→ filtert ──→ ad_assignment (prod nur bei db/app/web, debug nur bei app/web)
            ──→ filtert ──→ tshirt_size (dc braucht mind. M, db mind. S)
            ──→ filtert ──→ lb_subnet (nur sichtbar bei web/app)

mandant ──→ filtert ──→ org_area (ou1 nur bei a1/b1, ou2 nur bei b1/c1)
        ──→ filtert ──→ security_area (sec3 nur bei a1)

security_area ──→ filtert ──→ network_vlan (sec1→vlan100/200/400, sec2→vlan110/200/400, sec3→vlan300/400)
              ──→ filtert ──→ vmware_cluster (dual-site nur bei sec1/sec2)
              ──→ filtert ──→ location (standort2 nur bei sec1/sec2)

location ──→ fuellt ──→ dns_server (standort1→10.1.0.53, standort2→10.2.0.53)

ad_assignment ──→ filtert ──→ patch_wave (prod→wave3, test→wave1/wave2, debug→wave1)
              ──→ filtert ──→ maintenance_window (prod→sun, test/debug→wed/sat)

tshirt_size ──→ fuellt ──→ cpu_cores
            ──→ fuellt ──→ ram_gb
            ──→ fuellt ──→ os_disk_gb

backup_enabled ──→ sichtbar ──→ site_replication (nur bei true)

network_layer ──→ filtert ──→ network_vlan (management→nur vlan300/400)
```

### Vollstaendige Filtermatrix

#### system_type → ad_tier
| system_type | tier0 | tier1 | tier2 |
|-------------|:-----:|:-----:|:-----:|
| db          |       | ✓     |       |
| dc          | ✓     | ✓     |       |
| fp          |       | ✓     |       |
| app         |       | ✓     | ✓     |
| web         |       | ✓     | ✓     |

#### system_type → network_layer
| system_type | frontend | backend | management |
|-------------|:--------:|:-------:|:----------:|
| db          |          | ✓       | ✓          |
| dc          |          | ✓       | ✓          |
| fp          |          | ✓       |            |
| app         | ✓        | ✓       |            |
| web         | ✓        | ✓       |            |

#### system_type → ad_assignment
| system_type | app | debug | test | prod |
|-------------|:---:|:-----:|:----:|:----:|
| db          | ✓   |       | ✓    | ✓    |
| dc          | ✓   |       | ✓    | ✓    |
| fp          | ✓   |       | ✓    | ✓    |
| app         | ✓   | ✓     | ✓    | ✓    |
| web         | ✓   | ✓     | ✓    | ✓    |

#### system_type → tshirt_size (Mindestgroesse)
| system_type | xs | s | m | l | xl |
|-------------|:--:|:-:|:-:|:-:|:--:|
| db          |    | ✓ | ✓ | ✓ | ✓  |
| dc          |    |   | ✓ | ✓ | ✓  |
| fp          | ✓  | ✓ | ✓ | ✓ | ✓  |
| app         | ✓  | ✓ | ✓ | ✓ | ✓  |
| web         | ✓  | ✓ | ✓ | ✓ | ✓  |

#### mandant → org_area
| mandant | ou1 | ou2 |
|---------|:---:|:---:|
| a1      | ✓   |     |
| b1      | ✓   | ✓   |
| c1      |     | ✓   |

#### mandant → security_area
| mandant | sec1 | sec2 | sec3 |
|---------|:----:|:----:|:----:|
| a1      | ✓    | ✓    | ✓    |
| b1      | ✓    | ✓    |      |
| c1      | ✓    |      |      |

#### security_area → network_vlan
| security_area | vlan100 | vlan110 | vlan200 | vlan300 | vlan400 |
|---------------|:-------:|:-------:|:-------:|:-------:|:-------:|
| sec1          | ✓       |         | ✓       |         | ✓       |
| sec2          |         | ✓       | ✓       |         | ✓       |
| sec3          |         |         |         | ✓       | ✓       |

#### security_area → vmware_cluster
| security_area | single-site | dual-site |
|---------------|:-----------:|:---------:|
| sec1          | ✓           | ✓         |
| sec2          | ✓           | ✓         |
| sec3          | ✓           |           |

#### security_area → location
| security_area | standort1 | standort2 |
|---------------|:---------:|:---------:|
| sec1          | ✓         | ✓         |
| sec2          | ✓         | ✓         |
| sec3          | ✓         |           |

#### ad_assignment → patch_wave
| ad_assignment | wave1 | wave2 | wave3 |
|---------------|:-----:|:-----:|:-----:|
| app           | ✓     | ✓     |       |
| debug         | ✓     |       |       |
| test          | ✓     | ✓     |       |
| prod          |       |       | ✓     |

#### ad_assignment → maintenance_window
| ad_assignment | wed-02-06 | sat-02-06 | sun-02-06 |
|---------------|:---------:|:---------:|:---------:|
| app           | ✓         | ✓         |           |
| debug         | ✓         | ✓         |           |
| test          | ✓         | ✓         |           |
| prod          |           |           | ✓         |

#### network_layer → network_vlan (zusaetzliche Einschraenkung)
| network_layer | vlan100 | vlan110 | vlan200 | vlan300 | vlan400 |
|---------------|:-------:|:-------:|:-------:|:-------:|:-------:|
| frontend      | ✓       | ✓       | ✓       |         | ✓       |
| backend       | ✓       | ✓       | ✓       |         |         |
| management    |         |         |         | ✓       | ✓       |

#### location → dns_server (Auto-Fill)
| location | dns_server |
|----------|-----------|
| standort1 | 10.1.0.53 |
| standort2 | 10.2.0.53 |

## Gueltige Kombinationen (geschaetzt)

Mit allen Einschraenkungen reduzieren sich die ~11.6 Mio auf ca. **~45.000 gueltige Kombinationen**.

Hauptreduktionen:
- mandant→security_area: 3x3=9 → 6 gueltig (33% weniger)
- mandant→org_area: 3x2=6 → 4 gueltig (33% weniger)
- system_type→ad_tier: 5x3=15 → 8 gueltig (47% weniger)
- security_area→vlan: 3x5=15 → 8 gueltig (47% weniger)
- ad_assignment→patch_wave: 4x3=12 → 5 gueltig (58% weniger)
- ad_assignment→maintenance: 4x3=12 → 5 gueltig (58% weniger)
- system_type→tshirt: 5x5=25 → 21 gueltig (16% weniger)
