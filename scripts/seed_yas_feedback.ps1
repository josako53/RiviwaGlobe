# seed_yas_feedback.ps1 — Yas Tanzania comprehensive feedback seeding
# Run after inserting project into fb_projects via psql
# Usage: .\scripts\seed_yas_feedback.ps1

param(
    [string]$BaseUrl = "https://api.riviwa.com"
)

# ── Login ─────────────────────────────────────────────────────────────────────
$wr1 = Invoke-WebRequest -Uri "$BaseUrl/api/v1/auth/login" -Method POST `
    -Body '{"identifier":"admin@yas.co.tz","password":"YasTZ_Admin@2026!"}' `
    -ContentType "application/json" -UseBasicParsing
$lt  = ($wr1.Content | ConvertFrom-Json).login_token

$wr2 = Invoke-WebRequest -Uri "$BaseUrl/api/v1/auth/login/verify-otp" -Method POST `
    -Body "{`"login_token`":`"$lt`",`"otp_code`":`"000000`"}" `
    -ContentType "application/json" -UseBasicParsing
$T   = ($wr2.Content | ConvertFrom-Json).access_token
Write-Host "[AUTH] Token obtained (len=$($T.Length))"

# ── Constants ─────────────────────────────────────────────────────────────────
$PROJ  = "61d7cc39-1029-4cf2-b635-18289b85285e"

# Departments (branch auto-resolved from each)
$DID_CC  = "afd5b4e2-10f5-4874-b1da-248a74091805"  # Customer Care  → DSM
$DID_TS  = "17f96d55-6590-42e6-837f-48db490fcd96"  # Technical Supp → DSM
$DID_BP  = "17865dce-9c61-484c-a9dc-8d9696315904"  # Billing        → MWZ
$DID_SM  = "3dbd8c31-a7a7-4481-894e-c3a7a97c12a4"  # Sales & Mktg   → ARU
$DID_NO  = "6cc69174-a2f6-4bb5-ae1c-b0b521dff974"  # Network Ops    → DOD
$DID_YPA = "699a2c9c-2cd8-4bda-93de-88c9aed3a861"  # YasPesa Agency → MBY

# Services
$SVC_VOICE = "b309a69e-0f1f-4dcd-ad20-b3c5601344eb"  # Voice/4G
$SVC_YP    = "411da113-cb61-4819-9d11-af9ef08893c0"  # YasPesa
$SVC_FIBER = "e73c0dcc-d527-44fb-a87e-14b64946927b"  # Fiber
$SVC_BIZ   = "e9925395-cb04-4b14-96c2-144545cd9488"  # Business

function Submit-Feedback {
    param($body)
    $body | ConvertTo-Json -Compress | Out-File "$env:TEMP\fb_seed.json" -Encoding utf8 -NoNewline
    $r = curl.exe -s -w "\nSTATUS:%{http_code}" -X POST "$BaseUrl/api/v1/feedback" `
        -H "Authorization: Bearer $T" -H "Content-Type: application/json" `
        -d "@$env:TEMP\fb_seed.json" --insecure
    $lines  = $r -split "\n"
    $status = ($lines | Where-Object { $_ -match "^STATUS:" }) -replace "STATUS:",""
    $body   = ($lines | Where-Object { $_ -notmatch "^STATUS:" }) -join ""
    if ($status -eq "201") {
        $d = $body | ConvertFrom-Json
        Write-Host "  OK  [$status] $($d.tracking_number) — $($d.feedback_type)"
        return $d.feedback_id
    } else {
        Write-Host "  ERR [$status] $($body.Substring(0,[Math]::Min(120,$body.Length)))"
        return $null
    }
}

