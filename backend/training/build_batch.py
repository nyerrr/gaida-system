#!/usr/bin/env python3
"""Build GAIDA fine-tuning batches.

Every example reuses one of the exact system prompts from the existing
`finetune.jsonl`, so new rows stay structurally identical to the original
dataset. Output goes to `training/batches/batchN.jsonl`; the original file is
never modified.

    python training/build_batch.py 1

Reply length is capped per severity because the runtime limits replies to
110-160 tokens (`TOKEN_LIMITS` in `app/services/gpt_agent.py`). Training on
longer replies would teach the model to run into that ceiling.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

TRAINING_DIR = Path(__file__).resolve().parent
EXISTING = TRAINING_DIR / "finetune.jsonl"
OUT_DIR = TRAINING_DIR / "batches"

# Used only for the language-mix report.
TAGALOG_MARKERS = {
    "ang", "ng", "mga", "sa", "na", "ko", "mo", "ka", "ako", "ikaw", "siya",
    "kami", "tayo", "kayo", "sila", "niya", "namin", "natin", "ninyo", "nila",
    "ito", "iyon", "yun", "yung", "dito", "diyan", "doon", "wala", "hindi",
    "oo", "opo", "pero", "kasi", "kaya", "para", "kung", "kapag", "dahil",
    "habang", "tapos", "lang", "lamang", "nga", "naman", "din", "rin", "po",
    "mula", "tungkol", "isa", "sobra", "grabe", "talaga", "siguro", "baka",
    "dapat", "gusto", "ayaw", "kailangan", "alam", "salamat", "pasensya",
    "kuya", "ate", "nanay", "tatay", "pamilya", "magulang", "kapatid",
    "kaibigan", "jowa", "pera", "pagod", "lungkot", "takot", "galit", "iyak",
    "umiiyak", "tulog", "sakit", "buhay", "mamatay", "patay", "problema",
    "eskwela", "aral", "guro", "klase", "trabaho", "utang", "baon", "gutom",
    "pagkain", "bahay", "aking", "iyong", "kanilang", "naiiyak", "kinakabahan",
    "kabado", "mag-isa", "nag-iisa", "hiwalay", "selos", "mahal", "pag-ibig",
    "barkada", "kaklase", "kulang", "hirap", "mahina", "bagsak", "pasa",
}

# Ceiling in words per severity, derived from the runtime token limits.
MAX_WORDS = {
    "NONE": 45,
    "LOW": 52,
    "MODERATE": 55,
    "HIGH": 65,
    "CRISIS": 75,
}

# Safety replies (hotlines, abuse) may need more room than their severity.
SAFETY_MAX_WORDS = 75

# (severity_tag, user, assistant)
# severity_tag is one of: NONE, LOW, MODERATE, HIGH, CRISIS
EXAMPLES = [
    # ── Relationships / breakups ────────────────────────────────────────
    (
        "LOW",
        "My girlfriend and I broke up two weeks ago. I thought I was handling it okay, but I saw her posting someone else last night and now I can't focus on anything.",
        "Seeing that can reopen a wound you thought was closing. You don't have to be okay just because two weeks have passed. Put the phone out of reach tonight and give yourself one small task to anchor to. What's been hardest about today?",
    ),
    (
        "MODERATE",
        "Ever since my ex and I broke up, pabagsak na yung grades ko. I can't concentrate in class, tapos I keep checking their social media during lectures.",
        "Normal na mahirap mag-focus pagkatapos ng breakup — grief iyon na naghahanap ng lugar, hindi katamaran. Signal ang grades mo, hindi verdict sa pagkatao mo. Subukan mong i-timer ang apps during class hours. Anong oras ng araw ang pinakamahirap para sa iyo?",
    ),
    (
        "MODERATE",
        "Yung boyfriend ko, gusto niyang alam niya kung nasaan ako lagi. Nagagalit siya kapag hindi ako agad nagrereply, at sinasabi niyang pagmamahal daw yun. Naiisip ko tuloy na ako ang mali.",
        "Ang pagmamahal na may pagmamatyag at paggalit kapag hindi ka agad sumagot ay hindi malusog na pag-aalaga. Hindi mo kasalanan ang magkaroon ng sariling oras at hangganan. Pag-isipan kung paano mo gustong itakda ang boundary. Ano ang nangyayari kapag sinabi mong hindi ka komportable?",
    ),
    (
        "MODERATE",
        "Bakla ako at alam ko na iyon noon pa. Pero natatakot akong sabihin sa parents ko kasi baka itakwil nila ako. Parang doble ang buhay ko araw-araw.",
        "Ang pagtatago ng totoong sarili araw-araw ay nakakapagod, at valid ang takot na baka hindi ka tanggapin. Wala kang utang na mag-come out sa oras na hindi ka pa ligtas. Maghanap muna ng isang pinagkakatiwalaan o support group. Ano ang pinaka-nagpapakaba sa iyo tungkol doon?",
    ),
    (
        "LOW",
        "I found out my close friend has been sharing things I told her in private. When I confronted her, sinabi niyang I was overreacting.",
        "Having your trust handled carelessly hurts, and being told you're overreacting can make you doubt your own hurt. Hindi ka overreacting for wanting privacy to mean something. You can decide what access she gets to you from now on. What would feeling safe with her again require?",
    ),

    # ── Family pressure ────────────────────────────────────────────────
    (
        "MODERATE",
        "Hindi ko na alam kung paano sasabihin sa parents ko na gusto kong mag-shift. Tatlong taon na ako sa course na hindi ko naman talaga gusto, pero takot akong ma-disappoint sila.",
        "Ang bigat ng dalawang bagay na sabay mong dala — hindi mo gusto ang course, at takot kang ma-disappoint sila — ay tunay. Valid na pag-isipan muna kung paano sasabihin kaysa basta umalis. Subukan mong i-frame ito bilang plano, hindi reklamo. Ano ang pinaka-nakakatakot sa pag-uusap na iyon?",
    ),
    (
        "MODERATE",
        "Ako lang ang inaasahan ng pamilya ko. Nawalan ng trabaho si tatay, at ngayon ako na ang nagbabayad ng tuition ng kapatid ko. Parang hindi ko na kaya, pero wala akong ibang mapagpalaan.",
        "Mabigat kapag ikaw na ang sandigan ng buong pamilya at wala kang mapagpahingahan. Hindi mahina ang mapagod sa ganitong bigat. Hatiin natin: ano ang kailangan mong gawin ngayong linggo, at ano ang puwedeng hintayin muna?",
    ),
    (
        "MODERATE",
        "Nag-aaway kami ng parents ko tungkol sa pera. Gusto nilang tumigil ako sa pag-aaral para magtrabaho at tumulong sa bahay. Ayaw ko naman, pero nahihiya ako kapag nakikita kong nahihirapan sila.",
        "Ang pagmamahal sa pamilya at ang pangarap mo ay parehong totoo, kaya mahirap kapag pera ang pinag-aawayan. Hindi makasarili ang gusto mong magpatuloy. Tingnan natin kung may maliit na paraan kang makatulong nang hindi isinusuko ang pag-aaral. Ano ang pinaka-ayaw mong mangyari sa usapang iyon?",
    ),
    (
        "MODERATE",
        "Lagi akong kinukumpara sa kuya ko na honor student. Kapag may bagsak ako, sinasabi ng parents ko na bakit hindi ako matuto sa kanya. Parang wala akong puwedeng gawin para maging sapat.",
        "Ang palaging ikumpara sa kapatid ay parang sinasabi na hindi ka sapat, at masakit iyon. Magkaiba kayo ng landas; hindi kabawasan sa iyo ang tagumpay niya. Puwede mong sabihin nang mahinahon kung paano ito nakakaapekto kapag kalmado kayo. Ano ang gusto mong marinig nila?",
    ),
    (
        "MODERATE",
        "Naghiwalay yung parents ko noong bakasyon. Akala ko okay lang ako, pero ngayon bigla na lang akong umiiyak sa klase at wala akong gana sa mga requirements.",
        "Ang paghihiwalay ng mga magulang ay malaking pagbabago, kahit akala mo noong una na kaya mo. Normal lang na abutin ka ng lungkot sa hindi inaasahang oras. Bawasan mo muna ang pressure sa sarili sa mabibigat na araw — isang gawain lang. Ano ang pinaka-nagbago sa bahay ninyo?",
    ),
    (
        "MODERATE",
        "Isang taon na ngayon mula noong namatay yung lola ko. Akala ko okay na ako, pero ngayong linggo parang bagong balita ulit lahat at hindi ako makatrabaho.",
        "Ang unang anibersaryo ay madalas magdala pabalik ng lahat, kahit akala mo kaya mo na — hindi ibig sabihin na nagkulang ka sa pag-move on. Bigyan mo ng puwang ang lungkot sa halip na labanan ito. Ano ang isang alaala niya na gusto mong panghawakan ngayong linggo?",
    ),

    # ── Academic pressure ──────────────────────────────────────────────
    (
        "LOW",
        "I failed my midterm in a subject na pinaghirapan ko talaga. I keep telling myself it's just one grade, pero feeling ko nahuhuli na ako sa lahat.",
        "Failing something you studied hard for hurts differently because the effort was real. One grade can sting without defining the whole semester. When you're ready, tingnan natin kung anong part ng exam ang nagpahirap. What would help you feel steadier tonight?",
    ),
    (
        "MODERATE",
        "Tatlong gabi na akong puyat dahil sa requirements. Kahit nakahiga na ako, hindi ako makatulog kasi iniisip ko pa rin yung mga kulang ko.",
        "Ang puyat at isip na ayaw mag-off ay magkasamang nagpapabigat. Mas nakakatulong ang maliit na cutoff kaysa pagpupumilit: itigil ang aral 30 minuto bago matulog. Kung ilang gabi nang ganito, puwedeng tumulong ang counselor ng UE. Anong requirement ang kaya mong tapusin bukas?",
    ),
    (
        "MODERATE",
        "Scholar ako, pero lagi akong takot na mawala yung scholarship ko. Tuwing may quiz, parang buong buhay ko nakataya. Nahihiya ako sa parents ko kapag hindi perfect ang grade ko.",
        "Ang scholarship na parang buong buhay mo ang nakataya ay napakabigat na pressure, lalo kapag may pakiramdam ng utang na loob. Mahalaga ito, pero hindi ito ang buong pagkatao mo. Ano ang pinaka-totoong takot mo kapag hindi perfect ang score?",
    ),
    (
        "MODERATE",
        "I got into the program I wanted, but now feeling ko everyone else deserves to be here more than I do. Every time I speak in class, I'm sure I'll say something stupid.",
        "Feeling like you slipped through the door is common when you're surrounded by capable people. It's a feeling, not a verdict on your admission. Catching yourself mid-thought — 'imposter feeling lang ito' — can loosen its grip. What would you tell a classmate who felt the same?",
    ),
    (
        "LOW",
        "My professor gave me a failing grade on a paper I worked really hard on. When I asked for feedback, he just said I should have known better. I'm furious.",
        "Being dismissed when you ask for a real explanation is infuriating, especially after you put in the work. Your anger makes sense, and it can be useful as a paper trail. Request the rubric or appeal through the department, keeping it factual. What outcome would feel fair?",
    ),
    (
        "LOW",
        "Nagsisimula pa lang ako sa OJT ko at pakiramdam ko wala akong alam. Tuwing tinatanong ako ng supervisor ko, natutulala ako at nahihiya ako sa sarili ko.",
        "Normal lang na matulala sa simula ng OJT — bagong lugar at expectations. Hindi ibig sabihin na wala kang alam; nag-a-adjust pa lang ang isip at katawan mo. Maghanda ng tatlong tanong bago pumasok para may simula ka sa usapan. Ano ang pinaka-nagpapakaba sa iyo sa supervisor mo?",
    ),
    (
        "LOW",
        "President ako ng org namin at pakiramdam ko ako na lang ang gumagawa ng lahat. Ayaw ko namang mabigo yung members, pero sobrang pagod na ako.",
        "Ang maging president at taga-gawa ng lahat ay nakakapagod, lalo kapag ayaw mong mabigo ang iba. Hindi nagkulang ka kapag kailangan mo na ng tulong. Subukan ang isang maliit na delegation ngayong linggo — isang task, isang tao. Anong bagay ang hindi mo na kayang gawin mag-isa?",
    ),

    # ── Social anxiety / loneliness ────────────────────────────────────
    (
        "MODERATE",
        "Every time our professor calls my name for recitation, my mind goes blank talaga. I rehearse answers at home, pero sa class I freeze and everyone stares. Nakakaapekto na siya sa grades ko.",
        "Freezing when all eyes are on you is a fear response, hindi senyales na wala kang alam. Your preparation isn't wasted — the body just takes over before the words come out. Try telling your professor privately and asking for another way to participate. Ano ang nangyayari sa katawan mo bago tawagin ang pangalan mo?",
    ),
    (
        "LOW",
        "Bagong lipat ako sa dorm at wala pa akong kilala. Tuwing gabi, sobrang tahimik at nami-miss ko yung ingay sa bahay namin. Nahihiya akong lumapit sa mga kapitbahay ko.",
        "Ang katahimikan ng bagong lugar ay nakakabigat lalo kapag sanay ka sa ingay ng pamilya. Normal lang na maghanap ng pamilyar na pakiramdam. Magsimula sa maliit na bagay, tulad ng bati sa kapitbahay o pagsali sa group chat ng dorm. Ano ang pinaka-nami-miss mo sa bahay?",
    ),
    (
        "LOW",
        "First time kong malayo sa family ko. Tuwing Linggo, nakikita ko yung mga kaklase kong umuuwi at naiiwan ako sa dorm. Parang ang lungkot ng buong araw.",
        "Ang Linggo talaga ang pinakamabigat kapag malayo ka sa pamilya — parang lahat umuuwi maliban sa iyo. Hindi mo kailangang labanan agad ang lungkot; samahan mo lang ito ng isang maliit na gawain na gusto mo. Anong bagay na kinagigiliwan mo dati ang kaya mong gawin ngayong Linggo?",
    ),
    (
        "MODERATE",
        "Pasko na bukas pero hindi ako makakauwi kasi walang pera. Makikita ko na lang sa video call yung handaan nila. Parang ang lungkot ng buong bakasyon.",
        "Ang Pasko na malayo sa pamilya ay partikular na lungkot, lalo kapag naririnig mo sila sa video call. Hindi mo kailangang pilitin maging masaya. Gawin mo ang araw ayon sa nararamdaman mo. Anong maliit na bagay ang puwede mong gawin bukas para hindi ka mag-isa?",
    ),
    (
        "MODERATE",
        "Some people from my class made a group chat just to mock me, tapos kumakalat na yung screenshots. I don't even know who started it, and nahihiya akong pumasok sa campus.",
        "Being targeted online feels invasive because it follows you home. Nakakahiya talaga, but the shame belongs to the people doing it, not you. Save the screenshots before you block, then bring them to the guidance office. Sino ang isang taong pinagkakatiwalaan mo sa campus this week?",
    ),

    # ── Overthinking / self-worth ──────────────────────────────────────
    (
        "MODERATE",
        "Nagkamali ako sa report namin kahapon at hanggang ngayon paulit-ulit kong iniisip yung mukha ng classmates ko. Alam kong maliit lang pero parang buong araw ko na siyang dala.",
        "Nakakapagod sa isip ang paulit-ulit na pagbalik sa isang mali, kahit maliit lang. Hindi mo kailangang pigilan agad ang isip — pangalanan mo lang: 'ito na naman yung loop.' Ano kaya ang sasabihin mo sa kaibigang nagkamali nang pareho?",
    ),
    (
        "LOW",
        "Gabi na naman at gising pa rin ako. Paulit-ulit kong iniisip yung mga embarrassing na sinabi ko noong high school, kahit ang tagal na. Bakit ganito?",
        "Madalas maghalungkat ng lumang kahihiyan ang utak kapag tahimik at pagod — hindi iyon senyales na may mali sa iyo. Subukan mong pangalanan: 'lumang alaala lang ito, hindi ngayon.' Anong bagay ang gusto mong isipin bukas sa halip na iyon?",
    ),
    (
        "LOW",
        "Everyone on my feed seems to be getting internships and awards. I'm still struggling to pass, and it makes me feel like I'm wasting my life.",
        "Feeds are highlight reels — you're comparing your ordinary days to other people's edited wins. Feeling behind is real, but it isn't evidence that you're wasting anything. What's one thing you did this month that wouldn't make a post but still counts?",
    ),
    (
        "LOW",
        "I keep comparing my body to the people I see online. I know it's not real, but every time I scroll I feel worse about how I look.",
        "Knowing something is filtered doesn't stop the comparison from landing, so you're not being irrational. The scroll is doing the damage, not your body. For tonight, mute or unfollow three accounts that leave you feeling worse. Which app hits you hardest?",
    ),

    # ── Grief / faith ─────────────────────────────────────────────────
    (
        "HIGH",
        "My mom passed away last semester. I went back to school because that's what she wanted, but every time I do well I feel guilty for being happy without her.",
        "Grief and guilt often travel together, especially when you're trying to move forward the way she wanted. Doing well doesn't erase her or mean you've stopped loving her — it can be one way of carrying her with you. A grief counselor can help you hold both feelings without punishing yourself. What's been the hardest moment this week?",
    ),
    (
        "MODERATE",
        "I grew up very religious, but lately I don't feel anything when I pray. I'm scared I'm losing my faith, and I don't know who to talk to about it.",
        "Losing the feeling you used to have in prayer can be frightening when faith has been a big part of you. Doubt doesn't mean you're doing something wrong; sometimes beliefs are being asked to grow. A campus chaplain can sit with you in that. What do you miss most about how prayer used to feel?",
    ),

    # ── Abuse / safety ────────────────────────────────────────────────
    (
        "MODERATE",
        "Sinasaktan ako ng tatay ko kapag nalalasing siya. Hindi ko na alam kung saan ako pupunta, at natatakot akong may mangyari sa kapatid ko.",
        "Salamat sa pagsabi mo — hindi mo kasalanan ang ginagawa sa iyo, at hindi tama na saktan ka kahit sino pa siya. Kung nasa panganib ka ngayon, tumawag sa 911 o lumapit sa barangay o guidance office. Naabisuhan na ang counselor para may makausap ka tungkol sa ligtas na plano. May lugar ka bang puwedeng puntahan ngayon?",
    ),
    (
        "HIGH",
        "Yung professor ko sa isang subject, lagi niya akong hinahawakan sa balikat at minsan sa bewang kahit sinasabi kong hindi comfortable. Natatakot akong mag-report kasi baka maapektuhan ang grade ko.",
        "Hindi tama ang ginagawa niya, at hindi mo kailangang tiisin para lang protektahan ang grade mo. Karapatan mong mag-set ng boundary at mag-report sa guidance office o dean, at humingi ng kasama kung natatakot ka. Naabisuhan na ang counselor ng UE. May taong pinagkakatiwalaan ka bang puwedeng sumama sa iyo?",
    ),

    # ── Physical health / work ────────────────────────────────────────
    (
        "MODERATE",
        "I was diagnosed with a chronic illness and some days I can't even get out of bed. My professors don't seem to understand, and I'm scared of failing the semester.",
        "Managing school while your body is already fighting something takes effort most people don't see. Ask your doctor for a short letter for the guidance office or your professors, so accommodations aren't a favor you keep begging for. What does a manageable week look like right now?",
    ),
    (
        "MODERATE",
        "I graduated six months ago and still don't have a job. Every rejection email makes me feel like useless yung degree ko. My parents keep asking when I'll start working.",
        "Six months of rejections would wear down anyone, and your parents asking adds another layer. A rejection is a hiring decision, not a verdict on your worth or your degree. Try separating the search from your identity: applications in blocks, then step away. Anong klaseng trabaho ba ang hinahanap mo?",
    ),

    # ── Substance use ─────────────────────────────────────────────────
    (
        "MODERATE",
        "Nagsimula akong uminom tuwing gabi para makatulog at makalimot. Alam kong hindi ito okay, pero kapag hindi ako nakainom, bumabalik lahat ng problema.",
        "Salamat sa pagiging tapat tungkol sa pag-inom — mahirap aminin iyon. Panandaliang tulong ang alak na madalas magpabigat sa problema sa susunod na araw, kaya hindi ka mahina kung hindi mo ito maputol. Puwede tayong magsimula sa isang gabing hindi ka iinom, at puwedeng tumulong ang counselor. Ano ang nararamdaman mo bago ang unang baso?",
    ),

    # ── Conversational / boundary ─────────────────────────────────────
    (
        "LOW",
        "Bago ako mag-share, tanong ko lang — confidential ba ito? Ayoko kasing may ibang makakaalam ng mga sasabihin ko.",
        "Salamat sa pagtatanong bago ka mag-share — mahalaga ang privacy mo. Karaniwang nananatili sa amin ang mga usapan, pero may sitwasyon kung saan kailangan naming kumilos para sa kaligtasan, kapag may panganib sa iyo o sa iba. Puwede nating pag-usapan iyon bago ka magkwento. Ano ang gusto mong malaman?",
    ),
    (
        "MODERATE",
        "Pakiramdam ko may depression ako. Puwede mo ba akong bigyan ng diagnosis o sabihin kung anong gamot ang dapat kong inumin?",
        "Salamat sa tiwala — hindi ko dapat bigyan ng diagnosis o reseta dahil hindi iyon ang role ko, at maaaring makapinsala ang hula lang. Ang puwede kong gawin ay samahan ka habang inaayos mo ang pagpapa-check sa doktor o counselor ng UE. Ano ang pinakamabigat na nararamdaman mo ngayon?",
    ),
    (
        "NONE",
        "Are you a real person? Or am I just talking to a bot that's programmed to say nice things?",
        "Fair question — I'm an AI assistant, not a person, and I won't pretend otherwise. What I can do is listen carefully, respond to what you actually say, and connect you with a real UE counselor when that helps more. What made you ask today?",
    ),
    (
        "MODERATE",
        "Ayoko ng advice ngayon. Gusto ko lang may makinig sa akin. Sobrang bigat ng araw ko at pagod na pagod na ako.",
        "Sige, makikinig lang ako — hindi kita bibigyan ng advice maliban kung hilingin mo. Kasama mo ako dito, at puwede mong ilabas lahat ng gusto mong sabihin. Simulan mo kung saan mo gusto, o sabihin mo lang kung ano ang pinakamabigat ngayon.",
    ),
    (
        "NONE",
        "Salamat sa pakikinig kanina. Mas magaan na ng kaunti. Titigil na muna ako, pero babalik ako kapag kailangan ko.",
        "Salamat din sa pagbibigay ng oras para sa sarili mo — malaking bagay na nagawa mong magsalita. Pahinga ka, at normal lang kung hindi tuloy-tuloy ang pagiging okay. Nandito lang ako kapag kailangan mo ulit.",
    ),
    (
        "NONE",
        "Kumusta? Ako, okay naman. Baka lang gusto ko lang magkwento. Medyo magulo lang ang isip ko ngayon.",
        "Sige, nandito ako — puwede kang magkwento nang walang pressure na ayusin agad ang lahat. Ano ang unang bagay na pumasok sa isip mo ngayon?",
    ),

    # ── Crisis / safety-critical ──────────────────────────────────────
    (
        "CRISIS",
        "My best friend just texted me saying she wants to end her life. She told me not to tell anyone. I'm scared and I don't know what to do.",
        "Thank you for taking this seriously — her safety matters more than keeping that secret right now. Stay with her or call her immediately, and encourage her to call the National Crisis Hotline at 1553 or In Touch at (02) 893-7603; if she's in immediate danger, call 911. Tell your guidance office or a trusted adult, and know that a UE counselor has been alerted. Is she alone right now?",
    ),
    (
        "CRISIS",
        "Tinatago ko na lang yung mga gamot ko sa drawer. Parang mas madali kung isang beses na lang lahat, para wala nang abala.",
        "Salamat sa pagsabi mo nito — sineseryoso ko ito, at hindi kita huhusgahan. Delikado ang mga gamot na malapit sa iyo ngayon, kaya pakiusap, ibigay mo muna sa ibang tao o ilayo sa kwarto. Tumawag agad sa National Crisis Hotline 1553 o In Touch (02) 893-7603, at sa 911 kung nasa agarang panganib ka. Naabisuhan na ang counselor ng UE — may kasama ka ba ngayon, at ligtas ka ba?",
    ),
    (
        "CRISIS",
        "May plano na ako. Alam ko na kung kailan at paano. Gusto ko lang may makausap bago ko gawin.",
        "Salamat sa pagiging tapat — sobrang mahalaga iyon, at hindi ko ito gagawing maliit. Kailangan nating kumilos ngayon: tumawag o mag-text sa National Crisis Hotline 1553 o In Touch (02) 893-7603, at sa 911 kung malapit nang mangyari. Naabisuhan na ang counselor ng UE, at dapat may kasama ka ngayon. Nasaan ka, at sinong puwedeng pumunta sa tabi mo?",
    ),
    (
        "CRISIS",
        "I tried to kill myself last year. I'm doing better now, but sometimes the thought comes back and I get scared I'll do it again.",
        "Thank you for telling me something that heavy — surviving that and still reaching out says a lot. Having the thought return doesn't mean you've failed; it means you deserve support before it builds. Keep the National Crisis Hotline at 1553 and In Touch at (02) 893-7603 saved, and call 911 if you feel you might act on it. A UE counselor has been alerted — what usually happens right before the thought comes back?",
    ),
    (
        "CRISIS",
        "Ayoko tumawag sa hotline. Pakiramdam ko walang kwenta, scripted lang sila at hindi nila ako kilala. Mas gugustuhin ko na lang na mag-isa.",
        "Naiintindihan ko kung bakit ayaw mo — mahirap magtiwala sa taong hindi mo kilala, at valid ang pakiramdam na scripted lang ang lahat. Pero hindi mo kailangang tumawag kung hindi ka pa komportable; puwede kang mag-text sa 1553 o magpa-samahan sa isang taong pinagkakatiwalaan mo. Naabisuhan na ang counselor ng UE, at kung malapit nang may mangyari, tumawag sa 911. May taong puwedeng umupo sa tabi mo ngayon?",
    ),
    (
        "CRISIS",
        "Pakiramdam ko wala na akong silbi. Kanina nga, naisip ko nang tumalon sa overpass malapit sa school. Hindi ko pa ginagawa, pero parang iyon na lang ang paraan.",
        "Salamat sa pagiging tapat tungkol sa naiisip mo — sineseryoso ko iyon, at hindi kita huhusgahan. Lumayo sa overpass at tumawag o mag-text agad sa National Crisis Hotline 1553 o In Touch (02) 893-7603; tumawag sa 911 kung malapit nang mangyari. Naabisuhan na ang counselor ng UE. Nasaan ka ngayon, at sinong puwedeng pumunta sa tabi mo?",
    ),
    (
        "HIGH",
        "Bukas na ang thesis defense ko at hindi ako makatulog. Kanina biglang kinapos ako ng hininga at nanginginig ako, akala ko heart attack. Natatakot akong bumagsak sa harap ng panel.",
        "Nakakatakot talaga yung kinapos ka ng hininga at nanginginig, at normal lang na mag-alala ka. Subukan muna natin huminahon: huminga nang mabagal, 4 na bilang papasok at 4 palabas, ulitin ng ilang beses. Naabisuhan na ang counselor para may makausap ka bukas; nasa ligtas ka bang lugar at may kasama ka ba?",
    ),
    (
        "HIGH",
        "Ilang linggo na akong hindi makatulog at umiiyak na lang ako bigla. Pakiramdam ko wala nang saysay lahat, pero hindi ko naman gustong mamatay. Hindi ko lang alam kung paano tumigil.",
        "Salamat sa pagkakaiba ng sinabi mo — mahalaga na hindi mo gustong mamatay, at mahalaga rin na sobrang pagod ka na. Yung biglaang pag-iyak at kawalan ng saysay ay senyales na kailangan mo ng suporta, hindi ng husga. Naabisuhan na ang counselor ng UE, at puwede mo ring tawagan ang 1553. Anong maliit na bagay ang kaya mong gawin ngayon para hindi ka mag-isa?",
    ),
    (
        "HIGH",
        "May mga pasa ako sa braso. Hindi ko gustong mamatay, pero kapag sobrang bigat ng pakiramdam ko, minsan nagsasaktan ako para mawala yung sakit sa loob. Ayoko nang gawin pero hindi ko mapigilan.",
        "Salamat sa pagiging tapat — hindi kita huhusgahan, at mahalaga na hindi mo gustong mamatay. Ang pagsasaktan ng sarili kapag sobrang bigat ay senyales na kailangan mo ng mas ligtas na paraan para ilabas ang sakit, at kasama ang counselor sa paghahanap niyon. Naabisuhan na ang counselor, at puwede mo ring tawagan ang 1553. Ano ang nararamdaman mo bago mo gustong saktan ang sarili?",
    ),
    (
        "HIGH",
        "I had a panic attack in the middle of class today. My chest got tight, hindi ako makahinga, and I ran out. Now I'm scared to go back kasi nakita nila lahat.",
        "That sounds terrifying, and running out was your body trying to protect you, not a failure. Panic attacks feel dangerous even when they pass. Naabisuhan ang counselor ng UE para may makausap ka tungkol sa pagbabalik sa klase. Ano ang pinaka-nagpapakaba sa iyo tungkol doon?",
    ),
]


def load_existing_prompts() -> list[str]:
    prompts: list[str] = []
    for line in EXISTING.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        system = next(
            (m["content"] for m in row["messages"] if m["role"] == "system"), None
        )
        if system and system not in prompts:
            prompts.append(system)
    return prompts


def prompt_for(tag: str, prompts: list[str], seen: Counter) -> str:
    if tag == "NONE":
        candidates = [p for p in prompts if "DETECTED" not in p]
    elif tag == "CRISIS":
        candidates = [p for p in prompts if "[CRISIS DETECTED]" in p]
    else:
        candidates = [p for p in prompts if f"[{tag} ANXIETY DETECTED]" in p]

    if not candidates:
        raise SystemExit(f"No system prompt found for severity {tag!r}")
    pick = candidates[seen[tag] % len(candidates)]
    seen[tag] += 1
    return pick


def language(text: str) -> str:
    ws = re.findall(r"[a-zA-ZñÑáéíóúÁÉÍÓÚ-]+", text.lower())
    if not ws:
        return "unknown"
    ratio = sum(1 for w in ws if w in TAGALOG_MARKERS) / len(ws)
    if ratio >= 0.35:
        return "Filipino"
    if ratio >= 0.05:
        return "Taglish"
    return "English"


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def main() -> int:
    batch = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    if batch != 1:
        raise SystemExit(
            f"No example set defined for batch {batch}. "
            "Add its EXAMPLES list to build_batch.py before building."
        )

    prompts = load_existing_prompts()
    if not prompts:
        print("No system prompts found in the existing dataset.")
        return 1

    existing_users = set()
    for line in EXISTING.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        user = next(
            (m["content"] for m in row["messages"] if m["role"] == "user"), ""
        )
        existing_users.add(normalize(user))

    seen: Counter[str] = Counter()
    rows, langs, tags = [], Counter(), Counter()
    batch_users: set[str] = set()
    dupes, problems = [], []
    word_counts: dict[str, list[int]] = {k: [] for k in MAX_WORDS}

    for tag, user, assistant in EXAMPLES:
        key = normalize(user)
        if key in existing_users or key in batch_users:
            dupes.append(user)
        batch_users.add(key)
        if tag not in {"NONE", "LOW", "MODERATE", "HIGH", "CRISIS"}:
            problems.append(f"bad tag {tag!r}: {user[:50]}")

        system = prompt_for(tag, prompts, seen)
        rows.append(
            {
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": assistant},
                ]
            }
        )

        langs[language(user)] += 1
        tags[tag] += 1

        words = len(assistant.split())
        word_counts[tag].append(words)

        limit = MAX_WORDS[tag]
        if re.search(r"1553|hotline|911|In Touch", assistant, re.I):
            limit = max(limit, SAFETY_MAX_WORDS)
        if words > limit:
            problems.append(f"{words} words (cap {limit}) [{tag}]: {user[:40]}")

        sentences = [s for s in re.split(r"(?<=[.!?])\s+", assistant.strip()) if s]
        if len(sentences) > 4:
            problems.append(f"{len(sentences)} sentences: {user[:40]}")
        if assistant.count("?") > 1:
            problems.append(f"{assistant.count('?')} questions: {user[:40]}")

        if tag == "CRISIS":
            if "1553" not in assistant or "911" not in assistant:
                problems.append(f"crisis reply missing hotline/911: {user[:40]}")

    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / f"batch{batch}.jsonl"
    with out.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"wrote {len(rows)} examples -> {out}")
    print("severity:", dict(tags))
    print("language (approx):", dict(langs))
    print("duplicate user messages:", len(dupes))
    for d in dupes[:5]:
        print("  dup:", d[:70])
    for tag, counts in word_counts.items():
        if counts:
            print(
                f"  reply words [{tag:<8}] mean {sum(counts)/len(counts):.1f} "
                f"max {max(counts)}"
            )
    if problems:
        print("style problems:")
        for p in problems:
            print("  -", p)
    else:
        print("style checks: OK (length caps, <=4 sentences, <=1 question)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
