# GAIDA User Manual

**Guidance System with Multimodal Anxiety Detection**  
University of the East — Guidance and Counseling Office

| Document information | |
|---|---|
| Manual version | 1.0 |
| Last updated | 7 November 2026 |
| Intended readers | Students, counselors, research participants, and system administrators |
| System | GAIDA web app and counselor dashboard |

> **Safety first.** GAIDA is a support tool, not a doctor, diagnosis, or emergency service. If you or someone else is in immediate danger, call **911**. For mental-health crisis support, call the **NCMH Crisis Hotline at 1553** (24/7, toll-free).

---

## Contents

1. [About this manual](#1-about-this-manual)
2. [What GAIDA does](#2-what-gaida-does)
3. [Quick start](#3-quick-start)
4. [Portals and sign-in](#4-portals-and-sign-in)
5. [Student guide](#5-student-guide)
6. [Counselor guide](#6-counselor-guide)
7. [Research participant guide](#7-research-participant-guide)
8. [Accounts and access](#8-accounts-and-access)
9. [Troubleshooting and FAQ](#9-troubleshooting-and-faq)
10. [Privacy, safety, and limitations](#10-privacy-safety-and-limitations)
11. [Accessibility and supported devices](#11-accessibility-and-supported-devices)
12. [Glossary](#12-glossary)
- [Appendix A — Administrator and developer notes](#appendix-a--administrator-and-developer-notes)
- [Appendix B — Pilot test accounts](#appendix-b--pilot-test-accounts)

---

## 1. About this manual

This manual explains how to use GAIDA from three points of view:

- **Students** — signing in, giving consent, chatting with GAIDA, using voice input, requesting a counselor, and ending a session.
- **Counselors** — monitoring alerts and sessions, joining a conversation, writing case notes, resolving cases, running welfare checks, and reading reports.
- **Research participants** — joining the optional study, answering the GAD-7 and SUS questionnaires, saving an anonymous participant token, and withdrawing data.

**Conventions used in this manual**

- **Bold text** means a button, tab, menu item, or field label you will see on screen.
- `Monospace text` means a value or identifier, such as a student number or participant token.
- Notes marked **Important** or **Safety** should be read before continuing.

---

## 2. What GAIDA does

GAIDA is a virtual guidance assistant for University of the East students. It combines:

| Capability | What it means for you |
|---|---|
| AI chat | GAIDA replies in English, Tagalog, or Taglish and follows the language the student uses. |
| Text anxiety detection | Each message is classified into a level such as Normal, Low, Moderate, High, or Crisis using rules and a machine-learning ensemble. |
| Voice analysis | When voice input is used, speech features such as pitch, energy, pauses, and speech rate are analyzed. |
| Human escalation | High and Crisis situations can notify a counselor and pause GAIDA until a counselor joins. |
| Counselor workspace | Counselors review alerts, open flagged sessions, take over a conversation, record case notes, and export PDFs. |
| Reports | The dashboard summarizes alerts, sessions, anxiety trends, and severity breakdowns. |
| Research | An optional research flow collects consent, demographics, GAD-7 answers, and a post-session usability survey. |
| Offline support | The app can open offline, and messages written offline are queued and sent when the connection returns. |

**GAIDA is not a diagnosis.** The anxiety level is a support signal that helps a counselor decide when to check in. It can be wrong, incomplete, or based on a single message.

---

## 3. Quick start

### 3.1 Where to open GAIDA

| Environment | Frontend | Backend |
|---|---|---|
| Live deployment | `https://gaida-system.vercel.app` | `https://gaida-system--rainierburlasa4.replit.app` |
| Local development | `http://localhost:5173` | `http://127.0.0.1:8000` |

Use a current version of **Chrome, Edge, Safari, or Firefox**. Voice input and text-to-speech work best in Chrome or Edge, but availability depends on the browser and microphone permissions.

GAIDA can be installed as a **Progressive Web App (PWA)**. If the browser shows an install prompt, follow it. The installed app can open without a connection, but GAIDA's replies and new data still require the server.

### 3.2 Choose your entry point

| You are… | Open | You will need |
|---|---|---|
| A student | **Student Portal** | Student number, UE email, password, and verification code |
| A counselor | **Counselor Dashboard** | Faculty ID and password, or an authorized UE Google account, plus a verification code |
| A research participant | **Research Participation** | No account; consent and a verification code are required |
| An administrator | The backend/server tools | Server environment and database access |

### 3.3 The three portals

The opening screen offers:

1. **Student Portal** — chat with GAIDA, use voice input, and request a counselor.
2. **Counselor Dashboard** — monitor alerts, sessions, welfare checks, reports, and resolved cases.
3. **Research Participation** — join the optional thesis study with a student number or anonymously.

A **Withdraw from the research study** link also appears at the bottom of the portal screen.

---

## 4. Portals and sign-in

### 4.1 Verification code (CAPTCHA)

Student, counselor, research, and withdrawal forms use a server-generated verification image.

1. Read the **6-character code** in the image. Characters are not case-sensitive.
2. Type it into **Verification Code**.
3. If the code is unreadable or expired, press **Refresh** and type the new code.

**Important:**

- Each code works **once**. A wrong guess uses up the code, so refresh after an error.
- A code expires after about **3 minutes**.
- If you reload the page or wait too long, request a new code before submitting.

### 4.2 Student sign-in

1. Select **Student Portal**.
2. Enter your **Student Number**.
3. Enter your **UE Email Address** (it must end in `@ue.edu.ph`).
4. Enter your **Password**. Use the eye icon to show or hide it.
5. Enter the **Verification Code**.
6. Select **Log In**.

If **Sign in with Google** is shown, you may use an authorized `@ue.edu.ph` Google account instead of typing a password. Google sign-in only works when the deployment has Google authentication configured.

### 4.3 Counselor sign-in

1. Select **Counselor Dashboard**.
2. Enter your **Faculty ID**.
3. Enter your **Password**.
4. Enter the **Verification Code**.
5. Select **Log In**.

Counselors may also use **Sign in with Google** when the deployment has it configured and their UE email is on the authorized counselor list.

**About demo counselor accounts:** the built-in counselor IDs such as `COUNSELOR01` only work on a development server or when the deployment explicitly enables demo counselors. On a normal production server, counselor ID/password accounts must be configured by the administrator. See [Appendix A](#appendix-a--administrator-and-developer-notes).

### 4.4 Forgot password

The **Forgot Password?** screen asks for a UE email and shows a confirmation message.

**Important:** at this stage the reset request is intentionally show-only — it always reports that a reset link was sent so that outsiders cannot discover which emails are registered, but **no reset email is currently delivered**. Contact the Guidance Office or system administrator to have a password reset.

### 4.5 Signing out

- **Students:** ending a session clears the session token, student ID, consent flag, cached chat data, and the offline queue from the device, then returns to the login screen.
- **Counselors:** use **Logout** in the sidebar (or the profile drawer on mobile) and confirm **Log out**.
- Always sign out on shared or laboratory computers.

---

## 5. Student guide

### 5.1 Sign in and give consent

After signing in, the **Informed Consent** page appears before the chat. Read the sections:

- Purpose
- Data Collection
- AI Processing
- Privacy
- Limitations
- Session Recording
- Counselor Alerts
- Rights
- Data Retention
- Questions or Concerns

To continue:

1. Tick the consent checkbox: *“I have read and understood the terms above…”*
2. Select **I Accept - Start Session**.
3. To stop instead, select **Decline & Logout**.

You cannot start a chat without accepting consent.

### 5.2 Student dashboard tour

| Area | What it shows |
|---|---|
| **Session** | Duration and number of messages |
| **How you're doing** | The currently detected anxiety level and a colored level bar |
| **Mode** | **Talk** (normal support) or **Vent** (GAIDA mainly listens) |
| **Talk to a counselor** | Requests a human counselor |
| **Settings** | Color themes (**Sky**, **Sage**, **Lavender**, **Sand**) and quick tips |
| **Emergency Hotlines** | Opens the crisis and campus support numbers |
| **End session** | Ends the chat and shows the session summary |
| Top bar | Menu button on mobile, **Hotlines**, current level, and status (Online, Vent mode, or Counselor active) |
| Chat area | Suggested openers, messages, feedback buttons, and the message box |
| Message box | Type, use the microphone, or press Send |

On a phone, the sidebar becomes a drawer. Use the menu button in the top bar to open it.

### 5.3 Start a conversation

1. Type in **Type your message...**.
2. Press **Enter** to send, or **Shift + Enter** for a new line.
3. Select **Send** (the arrow button) if you prefer.
4. You can also choose a suggested opener:
   - *“I'm stressed about my exams”*
   - *“I just want to talk to someone”*
   - *“Things have been hard lately”*

GAIDA replies in the language you use. You may write in English, Tagalog, or Taglish.

### 5.4 Use voice input

1. Select the **microphone** button next to the message box.
2. Allow microphone access if the browser asks.
3. Speak. The browser creates a transcript.
4. Review the transcript and confirm to send it, or cancel to discard it.

Voice availability depends on the browser, microphone permission, and connection quality. If voice input is unavailable, typing still works.

### 5.5 Listen to a reply

GAIDA replies have a **Listen** button (speaker icon). Select it to have the reply read aloud, and select it again to stop. This uses the browser's text-to-speech support; it may not be available in every browser.

### 5.6 Give feedback on a reply

Under each GAIDA reply you can choose:

- **Helpful**
- **Not helpful**

After choosing one, you may add an optional short comment. Feedback helps improve the system; it is linked to the session.

### 5.7 Talk mode and Vent mode

| Mode | What GAIDA does |
|---|---|
| **Talk** | Normal conversation. GAIDA may reflect feelings, offer coping steps, and ask questions. |
| **Vent** | GAIDA mainly listens. It avoids advice and redirects while you share freely. |

**Important:** Vent mode does not disable safety. If a High or Crisis signal appears, GAIDA can still share hotlines, pause replies, and notify a counselor.

### 5.8 How detection works

GAIDA assigns a level to messages using text and, when used, voice features. The counselor dashboard shows these approximate thresholds:

| Level | Approximate confidence | What typically happens |
|---|---|---|
| **Normal** | Below 0.45 | GAIDA responds freely |
| **Low** | 0.46 – 0.70 | A counselor-written support protocol is added to the reply |
| **Moderate** | 0.71 – 0.75 | A stronger support protocol is added |
| **High** | 0.76 – 0.98 | A counselor alert is fired and GAIDA may pause |
| **Crisis** | 0.99 – 1.00 | Immediate intervention flow, alert, and hotline guidance |

These levels are **support signals, not a diagnosis**. A “Normal” result does not prove that someone is safe, and a high result does not by itself confirm a condition.

### 5.9 If GAIDA pauses (High/Crisis hold)

When a High or Crisis signal is detected:

- A counselor is notified.
- GAIDA may pause its replies until the counselor reviews the session.
- A banner explains that a counselor has been notified and will message you in the chat.
- You can keep typing; the counselor will see what you send.
- The banner shows **1553** and **911** for immediate help.

Do not wait for the chat if you are in immediate danger. Call **911** or **1553**.

### 5.10 Request a counselor

1. Select **Talk to a counselor** in the sidebar.
2. Wait for **Counselor notified**. A counselor may join shortly.
3. When a counselor joins, the chat shows **A counselor has joined your session** and the status changes to **Counselor active**.
4. Continue in the same chat so the counselor can follow the conversation.

If the request fails, GAIDA shows a message and you can try again or send a message first.

### 5.11 End a session

1. Select **End session**.
2. If you have exchanged messages, GAIDA shows a **Session Summary**:
   - Messages exchanged
   - Your messages
   - Voice messages (if any)
   - Highest anxiety level detected
   - Notes when the session reached High/Crisis, a counselor joined, or Vent mode was used
3. Select **Continue**.
4. Answer **“How are you feeling right now compared to when we started?”**:
   - Much worse
   - About the same
   - A little better
   - Much better
   - Or select **Skip**
5. The session ends and you return to the student login screen.

If the session had no messages, **End session** ends it immediately without the summary. Research sessions go to the **One Last Thing** usability survey instead of the student login.

### 5.12 Offline use

GAIDA can open without a connection because the app shell is cached.

- A message written offline is saved on the device and shown as **Waiting to send**.
- When the connection returns, queued messages are sent automatically in order.
- GAIDA's reply still needs the server, so replies resume only after reconnecting.
- Previous chat transcripts are **not** available offline.
- The offline queue is cleared when you log out or end the session.

Keep the app open until queued messages are delivered. If you log out first, the queue is discarded.

### 5.13 Emergency and support contacts

The **Emergency Hotlines** button opens the current list:

| Contact | Number | Notes |
|---|---|---|
| **NCMH Crisis Hotline** | **1553** | Toll-free nationwide, 24/7 mental-health crisis support |
| **HOPELINE Philippines** | (02) 8804-4673 / 0917-558-4673 | 24/7 suicide prevention; toll-free for Globe/TM |
| **In Touch Community Services** | (02) 8893-7603 / 0917-800-1123 | Free, confidential crisis counseling |
| **Philippine National Emergency Hotline** | **911** | Immediate life-threatening emergencies |
| **UE Guidance and Counseling Office (Manila)** | (02) 8735-5471 loc. 390 | Mon–Fri, 8:00 AM – 5:00 PM |
| **UE Guidance and Counseling Office (Caloocan)** | (02) 8367-4572 loc. 175 | Mon–Fri, 8:00 AM – 5:00 PM |

### 5.14 Privacy and data

- Chat messages may be processed by third-party AI services to generate replies and detect anxiety.
- Voice recordings are processed for speech features and are not intended to be retained after processing.
- Session data is stored in the project's Supabase database.
- Counselors can access sessions that are flagged or relevant to a case.
- Do not share passwords, bank details, or unnecessary identifying information in chat.

---

## 6. Counselor guide

### 6.1 Sign in

1. Select **Counselor Dashboard**.
2. Enter your **Faculty ID** and **Password**.
3. Enter the **Verification Code**.
4. Select **Log In**.

After sign-in, the sidebar shows your name, **Guidance Counselor**, your workspace ID, and a connection dot.

### 6.2 Workspace layout

The desktop sidebar is grouped as follows:

| Group | Items |
|---|---|
| **Monitor** | Overview, Alerts, Active Sessions, Anxiety Detection |
| **Follow-up** | Welfare Checks, Resolved Cases, Reports |
| **Settings** | Privacy and Consent, Test Alert Chime |
| Pinned utilities | Crisis hotlines, Collapse/Expand, Logout |

The **Alerts** item shows a badge with the number of pending alerts.

**Desktop controls**

- Select your avatar or **Collapse** to shrink the sidebar to an icon rail.
- Hover or focus an icon in the collapsed rail to see its name.
- The sidebar remembers whether it was expanded or collapsed.
- **Dark mode** is in the top bar.
- The top bar also shows the connection badge and the last update time.

**Mobile controls**

- The bottom navigation has **Overview**, **Alerts**, **Sessions**, and **More**.
- **More** opens Welfare Checks, Anxiety Detection, Reports, and Resolved Cases.
- Select the avatar to open the profile and navigation drawer.
- A floating **Crisis hotlines** button is available on mobile.

**Connection badge**

| Badge | Meaning |
|---|---|
| **Live** | Real-time connection is active |
| **Reconnecting** | The real-time stream dropped; the dashboard is polling as a fallback |
| **Offline** | No connection; data may be stale |

### 6.3 Overview page

The Overview page shows:

- A banner when alerts need review, with **Review alert**.
- A **Crisis** card when a pending Crisis alert exists. It can **Show identity** / **Hide identity**, **Acknowledge**, **View session**, or open **Alerts**.
- Four clickable KPI cards:

| KPI | Meaning |
|---|---|
| **Active Sessions** | Sessions currently in progress |
| **Pending Alerts** | Alerts not yet resolved (New + Acknowledged) |
| **At-Risk Sessions** | Sessions at Moderate severity or above |
| **Total Alerts** | All alerts recorded |

Each KPI includes a week-over-week comparison when available; otherwise it says **Last week comparison unavailable**.

Charts and panels:

- **Anxiety Level Trends** — monthly trend lines.
- **Sessions This Week** — sessions per day.
- **Anxiety Distribution** — current distribution by level.

Each panel has skeleton, empty, and error states with **Try again**. Analytics requests time out after about **10 seconds**.

At the bottom of every dashboard page:

> *“A zero count does not confirm safety. Follow your campus emergency procedure.”*

### 6.4 Alerts page

The Alerts page lists **Moderate**, **High**, **Crisis**, and **Requested** alerts, highest risk first.

**Statuses**

| Status | Meaning | Available actions |
|---|---|---|
| **New** | Not yet acknowledged | **Acknowledge**, **View session**, **Show identity** |
| **Acknowledged** | A counselor has seen it | **Mark Reviewed**, **View session**, **Show identity** |
| **Resolved** | Reviewed or resolved | View only |

**Find an alert**

- Type in **Search alerts...** to search by student ID, name, initial message, or trigger reason.
- Use **Filter** or the severity dropdown to show **All Severities**, **Crisis only**, **High only**, **Moderate only**, or **Requested only**.
- The color legend shows Crisis (red), High (red-orange), and Moderate (amber).

**Escalation badges**

| Badge | Meaning |
|---|---|
| **Waiting …m+** | The alert is approaching its response deadline |
| **Unattended …m** | The alert is urgent and still unacknowledged |
| **Overdue …m** | The deadline has passed; a supervisor/backup has been notified by email |
| **Needs supervisor** | The alert passed the overdue deadline |
| **Off-hours** | The session happened outside office hours |

**Mobile gestures**

- Swipe **right** on a New alert to acknowledge it.
- Swipe **left** to view the session.
- A one-time hint explains the gestures; dismissing it saves the choice.

If a Crisis session is live, a red **Crisis session live** banner appears at the top; select it to open the session immediately.

### 6.5 Active Sessions

The Active Sessions page lists ongoing conversations with:

- Severity color and level
- Alert status (if any)
- Assigned counselor (if any)
- Message count, duration, and intent
- Detection confidence

Chat content is shown only for flagged sessions. For **High**, **Crisis**, or alerted sessions, select **View Chat**.

The list refreshes automatically. You can also pull down to refresh on mobile.

### 6.6 Session detail window

Open a session from an alert, the crisis card, Active Sessions, or Welfare Checks. The window has three tabs:

| Tab | Contents |
|---|---|
| **Chat Transcript** | Full conversation, detection details, typing indicator, quick responses, and the message box |
| **Anxiety Progression** | Confidence per student message, threshold lines, and current status |
| **Case Notes** | Outcome, notes, independent assessment, and **Save note** |

**Take over a conversation**

1. Review the transcript first.
2. Select a **quick response** or type in **Type a message to the student...**.
3. Select **Send**.
4. Sending a counselor message joins you to the session; GAIDA pauses while you are active.
5. Use **← Return to GAIDA** when it is appropriate to hand the conversation back.

Quick responses include:

- **I'm here**
- **Take a breath**
- **Help coming**
- **Call hotline**
- **Safe?**
- **Follow up**

You can edit them or write your own message. Personalize the wording to the student's situation.

**Write a case note**

1. Open the **Case Notes** tab.
2. Choose an **Outcome**:
   - **Resolved** — handled, no further action
   - **False alarm** — flagged but not concerning
   - **Referred** — escalated to the in-person guidance office
   - **Follow-up scheduled** — counselor will check in again
   - **Ongoing** — still being monitored
3. Write factual notes: what happened, what was said, and what you did.
4. Optionally record your **Independent assessment**, kept separate from GAIDA's automated classification.
5. Select **Save note**. The button changes to **Update note** if a note already exists.

**Resolve a session**

1. Save a case note first. **Resolve session** stays disabled until a note exists.
2. Select **Resolve session**.
3. Confirm **Resolve session** in the dialog.

The session leaves active alerts and appears in **Resolved Cases**.

**Export a session**

Select **Export** in the session header, or **Export PDF** in Resolved Cases. The file downloads as a PDF. Store exported files according to office privacy and retention rules.

### 6.7 Welfare Checks

Welfare Checks lists **High** or **Crisis** sessions that went silent without follow-up.

Each card shows:

- Peak severity
- How many minutes the student has been silent
- Session code
- Last message

Actions:

- **View Chat** — open the session transcript.
- **Mark Checked** — record that a human follow-up was made.

Use the approved office procedure to contact the student. **Mark Checked** is not a substitute for the actual check-in.

### 6.8 Anxiety Detection

This page explains the detection setup:

- **Voice Analysis** — pitch, energy, jitter, speech rate, and pauses
- **Text Analysis** — logistic regression, random forest, and neural-network ensemble
- **Anxiety Level Thresholds** — Normal, Low, Moderate, High, and Crisis, with the approximate confidence ranges and what each level triggers

### 6.9 Reports & Analytics

Open **Reports** in the Follow-up group.

- Breadcrumb: **Guidance system / Reports**
- **Reporting period**: Last 7 days, Last 30 days, This term, or Custom range. The selection stays in place while you retry. The panels below show the monthly report returned by the server.
- **Refresh reports** reloads the data.
- The connection badge and last-updated time are shown in the header.

Panels:

1. **Monthly Trends** — sessions and alerts per month.
2. **Severity Breakdown by Month** — sessions, alerts, and counts for Normal, Low, Moderate, High, and Crisis.

**If reports fail:**

- A banner reads: *“Reports could not load. Monthly Trends and Severity Breakdown are unavailable.”*
- **Retry** is disabled while a retry is running.
- Each chart also shows **Couldn't load Monthly Trends** or **Couldn't load Severity Breakdown** with **Try again**.
- Requests time out after about **10 seconds**.
- **No data available** appears only when the request succeeded but there is no data.

### 6.10 Resolved Cases

Resolved Cases shows closed sessions with case notes and transcripts.

- **Search cases or notes...** searches student ID, name, program, and note text.
- The outcome filter supports All Outcomes, Resolved, Referred, Follow-up, False alarm, and Ongoing.
- Select a case to expand it and see the case note and transcript.
- **Export PDF** downloads the session report.
- **Delete** removes the case from the resolved list after confirmation.

### 6.11 Utilities

| Utility | What it does |
|---|---|
| **Privacy and Consent** | Opens the privacy and informed-consent information |
| **Test Alert Chime** | Plays the alert sound and flashes the control so you can confirm audio works |
| **Crisis hotlines** | Opens NCMH **1553** and Hopeline **(02) 8804-4673** |
| **Collapse / Expand** | Shrinks or restores the desktop sidebar |
| **Dark mode** | Switches the dashboard theme; the choice is remembered |
| **Logout** | Ends the counselor session after confirmation |

Alerts also play a sound. If the browser has notifications enabled and permission is granted, GAIDA can show a desktop notification. Approval is requested when the dashboard opens.

### 6.12 Recommended response workflow

1. **Triage by severity** — Crisis first, then High, then Moderate, then Requested check-ins.
2. **Acknowledge** a New alert as soon as you see it.
3. **Open the session** and read the transcript before replying.
4. **Check immediate safety** for High/Crisis: ask whether the student is safe and whether anyone is with them.
5. **Share hotlines** when immediate help may be needed: **1553** and **911**.
6. **Take over** the conversation with a short, human message.
7. **Document** the outcome and actions in a case note.
8. **Resolve** the session only after follow-up is complete.
9. **Escalate** to a supervisor or the in-person Guidance Office when the case exceeds your scope or the alert is overdue.
10. **Remember:** a zero count does not confirm safety.

---

## 7. Research participant guide

Research participation is optional and separate from the normal student portal. It is part of an undergraduate thesis study and does not require a GAIDA account.

### 7.1 Consent and verification code

1. Open **Research Participation** from the portal screen.
2. Read the research consent terms.
3. Tick *“I have read the above and voluntarily agree to participate.”*
4. Enter the verification code.
5. Select **Continue**.

If you are under 18, have a parent or guardian review the consent with you.

### 7.2 Choose identified or anonymous participation

| Option | What is collected | What it means |
|---|---|---|
| **Participate with my student number** | Student number linked to the session | The research team can follow up and, for high-risk cases, notify the Guidance Office |
| **Participate anonymously** | No student number, name, or email | No one can identify or contact you about the session |

Anonymous participants who already have a token can tick *“I have a participant token from a previous anonymous session”* and paste it to continue as the same participant.

### 7.3 Demographics (optional)

All fields are optional:

- Year level
- Program
- Gender
- Region / hometown

Leave any field blank if you prefer not to say.

### 7.4 GAD-7 questionnaire

Answer the seven questions about the **last two weeks**. Each question uses:

- **Not at all**
- **Several days**
- **More than half the days**
- **Nearly every day**

All seven answers are required before you can submit. The GAD-7 is a screening questionnaire, not a diagnosis.

### 7.5 Start the session and save your token

After you confirm **Submit final form**, GAIDA creates a research session and opens the student chat.

**Anonymous participants:** a participant token is shown once. It is the only way to reference the session later.

1. Select **Copy participant token**.
2. Store it somewhere safe.
3. Select **I've saved my token — Continue**.

If you lose the token, the research team cannot locate your anonymous session.

### 7.6 Chat and finish

Use the chat as a normal student session. When you end the session, a research participant is taken to **One Last Thing**, a 10-item System Usability Scale (SUS) survey.

### 7.7 SUS survey

Rate each statement from **Strongly disagree** to **Strongly agree**. All 10 answers are required. Submit to finish; the page confirms that your feedback was recorded.

### 7.8 Withdraw and delete data

Anonymous participants can permanently delete everything tied to their token:

1. Open **Withdraw from the research study** from the portal screen, or use the link shown after token creation.
2. Paste your participant token.
3. Tick the confirmation that the deletion cannot be undone.
4. Enter the verification code.
5. Select **Delete My Data**.

The request deletes sessions, messages, GAD-7 and SUS responses, ratings, notes, alerts, acoustic logs, and the participant record. If deletion is only partially completed, the page tells you to contact the research team with your token.

**Identified participants:** contact the research team or the Guidance Office to request access to or deletion of your data.

---

## 8. Accounts and access

### 8.1 Roles

| Role | Access |
|---|---|
| **Student** | Chat, consent, voice input, feedback, hotlines, own session history during the session |
| **Counselor** | Alerts, active sessions, welfare checks, case notes, resolved cases, reports, PDF exports |
| **Research participant** | Research consent, GAD-7, chat session, SUS, anonymous withdrawal |
| **Administrator / developer** | Server configuration, accounts, database, deployment; no separate admin dashboard |

### 8.2 Production accounts

- **Students** sign in with their student number, UE email, password, and verification code, or with an authorized UE Google account.
- **Counselors** are configured by the administrator through the `COUNSELOR_ACCOUNTS` server variable, or sign in with Google when their email is on the authorized counselor list.
- Built-in demo counselor accounts are disabled on production unless demo mode is explicitly enabled.

### 8.3 Password and account security

- Do not share passwords or verification codes.
- Do not reuse your UE password on other sites.
- Sign out on shared computers.
- Report suspected unauthorized access to the Guidance Office or system administrator.

---

## 9. Troubleshooting and FAQ

### 9.1 Quick fixes

| Problem | Likely cause | What to do |
|---|---|---|
| **“Invalid credentials”** on counselor login | No matching counselor account on this server | Check the Faculty ID and password. On a local server, demo counselors require development mode or `GAIDA_ALLOW_DEMO_COUNSELORS=1`. On production, ask the administrator to configure your account. |
| **“Invalid credentials”** on student login | Wrong student number, email, or password | Re-enter the exact student number and `@ue.edu.ph` email. For pilot accounts, copy the values from [Appendix B](#appendix-b--pilot-test-accounts). |
| **“Incorrect or expired verification code”** | Code was typed wrong, already used, or expired | Press **Refresh**, type the new 6-character code, and submit again. Do not reuse an old code. |
| **“Getting a new verification code”** | A refresh is still in flight | Wait a moment, then submit. |
| **Google sign-in button is missing** | Google authentication is not configured for this deployment | Use the ID/password form instead. |
| **Forgot Password shows success but no email arrives** | Reset email delivery is not enabled at this stage | Contact the Guidance Office or administrator to reset the password. |
| **Blank page or “Failed to fetch dynamically imported module”** | The tab is holding an old build after a deployment | Reload the page. GAIDA tries to refresh the service worker and reload once automatically. If it still fails, close the tab and reopen the site. |
| **“Waiting to send”** | The device is offline or the connection dropped | Keep the app open and reconnect. Queued messages send automatically. Do not log out until they are delivered. |
| **Chat history cannot load offline** | Transcripts are not cached offline | Reconnect and select **Retry Loading**. |
| **Dashboard shows zero or stale data** | Backend or database is unreachable, or there is genuinely no data | Check the connection badge. If it says **Offline** or **Reconnecting**, wait or refresh. If it stays Live with zeros, there may be no recorded sessions. |
| **Reports banner: “Reports could not load…”** | Request failed or timed out after 10 seconds | Select **Retry**. If it keeps failing, check the backend and database connection. |
| **“Couldn't load Monthly Trends”** | The reports request failed | Select **Try again**. Other panels may still load. |
| **Resolve session is disabled** | No case note has been saved | Open **Case Notes**, choose an outcome, write a note, and select **Save note**. |
| **PDF export fails** | Session expired, network error, or server problem | Sign in again and retry. If it still fails, report the session ID and time to the administrator. |
| **Microphone does not work** | Permission denied, unsupported browser, or no microphone | Allow microphone access in the browser, use a supported browser, or type instead. |
| **“Listen” does nothing** | Browser text-to-speech is unavailable | Use a supported browser or read the reply on screen. |
| **No alert sound** | Browser audio is muted or blocked until you interact with the page | Select **Test Alert Chime** once, unmute the tab, and check system volume. |
| **No desktop notification** | Notification permission was denied | Allow notifications in the browser's site settings; the in-app badge still works. |
| **A resolved case is missing** | The session was not resolved, or the list has not refreshed | Confirm the session was resolved after saving a note, then reload Resolved Cases. |

### 9.2 If the problem continues

Report the following to the system administrator:

- Your role and account ID
- The page or feature
- The exact error message
- The time and date
- The session code or alert code, if shown
- A screenshot, if possible

Do not send passwords, verification codes, or participant tokens in a support message unless the administrator specifically asks through an approved channel.

---

## 10. Privacy, safety, and limitations

### 10.1 What GAIDA is not

- Not a doctor or licensed diagnosis
- Not an emergency service
- Not a substitute for a counselor's professional judgment
- Not guaranteed to detect every risk

### 10.2 Safety rules

- If someone is in immediate danger, call **911**.
- For mental-health crisis support, call **1553** (NCMH, 24/7).
- Do not wait for an in-app reply during an emergency.
- A zero alert count does not confirm that all students are safe.
- Follow the campus emergency procedure and your office's escalation policy.

### 10.3 Data handling

- Chat text may be sent to third-party AI services to generate replies and support detection.
- Voice is processed for speech features; recordings are not intended to be stored after processing.
- Data is stored in Supabase.
- Counselors can access flagged sessions and case records.
- Exported PDFs leave the system; store and dispose of them according to university policy.
- Research data is used for the thesis and may appear in reports without names attached to quoted excerpts.

### 10.4 Account and device hygiene

- Use a private device when possible.
- Sign out after use.
- Do not leave an unlocked dashboard unattended.
- Keep verification codes private.

---

## 11. Accessibility and supported devices

GAIDA includes:

- Keyboard-reachable navigation and controls
- Visible focus indicators
- Screen-reader labels for icon-only buttons, badges, dialogs, and charts
- Text alternatives for status colors
- Minimum 44 px touch targets on mobile
- Reduced-motion support for users who enable it in their operating system
- Responsive layouts for desktop, tablet, and phone
- Light and dark counselor themes

**Supported browsers:** current Chrome, Edge, Safari, and Firefox. Install the PWA for an app-like experience and offline app-shell access. Voice input and text-to-speech depend on browser support and device permissions.

---

## 12. Glossary

| Term | Meaning |
|---|---|
| **Acknowledged** | A counselor has seen an alert but has not finished reviewing it |
| **Active session** | A student conversation currently in progress |
| **Alert** | A notification created when a session needs counselor attention |
| **Case note** | The counselor's record of what happened and what was done |
| **Crisis** | The highest detected level, intended for immediate intervention |
| **Escalation** | Raising an alert to a supervisor, backup, or in-person office |
| **GAD-7** | A seven-item anxiety screening questionnaire |
| **GAIDA** | Guidance system with multimodal Anxiety Intelligence and Detection Assistance |
| **High** | A serious level that fires a counselor alert and may pause GAIDA |
| **Moderate** | A level that adds a stronger support protocol |
| **New** | An alert that has not been acknowledged |
| **Participant token** | The private code that identifies an anonymous research session |
| **Pending alert** | Any alert that is not yet resolved |
| **Resolved** | A case or alert that has been reviewed and closed |
| **Severity** | The detected anxiety level: Normal, Low, Moderate, High, or Crisis |
| **SUS** | System Usability Scale, a 10-item usability survey |
| **Takeover** | A counselor joining a live session and replying directly |
| **Welfare check** | A human follow-up for a silent High or Crisis session |
| **Workspace ID** | The counselor's ID shown in the sidebar profile |

---

## Appendix A — Administrator and developer notes

### A.1 Local startup

**Backend (PowerShell):**

```powershell
cd backend
.\venv\Scripts\Activate.ps1
$env:ENVIRONMENT = "development"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Frontend (second terminal):**

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

**Why `ENVIRONMENT=development` matters:** the built-in demo counselor accounts (`COUNSELOR01` / `counsel123`, and so on) are only enabled when `ENVIRONMENT=development` or `GAIDA_ALLOW_DEMO_COUNSELORS=1`. Without either, the counselor ID/password login has **no accounts** and returns “Invalid credentials.” Never enable demo counselors on a real deployment.

### A.2 Environment variables

| Variable | Purpose |
|---|---|
| `ENVIRONMENT` | Set to `development` for local demo accounts and development behavior |
| `GAIDA_ALLOW_DEMO_COUNSELORS` | Set to `1` to enable demo counselors without development mode |
| `COUNSELOR_ACCOUNTS` | JSON list of production counselor accounts |
| `SUPABASE_URL`, `SUPABASE_KEY` | Database connection |
| `OPENAI_API_KEY` | AI reply generation |
| `GOOGLE_CLIENT_ID` | Google sign-in verification |
| `SMTP_*`, `ALERT_FROM_EMAIL`, `COUNSELOR_ALERT_EMAILS` | Email alerts and escalation notices |
| `FRONTEND_URL` | Allowed frontend origin and email links |
| `CAPTCHA_SECRET` or `AUTH_SECRET` | Stable captcha signing secret across restarts |

Do not commit `.env` files or share their contents.

### A.3 Health checks and tests

- Backend health: `GET http://127.0.0.1:8000/health`
- API documentation in development: `http://127.0.0.1:8000/docs`
- Backend tests:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m pytest -q
```

- Frontend production build:

```powershell
cd frontend
npm run build
```

### A.4 Common operational issues

| Symptom | Check |
|---|---|
| `Supabase warm skipped: getaddrinfo failed` | DNS or network cannot resolve the Supabase host; login may work while dashboard data stays empty |
| Counselor login returns 401 “Invalid credentials” | `ENVIRONMENT`, `GAIDA_ALLOW_DEMO_COUNSELORS`, or `COUNSELOR_ACCOUNTS` is not configured |
| `/docs` returns 404 | The backend is not running in development mode |
| Verification codes always fail | The server restarted and the captcha secret changed; set `CAPTCHA_SECRET` for stable tokens |
| Reports time out | Backend or Supabase is slow/unreachable; check the 10-second timeout and server logs |
| Alerts do not arrive live | The real-time stream may have dropped; the badge should show **Reconnecting** and polling should continue |

---

## Appendix B — Pilot test accounts

These accounts are for pilot testing and local demonstrations. **Do not use them in a real deployment.** Administrators should configure real accounts and disable demo counselors.

### B.1 Student demo accounts

| Student number | Email | Password | Name | Program | Year |
|---|---|---|---|---|---|
| `2024001` | `student1@ue.edu.ph` | `ACCESS123` | Maria Santos | BS Psychology | 2 |
| `2024002` | `student2@ue.edu.ph` | `ACCESS456` | Juan dela Cruz | BS Computer Science | 3 |
| `2024003` | `student3@ue.edu.ph` | `ACCESS789` | Ana Reyes | BS Nursing | 1 |

Student sign-in also requires a new verification code.

### B.2 Counselor demo accounts

These only work when demo counselors are enabled (`ENVIRONMENT=development` or `GAIDA_ALLOW_DEMO_COUNSELORS=1`).

| Faculty ID | Password | Name |
|---|---|---|
| `COUNSELOR01` | `counsel123` | Dr. Patricia Lim |
| `COUNSELOR02` | `counsel202` | Guidance Counselor 2 |
| `COUNSELOR03` | `counsel303` | Guidance Counselor 3 |
| `COUNSELOR04` | `counsel404` | Guidance Counselor 4 |
| `COUNSELOR05` | `counsel505` | Guidance Counselor 5 |

Counselor sign-in also requires a new verification code.

---

*End of manual.*