# ── 40 feedback submissions ────────────────────────────────────────────────────
Write-Host "`n[PHASE A] Grievances — Network & Connectivity (DSM/DOD)"

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="grievance"; category="connectivity"
    channel="mobile_app"; priority="high"
    subject="4G internet drops every night 7–10pm in Kinondoni"
    description="For the past 3 weeks my Yas 4G data bundle stops working between 7pm and 10pm every evening. I have tried restarting my phone and re-inserting SIM but nothing helps. This affects my ability to work from home."
    submitter_name="Fatuma Ally"; submitter_phone="+255712100001"
    department_id="$DID_TS"; service_id="$SVC_VOICE"
    issue_lga="Kinondoni"; issue_ward="Mwananyamala"
    submitted_at="2026-04-20T09:15:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="grievance"; category="connectivity"
    channel="web_portal"; priority="critical"
    subject="Network completely down in Tabata area for 48 hours"
    description="There has been zero signal for both voice and data in Tabata area since Saturday morning. Customers are furious and we are losing business. Please escalate immediately."
    submitter_name="Hassan Mwamba"; submitter_phone="+255712100002"
    department_id="$DID_NO"; service_id="$SVC_VOICE"
    issue_lga="Ilala"; issue_ward="Tabata"
    submitted_at="2026-04-25T14:30:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="grievance"; category="connectivity"
    channel="phone_call"; priority="high"
    subject="Fiber internet speed very slow since router installation"
    description="My Yas Fiber was installed 2 weeks ago but the speed is only 5 Mbps when I'm paying for 50 Mbps. I've called technical support twice but the problem persists. Please send a technician."
    submitter_name="Grace Mwangi"; submitter_phone="+255712100003"
    department_id="$DID_TS"; service_id="$SVC_FIBER"
    issue_lga="Kinondoni"; issue_ward="Sinza"
    submitted_at="2026-04-28T11:00:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="grievance"; category="connectivity"
    channel="in_person"; priority="medium"
    subject="No network coverage at Mwanza Industrial Area"
    description="Our entire factory in Mwanza industrial area has no Yas network coverage. Over 200 workers cannot make calls or use internet. Competitors have better coverage. Please install a tower near us."
    submitter_name="John Msimbe"; submitter_phone="+255754200001"
    department_id="$DID_NO"
    issue_lga="Nyamagana"; issue_ward="Ilemela"
    submitted_at="2026-05-01T08:45:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="grievance"; category="connectivity"
    channel="sms"; priority="high"
    subject="Call drops during important business meetings"
    description="I experience call drops every 5 minutes during voice calls on Yas network. This is unacceptable for business customers. I am paying for the Premium Business SIM package."
    submitter_name="Amina Bakari"; submitter_phone="+255712100005"
    department_id="$DID_TS"; service_id="$SVC_BIZ"
    issue_lga="Kinondoni"; issue_ward="Msasani"
    submitted_at="2026-05-03T13:20:00"
}

