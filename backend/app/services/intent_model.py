"""
intent_model.py
---------------
Trains and loads a scikit-learn text classifier for mental health intent detection.
Labels: anxiety, sadness, stress, neutral, suicidal

Usage:
    python -m app.services.intent_model        # train and evaluate
    python -m app.services.intent_model compare # run class weight comparison
"""

import pickle
import random
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

MODEL_PATH = Path(__file__).parent / "intent_classifier.pkl"

# ─────────────────────────────────────────────
# Augmentation
# ─────────────────────────────────────────────
REPLACEMENTS = {
    "kabado": ["kinakabahan", "nervous"],
    "malungkot": ["down", "sad"],
    "pagod": ["drained", "exhausted"],
    "stress": ["pressure", "overwhelmed"],
    "wala": ["none", "nothing"],
    "gusto": ["want", "feel like"],
    "takot": ["scared", "afraid"],
    "kaba": ["nervousness", "anxiety"],
    "lungkot": ["sadness", "sorrow"],
    "grabe": ["sobrang", "intense"],
    "drained": ["exhausted", "burnt out"],
    "overwhelmed": ["overloaded", "swamped"],
}

def augment_text(text: str) -> str:
    words = text.split()
    new_words = []
    for w in words:
        if w.lower() in REPLACEMENTS and random.random() > 0.4:
            new_words.append(random.choice(REPLACEMENTS[w.lower()]))
        else:
            new_words.append(w)
    return " ".join(new_words)

def augment_dataset(data, augments_per_sample=2):
    augmented = list(data)
    for text, label in data:
        for _ in range(augments_per_sample):
            new_text = augment_text(text)
            if new_text != text:
                augmented.append((new_text, label))
    return augmented


