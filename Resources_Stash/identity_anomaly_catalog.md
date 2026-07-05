# Identity Anomaly Catalog
## Comprehensive UEBA Detection Patterns for Identity & Access Events

*Reference document — not all patterns are implemented in the current generator.*

---

### 1. Geographic & Travel Anomalies

| # | Anomaly | Description | MITRE ATT&CK | Notes |
|---|---------|-------------|--------------|-------|
| 1 | **Impossible Travel** | Same user authenticates from two cities too far apart for the time elapsed | T1078 (Valid Accounts) | Flags credential theft; speed threshold typically ~900 km/h |
| 2 | **New Country Login** | User logs in from a country they have never visited before | T1078 (Valid Accounts) | High signal if combined with odd hour |
| 3 | **New City Login** | User logs in from an unfamiliar city within an otherwise known country | T1078 (Valid Accounts) | Lower severity than new country |
| 4 | **New Country Odd Hour** | Login from new country during user's typical sleeping hours | T1078 (Valid Accounts) | Strong signal — stolen creds resold internationally |
| 5 | **Unusual Geo Velocity** | User moves between countries at unusual speed (not quite impossible, but suspicious) | T1078 (Valid Accounts) | e.g., 3 countries in 6 hours |
| 6 | **Known Bad Region** | Login from a sanctioned or high-risk country (e.g., Russia, North Korea, Iran) | T1078 (Valid Accounts) | Requires geo-threat intelligence feed |
| 7 | **Tor Exit Node Login** | Authentication from a known Tor exit node | T1090.002 (Proxy: External Proxy) | Anonymization flag |
| 8 | **Datacenter/Hosting IP Login** | Login from a cloud or datacenter IP range not associated with the user's org | T1090.002 (Proxy: External Proxy) | Common for attackers using VPS proxies |
| 9 | **Coordinate Anomaly** | GPS coordinates inconsistent with claimed city (spoofed location) | T1078 (Valid Accounts) | Requires device GPS data |
| 10 | **Port/IP Rotation** | Rapid cycling through IPs/ports — scanning or proxy rotation | T1090 (Proxy) | May indicate C2 infrastructure |

---

### 2. Temporal & Behavioral Anomalies

| # | Anomaly | Description | MITRE ATT&CK | Notes |
|---|---------|-------------|--------------|-------|
| 11 | **Off-Hours Access** | Login during unusual hours for the user (single event) | T1078 (Valid Accounts) | Check user's local timezone |
| 12 | **Sustained Off-Hours Activity** | Repeated off-hours access over multiple days | T1078 / T1098 (Account Manipulation) | Insider threat pattern |
| 13 | **Weekend/Holiday Login** | First-time login on a weekend or public holiday | T1078 (Valid Accounts) | Escalates when paired with data access |
| 14 | **Holiday Paradox** | User logged in from a country on a date when the user's home country celebrates a holiday | T1078 (Valid Accounts) | User "should" be at home |
| 15 | **Unusual Login Frequency** | User logging in much more frequently than their historical baseline | T1078 (Valid Accounts) | Automation or scripted access |
| 16 | **Inactivity After Anomaly** | No further activity from the user after a suspicious event | T1078 (Valid Accounts) | Could indicate session hijack then exit |
| 17 | **Time Drift** | User's event timestamps deviate from their typical hourly pattern | T1078 (Valid Accounts) | Suggests account shared across timezones |

---

### 3. Authentication Failure Anomalies

| # | Anomaly | Description | MITRE ATT&CK | Notes |
|---|---------|-------------|--------------|-------|
| 18 | **Brute Force (Single User)** | Multiple rapid failed logins targeting one account | T1110.001 (Password Guessing) | Lockout threshold |
| 19 | **Password Spraying** | Single password tried across many accounts | T1110.003 (Password Spraying) | Common AD attack — avoids lockout |
| 20 | **Credential Stuffing** | Known breached credentials used at scale | T1110.004 (Credential Stuffing) | Often from dark web credential dumps |
| 21 | **Fail-to-Success Ratio Spike** | Sudden increase in failed-to-successful login ratio | T1110 (Brute Force) | Early indicator |
| 22 | **Spike in MFA Denials** | User denies multiple MFA push requests | T1556.006 (Multi-Factor Authentication) | MFA fatigue attack |
| 23 | **Success After Fail Chain** | Successful login immediately following a chain of failures | T1110 (Brute Force) | Indicates attacker finally guessed correctly |
| 24 | **Failover Auth Method** | User switches to backup authentication after primary fails | T1556 (Modify Auth. Process) | Could indicate credential theft |
| 25 | **Password Reset Followed by Login** | Password reset then immediate login from new device/location | T1078 (Valid Accounts) | Attacker uses self-service reset |