Write-Host "`n[PHASE B] Grievances — Billing & Payment (MWZ/DSM)"

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="grievance"; category="billing"
    channel="mobile_app"; priority="high"
    subject="Overcharged Tsh 45,000 — bundle expired before time"
    description="I bought a 30-day bundle for Tsh 45,000 on 1st May but it expired on 25th May — 5 days early. When I contacted customer care they said nothing can be done. I need a refund or extension."
    submitter_name="Zainab Hassan"; submitter_phone="+255712100006"
    department_id="$DID_BP"
    issue_lga="Kinondoni"; issue_ward="Mbezi"
    submitted_at="2026-05-05T10:30:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="grievance"; category="billing"
    channel="web_portal"; priority="high"
    subject="Charged twice for same fiber monthly subscription"
    description="My bank statement shows two deductions of Tsh 85,000 each (total Tsh 170,000) for my Yas Fiber monthly subscription in April. I only subscribed once. Please refund the duplicate charge immediately."
    submitter_name="Peter Kimaro"; submitter_phone="+255712100007"
    department_id="$DID_BP"; service_id="$SVC_FIBER"
    issue_lga="Kinondoni"; issue_ward="Regent Estate"
    submitted_at="2026-05-02T15:45:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="grievance"; category="billing"
    channel="email"; priority="medium"
    subject="Invoice shows wrong tariff rate for business account"
    description="Our corporate invoice for April 2026 shows tariff rate of Tsh 25/MB instead of the Tsh 15/MB agreed in our contract. The difference amounts to Tsh 180,000 overcharge. Attached is a copy of our agreement."
    submitter_name="Sophia Kimani"; submitter_phone="+255712100008"
    department_id="$DID_BP"; service_id="$SVC_BIZ"
    issue_lga="Ilala"; issue_ward="CBD"
    submitted_at="2026-05-04T09:00:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="grievance"; category="billing"
    channel="in_person"; priority="critical"
    subject="Tsh 500,000 deducted from YasPesa wallet without authorization"
    description="On the morning of 7th May 2026, Tsh 500,000 was deducted from my YasPesa mobile wallet without my authorization. I did not initiate any transaction. I need immediate reversal and investigation."
    submitter_name="Mohamed Juma"; submitter_phone="+255712100009"
    department_id="$DID_YPA"; service_id="$SVC_YP"
    issue_lga="Mbeya Urban"; issue_ward="Mbeya"
    submitted_at="2026-05-07T07:30:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="grievance"; category="billing"
    channel="sms"; priority="high"
    subject="YasPesa agent refused to give receipt for deposit"
    description="The YasPesa agent at Kariakoo market refused to give me a receipt after I deposited Tsh 200,000. The transaction shows as pending on my phone but the money is gone from my hand. Agent name: Abdallah."
    submitter_name="Rose Mtui"; submitter_phone="+255712100010"
    department_id="$DID_YPA"; service_id="$SVC_YP"
    issue_lga="Ilala"; issue_ward="Kariakoo"
    submitted_at="2026-05-06T14:00:00"
}

Write-Host "`n[PHASE C] Grievances — Agent Fraud (MBY/DSM)"

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="grievance"; category="agent-fraud"
    channel="phone_call"; priority="critical"
    subject="YasPesa agent collected cash but never processed deposit"
    description="I gave Tsh 150,000 cash to a YasPesa agent in Mbeya Tunduma road for deposit to my wallet. The agent processed something on his phone, I got no confirmation SMS, and the money never appeared. This is fraud. Agent phone: +255754999001"
    submitter_name="Kulwa Ngowi"; submitter_phone="+255712100011"
    department_id="$DID_YPA"; service_id="$SVC_YP"
    issue_lga="Mbeya Urban"; issue_ward="Mbalizi"
    submitted_at="2026-04-22T16:00:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="grievance"; category="agent-fraud"
    channel="web_portal"; priority="critical"
    subject="Fake Yas agent using counterfeit SIM card to defraud customers"
    description="There is a person in Mbeya Soweto area pretending to be a registered Yas agent selling counterfeit SIM cards. At least 10 people in our neighborhood have been defrauded. Please send investigation team immediately."
    submitter_name="Richard Nkosi"; submitter_phone="+255712100012"
    department_id="$DID_YPA"
    issue_lga="Mbeya Urban"; issue_ward="Soweto"
    submitted_at="2026-04-30T10:15:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="grievance"; category="agent-fraud"
    channel="in_person"; priority="critical"
    subject="Agent charging Tsh 2,000 commission for free transactions"
    description="The YasPesa agent at Geita bus terminal is charging Tsh 2,000 illegal commission for every withdrawal. He claims this is Yas fee but Yas agents are not supposed to charge beyond official rates. This is extortion."
    submitter_name="Diana Massawe"; submitter_phone="+255712100013"
    department_id="$DID_YPA"; service_id="$SVC_YP"
    issue_lga="Geita"; issue_ward="Geita Urban"
    submitted_at="2026-05-05T09:30:00"
}