# ─────────────────────────────────────────────
# Training Data (~80 per label before augmentation)
# ─────────────────────────────────────────────
TRAINING_DATA = [
    # ANXIETY
    ("I feel so anxious about my exams", "anxiety"),
    ("I keep overthinking everything", "anxiety"),
    ("My heart is racing and I can't calm down", "anxiety"),
    ("I'm nervous about my presentation tomorrow", "anxiety"),
    ("I feel restless and can't stop worrying", "anxiety"),
    ("Kinakabahan ako sa susunod na klase", "anxiety"),
    ("Natatakot ako sa mga tao", "anxiety"),
    ("Hindi ako makatulog sa pagaalala", "anxiety"),
    ("I had a panic attack earlier", "anxiety"),
    ("I feel uneasy all the time", "anxiety"),
    ("Balisa na balisa na ako", "anxiety"),
    ("Natataranta na ako", "anxiety"),
    ("I can't focus because I keep worrying", "anxiety"),
    ("Everything makes me feel scared", "anxiety"),
    ("I'm always on edge", "anxiety"),
    ("I feel overwhelmed with anxiety", "anxiety"),
    ("My anxiety is getting worse", "anxiety"),
    ("I overthink every small thing", "anxiety"),
    ("I'm scared of failing my subjects", "anxiety"),
    ("Lagi akong natatakot na mangyari ang masama", "anxiety"),
    ("Hindi ako makatulog sa daming iniisip", "anxiety"),
    ("Parang lagi akong nag aalala", "anxiety"),
    ("I feel like something bad is about to happen", "anxiety"),
    ("My hands are shaking from nervousness", "anxiety"),
    ("I freeze whenever I have to speak in class", "anxiety"),
    ("Kabado ako palagi", "anxiety"),
    ("I constantly worry about what others think of me", "anxiety"),
    ("I feel tense and anxious every morning", "anxiety"),
    ("Nakakapraning yung feeling", "anxiety"),
    ("I feel panicky for no reason", "anxiety"),
    ("My mind won't stop racing", "anxiety"),
    ("Natatakot ako pumunta sa school", "anxiety"),
    ("I feel sick with worry", "anxiety"),
    ("I am terrified of making mistakes", "anxiety"),
    ("I feel a tight chest whenever I think about it", "anxiety"),
    ("Parang may masamang mangyayari", "anxiety"),
    ("I dread going to class every day", "anxiety"),
    ("Anxiety attacks are happening more often", "anxiety"),
    ("Nahihirapan akong huminga pag nag aalala ako", "anxiety"),
    ("Grabe yung kaba ko today", "anxiety"),
    ("Hindi ako mapakali sa kaiisip", "anxiety"),
    ("Parang may mali pero di ko alam kung ano", "anxiety"),
    ("I feel tense the whole day", "anxiety"),
    ("Kinakabahan ako kahit walang dahilan", "anxiety"),
    ("Nagpapanic ako pag maraming tao", "anxiety"),
    ("My chest feels tight when I think about school", "anxiety"),
    ("Overthink malala before matulog", "anxiety"),
    ("I keep expecting the worst", "anxiety"),
    ("Takot ako mapahiya", "anxiety"),
    ("Hindi ako makahinga pag kinakabahan", "anxiety"),
    ("I get anxious talking to people", "anxiety"),
    ("Parang lagi akong may kaba sa dibdib", "anxiety"),
    ("I feel nervous kahit maliit na bagay", "anxiety"),
    ("Ayoko mag recitation kasi nanginginig ako", "anxiety"),
    ("I feel paralyzed by fear", "anxiety"),
    ("Nahihiya ako palagi kaya hindi ako nagsasalita", "anxiety"),
    ("I worry that people are judging me", "anxiety"),
    ("Parang may nagbabantay sakin palagi", "anxiety"),
    ("I feel anxious even when I'm at home", "anxiety"),
    ("Pag nag iisip ako ng future, kinakabahan ako", "anxiety"),
    ("Grabe yung kaba ko ngayon", "anxiety"),
    ("Grabe ang kaba ko sa exam", "anxiety"),
    ("Grabe ang nerbyos ko", "anxiety"),
    ("Grabe yung takot ko", "anxiety"),
    ("Kinakabahan ako grabe", "anxiety"),
    ("Bigla akong kinakabahan kahit okay naman", "anxiety"),
    ("I feel uneasy pag may sudden changes", "anxiety"),
    ("Nagpapanic ako pag may exam announcement", "anxiety"),
    ("I get anxious when people judge me", "anxiety"),
    ("Di ako mapakali pag may deadline", "anxiety"),
    ("My thoughts won't stop racing", "anxiety"),
    ("Kinakabahan ako sa future ko", "anxiety"),
    ("I feel tense kahit simple task lang", "anxiety"),
    ("Parang may danger kahit wala naman", "anxiety"),
    ("I worry about small mistakes", "anxiety"),
    ("Hindi ako makapag concentrate sa kaba", "anxiety"),
    ("I feel restless at night", "anxiety"),
    ("Takot ako mag disappoint ng iba", "anxiety"),
    ("I keep checking things dahil nag aalala", "anxiety"),
    ("Nag aalala ako sa sasabihin ng tao", "anxiety"),
    ("Kabado ako pag may bagong environment", "anxiety"),
    ("Hindi ako mapanatag", "anxiety"),

    # SADNESS
    ("I feel so sad and empty", "sadness"),
    ("Nobody cares about me", "sadness"),
    ("I've been crying a lot lately", "sadness"),
    ("I feel hopeless about everything", "sadness"),
    ("Malungkot na malungkot ako ngayon", "sadness"),
    ("Wala na akong gana sa buhay", "sadness"),
    ("I feel worthless", "sadness"),
    ("Everything feels pointless", "sadness"),
    ("I don't see the point anymore", "sadness"),
    ("I feel so alone", "sadness"),
    ("Di ko na kaya ang lahat", "sadness"),
    ("Parang wala akong halaga", "sadness"),
    ("I keep crying for no reason", "sadness"),
    ("I feel deeply depressed", "sadness"),
    ("Lungkot na lungkot ako", "sadness"),
    ("I lost interest in things I used to enjoy", "sadness"),
    ("I feel like a burden to everyone", "sadness"),
    ("Nobody understands how I feel", "sadness"),
    ("I feel completely broken inside", "sadness"),
    ("Ayoko na umalis sa kwarto ko", "sadness"),
    ("I have no motivation to do anything", "sadness"),
    ("Feeling empty and hollow inside", "sadness"),
    ("I cry myself to sleep every night", "sadness"),
    ("Parang walang point ng lahat", "sadness"),
    ("I feel invisible to everyone around me", "sadness"),
    ("Wala akong mapagtanungan", "sadness"),
    ("I miss being happy", "sadness"),
    ("I feel numb most of the time", "sadness"),
    ("Parang hindi ako mahal ng kahit sino", "sadness"),
    ("I don't enjoy anything anymore", "sadness"),
    ("I feel like crying but I don't know why", "sadness"),
    ("Sobrang lungkot ko ngayon", "sadness"),
    ("I feel disconnected from everyone", "sadness"),
    ("I have been feeling down for weeks", "sadness"),
    ("Parang ang bigat ng pakiramdam ko", "sadness"),
    ("Wala akong gana kumain", "sadness"),
    ("Nakakatulala lang ako buong araw", "sadness"),
    ("I feel unloved", "sadness"),
    ("Pakiramdam ko wala akong kwenta", "sadness"),
    ("Di ko na alam ano purpose ko", "sadness"),
    ("Hindi na ako masaya kahit dati kong hobbies", "sadness"),
    ("Parang ang dilim ng lahat", "sadness"),
    ("I feel emotionally numb", "sadness"),
    ("Gusto ko lang umiyak lagi", "sadness"),
    ("I feel left out", "sadness"),
    ("Walang nakakaintindi sakin", "sadness"),
    ("I feel hopeless about my future", "sadness"),
    ("I feel sad even when good things happen", "sadness"),
    ("Hindi ko na alam kung para saan pa ako", "sadness"),
    ("I feel like giving up on everything", "sadness"),
    ("Parang lahat ay walang saysay", "sadness"),
    ("Wala na akong masaya", "sadness"),
    ("I wake up sad every single day", "sadness"),
    ("Parang hindi na ako yung dati", "sadness"),
    ("I feel broken and unfixable", "sadness"),
    ("Minsan gusto ko lang maiyak ng walang tigil", "sadness"),
    ("I am tired of feeling this way", "sadness"),
    ("Parang paulit ulit lang ang lungkot", "sadness"),
    ("Pakiramdam ko ako lang nag iisa sa mundo", "sadness"),
    ("Wala akong masiyahang sandali", "sadness"),
    ("Lagi akong naiiyak", "sadness"),
    ("Parang puso ko ay sira", "sadness"),
    ("Ang hirap maging masaya", "sadness"),
    ("Hindi ko maalala kung kailan ako huling natuwa", "sadness"),
    ("Parang walang nagtitingin sakin", "sadness"),
    ("Lagi akong malungkot kahit walang dahilan", "sadness"),
    ("Pakiramdam ko walang may pakialam", "sadness"),
    ("I feel empty and tired", "sadness"),
    ("Parang wala akong direction", "sadness"),
    ("I feel abandoned", "sadness"),
    ("Di ko mahanap yung motivation ko", "sadness"),
    ("Wala akong gana makipag kita", "sadness"),
    ("I feel like I lost myself", "sadness"),
    ("Parang walang nagbabago", "sadness"),
    ("I feel unwanted by everyone", "sadness"),
    ("Nakakapagod umiyak gabi gabi", "sadness"),
    ("Hindi ko na makita yung hope", "sadness"),
    ("I feel emotionally drained and sad", "sadness"),
    ("Parang ako lang mag isa palagi", "sadness"),
    ("I feel ignored", "sadness"),
    ("Hindi ko alam paano maging okay ulit", "sadness"),
    ("I feel down the whole week", "sadness"),
    ("Wala na akong excitement sa kahit ano", "sadness"),
    ("Parang ang lungkot kahit may kasama", "sadness"),
    ("I feel broken and tired", "sadness"),

    # STRESS
    ("I have so many deadlines and I can't cope", "stress"),
    ("I'm so stressed with school", "stress"),
    ("The pressure is too much", "stress"),
    ("I feel burned out", "stress"),
    ("Pagod na pagod na ako", "stress"),
    ("Naiistress ako sa daming trabaho", "stress"),
    ("I can't handle all my requirements", "stress"),
    ("I'm exhausted from everything", "stress"),
    ("Too much work and too little time", "stress"),
    ("Nakakapagod na ang lahat", "stress"),
    ("I feel drained every single day", "stress"),
    ("My workload is killing me", "stress"),
    ("I haven't slept properly in days", "stress"),
    ("Pagod na ko sa lahat ng ito", "stress"),
    ("I'm stretched too thin", "stress"),
    ("So many requirements I don't know where to start", "stress"),
    ("The stress is becoming unbearable", "stress"),
    ("I feel like I'm drowning in tasks", "stress"),
    ("Ubos na ang energy ko", "stress"),
    ("Hindi ko na kaya ang pressure", "stress"),
    ("I have back to back exams this week", "stress"),
    ("My professor keeps adding more work", "stress"),
    ("I can't finish everything on time", "stress"),
    ("Grabe ang daming requirements ngayong sem", "stress"),
    ("I feel like I never have enough time", "stress"),
    ("Pagod na ako sa school", "stress"),
    ("I'm running on no sleep because of deadlines", "stress"),
    ("The pressure from my parents is too much", "stress"),
    ("I feel mentally and physically exhausted", "stress"),
    ("Too many things happening at once", "stress"),
    ("Nakakapagod mag aral araw araw", "stress"),
    ("I feel like I'm about to break down", "stress"),
    ("My schedule is overwhelming", "stress"),
    ("Palagi akong kulang sa tulog dahil sa assignments", "stress"),
    ("I can't keep up with everything anymore", "stress"),
    ("Daming trabaho wala pa akong magawa", "stress"),
    ("I feel like I have no time for myself", "stress"),
    ("The academic pressure is suffocating", "stress"),
    ("Grabe ang stress ko sa thesis", "stress"),
    ("Sabog na utak ko sa dami ng tasks", "stress"),
    ("Sunod sunod yung deadlines", "stress"),
    ("I have too many responsibilities", "stress"),
    ("Pagod na ako mentally", "stress"),
    ("Pressure sa family at school", "stress"),
    ("Di ko na ma manage time ko", "stress"),
    ("Nakaka overwhelm yung requirements", "stress"),
    ("Wala na akong pahinga", "stress"),
    ("I feel overloaded", "stress"),
    ("Grabe yung academic pressure", "stress"),
    ("Burnout na ako sa acads", "stress"),
    ("Di ko matapos tapos yung trabaho", "stress"),
    ("Sobrang dami kong iniintindi", "stress"),
    ("I feel pressured to succeed", "stress"),
    ("Pagod na pagod na utak ko", "stress"),
    ("I feel like I cannot breathe because of stress", "stress"),
    ("Wala akong time para sa sarili ko", "stress"),
    ("Lagi akong kulang sa tulog", "stress"),
    ("Everything is piling up and I can't handle it", "stress"),
    ("Grabe ang daming ginagawa ko", "stress"),
    ("I feel like a machine with no rest", "stress"),
    ("Sobrang busy ko hindi na ako makahinga", "stress"),
    ("I feel overwhelmed sa responsibilities", "stress"),
    ("Sunod sunod yung tasks ko today", "stress"),
    ("Wala akong break sa schedule", "stress"),
    ("I feel pressure sa grades ko", "stress"),
    ("Andaming expectations sakin", "stress"),
    ("Hindi ko ma manage workload ko", "stress"),
    ("I feel drained from productivity", "stress"),
    ("Nakaka stress yung financial problems", "stress"),
    ("Di ko alam paano hahatiin oras ko", "stress"),
    ("Parang sabay sabay lahat ng problema", "stress"),
    ("I feel burned out sa trabaho", "stress"),
    ("Wala na akong time matulog", "stress"),
    ("Nakaka pagod yung responsibilities sa bahay", "stress"),
    ("I feel pressured to perform well", "stress"),
    ("Andami kong commitments", "stress"),
    ("Hindi ko matapos yung to do list ko", "stress"),
    ("I feel squeezed by deadlines", "stress"),
    ("Pagod na ako sa routine na to", "stress"),
    ("Nakaka overwhelm yung expectations ng iba", "stress"),

    # NEUTRAL
    ("Hello, how are you?", "neutral"),
    ("What can you do?", "neutral"),
    ("I just wanted to talk", "neutral"),
    ("Good morning", "neutral"),
    ("Can you help me?", "neutral"),
    ("I am okay today", "neutral"),
    ("Just checking in", "neutral"),
    ("Hi there", "neutral"),
    ("I feel fine", "neutral"),
    ("Nothing special today", "neutral"),
    ("Kumusta ka?", "neutral"),
    ("Okay lang ako", "neutral"),
    ("Magandang umaga", "neutral"),
    ("What is this app for?", "neutral"),
    ("I need some information", "neutral"),
    ("Tell me about yourself", "neutral"),
    ("I'm doing alright", "neutral"),
    ("Everything is normal", "neutral"),
    ("Just wanted to say hi", "neutral"),
    ("I don't have any problems right now", "neutral"),
    ("Can we talk?", "neutral"),
    ("I want to learn more about this app", "neutral"),
    ("Is anyone there?", "neutral"),
    ("I had a normal day today", "neutral"),
    ("Things are going well for me", "neutral"),
    ("Wala lang akong gustong sabihin", "neutral"),
    ("Just browsing", "neutral"),
    ("I feel pretty good today", "neutral"),
    ("Nothing is bothering me", "neutral"),
    ("I'm just here to explore", "neutral"),
    ("Good afternoon", "neutral"),
    ("I wanted to check this out", "neutral"),
    ("Ano ba ito?", "neutral"),
    ("I'm not sure what to say", "neutral"),
    ("Everything is fine with me", "neutral"),
    ("I had a productive day", "neutral"),
    ("I feel calm and relaxed", "neutral"),
    ("Walang problema ngayon", "neutral"),
    ("I just want to chat", "neutral"),
    ("I'm curious about this system", "neutral"),
    ("Pwede ba magtanong?", "neutral"),
    ("Testing lang ito", "neutral"),
    ("Ano ginagawa mo?", "neutral"),
    ("Gusto ko lang mag chat", "neutral"),
    ("Nag browse lang ako", "neutral"),
    ("Okay naman araw ko", "neutral"),
    ("May tanong lang ako tungkol sa app", "neutral"),
    ("Normal day lang", "neutral"),
    ("Hi kumusta ka today?", "neutral"),
    ("Wala lang, bored lang ako", "neutral"),
    ("I had a great lunch today", "neutral"),
    ("Just passing time", "neutral"),
    ("I am here to try this out", "neutral"),
    ("I feel okay for now", "neutral"),
    ("Nothing much is happening", "neutral"),
    ("I am fine thank you", "neutral"),
    ("Maayos naman ako", "neutral"),
    ("I want to know more about GAIDA", "neutral"),
    ("This is interesting", "neutral"),
    ("Nag try lang ako dito", "neutral"),
    ("Okay naman mood ko today", "neutral"),
    ("May gusto lang ako itanong sa system", "neutral"),
    ("Testing message lang", "neutral"),
    ("Normal lang araw ko", "neutral"),
    ("Okay lang ako ngayon", "neutral"),
    ("Nag check in lang ako", "neutral"),
    ("Wala naman problema", "neutral"),
    ("May random thought lang ako", "neutral"),
    ("Pwede ba mag ask?", "neutral"),
    ("Curious ako sa features", "neutral"),
    ("Okay naman lahat sa school", "neutral"),
    ("Gusto ko lang mag type dito", "neutral"),
    ("Hi good afternoon", "neutral"),
    ("Checking lang kung active ka", "neutral"),
    ("Nothing serious today", "neutral"),
    ("May small question ako", "neutral"),
    ("Gusto ko lang mag explore", "neutral"),
    ("Okay ang pakiramdam ko", "neutral"),

    # SUICIDAL
    ("I want to end my life", "suicidal"),
    ("I don't want to live anymore", "suicidal"),
    ("I'm thinking about killing myself", "suicidal"),
    ("Gusto ko na mamatay", "suicidal"),
    ("Ayoko na mabuhay", "suicidal"),
    ("Magpapakamatay na ako", "suicidal"),
    ("I have no reason to live", "suicidal"),
    ("Wala na akong dahilan para mabuhay", "suicidal"),
    ("I want to disappear forever", "suicidal"),
    ("Nobody would miss me if I was gone", "suicidal"),
    ("I've been thinking about suicide", "suicidal"),
    ("Tapusin ko na ang lahat", "suicidal"),
    ("I can't take it anymore and want to die", "suicidal"),
    ("Life is not worth living", "suicidal"),
    ("I want to hurt myself", "suicidal"),
    ("Gusto ko na mawala sa mundo", "suicidal"),
    ("Hindi na ako dapat mabuhay", "suicidal"),
    ("Mas mabuti pa kung wala na ako", "suicidal"),
    ("I've already thought of how to do it", "suicidal"),
    ("I don't want to exist anymore", "suicidal"),
    ("Tapusin ko na ang buhay ko", "suicidal"),
    ("I feel like everyone would be better without me", "suicidal"),
    ("I have nothing left to live for", "suicidal"),
    ("Ayoko na talagang mabuhay", "suicidal"),
    ("I just want to stop existing", "suicidal"),
    ("I think about death every day", "suicidal"),
    ("Mas madali kung wala na lang ako", "suicidal"),
    ("I feel like dying is the only way out", "suicidal"),
    ("I wrote a goodbye letter", "suicidal"),
    ("I gave away my things already", "suicidal"),
    ("Wala na kong dahilan para magpatuloy", "suicidal"),
    ("I am ready to die", "suicidal"),
    ("I keep imagining my own funeral", "suicidal"),
    ("Hindi ko na gusto pang gumising bukas", "suicidal"),
    ("I feel like the world is better without me", "suicidal"),
    ("Sana hindi na ako nagising", "suicidal"),
    ("I have been saying my goodbyes", "suicidal"),
    ("Pagod na ako mabuhay", "suicidal"),
    ("Mas okay siguro kung wala na ako", "suicidal"),
    ("Ayoko na sa mundo", "suicidal"),
    ("I wish I was never born", "suicidal"),
    ("Gusto ko na lang mawala", "suicidal"),
    ("Parang gusto ko na tapusin lahat", "suicidal"),
    ("I feel like ending everything", "suicidal"),
    ("Hindi ko na kaya mabuhay ng ganito", "suicidal"),
    ("Kung mawala ako, okay lang", "suicidal"),
    ("Gusto ko na saktan sarili ko", "suicidal"),
    ("Iniisip ko minsan na tapusin na", "suicidal"),
    ("Sana kunin na ako ni Lord", "suicidal"),
    ("Ayoko na magising bukas", "suicidal"),
    ("I don't think I deserve to live", "suicidal"),
    ("I feel like I am a burden and should disappear", "suicidal"),
    ("Wala na kong pakialam kung mabuhay pa ako", "suicidal"),
    ("I have been planning my exit", "suicidal"),
    ("Lagi kong iniisip na wala na lang ako", "suicidal"),
    ("I feel trapped and the only way out is death", "suicidal"),
    ("Hindi na ako makakita ng dahilan para magpatuloy", "suicidal"),
    ("I want this pain to end permanently", "suicidal"),
    ("Mas maayos pa ang lahat kung wala na ako", "suicidal"),
    ("I keep thinking about not waking up tomorrow", "suicidal"),
    ("Sana mawala na lahat ng sakit permanently", "suicidal"),
    ("Pagod na ako lumaban", "suicidal"),
    ("I don't want to continue living like this", "suicidal"),
    ("Mas tahimik siguro kung wala ako", "suicidal"),
    ("Parang gusto ko na mag give up sa life", "suicidal"),
    ("I feel like ending my existence", "suicidal"),
    ("Wala na akong nakikitang future", "suicidal"),
    ("I don't see any reason to stay alive", "suicidal"),
    ("Pakiramdam ko pabigat lang ako", "suicidal"),
    ("Ayoko na magising pa", "suicidal"),
    ("I feel like hurting myself", "suicidal"),
    ("Kung pwede lang mawala na ako", "suicidal"),
    ("Gusto ko na sumuko sa buhay", "suicidal"),
    ("I am thinking of ending everything", "suicidal"),
    ("Parang wala nang saysay mabuhay", "suicidal"),
    ("Sana di na lang ako ipinanganak", "suicidal"),
    ("Pagod na ako sa existence ko", "suicidal"),
    ("I want everything to stop permanently", "suicidal"),

    # Romantic anxiety — add inside TRAINING_DATA under # ANXIETY section
    ("I keep overthinking about a girl I like", "anxiety"),
    ("I replay conversations with my crush", "anxiety"),
    ("I get nervous around someone I have feelings for", "anxiety"),
    ("Hindi ko alam kung nagugustuhan niya ako", "anxiety"),
    ("I overanalyze everything she does", "anxiety"),
    ("I feel anxious around someone I like", "anxiety"),
    ("I don't know if she likes me back and it's stressing me out", "anxiety"),
    ("Kinakabahan ako tuwing kasama ko siya", "anxiety"),
    ("I'm scared to confess my feelings", "anxiety"),
    ("I overthink every text message I send her", "anxiety"),
    ("Parang nag aalala ako sa kung ano nararamdaman niya", "anxiety"),
    ("I get anxious waiting for her reply", "anxiety"),
    ("I'm reading too much into small things she does", "anxiety"),
    ("I keep imagining scenarios in my head about us", "anxiety"),
    ("I feel confused and excited and scared at the same time about someone", "anxiety"),
    ("Hindi ko matigilan mag isip sa kanya", "anxiety"),
    ("I freeze when she talks to me", "anxiety"),
    ("I don't know if she's just being friendly or something more", "anxiety"),
    ("Overthinking kung ano ibig sabihin ng ginawa niya", "anxiety"),
    ("I feel restless not knowing if she likes me", "anxiety"),
]