---

### 4. Device & Browser Anomalies

| # | Anomaly | Description | MITRE ATT&CK | Notes |
|---|---------|-------------|--------------|-------|
| 26 | **Unknown Device** | First-seen device authenticating | T1078 (Valid Accounts) | Low signal alone, high with other factors |
| 27 | **Unknown Browser/OS** | Unfamiliar user-agent string | T1078 (Valid Accounts) | E.g., Chrome→Tor Browser |
| 28 | **Unknown Device + VPN** | First-seen device connecting through a VPN | T1090.002 (Proxy) + T1078 | Strong stolen-credential signal |
| 29 | **Device Spoofing** | Device fingerprint mismatch (claimed vs actual OS, screen, fonts) | T1078 (Valid Accounts) | Anti-fingerprinting evasion |
| 30 | **Emulator/VM Detection** | Login from Android emulator, iOS simulator, or VM | T1078 (Valid Accounts) | Common in bot/fraud networks |
| 31 | **Rooted/Jailbroken Device** | Device security policy violation | T1200 (Hardware Additions) | Policy enforcement |
| 32 | **Browser Incognito/Private Mode** | User accessing via private/incognito browsing | — | Low severity; mainly log |
| 33 | **Cookie Reuse** | Session cookie used from a different device/IP | T1539 (Steal Session Cookie) | Token theft |
| 34 | **Device OS Outdated** | Login from a device running unpatched/unusual OS | T1078 (Valid Accounts) | Policy violation, lateral movement vector |
| 35 | **Certificate Anomaly** | Client certificate expired, revoked, or mismatched | T1649 (Steal Digital Certificates) | Certificate theft |

---

### 5. Data Transfer & Exfiltration Anomalies

| # | Anomaly | Description | MITRE ATT&CK | Notes |
|---|---------|-------------|--------------|-------|
| 36 | **Bulk Transfer — New IP** | Large data volume to a previously unseen IP | T1041 (Exfiltration Over C2) | C2 or staged exfil |
| 37 | **Bulk Transfer — New Country** | Large data transfer to a new country | T1041 (Exfiltration Over C2) | Geopolitical risk |
| 38 | **Off-Hours Download** | Large download during non-business hours | T1041 (Exfiltration Over C2) | Insider threat |
| 39 | **Unusual Data Volume Spike** | Sudden increase in data transfer vs user baseline | T1041 / T1567 | Statistical anomaly |
| 40 | **Data to Personal Cloud** | Transfer to personal cloud storage (Google Drive, Dropbox, etc.) | T1567 (Exfil Over Web Service) | Insider exfiltration vector |
| 41 | **Data to External Email** | Sending data to external email addresses | T1567.003 (Exfil Over Email) | Corporate email→personal email |
| 42 | **Compressed/Encrypted Output** | User creating archive files and uploading in unusual volumes | T1560 (Archive Collected Data) | Data staging before exfil |
| 43 | **Print Spooling Spike** | Unusual increase in print jobs before resignation | T1059 (Command & Scripting Interpreter: PowerShell) | Insider — documents leaving company |
| 44 | **USB Activity Spike** | Rapid file copy to removable media | T1091 (Replication Through Removable Media) | Policy violation |

---

### 6. Privilege & Account Manipulation

| # | Anomaly | Description | MITRE ATT&CK | Notes |
|---|---------|-------------|--------------|-------|
| 45 | **Privilege Escalation** | Account suddenly granted admin/privileged access | T1098 (Account Manipulation) | Frustrated privilege escalation |
| 46 | **Group Membership Change** | User added/removed from security groups | T1098 (Account Manipulation) | Lateral movement prep |
| 47 | **New Admin Account** | Creation of a new privileged account | T1136 (Create Account) | Persistence |
| 48 | **Service Principal Added** | New service principal or app registration | T1098 (Account Manipulation) | Backdoor/OAuth abuse |
| 49 | **Role Assumption** | User assumes an IAM role they have never used before | T1078 (Valid Accounts) | Cloud-specific (AWS STS) |
| 50 | **API Key Creation** | Unusual API key or access key generation | T1098 (Account Manipulation) | Persistence/automation |
| 51 | **Dormant Account Reactivation** | Account inactive >90 days suddenly active | T1078 (Valid Accounts) | Stale account compromise |
| 52 | **Shadow Admin** | Regular user unexpectedly able to perform admin actions | T1078.004 (Cloud Accounts) | Cloud misconfiguration abuse |
| 53 | **Cross-Tenant Access** | User accessing resources in another tenant | T1526 (Cloud Service Discovery) | Multi-tenant attack |