Write-Host "`n[PHASE D] Grievances — Customer Service & Sales (ARU/DSM)"

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="grievance"; category="customer-service"
    channel="phone_call"; priority="medium"
    subject="Customer care hotline keeps disconnecting after 2 minutes"
    description="Every time I call Yas customer care (0800-YAS-HELP) the call disconnects after exactly 2 minutes without resolving my issue. This has happened 6 times today. Please fix your IVR system."
    submitter_name="Alice Mwakyusa"; submitter_phone="+255712100014"
    department_id="$DID_CC"
    issue_lga="Kinondoni"; issue_ward="Mikocheni"
    submitted_at="2026-05-04T11:30:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="grievance"; category="customer-service"
    channel="mobile_app"; priority="high"
    subject="Promised SIM card upgrade never delivered after 3 weeks"
    description="Sales agent at Arusha branch promised to deliver upgraded 5G SIM card within 3 days. It has been 3 weeks. I have called 5 times and each time get a different excuse. I want my upgrade or a refund of the Tsh 10,000 I paid."
    submitter_name="James Olele"; submitter_phone="+255712100015"
    department_id="$DID_SM"
    issue_lga="Arusha"; issue_ward="Sekei"
    submitted_at="2026-05-01T14:00:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="grievance"; category="customer-service"
    channel="email"; priority="medium"
    subject="Waited 3 hours at Arusha branch with no service"
    description="I visited Yas Tanzania Arusha branch at 9am and was given queue number 45. I left at 12pm after still not being served. There were only 2 staff members for a queue of 60+ customers. This is unacceptable service."
    submitter_name="Mary Kessy"; submitter_phone="+255712100016"
    department_id="$DID_SM"
    issue_lga="Arusha"; issue_ward="Arusha City"
    submitted_at="2026-04-28T12:30:00"
}

Write-Host "`n[PHASE E] Suggestions — Service Improvement"

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="suggestion"; category="service-improvement"
    channel="mobile_app"; priority="medium"
    subject="Introduce data rollover for unused monthly bundles"
    description="I suggest Yas Tanzania introduces data rollover where unused data from the current month rolls over to the next month. Other operators in East Africa offer this. It would increase customer loyalty significantly."
    submitter_name="Bernard Lema"; submitter_phone="+255712100017"
    department_id="$DID_CC"; service_id="$SVC_VOICE"
    issue_lga="Kinondoni"
    submitted_at="2026-04-26T10:00:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="suggestion"; category="network-expansion"
    channel="web_portal"; priority="low"
    subject="Install Yas tower at Songea University to serve 5,000 students"
    description="Songea University of Science and Technology has over 5,000 students with very poor Yas network coverage. Installing a tower here would give Yas a huge customer base. I am willing to connect Yas with university management."
    submitter_name="Prof. Godfrey Mwita"; submitter_phone="+255712100018"
    department_id="$DID_NO"
    issue_lga="Songea"; issue_ward="Songea Urban"
    submitted_at="2026-05-02T08:00:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="suggestion"; category="product-improvement"
    channel="in_person"; priority="medium"
    subject="Add M-Pesa compatibility to YasPesa wallet for transfers"
    description="Many customers need to transfer money between YasPesa and M-Pesa. Currently this requires going through a bank which takes days. Adding interoperability would make YasPesa much more useful and competitive."
    submitter_name="Samuel Mgimba"; submitter_phone="+255712100019"
    department_id="$DID_YPA"; service_id="$SVC_YP"
    issue_lga="Dar es Salaam"; issue_ward="CBD"
    submitted_at="2026-05-03T15:00:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="suggestion"; category="pricing"
    channel="email"; priority="low"
    subject="Create student bundle packages at discounted rates"
    description="Students cannot afford regular Yas bundles on their allowances. A dedicated student package with verified university email at 40% discount would win market share from competitors who already do this."
    submitter_name="Esther Mollel"; submitter_phone="+255712100020"
    department_id="$DID_SM"
    issue_lga="Arusha"; issue_ward="Arusha City"
    submitted_at="2026-04-24T16:30:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="suggestion"; category="customer-service"
    channel="mobile_app"; priority="medium"
    subject="Enable live chat support in the Yas app"
    description="The Yas mobile app should have live chat support so customers can get help without calling. This would reduce call center load and give faster resolution. Many operators globally have this feature."
    submitter_name="Lilian Mwanzilima"; submitter_phone="+255712100021"
    department_id="$DID_CC"
    issue_lga="Kinondoni"; issue_ward="Msasani"
    submitted_at="2026-05-05T09:00:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="suggestion"; category="network-expansion"
    channel="web_portal"; priority="medium"
    subject="Extend fiber coverage to Dodoma suburbs — huge unserved market"
    description="Dodoma suburbs like Nzuguni, Mtumba, and Chamwino have zero fiber coverage. With Dodoma being the capital, many government officials work from home there. Covering these areas would capture premium customers."
    submitter_name="Dr. Agnes Kapinga"; submitter_phone="+255712100022"
    department_id="$DID_NO"; service_id="$SVC_FIBER"
    issue_lga="Dodoma"; issue_ward="Nzuguni"
    submitted_at="2026-04-29T14:00:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="suggestion"; category="process-improvement"
    channel="phone_call"; priority="low"
    subject="Automated SMS alert when bundle is at 20% remaining"
    description="Please send automatic SMS alerts when customers have used 80% of their data bundle. Right now customers run out of data unexpectedly. A warning at 20% remaining would improve customer experience greatly."
    submitter_name="Charles Kimola"; submitter_phone="+255712100023"
    department_id="$DID_CC"; service_id="$SVC_VOICE"
    issue_lga="Kinondoni"
    submitted_at="2026-05-06T11:00:00"
}