def build_pipeline(balanced=True):
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=8000,
            sublinear_tf=True,
            analyzer="word",
            token_pattern=r"\b\w+\b",
            min_df=1,
        )),
        ("clf", LogisticRegression(
            max_iter=1000,
            C=5.0,
            class_weight="balanced" if balanced else None,
            solver="lbfgs",
        )),
    ])


def train_model():
    texts = [t for t, _ in TRAINING_DATA]
    labels = [l for _, l in TRAINING_DATA]

    # Augment training data
    augmented = augment_dataset(list(zip(texts, labels)), augments_per_sample=2)
    aug_texts = [t for t, _ in augmented]
    aug_labels = [l for _, l in augmented]

    X_train, X_test, y_train, y_test = train_test_split(
        aug_texts, aug_labels, test_size=0.15, random_state=42, stratify=aug_labels
    )

    pipeline = build_pipeline(balanced=True)
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    print("=== Intent Classifier Evaluation ===")
    print(classification_report(y_test, y_pred))

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(pipeline, f)

    print(f"Model saved to {MODEL_PATH}")
    return pipeline


def compare_class_weights():
    """Run Experiment A vs B comparison."""
    texts = [t for t, _ in TRAINING_DATA]
    labels = [l for _, l in TRAINING_DATA]

    augmented = augment_dataset(list(zip(texts, labels)), augments_per_sample=2)
    aug_texts = [t for t, _ in augmented]
    aug_labels = [l for _, l in augmented]

    X_train, X_test, y_train, y_test = train_test_split(
        aug_texts, aug_labels, test_size=0.15, random_state=42, stratify=aug_labels
    )

    print("=== EXPERIMENT A: WITHOUT class_weight balancing ===")
    pipe_a = build_pipeline(balanced=False)
    pipe_a.fit(X_train, y_train)
    pred_a = pipe_a.predict(X_test)
    print(classification_report(y_test, pred_a))

    print("=== EXPERIMENT B: WITH class_weight='balanced' ===")
    pipe_b = build_pipeline(balanced=True)
    pipe_b.fit(X_train, y_train)
    pred_b = pipe_b.predict(X_test)
    print(classification_report(y_test, pred_b))