---

### 7. Session & Token Anomalies

| # | Anomaly | Description | MITRE ATT&CK | Notes |
|---|---------|-------------|--------------|-------|
| 54 | **Concurrent Sessions** | Same account active in multiple distinct locations simultaneously | T1078 (Valid Accounts) | Session hijack |
| 55 | **Token Replay** | Same session/JWT used from different IPs | T1539 (Steal Session Cookie) | Token theft |
| 56 | **Impossible Session Chain** | Events from same session in geographically impossible sequence | T1078 (Valid Accounts) | Session doppelgänger |
| 57 | **Token Lifetime Anomaly** | Session token living longer than typical TTL | T1539 (Steal Session Cookie) | Token misuse |
| 58 | **Refresh Token Abuse** | Refresh token used from unexpected location | T1528 (Steal Application Access Token) | OAuth abuse |
| 59 | **Non-Interactive Login via Browser** | User-agent shows browser but auth protocol is non-interactive (e.g., ROPC) | T1078 (Valid Accounts) | Automation misusing browser profile |

---

### 8. Behavioral Drift & Baseline Anomalies

| # | Anomaly | Description | MITRE ATT&CK | Notes |
|---|---------|-------------|--------------|-------|
| 60 | **App Access Change** | User accessing an application they have never used before | T1078 (Valid Accounts) | Recon/lateral movement |
| 61 | **Resource Access Change** | User accessing unusual servers, shares, or databases | T1078 (Valid Accounts) | Data discovery |
| 62 | **Unusual Query Pattern** | Unusually complex or voluminous database queries | T1059 (Command & Scripting Interpreter) | Data scraping |
| 63 | **Service-to-Service Anomaly** | Service account behaving unlike its historical baseline | T1078 (Valid Accounts) | Compromised service principal |
| 64 | **User Agent Drift** | User's browser/app version changing abruptly | — | Possible device change |
| 65 | **Working Hour Drift** | User's typical login time shifting by >2 hours over several days | — | Could indicate shared account |
| 66 | **Clickstream Anomaly** | Navigation pattern differs from user's typical workflows | — | RPA/bot activity |
| 67 | **Keyboard/Mouse Biometrics** | Keystroke dynamics or mouse movement anomaly | — | Account takeover |

---

### 9. Compliance & Insider Threat

| # | Anomaly | Description | MITRE ATT&CK | Notes |
|---|---------|-------------|--------------|-------|
| 68 | **Data Hoarding Pre-Exit** | Unusual data collection activity before resignation | — | Insider threat indicator |
| 69 | **Resignation Date Proximity** | Anomalous activity spike within N days of resignation | — | IP theft window |
| 70 | **Policy Violation — PII Access** | Access to data user has no business need for | — | GDPR/HIPAA compliance |
| 71 | **Non-Employee Access Spike** | Contractor/partner accessing internal systems unusually | — | Third-party risk |
| 72 | **Internal Recon** | User enumerating directory users, groups, or permissions | T1069 (Permission Groups Discovery) | Lateral movement prep. |
| 73 | **SharePoint/Drive Crawl** | User listing/downloading all files in a repository | T1213 (Data from Information Repositories) | Data staging |
| 74 | **Multiple Failed MFA Challenges** | User fails MFA multiple times then succeeds | T1556.006 (MFA) | MFA bypass attempt |

---

### Distribution by Risk Level (subjective)

| Risk Level | Count | Example Patterns |
|---|---|---|
| **Critical** | ~15 | Impossible travel, token replay, bulk exfil to new country, dormant account, MFA fatigue success |
| **High** | ~20 | New country login, brute force, privilege escalation, data hoarding, concurrent sessions |
| **Medium** | ~25 | Unknown device, off-hours access, new app access, working hour drift |
| **Low** | ~14 | Weekend login, device OS outdated, private browsing, user agent drift |

---

### MITRE ATT&CK Coverage Summary

| Tactic | Techniques Covered |
|---|---|
| Initial Access | T1078 (Valid Accounts) |
| Credential Access | T1110 (Brute Force), T1556 (Modify Auth) |
| Exfiltration | T1041, T1567 (Web Service), T1560 (Archive) |
| Command & Control | T1090 (Proxy) |
| Persistence | T1098 (Account Manipulation), T1136 (Create Account) |
| Discovery | T1069, T1526 |
| Defense Evasion | T1649, T1539, T1528 |

---

*Generated: 2025-07-05 | Total: 74 anomaly patterns across 9 categories*