Write-Host "`n[PHASE F] Applause — Positive Recognition"

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="applause"; category="excellent-service"
    channel="mobile_app"; priority="low"
    subject="Technician Baraka fixed fiber in 30 minutes — outstanding service"
    description="Technician Baraka Mwakisu came to fix my fiber issue within 2 hours of my call and resolved it in 30 minutes. He was professional, explained everything clearly, and even cleaned up after himself. This is the service I expected from Yas!"
    submitter_name="Jane Msangi"; submitter_phone="+255712100024"
    department_id="$DID_TS"; service_id="$SVC_FIBER"
    issue_lga="Kinondoni"; issue_ward="Sinza"
    submitted_at="2026-04-21T17:30:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="applause"; category="excellent-service"
    channel="web_portal"; priority="low"
    subject="Customer care agent Zuhura resolved billing dispute instantly"
    description="Agent Zuhura Rashidi at Dar es Salaam branch resolved my 3-month billing dispute in one visit. She was patient, professional, and followed up with an email confirmation. Yas should have more staff like her."
    submitter_name="Ibrahim Salum"; submitter_phone="+255712100025"
    department_id="$DID_BP"
    issue_lga="Ilala"; issue_ward="CBD"
    submitted_at="2026-04-27T13:00:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="applause"; category="excellent-service"
    channel="in_person"; priority="low"
    subject="YasPesa agent Emmanuel went above and beyond to help elderly customer"
    description="YasPesa agent Emmanuel Ngowi in Mbeya spent 45 minutes helping an elderly woman (75+) who could not operate her phone for a transaction. He did this without charging any extra fee. This is what community service looks like."
    submitter_name="Neema Mwakalinga"; submitter_phone="+255712100026"
    department_id="$DID_YPA"; service_id="$SVC_YP"
    issue_lga="Mbeya Urban"; issue_ward="Forest"
    submitted_at="2026-05-02T14:00:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="applause"; category="fast-resolution"
    channel="phone_call"; priority="low"
    subject="Technical team restored network in Dodoma within 4 hours"
    description="When the network went down in our Dodoma area, the Yas technical team responded and restored it in just 4 hours, even on a Sunday. The duty officer kept us updated via SMS throughout. Commendable response time."
    submitter_name="Frank Simba"; submitter_phone="+255712100027"
    department_id="$DID_NO"
    issue_lga="Dodoma"; issue_ward="Dodoma Urban"
    submitted_at="2026-05-04T18:00:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="applause"; category="excellent-service"
    channel="email"; priority="low"
    subject="Sales team at Arusha delivered and configured 20 business SIMs perfectly"
    description="The Arusha sales team coordinated delivery of 20 business SIM cards for our company with APN configuration included. Everything was set up correctly the first time and the team even trained our IT staff. Excellent work."
    submitter_name="Patricia Mwaura"; submitter_phone="+255712100028"
    department_id="$DID_SM"; service_id="$SVC_BIZ"
    issue_lga="Arusha"; issue_ward="Kaloleni"
    submitted_at="2026-04-23T10:00:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="applause"; category="innovation"
    channel="mobile_app"; priority="low"
    subject="New Yas app update is much faster and more intuitive"
    description="The recent Yas app update (v3.2) is a huge improvement. Bundle purchase now takes 3 taps instead of 8, the interface is cleaner, and it no longer crashes on my Android 12. Thank the development team for listening to feedback."
    submitter_name="Kenneth Mhagama"; submitter_phone="+255712100029"
    department_id="$DID_CC"; service_id="$SVC_VOICE"
    issue_lga="Kinondoni"
    submitted_at="2026-05-01T19:00:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="applause"; category="excellent-service"
    channel="web_portal"; priority="low"
    subject="YasPesa loan feature helped my small business through cash flow crisis"
    description="The YasPesa instant loan feature saved my business when I needed Tsh 500,000 urgently. Approved in 10 minutes, no paperwork, reasonable interest. Repaid within the month. Yas has changed how small businesses access credit."
    submitter_name="Violet Mhango"; submitter_phone="+255712100030"
    department_id="$DID_YPA"; service_id="$SVC_YP"
    issue_lga="Mbeya Urban"
    submitted_at="2026-04-25T20:00:00"
}