def load_model():
    if not MODEL_PATH.exists():
        print("No saved model found. Training now...")
        return train_model()
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


_model = None

def _get_model():
    global _model
    if _model is None:
        _model = load_model()
    return _model


def predict_intent(text: str) -> dict:
    if not text or not text.strip():
        return {"intent": "neutral", "confidence": 0.5}

    model = _get_model()
    prediction = model.predict([text])[0]
    probabilities = model.predict_proba([text])[0]
    classes = model.classes_
    confidence = float(max(probabilities))

    return {
        "intent": prediction,
        "confidence": round(confidence, 3),
        "all_scores": {
            cls: round(float(prob), 3)
            for cls, prob in zip(classes, probabilities)
        }
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "compare":
        compare_class_weights()
    else:
        train_model()
        test_inputs = [
            "I feel so anxious about everything",
            "Malungkot na malungkot ako",
            "Pagod na pagod na ako sa deadlines",
            "Gusto ko na mamatay",
            "Good morning, I feel fine today",
            "Sana di na lang ako nagising",
            "Grabe yung kaba ko today",
            "Burnout na ako sa acads",
            "Parang ang bigat ng pakiramdam ko",
            "Wala lang, bored lang ako",
            "Pagod na ako mabuhay",
            "Sobrang busy ko hindi na ako makahinga",
            "Pakiramdam ko walang may pakialam",
            "Hindi ako mapanatag",
        ]
        print("\n=== Sample Predictions ===")
        for text in test_inputs:
            result = predict_intent(text)
            print(f"Input:  {text}")
            print(f"Intent: {result['intent']} ({result['confidence']})")
            print()