Write-Host "`n[PHASE G] Inquiries"

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="inquiry"; category="service-information"
    channel="sms"; priority="low"
    subject="What are the Yas Fiber installation costs and timeline?"
    description="I want to know the full cost of Yas Fiber installation at my home in Mbezi Beach. What is the connection fee? How long does installation take? What is the monthly subscription for 30 Mbps unlimited?"
    submitter_name="Anthony Lwehabura"; submitter_phone="+255712100031"
    department_id="$DID_CC"; service_id="$SVC_FIBER"
    issue_lga="Kinondoni"; issue_ward="Mbezi Beach"
    submitted_at="2026-05-03T08:00:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="inquiry"; category="pricing"
    channel="mobile_app"; priority="low"
    subject="Can I keep my current number when switching to Yas from competitor?"
    description="I want to switch from my current operator to Yas Tanzania. Can I keep my mobile number through MNP (Mobile Number Portability)? How long does the process take? Are there any charges involved?"
    submitter_name="Theresia Mwamba"; submitter_phone="+255712100032"
    department_id="$DID_SM"
    issue_lga="Arusha"; issue_ward="Arusha City"
    submitted_at="2026-04-29T11:00:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="inquiry"; category="account"
    channel="phone_call"; priority="low"
    subject="How do I register my business for a corporate Yas account?"
    description="I run an SME with 15 employees and want to set up a corporate account with Yas for business SIM cards and internet. What documents are needed? Is there a dedicated account manager? What discounts are available for businesses?"
    submitter_name="Geoffrey Chagula"; submitter_phone="+255712100033"
    department_id="$DID_SM"; service_id="$SVC_BIZ"
    issue_lga="Kinondoni"; issue_ward="Masaki"
    submitted_at="2026-05-05T14:30:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="inquiry"; category="technical"
    channel="web_portal"; priority="low"
    subject="What YasPesa features are available for merchants?"
    description="I own a retail shop and want to accept YasPesa payments. What merchant features does YasPesa offer? What are the transaction fees? How do I get a merchant QR code? Can I check my daily transactions online?"
    submitter_name="Catherine Macha"; submitter_phone="+255712100034"
    department_id="$DID_YPA"; service_id="$SVC_YP"
    issue_lga="Mbeya Urban"; issue_ward="Mbeya CBD"
    submitted_at="2026-04-22T09:00:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="inquiry"; category="service-information"
    channel="email"; priority="low"
    subject="Network coverage map for Dodoma region — business decision needed"
    description="We are deciding between Yas and another operator for our new Dodoma office. Can you share an up-to-date coverage map showing 4G signal strength across Dodoma and surrounding towns? We need this for board decision by end of month."
    submitter_name="William Mweze"; submitter_phone="+255712100035"
    department_id="$DID_NO"
    issue_lga="Dodoma"; issue_ward="Dodoma Urban"
    submitted_at="2026-05-06T08:00:00"
}

Write-Host "`n[PHASE H] High-priority escalated grievances (recent)"

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="grievance"; category="connectivity"
    channel="web_portal"; priority="critical"
    subject="Hospital emergency communications affected by Yas outage"
    description="Yas Tanzania network outage at Bugando Medical Centre in Mwanza is affecting emergency communications. Doctors cannot reach each other or ambulances. This is a medical emergency situation. PLEASE FIX IMMEDIATELY."
    submitter_name="Dr. Sarah Mutashobya"; submitter_phone="+255712100036"
    department_id="$DID_NO"
    issue_lga="Nyamagana"; issue_ward="Isamilo"
    submitted_at="2026-05-08T06:00:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="grievance"; category="billing"
    channel="mobile_app"; priority="high"
    subject="Wrong deductions of Tsh 12,000 three months in a row"
    description="Every month for the last 3 months, Tsh 12,000 is being deducted from my account without my authorization. No subscription I have costs this amount. Customer care says they cannot find the deduction. This is theft. Total loss: Tsh 36,000."
    submitter_name="Josephine Rweyemamu"; submitter_phone="+255712100037"
    department_id="$DID_BP"
    issue_lga="Kinondoni"; issue_ward="Kinondoni"
    submitted_at="2026-05-07T09:00:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="grievance"; category="customer-service"
    channel="in_person"; priority="high"
    subject="Staff member was rude and discriminatory at Mwanza branch"
    description="I visited the Mwanza branch on 6 May 2026. A staff member named Thomas was extremely rude and made discriminatory remarks about my tribal background when I struggled with the Swahili form. This is unacceptable behavior from a customer-facing employee."
    submitter_name="Emmanuel Kagera"; submitter_phone="+255712100038"
    department_id="$DID_CC"
    issue_lga="Nyamagana"; issue_ward="Nyamagana"
    submitted_at="2026-05-06T17:30:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="grievance"; category="connectivity"
    channel="sms"; priority="high"
    subject="Fiber internet down for 10 days — work from home impossible"
    description="My Yas fiber internet has been down for 10 consecutive days (since 28 April). I have logged 4 support tickets, sent 2 emails, and visited the branch once. No technician has been sent. I work entirely online and have lost significant income."
    submitter_name="Sandra Msemwa"; submitter_phone="+255712100039"
    department_id="$DID_TS"; service_id="$SVC_FIBER"
    issue_lga="Ilala"; issue_ward="Upanga"
    submitted_at="2026-05-08T11:00:00"
}

Submit-Feedback @{
    project_id="$PROJ"; feedback_type="grievance"; category="agent-fraud"
    channel="phone_call"; priority="critical"
    subject="Agent stole Tsh 800,000 from elderly widow — confirmed crime"
    description="An elderly widow in Mbeya (Mrs. Mbano, age 72) was tricked by a Yas agent who told her to provide her PIN to 'verify her account'. The agent then withdrew Tsh 800,000 from her YasPesa account. She is filing a police report. Yas must cooperate with police and compensate her."
    submitter_name="Pastor James Nkosi"; submitter_phone="+255712100040"
    department_id="$DID_YPA"; service_id="$SVC_YP"
    issue_lga="Mbeya Urban"; issue_ward="Mbeya"
    submitted_at="2026-05-09T08:00:00"
}

Write-Host "`n[DONE] Feedback seeding complete."
